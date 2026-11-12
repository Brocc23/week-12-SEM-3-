"""
Tampilan Laporan Keuangan & Aset Jaminan Pegadaian Digital Nusantara
Menyediakan laporan laba rugi komprehensif, rekapitulasi portofolio agunan, dan ekspor data ke file CSV
dalam tata letak scrollable responsif.
"""

import tkinter as tk
from tkinter import ttk, filedialog
from datetime import date
from decimal import Decimal
from typing import Optional, Dict, Any, List

from pawn.ui.theme import (
    BG_CARD, BG_CARD_ALT, BG_MAIN, BORDER_COLOR, PRIMARY, PRIMARY_DARK,
    SECONDARY, DANGER, SUCCESS, INFO, TEXT_MAIN, TEXT_SECONDARY, TEXT_MUTED, TEXT_WHITE,
    FONT_TITLE, FONT_HEADER, FONT_SECTION, FONT_BODY, FONT_BODY_BOLD,
    FONT_LABEL, FONT_SMALL, FONT_SMALL_BOLD, FONT_METRIC,
    format_rupiah, format_date, show_pesan_sukses, show_pesan_error
)
from pawn.ui.widgets import Card, StatCard, DataTable, ScrollableFrame
try:
    from pawn.errors import PawnError
except ImportError:
    class PawnError(Exception): pass


