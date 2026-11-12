"""
Tampilan Gudang & Inventaris Jaminan Pegadaian Digital Nusantara
Menyediakan pencarian barang jaminan, pemantauan lokasi rak/brankas, kondisi fisik, dan status penyimpanan.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Dict, Any, List

from pawn.ui.theme import (
    BG_CARD, BG_CARD_ALT, BG_MAIN, BORDER_COLOR, PRIMARY, PRIMARY_DARK,
    SECONDARY, DANGER, SUCCESS, INFO, TEXT_MAIN, TEXT_SECONDARY, TEXT_MUTED, TEXT_WHITE,
    FONT_TITLE, FONT_HEADER, FONT_SECTION, FONT_BODY, FONT_BODY_BOLD,
    FONT_LABEL, FONT_SMALL, FONT_SMALL_BOLD,
    format_date
)
from pawn.ui.widgets import Card, DataTable


class GudangView(tk.Frame):
    """Layar Pemantauan Inventaris Gudang & Brankas Penyimpanan Agunan."""
    def __init__(self, parent, facade, **kwargs):
        super().__init__(parent, bg=BG_MAIN, padx=24, pady=20, **kwargs)
        self.facade = facade
        self._build_ui()
        self.refresh_data()

    def _build_ui(self):
        # 1. Header
        header = tk.Frame(self, bg=BG_MAIN)
        header.pack(fill="x", pady=(0, 16))

        tk.Label(header, text="🏢 LOGISTIK GUDANG & BRANKAS AGUNAN", font=FONT_HEADER,
                 fg=TEXT_MAIN, bg=BG_MAIN).pack(anchor="w")
        tk.Label(header, text="Pelacakan lokasi penyimpanan barang jaminan, kondisi fisik saat serah terima, dan status mutasi barang",
                 font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_MAIN).pack(anchor="w", pady=(2, 0))

        # 2. Filter Bar Card
        filter_card = Card(self, padx=16, pady=12)
        filter_card.pack(fill="x", pady=(0, 16))

        fb = tk.Frame(filter_card.inner, bg=BG_CARD)
        fb.pack(fill="x")

        tk.Label(fb, text="No. Kontrak:", font=FONT_LABEL, fg=TEXT_MAIN, bg=BG_CARD).pack(side="left", padx=(0, 6))
        self.ent_kontrak = ttk.Entry(fb, width=20)
        self.ent_kontrak.pack(side="left", padx=(0, 14))
        self.ent_kontrak.bind("<Return>", lambda e: self.refresh_data())

        tk.Label(fb, text="Kode Barang:", font=FONT_LABEL, fg=TEXT_MAIN, bg=BG_CARD).pack(side="left", padx=(0, 6))
        self.ent_kode_barang = ttk.Entry(fb, width=18)
        self.ent_kode_barang.pack(side="left", padx=(0, 14))
        self.ent_kode_barang.bind("<Return>", lambda e: self.refresh_data())

        ttk.Button(fb, text="🔍 Cari Barang", style="Primary.TButton",
                   command=self.refresh_data).pack(side="left", padx=(0, 8))

        ttk.Button(fb, text="Reset", style="Secondary.TButton",
                   command=self._reset_filter).pack(side="left")

        # 3. Tabel Gudang Card
        table_card = Card(self, padx=16, pady=16)
        table_card.pack(fill="both", expand=True)

        cols = [
            ("kode_barang", "Kode Barang", 120, "center"),
            ("lokasi", "Lokasi Rak/Brankas", 150, "w"),
            ("no_kontrak", "No. Kontrak", 150, "w"),
            ("deskripsi", "Deskripsi Barang Agunan", 220, "w"),
            ("kondisi", "Kondisi Fisik", 120, "center"),
            ("tgl_masuk", "Tgl Masuk", 100, "center"),
            ("status", "Status Barang", 130, "center"),
        ]

        self.table = DataTable(table_card.inner, columns=cols, stretch_col="deskripsi",
                               on_select=self._on_row_select)
        self.table.pack(fill="both", expand=True)

        # 4. Status Bar Info Bawah Card (Soft Border)
        bar_wrap = tk.Frame(self, bg=BORDER_COLOR, padx=1, pady=1, highlightthickness=0, bd=0)
        bar_wrap.pack(fill="x", pady=(14, 0))
        self.status_bar = tk.Frame(bar_wrap, bg=BG_CARD, padx=18, pady=12, highlightthickness=0, bd=0)
        self.status_bar.pack(fill="both", expand=True)

        self.lbl_info = tk.Label(self.status_bar, text="Total barang tercatat di gudang: 0 item",
                                 font=FONT_LABEL, fg=TEXT_MAIN, bg=BG_CARD)
        self.lbl_info.pack(side="left")

    def _reset_filter(self):
        self.ent_kontrak.delete(0, tk.END)
        self.ent_kode_barang.delete(0, tk.END)
        self.refresh_data()

    def _on_row_select(self, row: Optional[Dict[str, Any]]):
        if row:
            brg = row.get("kode_barang", "-")
            lok = row.get("lokasi", "-")
            kond = row.get("kondisi", "-")
            st = row.get("status", "-")
            self.lbl_info.config(text=f"Agunan: {brg}  |  Penyimpanan: {lok}  |  Kondisi: {kond}  |  Status: {st}")

    def refresh_data(self):
        """Memuat daftar logistik gudang."""
        try:
            no_kontrak = self.ent_kontrak.get().strip()
            kode_barang = self.ent_kode_barang.get().strip()

            data = self.facade.cari_gudang(
                no_kontrak=no_kontrak,
                kode_barang=kode_barang
            )

            formatters = {
                "tgl_masuk": lambda v, r: format_date(v)
            }
            self.table.set_data(data, formatters=formatters)
            self.lbl_info.config(text=f"Total barang tercatat di gudang: {len(data)} item")
        except Exception:
            pass
