"""
Tampilan Riwayat & Pencarian Transaksi Pegadaian Digital Nusantara
Menyediakan filter multi-kriteria (jenis transaksi, metode, status berhasil/gagal, rentang tanggal, kata kunci).
"""

import tkinter as tk
from tkinter import ttk
from decimal import Decimal
from typing import Optional, Dict, Any, List

from pawn.ui.theme import (
    BG_CARD, BG_CARD_ALT, BG_MAIN, BORDER_COLOR, PRIMARY, PRIMARY_DARK,
    SECONDARY, DANGER, SUCCESS, INFO, TEXT_MAIN, TEXT_SECONDARY, TEXT_MUTED, TEXT_WHITE,
    FONT_TITLE, FONT_HEADER, FONT_SECTION, FONT_BODY, FONT_BODY_BOLD,
    FONT_LABEL, FONT_SMALL, FONT_SMALL_BOLD,
    format_rupiah, format_date
)
from pawn.ui.widgets import Card, DataTable


class TransaksiView(tk.Frame):
    """Layar Audit dan Riwayat Transaksi Finansial Kas."""
    def __init__(self, parent, facade, **kwargs):
        super().__init__(parent, bg=BG_MAIN, padx=24, pady=20, **kwargs)
        self.facade = facade
        self._build_ui()
        self.refresh_data()

    def _build_ui(self):
        # 1. Header
        header = tk.Frame(self, bg=BG_MAIN)
        header.pack(fill="x", pady=(0, 16))

        tk.Label(header, text="📜 RIWAYAT & AUDIT BUKU TRANSAKSI", font=FONT_HEADER,
                 fg=TEXT_MAIN, bg=BG_MAIN).pack(anchor="w")
        tk.Label(header, text="Pencarian mendalam buku transaksi kas: pencairan gadai, pembayaran angsuran, pelunasan, dan perpanjangan",
                 font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_MAIN).pack(anchor="w", pady=(2, 0))

        # 2. Filter Bar Card
        filter_card = Card(self, padx=18, pady=14)
        filter_card.pack(fill="x", pady=(0, 16))

        row1 = tk.Frame(filter_card.inner, bg=BG_CARD)
        row1.pack(fill="x", pady=(0, 10))

        tk.Label(row1, text="Cari (No. TRX / Kontrak):", font=FONT_LABEL, fg=TEXT_MAIN, bg=BG_CARD).pack(side="left", padx=(0, 6))
        self.ent_cari = ttk.Entry(row1, width=22)
        self.ent_cari.pack(side="left", padx=(0, 14))
        self.ent_cari.bind("<Return>", lambda e: self.refresh_data())

        tk.Label(row1, text="Jenis Transaksi:", font=FONT_LABEL, fg=TEXT_MAIN, bg=BG_CARD).pack(side="left", padx=(0, 6))
        self.combo_jenis = ttk.Combobox(
            row1, state="readonly", width=16,
            values=["SEMUA", "GADAI", "ANGSURAN", "PELUNASAN", "PERPANJANGAN"]
        )
        self.combo_jenis.set("SEMUA")
        self.combo_jenis.pack(side="left", padx=(0, 14))

        tk.Label(row1, text="Status:", font=FONT_LABEL, fg=TEXT_MAIN, bg=BG_CARD).pack(side="left", padx=(0, 6))
        self.combo_status = ttk.Combobox(
            row1, state="readonly", width=14,
            values=["SEMUA", "BERHASIL", "GAGAL"]
        )
        self.combo_status.set("SEMUA")
        self.combo_status.pack(side="left")

        # Baris 2: Rentang Tanggal & Tombol
        row2 = tk.Frame(filter_card.inner, bg=BG_CARD)
        row2.pack(fill="x")

        tk.Label(row2, text="Dari Tanggal (YYYY-MM-DD):", font=FONT_LABEL, fg=TEXT_MAIN, bg=BG_CARD).pack(side="left", padx=(0, 6))
        self.ent_dari = ttk.Entry(row2, width=14)
        self.ent_dari.pack(side="left", padx=(0, 12))

        tk.Label(row2, text="Sampai:", font=FONT_LABEL, fg=TEXT_MAIN, bg=BG_CARD).pack(side="left", padx=(0, 6))
        self.ent_sampai = ttk.Entry(row2, width=14)
        self.ent_sampai.pack(side="left", padx=(0, 16))

        ttk.Button(row2, text="🔍 Terapkan Filter", style="Primary.TButton",
                   command=self.refresh_data).pack(side="left", padx=(0, 8))

        ttk.Button(row2, text="Reset", style="Secondary.TButton",
                   command=self._reset_filter).pack(side="left")

        # 3. Tabel Riwayat Transaksi Card
        table_card = Card(self, padx=16, pady=16)
        table_card.pack(fill="both", expand=True, pady=(0, 14))

        cols = [
            ("no_transaksi", "No. Transaksi", 170, "w"),
            ("waktu", "Waktu Transaksi", 140, "center"),
            ("no_kontrak", "No. Kontrak", 140, "w"),
            ("jenis", "Jenis", 110, "center"),
            ("jumlah", "Nominal (Rp)", 130, "e"),
            ("metode", "Metode", 90, "center"),
            ("status", "Status", 95, "center"),
            ("keterangan", "Uraian / Keterangan", 200, "w"),
        ]

        self.table = DataTable(table_card.inner, columns=cols, stretch_col="keterangan")
        self.table.pack(fill="both", expand=True)

        # 4. Ringkasan Footer Card (Soft Border)
        footer_wrap = tk.Frame(self, bg=BORDER_COLOR, padx=1, pady=1, highlightthickness=0, bd=0)
        footer_wrap.pack(fill="x")
        self.footer = tk.Frame(footer_wrap, bg=BG_CARD, padx=18, pady=12, highlightthickness=0, bd=0)
        self.footer.pack(fill="both", expand=True)

        self.lbl_summary_count = tk.Label(self.footer, text="Ditemukan: 0 transaksi",
                                          font=FONT_LABEL, fg=TEXT_MAIN, bg=BG_CARD)
        self.lbl_summary_count.pack(side="left")

        self.lbl_summary_total = tk.Label(self.footer, text="Total Transaksi Berhasil: Rp 0",
                                          font=FONT_HEADER, fg=PRIMARY_DARK, bg=BG_CARD)
        self.lbl_summary_total.pack(side="right")

    def _reset_filter(self):
        self.ent_cari.delete(0, tk.END)
        self.combo_jenis.set("SEMUA")
        self.combo_status.set("SEMUA")
        self.ent_dari.delete(0, tk.END)
        self.ent_sampai.delete(0, tk.END)
        self.refresh_data()

    def refresh_data(self):
        """Memuat daftar transaksi sesuai parameter pencarian."""
        try:
            filters = {}
            cari = self.ent_cari.get().strip()
            if cari:
                filters["cari"] = cari

            jenis = self.combo_jenis.get()
            if jenis != "SEMUA":
                filters["jenis"] = jenis

            status = self.combo_status.get()
            if status != "SEMUA":
                filters["status"] = status

            dari = self.ent_dari.get().strip()
            if dari:
                filters["dari"] = dari

            sampai = self.ent_sampai.get().strip()
            if sampai:
                filters["sampai"] = sampai

            data = self.facade.daftar_transaksi(filters)

            formatters = {
                "jumlah": lambda v, r: format_rupiah(v),
                "waktu": lambda v, r: format_date(v)
            }
            self.table.set_data(data, formatters=formatters)

            total_nominal = Decimal("0")
            for t in data:
                if str(t.get("status", "")).upper() == "BERHASIL":
                    try:
                        total_nominal += Decimal(str(t.get("jumlah", 0)))
                    except Exception:
                        pass

            self.lbl_summary_count.config(text=f"Ditemukan: {len(data)} transaksi tercatat")
            self.lbl_summary_total.config(text=f"Total Transaksi Berhasil: {format_rupiah(total_nominal)}")

        except Exception:
            pass