class LaporanView(tk.Frame):
    """Layar Laporan Keuangan Eksekutif & Portofolio Agunan."""
    def __init__(self, parent, facade, **kwargs):
        super().__init__(parent, bg=BG_MAIN, padx=24, pady=20, **kwargs)
        self.facade = facade
        self.cached_lr_rows: List[Dict[str, Any]] = []
        self.cached_aset_rows: List[Dict[str, Any]] = []

        self._build_ui()

    def _build_ui(self):
        # 1. Header
        header = tk.Frame(self, bg=BG_MAIN)
        header.pack(fill="x", pady=(0, 16))

        tk.Label(header, text="📈 LAPORAN KEUANGAN & EKSEKUTIF", font=FONT_HEADER,
                 fg=TEXT_MAIN, bg=BG_MAIN).pack(anchor="w")
        tk.Label(header, text="Analisis performa laba rugi, pendapatan bunga/admin, eksposur portofolio agunan, dan ekspor audit",
                 font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_MAIN).pack(anchor="w", pady=(2, 0))

        # 2. Notebook Tab
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True)

        self.tab_laba_rugi = tk.Frame(self.tabs, bg=BG_MAIN, padx=12, pady=14)
        self.tabs.add(self.tab_laba_rugi, text=" 📊 Laporan Laba Rugi ")
        self._build_tab_laba_rugi()

        self.tab_aset = tk.Frame(self.tabs, bg=BG_MAIN, padx=12, pady=14)
        self.tabs.add(self.tab_aset, text=" 🏛️ Laporan Aset Jaminan ")
        self._build_tab_aset()

    # --- TAB 1: LAPORAN LABA RUGI ---
    def _build_tab_laba_rugi(self):
        # Gunakan scrollable container agar kartu dan tabel tidak terpotong
        scroll = ScrollableFrame(self.tab_laba_rugi, bg=BG_MAIN)
        scroll.pack(fill="both", expand=True)

        content = scroll.scrollable_content

        # Filter tanggal Card
        f_card = Card(content, padx=16, pady=12)
        f_card.pack(fill="x", pady=(0, 14))

        fb = tk.Frame(f_card.inner, bg=BG_CARD)
        fb.pack(fill="x")

        today = date.today()
        start_year = date(today.year, 1, 1).strftime("%Y-%m-%d")
        end_year = today.strftime("%Y-%m-%d")

        tk.Label(fb, text="Periode Dari (YYYY-MM-DD):", font=FONT_LABEL, fg=TEXT_MAIN, bg=BG_CARD).pack(side="left", padx=(0, 6))
        self.ent_lr_dari = ttk.Entry(fb, width=14)
        self.ent_lr_dari.insert(0, start_year)
        self.ent_lr_dari.pack(side="left", padx=(0, 14))

        tk.Label(fb, text="Sampai:", font=FONT_LABEL, fg=TEXT_MAIN, bg=BG_CARD).pack(side="left", padx=(0, 6))
        self.ent_lr_sampai = ttk.Entry(fb, width=14)
        self.ent_lr_sampai.insert(0, end_year)
        self.ent_lr_sampai.pack(side="left", padx=(0, 16))

        ttk.Button(fb, text="⚡ Tampilkan Laporan", style="Primary.TButton",
                   command=self._generate_laba_rugi).pack(side="left", padx=(0, 10))

        ttk.Button(fb, text="📥 Ekspor Laba Rugi ke CSV", style="Secondary.TButton",
                   command=self._export_lr_csv).pack(side="right")

        # Baris Kartu Ringkasan Finansial
        stats_frame = tk.Frame(content, bg=BG_MAIN)
        stats_frame.pack(fill="x", pady=(0, 14))

        self.sc_bunga = StatCard(stats_frame, title="Pendapatan Bunga", value="Rp 0", accent_color=PRIMARY)
        self.sc_bunga.pack(side="left", fill="both", expand=True, padx=(0, 8))

        self.sc_admin = StatCard(stats_frame, title="Biaya Administrasi", value="Rp 0", accent_color=INFO)
        self.sc_admin.pack(side="left", fill="both", expand=True, padx=(0, 8))

        self.sc_denda = StatCard(stats_frame, title="Denda & Perpanjangan", value="Rp 0", accent_color=SECONDARY)
        self.sc_denda.pack(side="left", fill="both", expand=True, padx=(0, 8))

        self.sc_rugi_lelang = StatCard(stats_frame, title="Kerugian Lelang", value="Rp 0", accent_color=DANGER)
        self.sc_rugi_lelang.pack(side="left", fill="both", expand=True, padx=(0, 8))

        self.sc_laba_bersih = StatCard(stats_frame, title="Laba Bersih", value="Rp 0", accent_color=PRIMARY_DARK)
        self.sc_laba_bersih.pack(side="left", fill="both", expand=True)

        # Tabel Rincian Jurnal / Transaksi Laba Rugi
        table_card = Card(content, padx=16, pady=16)
        table_card.pack(fill="both", expand=True)

        cols = [
            ("tanggal", "Tanggal Transaksi", 120, "center"),
            ("kategori", "Pos Pendapatan / Beban", 180, "w"),
            ("keterangan", "Uraian / No. Referensi", 260, "w"),
            ("nominal", "Nominal (Rp)", 140, "e"),
        ]
        self.tbl_lr = DataTable(table_card.inner, columns=cols, stretch_col="keterangan")
        self.tbl_lr.pack(fill="both", expand=True)

    def _generate_laba_rugi(self):
        dari = self.ent_lr_dari.get().strip()
        sampai = self.ent_lr_sampai.get().strip()

        try:
            res = self.facade.laporan_laba_rugi(dari, sampai)
            bunga = res.get("pendapatan_bunga", 0)
            admin = res.get("pendapatan_admin", 0)
            denda = res.get("denda", 0)
            perpanjang = res.get("biaya_perpanjangan", 0)
            rugi = res.get("kerugian_lelang", 0)
            laba = res.get("laba_bersih", 0)

            total_denda_perpanjang = Decimal(str(denda)) + Decimal(str(perpanjang))

            self.sc_bunga.update_value(format_rupiah(bunga))
            self.sc_admin.update_value(format_rupiah(admin))
            self.sc_denda.update_value(format_rupiah(total_denda_perpanjang))
            self.sc_rugi_lelang.update_value(format_rupiah(rugi))
            self.sc_laba_bersih.update_value(format_rupiah(laba))

            rows = res.get("rows", [])
            self.cached_lr_rows = rows
            formatters = {
                "nominal": lambda v, r: format_rupiah(v),
                "tanggal": lambda v, r: format_date(v)
            }
            self.tbl_lr.set_data(rows, formatters=formatters)

        except PawnError as e:
            show_pesan_error(self, "Gagal Menampilkan Laporan", str(e))
        except Exception as e:
            show_pesan_error(self, "Error Laporan", str(e))

    def _export_lr_csv(self):
        if not self.cached_lr_rows:
            show_pesan_error(self, "Data Kosong", "Tampilkan laporan terlebih dahulu sebelum mengekspor.")
            return

        path = filedialog.asksaveasfilename(
            parent=self,
            title="Simpan Laporan Laba Rugi ke CSV",
            defaultextension=".csv",
            filetypes=[("File CSV", "*.csv"), ("Semua File", "*.*")]
        )
        if not path:
            return

        try:
            self.facade.export_laporan_csv(self.cached_lr_rows, path)
            show_pesan_sukses(self, "Ekspor Berhasil", f"Laporan laba rugi berhasil disimpan ke:\n{path}")
        except PawnError as e:
            show_pesan_error(self, "Gagal Ekspor", str(e))
        except Exception as e:
            show_pesan_error(self, "Error Ekspor", str(e))

    # --- TAB 2: LAPORAN ASET JAMINAN ---
    def _build_tab_aset(self):
        top_bar = tk.Frame(self.tab_aset, bg=BG_MAIN)
        top_bar.pack(fill="x", pady=(0, 14))

        ttk.Button(top_bar, text="🔄 Muat Portofolio Agunan", style="Primary.TButton",
                   command=self._generate_aset).pack(side="left")

        ttk.Button(top_bar, text="📥 Ekspor Aset Jaminan ke CSV", style="Secondary.TButton",
                   command=self._export_aset_csv).pack(side="right")

        table_card = Card(self.tab_aset, padx=16, pady=16)
        table_card.pack(fill="both", expand=True)

        cols = [
            ("kode", "Kode Barang", 110, "center"),
            ("jenis", "Kategori", 110, "center"),
            ("deskripsi", "Deskripsi Fisik", 220, "w"),
            ("nilai_taksiran", "Nilai Taksiran (Rp)", 140, "e"),
            ("lokasi", "Lokasi Penyimpanan", 140, "w"),
            ("status", "Status Agunan", 120, "center"),
        ]
        self.tbl_aset = DataTable(table_card.inner, columns=cols, stretch_col="deskripsi")
        self.tbl_aset.pack(fill="both", expand=True)

        # Footer ringkasan nilai (Soft Border)
        footer_wrap = tk.Frame(self.tab_aset, bg=BORDER_COLOR, padx=1, pady=1, highlightthickness=0, bd=0)
        footer_wrap.pack(fill="x", pady=(14, 0))
        self.footer_aset = tk.Frame(footer_wrap, bg=BG_CARD, padx=18, pady=12, highlightthickness=0, bd=0)
        self.footer_aset.pack(fill="both", expand=True)

        self.lbl_aset_summary = tk.Label(self.footer_aset, text="Total Aset Jaminan: 0 item  |  Total Nilai Taksiran: Rp 0",
                                         font=FONT_HEADER, fg=PRIMARY_DARK, bg=BG_CARD)
        self.lbl_aset_summary.pack(side="left")

    def _generate_aset(self):
        try:
            data = self.facade.laporan_aset_jaminan()
            self.cached_aset_rows = data

            total_nilai = Decimal("0")
            for item in data:
                val = item.get("nilai_taksiran", 0)
                try:
                    total_nilai += Decimal(str(val))
                except Exception:
                    pass

            formatters = {
                "nilai_taksiran": lambda v, r: format_rupiah(v)
            }
            self.tbl_aset.set_data(data, formatters=formatters)
            self.lbl_aset_summary.config(
                text=f"Total Aset Jaminan: {len(data)} item  |  Total Nilai Taksiran Agunan: {format_rupiah(total_nilai)}"
            )
        except Exception as e:
            show_pesan_error(self, "Error Aset Jaminan", str(e))

    def _export_aset_csv(self):
        if not self.cached_aset_rows:
            show_pesan_error(self, "Data Kosong", "Muat data aset jaminan terlebih dahulu sebelum mengekspor.")
            return

        path = filedialog.asksaveasfilename(
            parent=self,
            title="Simpan Laporan Aset Jaminan ke CSV",
            defaultextension=".csv",
            filetypes=[("File CSV", "*.csv"), ("Semua File", "*.*")]
        )
        if not path:
            return

        try:
            self.facade.export_laporan_csv(self.cached_aset_rows, path)
            show_pesan_sukses(self, "Ekspor Berhasil", f"Portofolio aset jaminan berhasil diekspor ke:\n{path}")
        except PawnError as e:
            show_pesan_error(self, "Gagal Ekspor", str(e))
        except Exception as e:
            show_pesan_error(self, "Error Ekspor", str(e))
