"""
Tampilan Dashboard Utama Pegadaian Digital Nusantara
Menampilkan ringkasan metrik finansial, pintasan operasional cepat, dan daftar pinjaman perhatian.
"""

import tkinter as tk
from tkinter import ttk
from decimal import Decimal
from typing import Callable, Optional

from pawn.ui.theme import (
    BG_CARD, BG_CARD_ALT, BG_MAIN, BORDER_COLOR, PRIMARY, PRIMARY_DARK,
    SECONDARY, DANGER, SUCCESS, INFO, TEXT_MAIN, TEXT_SECONDARY, TEXT_MUTED, TEXT_WHITE,
    FONT_TITLE, FONT_HEADER, FONT_SECTION, FONT_BODY, FONT_BODY_BOLD,
    FONT_LABEL, FONT_SMALL, FONT_SMALL_BOLD,
    format_rupiah, format_date
)
from pawn.ui.widgets import Card, StatCard, DataTable, ScrollableFrame


class DashboardView(tk.Frame):
    """Layar ringkasan dashboard operasional dengan tata letak responsif scrollable."""
    def __init__(self, parent, facade, navigate_to: Callable, **kwargs):
        super().__init__(parent, bg=BG_MAIN, **kwargs)
        self.facade = facade
        self.navigate_to = navigate_to
        
        self._build_ui()
        self.refresh_data()

    def _build_ui(self):
        # Gunakan ScrollableFrame agar tidak terpotong di layar laptop
        scroll = ScrollableFrame(self, bg=BG_MAIN)
        scroll.pack(fill="both", expand=True)

        content = tk.Frame(scroll.scrollable_content, bg=BG_MAIN, padx=24, pady=20)
        content.pack(fill="both", expand=True)

        # 1. Header Sambutan
        header_frame = tk.Frame(content, bg=BG_MAIN)
        header_frame.pack(fill="x", pady=(0, 18))

        user = getattr(self.facade, "pengguna_aktif", None)
        if callable(user):
            user = user()
        user_name = user.get("nama", "Petugas") if user else "Petugas"
        user_role = user.get("role", "STAF") if user else "STAF"
        
        title_box = tk.Frame(header_frame, bg=BG_MAIN)
        title_box.pack(side="left")

        self.lbl_welcome = tk.Label(title_box, text=f"Selamat Datang, {user_name} 👋",
                                    font=FONT_HEADER, fg=TEXT_MAIN, bg=BG_MAIN)
        self.lbl_welcome.pack(anchor="w")

        self.lbl_sub = tk.Label(title_box, text=f"Akses Peran: {user_role} • Ringkasan aktivitas dan operasional gadai terkini",
                                font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_MAIN)
        self.lbl_sub.pack(anchor="w", pady=(2, 0))

        btn_refresh = ttk.Button(header_frame, text="🔄 Segarkan Data", style="Secondary.TButton",
                                 command=self.refresh_data)
        btn_refresh.pack(side="right")

        # 2. Baris Kartu Metrik Ringkasan (StatCards)
        stats_frame = tk.Frame(content, bg=BG_MAIN)
        stats_frame.pack(fill="x", pady=(0, 18))

        self.card_aktif = StatCard(stats_frame, title="Pinjaman Berjalan",
                                   value="Rp 0", subtitle="0 kontrak aktif",
                                   accent_color=PRIMARY)
        self.card_aktif.pack(side="left", fill="both", expand=True, padx=(0, 10))

        self.card_jatuh_tempo = StatCard(stats_frame, title="Jatuh Tempo / Macet",
                                         value="0 Kontrak", subtitle="Perlu penagihan / lelang",
                                         accent_color=DANGER)
        self.card_jatuh_tempo.pack(side="left", fill="both", expand=True, padx=(0, 10))

        self.card_nasabah = StatCard(stats_frame, title="Nasabah Terdaftar",
                                     value="0 Orang", subtitle="Total debitur terdata",
                                     accent_color=INFO)
        self.card_nasabah.pack(side="left", fill="both", expand=True, padx=(0, 10))

        self.card_transaksi = StatCard(stats_frame, title="Total Transaksi",
                                       value="0 Transaksi", subtitle="Aktivitas pembukuan",
                                       accent_color=SECONDARY)
        self.card_transaksi.pack(side="left", fill="both", expand=True)

        # 3. Baris Tombol Aksi Cepat (Quick Shortcuts)
        action_card = Card(content, padx=20, pady=16)
        action_card.pack(fill="x", pady=(0, 18))

        tk.Label(action_card.inner, text="PINTASAN OPERASIONAL CEPAT", font=FONT_LABEL,
                 fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 12))

        btn_box = tk.Frame(action_card.inner, bg=BG_CARD)
        btn_box.pack(fill="x")

        ttk.Button(btn_box, text="📝 Ajukan Gadai", style="Primary.TButton",
                   command=lambda: self.navigate_to("gadai")).pack(side="left", padx=(0, 10))

        ttk.Button(btn_box, text="⚖️ Penaksiran", style="Secondary.TButton",
                   command=lambda: self.navigate_to("penaksiran")).pack(side="left", padx=(0, 10))

        ttk.Button(btn_box, text="💵 Pembayaran", style="Secondary.TButton",
                   command=lambda: self.navigate_to("pinjaman")).pack(side="left", padx=(0, 10))

        ttk.Button(btn_box, text="👥 Nasabah", style="Secondary.TButton",
                   command=lambda: self.navigate_to("nasabah")).pack(side="left", padx=(0, 10))

        ttk.Button(btn_box, text="⏰ Lelang & Jatuh Tempo", style="Secondary.TButton",
                   command=lambda: self.navigate_to("lelang")).pack(side="left")

        # 4. Tabel Perhatian: Pinjaman Jatuh Tempo / Menunggak
        table_card = Card(content, padx=20, pady=16)
        table_card.pack(fill="both", expand=True)

        header_tbl = tk.Frame(table_card.inner, bg=BG_CARD)
        header_tbl.pack(fill="x", pady=(0, 10))

        tk.Label(header_tbl, text="⚠️ PINJAMAN JATUH TEMPO & PERLU PERHATIAN",
                 font=FONT_LABEL, fg=DANGER, bg=BG_CARD).pack(side="left")
        tk.Label(header_tbl, text="(Klik dua kali pada baris untuk membuka detail pinjaman)",
                 font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_CARD).pack(side="left", padx=(8, 0))

        cols = [
            ("no_kontrak", "No. Kontrak", 140, "w"),
            ("nasabah_nama", "Nama Nasabah", 160, "w"),
            ("barang_nama", "Barang Jaminan", 140, "w"),
            ("sisa_pokok", "Sisa Pokok", 120, "e"),
            ("bunga_terutang", "Bunga", 100, "e"),
            ("tgl_jatuh_tempo", "Jatuh Tempo", 130, "center"),
            ("status", "Status", 110, "center"),
        ]

        self.table_perhatian = DataTable(
            table_card.inner,
            columns=cols,
            stretch_col="nasabah_nama",
            show_vsb=False,
            show_hsb=False,
            height=5,
            on_double_click=self._on_row_double_click
        )
        self.table_perhatian.pack(fill="both", expand=True)

    def _on_row_double_click(self, row):
        if row:
            self.navigate_to("pinjaman")

    def refresh_data(self):
        """Memuat ulang semua metrik dari Facade."""
        try:
            # 1. Nasabah count
            daftar_nsb = self.facade.daftar_nasabah("")
            total_nsb = len(daftar_nsb)
            self.card_nasabah.update_value(f"{total_nsb} Orang", "Nasabah terdaftar")

            # 2. Pinjaman
            pinjaman_list = self.facade.daftar_pinjaman()
            total_pokok_aktif = Decimal("0")
            count_aktif = 0
            list_jatuh_tempo = []

            for p in pinjaman_list:
                status = str(p.get("status", "")).upper()
                if status == "AKTIF":
                    count_aktif += 1
                    sisa = p.get("sisa_pokok", 0)
                    try:
                        total_pokok_aktif += Decimal(str(sisa))
                    except Exception:
                        pass
                elif status in ("JATUH_TEMPO", "DALAM_PROSES_LELANG"):
                    list_jatuh_tempo.append(p)

            self.card_aktif.update_value(
                format_rupiah(total_pokok_aktif),
                f"{count_aktif} kontrak aktif"
            )

            self.card_jatuh_tempo.update_value(
                f"{len(list_jatuh_tempo)} Kontrak",
                "Perlu notifikasi lelang" if list_jatuh_tempo else "Semua lancar"
            )

            # 3. Transaksi
            tx_list = self.facade.daftar_transaksi({})
            self.card_transaksi.update_value(
                f"{len(tx_list)} Transaksi",
                "Total riwayat tercatat"
            )

            # Format dan tampilkan di tabel perhatian
            formatters = {
                "sisa_pokok": lambda v, r: format_rupiah(v),
                "bunga_terutang": lambda v, r: format_rupiah(v),
                "tgl_jatuh_tempo": lambda v, r: format_date(v)
            }
            self.table_perhatian.set_data(list_jatuh_tempo, formatters=formatters)

        except Exception:
            pass
