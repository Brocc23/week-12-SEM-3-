"""
Tampilan Pengajuan Gadai (Alur 9-Langkah Stepper Wizard) Pegadaian Digital Nusantara
Mengimplementasikan verifikasi nasabah, penaksiran, penetapan plafon, alokasi gudang, dan pencairan dana
dalam antarmuka responsif anti-terpotong (Scrollable Container).
"""

import tkinter as tk
from tkinter import ttk
from decimal import Decimal
from datetime import timedelta
from typing import Callable, Optional, Dict, Any

from pawn.ui.theme import (
    BG_CARD, BG_CARD_ALT, BG_MAIN, BORDER_COLOR, PRIMARY, PRIMARY_LIGHT, PRIMARY_DARK,
    SECONDARY, SECONDARY_LIGHT, DANGER, SUCCESS, INFO, TEXT_MAIN, TEXT_SECONDARY, TEXT_MUTED, TEXT_WHITE,
    FONT_TITLE, FONT_HEADER, FONT_SECTION, FONT_BODY, FONT_BODY_BOLD,
    FONT_LABEL, FONT_SMALL, FONT_SMALL_BOLD, FONT_METRIC,
    format_rupiah, parse_rupiah, format_date, show_pesan_sukses, show_pesan_error
)
from pawn.ui.widgets import Card, StatCard, StepperWidget, ScrollableFrame, DataTable
try:
    from pawn.errors import PawnError
except ImportError:
    class PawnError(Exception): pass


class GadaiStepperView(tk.Frame):
    """Wizard Pengajuan Gadai 9 Langkah Responsif Sesuai Standar Operasional."""
    def __init__(self, parent, facade, navigate_to: Callable, preset: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(parent, bg=BG_MAIN, **kwargs)
        self.facade = facade
        self.navigate_to = navigate_to
        
        # State Data Pengajuan Gadai (Step 1 s.d. 9)
        self.current_step = 1
        self.data_gadai = {
            "nasabah": None,
            "jenis": "EMAS",
            "deskripsi": "",
            "atribut": {},
            "nilai_taksiran": Decimal("0"),
            "maks_pinjaman": Decimal("0"),
            "persen_ltv": Decimal("0"),
            "jumlah_pinjaman": Decimal("0"),
            "tenor_hari": 120,
            "lokasi_gudang": "BRANKAS-01",
            "kondisi_barang": "BAIK",
            "hasil_pinjaman": None
        }

        # Preset dari kalkulator penaksiran jika ada
        if preset:
            self.data_gadai["jenis"] = preset.get("jenis", "EMAS")
            self.data_gadai["atribut"] = preset.get("atribut", {})
            self.data_gadai["nilai_taksiran"] = preset.get("nilai_taksiran", Decimal("0"))
            self.data_gadai["maks_pinjaman"] = preset.get("maks_pinjaman", Decimal("0"))
            self.data_gadai["persen_ltv"] = preset.get("persen", Decimal("0"))

        self._build_ui()

    def _build_ui(self):
        # Header Halaman
        header = tk.Frame(self, bg=BG_MAIN, padx=24, pady=16)
        header.pack(fill="x")

        tk.Label(header, text="📝 PENGAJUAN AKAD GADAI BARU (9 LANGKAH)", font=FONT_HEADER,
                 fg=TEXT_MAIN, bg=BG_MAIN).pack(anchor="w")
        tk.Label(header, text="Verifikasi debitur, penaksiran agunan, penetapan plafon LTV, alokasi gudang, hingga pencairan dana",
                 font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_MAIN).pack(anchor="w", pady=(2, 0))

        # Indikator Visual Stepper
        step_names = [
            "Nasabah", "Kategori", "Atribut", "Taksiran",
            "Plafon", "Gudang", "Akad", "Eksekusi", "Selesai"
        ]
        stepper_box = Card(self, padx=12, pady=10)
        stepper_box.pack(fill="x", padx=24, pady=(0, 14))
        
        self.stepper = StepperWidget(stepper_box.inner, steps=step_names, current_step=self.current_step)
        self.stepper.pack(fill="x")

        # Navigasi Bawah (Packed first to bottom to ensure always visible)
        nav_card = Card(self, padx=18, pady=12)
        nav_card.pack(fill="x", side="bottom", padx=24, pady=(0, 16))

        nav_bar = tk.Frame(nav_card.inner, bg=BG_CARD)
        nav_bar.pack(fill="x")

        self.btn_prev = ttk.Button(nav_bar, text="⬅️ Sebelumnya", style="Secondary.TButton",
                                   command=self._go_prev)
        self.btn_prev.pack(side="left")

        self.lbl_step_counter = tk.Label(nav_bar, text="Langkah 1 dari 9", font=FONT_BODY_BOLD,
                                         fg=PRIMARY_DARK, bg=BG_CARD)
        self.lbl_step_counter.pack(side="left", expand=True)

        self.btn_next = ttk.Button(nav_bar, text="Selanjutnya ➡️", style="Primary.TButton",
                                   command=self._go_next)
        self.btn_next.pack(side="right")

        # Scrollable Kontainer Langkah Aktif (Tengah)
        self.scroll_step = ScrollableFrame(self, bg=BG_MAIN)
        self.scroll_step.pack(fill="both", expand=True, padx=24, pady=(0, 12))

        self.step_card = Card(self.scroll_step.scrollable_content, padx=24, pady=20)
        self.step_card.pack(fill="both", expand=True)

        self._render_current_step()

    def _render_current_step(self):
        """Merender isi panel berdasarkan step yang aktif."""
        for w in self.step_card.inner.winfo_children():
            w.destroy()

        self.stepper.set_step(self.current_step)
        self.lbl_step_counter.config(text=f"Langkah {self.current_step} dari 9")

        # Update status tombol navigasi
        self.btn_prev.config(state="disabled" if self.current_step in (1, 9) else "normal")
        if self.current_step == 8:
            self.btn_next.config(text="⚡ EKSEKUSI PENCAIRAN GADAI", style="Accent.TButton")
        elif self.current_step == 9:
            self.btn_next.config(text="Kembali ke Dashboard", style="Primary.TButton")
        else:
            self.btn_next.config(text="Selanjutnya ➡️", style="Primary.TButton")

        # Dispatch method step
        method = getattr(self, f"_step_{self.current_step}", None)
        if method:
            method()

    # --- LANGKAH 1: VERIFIKASI NASABAH AKTIF ---
    def _step_1(self):
        tk.Label(self.step_card.inner, text="LANGKAH 1: PILIH & VERIFIKASI NASABAH DEBITUR",
                 font=FONT_SECTION, fg=PRIMARY_DARK, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
        tk.Label(self.step_card.inner, text="Pilih nasabah yang terdaftar dan pastikan status keanggotaan AKTIF.",
                 font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_CARD).pack(anchor="w", pady=(0, 14))

        sb = tk.Frame(self.step_card.inner, bg=BG_CARD)
        sb.pack(fill="x", pady=(0, 10))
        
        tk.Label(sb, text="Cari Nama/NIK:", font=FONT_LABEL, fg=TEXT_MAIN, bg=BG_CARD).pack(side="left", padx=(0, 8))
        ent_cari = ttk.Entry(sb, width=28)
        ent_cari.pack(side="left", padx=(0, 8))

        cols = [
            ("id", "ID", 50, "center"),
            ("kode", "Kode", 100, "center"),
            ("nama", "Nama Lengkap Nasabah", 180, "w"),
            ("nik", "NIK KTP", 140, "center"),
            ("telepon", "No. Telepon", 120, "w"),
            ("status", "Status", 100, "center"),
        ]
        self.tbl_nsb_step1 = DataTable(self.step_card.inner, columns=cols, stretch_col="nama")
        self.tbl_nsb_step1.pack(fill="x", pady=(0, 12))

        try:
            nsb_list = self.facade.daftar_nasabah("")
            self.tbl_nsb_step1.set_data(nsb_list)
        except Exception:
            pass

        def on_cari():
            q = ent_cari.get().strip()
            res = self.facade.daftar_nasabah(q)
            self.tbl_nsb_step1.set_data(res)

        ttk.Button(sb, text="🔍 Cari", style="Secondary.TButton", command=on_cari).pack(side="left")

        # Info Terpilih (Soft 1px Sand Border)
        sel_wrap = tk.Frame(self.step_card.inner, bg=BORDER_COLOR, padx=1, pady=1, highlightthickness=0, bd=0)
        sel_wrap.pack(fill="x")
        self.lbl_selected_step1 = tk.Label(sel_wrap,
                                           text="Silakan klik baris nasabah di tabel untuk memilih debitur.",
                                           font=FONT_BODY_BOLD, fg=PRIMARY_DARK, bg=BG_CARD_ALT,
                                           padx=14, pady=10, relief="flat", bd=0)
        self.lbl_selected_step1.pack(fill="both", expand=True)

        if self.data_gadai["nasabah"]:
            n = self.data_gadai["nasabah"]
            self.lbl_selected_step1.config(text=f"Nasabah Terpilih: {n.get('nama')} (NIK: {n.get('nik')}) — Status: {n.get('status')}")

        def on_select_nsb(row):
            if row:
                self.data_gadai["nasabah"] = row
                self.lbl_selected_step1.config(
                    text=f"Nasabah Terpilih: {row.get('nama')} (NIK: {row.get('nik')}) — Status: {row.get('status')}"
                )
        self.tbl_nsb_step1.on_select = on_select_nsb

    # --- LANGKAH 2: PILIH KATEGORI BARANG JAMINAN (2-Column Soft Clickable Cards) ---
    def _step_2(self):
        tk.Label(self.step_card.inner, text="LANGKAH 2: PILIH KATEGORI BARANG AGUNAN",
                 font=FONT_SECTION, fg=PRIMARY_DARK, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
        tk.Label(self.step_card.inner, text="Tentukan jenis agunan untuk menerapkan rumus penilaian aktuaria dan rasio LTV yang tepat.",
                 font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_CARD).pack(anchor="w", pady=(0, 16))

        kategori_info = [
            ("EMAS", "Logam Mulia / Perhiasan Emas", "Plafon s.d. 90% dari nilai taksiran. Rumus berbasis berat bersih & kadar karat."),
            ("KENDARAAN", "Sepeda Motor / Mobil", "Plafon s.d. 75% dari nilai pasar. Mempertimbangkan tahun produksi & kondisi fisik/mesin."),
            ("ELEKTRONIK", "TV, Kamera, Perangkat", "Plafon s.d. 60% dari nilai pasar. Disusutkan berdasarkan umur pemakaian."),
            ("LAPTOP", "Komputer Portabel / Laptop", "Plafon s.d. 60% dari nilai pasar. Memperhitungkan spesifikasi prosesor & umur."),
            ("LAINNYA", "Barang Berharga Lainnya", "Barang berharga lainnya dengan taksiran berbasis harga pasar dan kondisi fisik."),
        ]

        grid_frame = tk.Frame(self.step_card.inner, bg=BG_CARD, highlightthickness=0, bd=0)
        grid_frame.pack(fill="x", pady=(0, 10))
        grid_frame.grid_columnconfigure(0, weight=1)
        grid_frame.grid_columnconfigure(1, weight=1)

        self.radio_kat_var = tk.StringVar(value=self.data_gadai["jenis"])
        self.category_card_widgets = {}

        def select_category(code):
            self.radio_kat_var.set(code)
            self.data_gadai["jenis"] = code
            for c, (outer, inner, title_lbl, desc_lbl, badge_lbl) in self.category_card_widgets.items():
                if c == code:
                    outer.config(bg=PRIMARY)
                    inner.config(bg=PRIMARY_LIGHT)
                    title_lbl.config(fg=PRIMARY_DARK, bg=PRIMARY_LIGHT)
                    desc_lbl.config(fg=TEXT_SECONDARY, bg=PRIMARY_LIGHT)
                    badge_lbl.config(text="✓ Dipilih", fg=PRIMARY_DARK, bg=PRIMARY_LIGHT)
                else:
                    outer.config(bg=BORDER_COLOR)
                    inner.config(bg=BG_CARD)
                    title_lbl.config(fg=TEXT_MAIN, bg=BG_CARD)
                    desc_lbl.config(fg=TEXT_MUTED, bg=BG_CARD)
                    badge_lbl.config(text="", bg=BG_CARD)

        for idx, (code, title, desc) in enumerate(kategori_info):
            r = idx // 2
            c = idx % 2
            colspan = 2 if idx == 4 else 1

            is_sel = (code == self.data_gadai["jenis"])
            border_c = PRIMARY if is_sel else BORDER_COLOR
            fill_c = PRIMARY_LIGHT if is_sel else BG_CARD
            title_fg = PRIMARY_DARK if is_sel else TEXT_MAIN
            desc_fg = TEXT_SECONDARY if is_sel else TEXT_MUTED

            outer = tk.Frame(grid_frame, bg=border_c, padx=1, pady=1, highlightthickness=0, bd=0, cursor="hand2")
            outer.grid(row=r, column=c, columnspan=colspan, padx=6, pady=6, sticky="nsew")

            inner = tk.Frame(outer, bg=fill_c, padx=16, pady=12, highlightthickness=0, bd=0, cursor="hand2")
            inner.pack(fill="both", expand=True)

            top_row = tk.Frame(inner, bg=fill_c, cursor="hand2", highlightthickness=0, bd=0)
            top_row.pack(fill="x")

            title_lbl = tk.Label(top_row, text=f"{code} — {title}", font=FONT_LABEL,
                                 fg=title_fg, bg=fill_c, cursor="hand2")
            title_lbl.pack(side="left")

            badge_text = "✓ Dipilih" if is_sel else ""
            badge_lbl = tk.Label(top_row, text=badge_text, font=FONT_SMALL_BOLD,
                                 fg=PRIMARY_DARK, bg=fill_c, cursor="hand2")
            badge_lbl.pack(side="right")

            desc_lbl = tk.Label(inner, text=desc, font=FONT_SMALL, fg=desc_fg, bg=fill_c,
                                wraplength=480 if colspan == 2 else 380, justify="left", cursor="hand2")
            desc_lbl.pack(anchor="w", pady=(4, 0))

            self.category_card_widgets[code] = (outer, inner, title_lbl, desc_lbl, badge_lbl)

            for w in (outer, inner, top_row, title_lbl, badge_lbl, desc_lbl):
                w.bind("<Button-1>", lambda e, cd=code: select_category(cd))

    # --- LANGKAH 3: DESKRIPSI & ATRIBUT SPESIFIK BARANG ---
    def _step_3(self):
        kat = self.data_gadai["jenis"]
        tk.Label(self.step_card.inner, text=f"LANGKAH 3: SPESIFIKASI & ATRIBUT BARANG ({kat})",
                 font=FONT_SECTION, fg=PRIMARY_DARK, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
        tk.Label(self.step_card.inner, text="Lengkapi deskripsi fisik dan variabel penentu taksiran barang jaminan.",
                 font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_CARD).pack(anchor="w", pady=(0, 14))

        tk.Label(self.step_card.inner, text="Deskripsi Fisik Barang Agunan *", font=FONT_LABEL,
                 fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
        self.ent_desc = ttk.Entry(self.step_card.inner)
        self.ent_desc.insert(0, self.data_gadai["deskripsi"] or f"Barang jaminan {kat}")
        self.ent_desc.pack(fill="x", pady=(0, 16))

        self.s3_inputs = {}
        atr = self.data_gadai["atribut"]

        if kat == "EMAS":
            tk.Label(self.step_card.inner, text="Berat Emas (Gram) *", font=FONT_LABEL,
                     fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
            ent_berat = ttk.Entry(self.step_card.inner)
            ent_berat.insert(0, str(atr.get("berat", "10.0")))
            ent_berat.pack(fill="x", pady=(0, 12))
            self.s3_inputs["berat"] = ent_berat

            tk.Label(self.step_card.inner, text="Kadar Kemurnian Emas (Karat) *", font=FONT_LABEL,
                     fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
            cmb_kadar = ttk.Combobox(self.step_card.inner, state="readonly",
                                     values=["24", "22", "20", "18", "16", "14", "10"])
            cmb_kadar.set(str(atr.get("kadar", "24")))
            cmb_kadar.pack(fill="x", pady=(0, 12))
            self.s3_inputs["kadar"] = cmb_kadar

        elif kat == "KENDARAAN":
            tk.Label(self.step_card.inner, text="Harga Pasar Wajar Kendaraan (Rp) *", font=FONT_LABEL,
                     fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
            ent_hp = ttk.Entry(self.step_card.inner)
            ent_hp.insert(0, str(atr.get("harga_pasar", "20000000")))
            ent_hp.pack(fill="x", pady=(0, 12))
            self.s3_inputs["harga_pasar"] = ent_hp

            tk.Label(self.step_card.inner, text="Tahun Pembuatan Kendaraan *", font=FONT_LABEL,
                     fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
            ent_th = ttk.Entry(self.step_card.inner)
            ent_th.insert(0, str(atr.get("tahun", "2021")))
            ent_th.pack(fill="x", pady=(0, 12))
            self.s3_inputs["tahun"] = ent_th

            tk.Label(self.step_card.inner, text="Kondisi Fisik & Mesin *", font=FONT_LABEL,
                     fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
            cmb_k = ttk.Combobox(self.step_card.inner, state="readonly",
                                 values=["BAIK", "CUKUP", "BURUK"])
            cmb_k.set(str(atr.get("kondisi", "BAIK")))
            cmb_k.pack(fill="x", pady=(0, 12))
            self.s3_inputs["kondisi"] = cmb_k

        elif kat == "ELEKTRONIK":
            tk.Label(self.step_card.inner, text="Harga Beli / Pasar Baru (Rp) *", font=FONT_LABEL,
                     fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
            ent_hp = ttk.Entry(self.step_card.inner)
            ent_hp.insert(0, str(atr.get("harga_pasar", "5000000")))
            ent_hp.pack(fill="x", pady=(0, 12))
            self.s3_inputs["harga_pasar"] = ent_hp

            tk.Label(self.step_card.inner, text="Umur Pemakaian (Tahun) *", font=FONT_LABEL,
                     fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
            ent_u = ttk.Entry(self.step_card.inner)
            ent_u.insert(0, str(atr.get("umur", "1")))
            ent_u.pack(fill="x", pady=(0, 12))
            self.s3_inputs["umur"] = ent_u

            tk.Label(self.step_card.inner, text="Kondisi Fisik Perangkat *", font=FONT_LABEL,
                     fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
            cmb_k = ttk.Combobox(self.step_card.inner, state="readonly",
                                 values=["BAIK", "CUKUP", "BURUK"])
            cmb_k.set(str(atr.get("kondisi", "BAIK")))
            cmb_k.pack(fill="x", pady=(0, 12))
            self.s3_inputs["kondisi"] = cmb_k

        elif kat == "LAPTOP":
            tk.Label(self.step_card.inner, text="Harga Beli / Pasar Baru (Rp) *", font=FONT_LABEL,
                     fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
            ent_hp = ttk.Entry(self.step_card.inner)
            ent_hp.insert(0, str(atr.get("harga_pasar", "12000000")))
            ent_hp.pack(fill="x", pady=(0, 12))
            self.s3_inputs["harga_pasar"] = ent_hp

            tk.Label(self.step_card.inner, text="Spesifikasi Processor / GPU *", font=FONT_LABEL,
                     fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
            cmb_spk = ttk.Combobox(self.step_card.inner, state="readonly",
                                   values=["LOW", "MID", "HIGH"])
            cmb_spk.set(str(atr.get("spesifikasi", "MID")))
            cmb_spk.pack(fill="x", pady=(0, 12))
            self.s3_inputs["spesifikasi"] = cmb_spk

            tk.Label(self.step_card.inner, text="Umur Pemakaian (Tahun) *", font=FONT_LABEL,
                     fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
            ent_u = ttk.Entry(self.step_card.inner)
            ent_u.insert(0, str(atr.get("umur", "1")))
            ent_u.pack(fill="x", pady=(0, 12))
            self.s3_inputs["umur"] = ent_u

            tk.Label(self.step_card.inner, text="Kondisi Fisik & Layar *", font=FONT_LABEL,
                     fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
            cmb_k = ttk.Combobox(self.step_card.inner, state="readonly",
                                 values=["BAIK", "CUKUP", "BURUK"])
            cmb_k.set(str(atr.get("kondisi", "BAIK")))
            cmb_k.pack(fill="x", pady=(0, 12))
            self.s3_inputs["kondisi"] = cmb_k

        elif kat == "LAINNYA":
            tk.Label(self.step_card.inner, text="Harga Pasar Wajar (Rp) *", font=FONT_LABEL,
                     fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
            ent_hp = ttk.Entry(self.step_card.inner)
            ent_hp.insert(0, str(atr.get("harga_pasar", "3000000")))
            ent_hp.pack(fill="x", pady=(0, 12))
            self.s3_inputs["harga_pasar"] = ent_hp

            tk.Label(self.step_card.inner, text="Kondisi Fisik Barang *", font=FONT_LABEL,
                     fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
            cmb_k = ttk.Combobox(self.step_card.inner, state="readonly",
                                 values=["BAIK", "CUKUP", "BURUK"])
            cmb_k.set(str(atr.get("kondisi", "BAIK")))
            cmb_k.pack(fill="x", pady=(0, 12))
            self.s3_inputs["kondisi"] = cmb_k

    # --- LANGKAH 4: HITUNG NILAI TAKSIRAN & PENAKSIR ---
    def _step_4(self):
        tk.Label(self.step_card.inner, text="LANGKAH 4: HASIL TAKSIRAN RESMI & PLAFON MAKSIMAL",
                 font=FONT_SECTION, fg=PRIMARY_DARK, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
        tk.Label(self.step_card.inner, text="Sistem menghitung nilai agunan dan batas maksimum pencairan pinjaman (P-Max).",
                 font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_CARD).pack(anchor="w", pady=(0, 16))

        try:
            res = self.facade.hitung_taksiran(self.data_gadai["jenis"], self.data_gadai["atribut"])
            self.data_gadai["nilai_taksiran"] = res.get("nilai_taksiran", Decimal("0"))
            self.data_gadai["maks_pinjaman"] = res.get("maks_pinjaman", Decimal("0"))
            self.data_gadai["persen_ltv"] = res.get("persen", Decimal("0"))
        except Exception as e:
            tk.Label(self.step_card.inner, text=f"⚠️ Gagal menghitung taksiran: {str(e)}",
                     font=FONT_BODY_BOLD, fg=DANGER, bg=BG_CARD).pack(anchor="w", pady=10)

        res_row = tk.Frame(self.step_card.inner, bg=BG_CARD)
        res_row.pack(fill="x", pady=(0, 16))

        c1 = StatCard(res_row, title="Nilai Taksiran Agunan",
                      value=format_rupiah(self.data_gadai["nilai_taksiran"]),
                      subtitle=f"Kategori {self.data_gadai['jenis']}", accent_color=INFO)
        c1.pack(side="left", fill="both", expand=True, padx=(0, 10))

        c2 = StatCard(res_row, title="Maksimal Plafon Pinjaman (P-Max)",
                      value=format_rupiah(self.data_gadai["maks_pinjaman"]),
                      subtitle="Batas tertinggi pencairan", accent_color=SECONDARY)
        c2.pack(side="left", fill="both", expand=True)

        info_wrap = tk.Frame(self.step_card.inner, bg=BORDER_COLOR, padx=1, pady=1, highlightthickness=0, bd=0)
        info_wrap.pack(fill="x")
        info_box = tk.Frame(info_wrap, bg=BG_CARD_ALT, padx=16, pady=12, highlightthickness=0, bd=0)
        info_box.pack(fill="both", expand=True)

        tk.Label(info_box, text=f"Agunan: {self.data_gadai['deskripsi']}", font=FONT_LABEL,
                 fg=TEXT_MAIN, bg=BG_CARD_ALT).pack(anchor="w")
        tk.Label(info_box, text=f"Nasabah Debitur: {self.data_gadai['nasabah'].get('nama', '')} (NIK: {self.data_gadai['nasabah'].get('nik', '')})",
                 font=FONT_BODY, fg=TEXT_SECONDARY, bg=BG_CARD_ALT).pack(anchor="w", pady=(4, 0))

    # --- LANGKAH 5: TENTUKAN JUMLAH PINJAMAN & TENOR ---
    def _step_5(self):
        tk.Label(self.step_card.inner, text="LANGKAH 5: PENGAJUAN PINJAMAN & JANGKA WAKTU (TENOR)",
                 font=FONT_SECTION, fg=PRIMARY_DARK, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
        tk.Label(self.step_card.inner, text=f"Maksimal pinjaman yang disetujui (P-Max) adalah {format_rupiah(self.data_gadai['maks_pinjaman'])}.",
                 font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_CARD).pack(anchor="w", pady=(0, 16))

        tk.Label(self.step_card.inner, text="Jumlah Pinjaman yang Diajukan (Rp) *", font=FONT_LABEL,
                 fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
        
        cur_pinjaman = self.data_gadai["jumlah_pinjaman"]
        if cur_pinjaman == Decimal("0"):
            cur_pinjaman = self.data_gadai["maks_pinjaman"]

        self.ent_jml_pinjaman = ttk.Entry(self.step_card.inner)
        self.ent_jml_pinjaman.insert(0, str(cur_pinjaman))
        self.ent_jml_pinjaman.pack(fill="x", pady=(0, 16))

        tk.Label(self.step_card.inner, text="Jangka Waktu / Tenor Pinjaman (Hari) *", font=FONT_LABEL,
                 fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
        self.ent_tenor = ttk.Entry(self.step_card.inner)
        self.ent_tenor.insert(0, str(self.data_gadai["tenor_hari"]))
        self.ent_tenor.pack(fill="x", pady=(0, 12))

        tk.Label(self.step_card.inner, text="* Standar tenor gadai adalah 120 hari dengan suku bunga per periode 15 hari.",
                 font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_CARD).pack(anchor="w")

    # --- LANGKAH 6: ALOKASI GUDANG & KONDISI FISIK ---
    def _step_6(self):
        tk.Label(self.step_card.inner, text="LANGKAH 6: PENYIMPANAN DI GUDANG / BRANKAS",
                 font=FONT_SECTION, fg=PRIMARY_DARK, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
        tk.Label(self.step_card.inner, text="Tentukan lokasi rak atau brankas penyimpanan barang jaminan dan verifikasi fisik saat penerimaan.",
                 font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_CARD).pack(anchor="w", pady=(0, 16))

        tk.Label(self.step_card.inner, text="Kode Lokasi Gudang / Rak / Brankas *", font=FONT_LABEL,
                 fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
        self.ent_lokasi = ttk.Entry(self.step_card.inner)
        self.ent_lokasi.insert(0, self.data_gadai["lokasi_gudang"])
        self.ent_lokasi.pack(fill="x", pady=(0, 16))

        tk.Label(self.step_card.inner, text="Catatan Kondisi Fisik Barang Saat Diterima *", font=FONT_LABEL,
                 fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
        self.ent_kondisi_terima = ttk.Entry(self.step_card.inner)
        self.ent_kondisi_terima.insert(0, self.data_gadai["kondisi_barang"])
        self.ent_kondisi_terima.pack(fill="x", pady=(0, 12))

    # --- LANGKAH 7: RINCIAN AKAD & BIAYA ---
    def _step_7(self):
        tk.Label(self.step_card.inner, text="LANGKAH 7: PRATINJAU AKAD GADAI & RINCIAN BIAYA",
                 font=FONT_SECTION, fg=PRIMARY_DARK, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
        tk.Label(self.step_card.inner, text="Periksa ringkasan kewajiban bunga, biaya administrasi, dan tanggal jatuh tempo sebelum eksekusi.",
                 font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_CARD).pack(anchor="w", pady=(0, 16))

        box_wrap = tk.Frame(self.step_card.inner, bg=BORDER_COLOR, padx=1, pady=1, highlightthickness=0, bd=0)
        box_wrap.pack(fill="both", expand=True)
        box = tk.Frame(box_wrap, bg=BG_CARD_ALT, padx=18, pady=16, highlightthickness=0, bd=0)
        box.pack(fill="both", expand=True)

        pinjaman = self.data_gadai["jumlah_pinjaman"]
        admin_est = pinjaman * Decimal("0.01")
        bunga_est = pinjaman * Decimal("0.012")

        try:
            today = self.facade.hari_ini()
            due_date = today + timedelta(days=int(self.data_gadai["tenor_hari"]))
        except Exception:
            due_date = "-"

        rincian = [
            ("Nama Debitur", self.data_gadai["nasabah"].get("nama", "-")),
            ("NIK KTP", self.data_gadai["nasabah"].get("nik", "-")),
            ("Barang Agunan", f"{self.data_gadai['deskripsi']} ({self.data_gadai['jenis']})"),
            ("Plafon Pokok Pinjaman", format_rupiah(pinjaman)),
            ("Biaya Administrasi (1%)", format_rupiah(admin_est)),
            ("Estimasi Bunga per Periode (1.2%)", format_rupiah(bunga_est)),
            ("Tenor Pinjaman", f"{self.data_gadai['tenor_hari']} Hari"),
            ("Estimasi Jatuh Tempo", format_date(due_date)),
            ("Lokasi Penyimpanan", self.data_gadai["lokasi_gudang"]),
        ]

        for label, val in rincian:
            row = tk.Frame(box, bg=BG_CARD_ALT)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=f"{label}:", font=FONT_BODY, fg=TEXT_MUTED, bg=BG_CARD_ALT, width=30, anchor="w").pack(side="left")
            tk.Label(row, text=str(val), font=FONT_LABEL, fg=TEXT_MAIN, bg=BG_CARD_ALT, anchor="w").pack(side="left")

    # --- LANGKAH 8: KONFIRMASI & EKSEKUSI ---
    def _step_8(self):
        tk.Label(self.step_card.inner, text="LANGKAH 8: KONFIRMASI AKHIR & PENCAIRAN DANA",
                 font=FONT_SECTION, fg=PRIMARY_DARK, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
        tk.Label(self.step_card.inner, text="Klik tombol 'EKSEKUSI PENCAIRAN GADAI' di bawah untuk menerbitkan kontrak resmi dan mencairkan dana.",
                 font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_CARD).pack(anchor="w", pady=(0, 16))

        confirm_wrap = tk.Frame(self.step_card.inner, bg=BORDER_COLOR, padx=1, pady=1, highlightthickness=0, bd=0)
        confirm_wrap.pack(fill="x", pady=(0, 16))
        card_confirm = tk.Frame(confirm_wrap, bg=PRIMARY_LIGHT, padx=20, pady=18, highlightthickness=0, bd=0)
        card_confirm.pack(fill="both", expand=True)

        tk.Label(card_confirm, text="PERSETUJUAN TRANSAKSI AKAD GADAI", font=FONT_HEADER,
                 fg=PRIMARY_DARK, bg=PRIMARY_LIGHT).pack(anchor="w")
        
        info_txt = (
            f"Dengan ini nasabah {self.data_gadai['nasabah'].get('nama')} menyetujui penyerahan agunan "
            f"berupa '{self.data_gadai['deskripsi']}' dengan pinjaman pokok senilai "
            f"{format_rupiah(self.data_gadai['jumlah_pinjaman'])}. Barang akan disimpan di "
            f"{self.data_gadai['lokasi_gudang']} dan pencairan dana dicatat ke jurnal keuangan."
        )
        tk.Label(card_confirm, text=info_txt, font=FONT_BODY, fg=TEXT_MAIN,
                 bg=PRIMARY_LIGHT, wraplength=550, justify="left").pack(anchor="w", pady=(10, 0))

    # --- LANGKAH 9: BUKTI AKAD & SELESAI ---
    def _step_9(self):
        tk.Label(self.step_card.inner, text="LANGKAH 9: AKAD GADAI BERHASIL DITERBITKAN 🎉",
                 font=FONT_HEADER, fg=SUCCESS, bg=BG_CARD).pack(anchor="w", pady=(0, 4))

        pinjaman = self.data_gadai.get("hasil_pinjaman", {}) or {}
        no_kontrak = pinjaman.get("no_kontrak", "GDI-KONTRAK-SUKSES")

        success_wrap = tk.Frame(self.step_card.inner, bg=BORDER_COLOR, padx=1, pady=1, highlightthickness=0, bd=0)
        success_wrap.pack(fill="both", expand=True, pady=(0, 16))
        success_card = tk.Frame(success_wrap, bg=BG_CARD_ALT, padx=20, pady=18, highlightthickness=0, bd=0)
        success_card.pack(fill="both", expand=True)

        tk.Label(success_card, text=f"NO. KONTRAK: {no_kontrak}", font=FONT_TITLE,
                 fg=PRIMARY_DARK, bg=BG_CARD_ALT).pack(anchor="w")
        tk.Label(success_card, text="Status Barang: TERGADAI  |  Status Kontrak: AKTIF  |  Dana Telah Dicairkan",
                 font=FONT_LABEL, fg=SUCCESS, bg=BG_CARD_ALT).pack(anchor="w", pady=(4, 12))

        items = [
            ("Debitur", self.data_gadai["nasabah"].get("nama", "-")),
            ("Barang Agunan", self.data_gadai["deskripsi"]),
            ("Pokok Pinjaman", format_rupiah(self.data_gadai["jumlah_pinjaman"])),
            ("Jatuh Tempo", format_date(pinjaman.get("tgl_jatuh_tempo", "-"))),
            ("Lokasi Gudang", self.data_gadai["lokasi_gudang"]),
        ]
        for l, v in items:
            r = tk.Frame(success_card, bg=BG_CARD_ALT)
            r.pack(fill="x", pady=3)
            tk.Label(r, text=f"{l}:", font=FONT_BODY, fg=TEXT_MUTED, bg=BG_CARD_ALT, width=24, anchor="w").pack(side="left")
            tk.Label(r, text=str(v), font=FONT_LABEL, fg=TEXT_MAIN, bg=BG_CARD_ALT).pack(side="left")

        btn_box = tk.Frame(self.step_card.inner, bg=BG_CARD)
        btn_box.pack(fill="x", pady=(12, 0))

        ttk.Button(btn_box, text="📋 Lihat di Buku Pinjaman", style="Secondary.TButton",
                   command=lambda: self.navigate_to("pinjaman")).pack(side="left", padx=(0, 10))

        ttk.Button(btn_box, text="📝 Ajukan Gadai Baru Lagi", style="Primary.TButton",
                   command=self._reset_wizard).pack(side="left")

    # ==========================================
    # LOGIKA VALIDASI DAN TRANSISI STEP
    # ==========================================
    def _go_prev(self):
        if self.current_step > 1:
            self.current_step -= 1
            self._render_current_step()

    def _go_next(self):
        if self.current_step == 1:
            if not self.data_gadai["nasabah"]:
                show_pesan_error(self, "Pilih Nasabah", "Silakan pilih salah satu nasabah dari tabel.")
                return
            status_nsb = str(self.data_gadai["nasabah"].get("status", "")).upper()
            if status_nsb != "AKTIF":
                show_pesan_error(self, "Nasabah Tidak Aktif", "Nasabah dengan status DITANGGUHKAN tidak dapat mengajukan gadai.")
                return

        elif self.current_step == 2:
            self.data_gadai["jenis"] = self.radio_kat_var.get()

        elif self.current_step == 3:
            desc = self.ent_desc.get().strip()
            if not desc:
                show_pesan_error(self, "Deskripsi Kosong", "Deskripsi barang jaminan wajib diisi.")
                return
            self.data_gadai["deskripsi"] = desc

            kat = self.data_gadai["jenis"]
            try:
                if kat == "EMAS":
                    self.data_gadai["atribut"] = {
                        "berat": Decimal(self.s3_inputs["berat"].get().strip()),
                        "kadar": int(self.s3_inputs["kadar"].get().strip())
                    }
                elif kat == "KENDARAAN":
                    self.data_gadai["atribut"] = {
                        "harga_pasar": parse_rupiah(self.s3_inputs["harga_pasar"].get()),
                        "tahun": int(self.s3_inputs["tahun"].get().strip()),
                        "kondisi": self.s3_inputs["kondisi"].get().strip()
                    }
                elif kat == "ELEKTRONIK":
                    self.data_gadai["atribut"] = {
                        "harga_pasar": parse_rupiah(self.s3_inputs["harga_pasar"].get()),
                        "umur": int(self.s3_inputs["umur"].get().strip()),
                        "kondisi": self.s3_inputs["kondisi"].get().strip()
                    }
                elif kat == "LAPTOP":
                    self.data_gadai["atribut"] = {
                        "harga_pasar": parse_rupiah(self.s3_inputs["harga_pasar"].get()),
                        "spesifikasi": self.s3_inputs["spesifikasi"].get().strip(),
                        "umur": int(self.s3_inputs["umur"].get().strip()),
                        "kondisi": self.s3_inputs["kondisi"].get().strip()
                    }
                elif kat == "LAINNYA":
                    self.data_gadai["atribut"] = {
                        "harga_pasar": parse_rupiah(self.s3_inputs["harga_pasar"].get()),
                        "kondisi": self.s3_inputs["kondisi"].get().strip()
                    }
            except Exception:
                show_pesan_error(self, "Input Atribut Tidak Valid", "Pastikan seluruh kolom atribut diisi angka yang benar.")
                return

        elif self.current_step == 5:
            try:
                jml = parse_rupiah(self.ent_jml_pinjaman.get())
                tenor = int(self.ent_tenor.get().strip())
                if jml <= Decimal("0"):
                    show_pesan_error(self, "Nilai Tidak Valid", "Jumlah pinjaman harus lebih besar dari 0.")
                    return
                if jml > self.data_gadai["maks_pinjaman"]:
                    show_pesan_error(
                        self, "Melebihi Plafon",
                        f"Jumlah pinjaman {format_rupiah(jml)} melebihi batas maksimal P-Max {format_rupiah(self.data_gadai['maks_pinjaman'])}."
                    )
                    return
                self.data_gadai["jumlah_pinjaman"] = jml
                self.data_gadai["tenor_hari"] = tenor
            except Exception:
                show_pesan_error(self, "Format Salah", "Masukkan jumlah pinjaman dan tenor dalam format angka.")
                return

        elif self.current_step == 6:
            lok = self.ent_lokasi.get().strip()
            kond = self.ent_kondisi_terima.get().strip()
            if not lok:
                show_pesan_error(self, "Lokasi Gudang", "Lokasi penyimpanan barang di gudang wajib diisi.")
                return
            self.data_gadai["lokasi_gudang"] = lok
            self.data_gadai["kondisi_barang"] = kond or "BAIK"

        elif self.current_step == 8:
            self._eksekusi_gadai()
            return

        elif self.current_step == 9:
            self.navigate_to("dashboard")
            return

        self.current_step += 1
        self._render_current_step()

    def _eksekusi_gadai(self):
        """Memanggil facade.ajukan_gadai() untuk menyelesaikan akad."""
        try:
            nsb_id = self.data_gadai["nasabah"].get("id")
            res = self.facade.ajukan_gadai(
                nasabah_id=nsb_id,
                jenis=self.data_gadai["jenis"],
                deskripsi=self.data_gadai["deskripsi"],
                atribut=self.data_gadai["atribut"],
                jumlah_pinjaman=self.data_gadai["jumlah_pinjaman"],
                tenor_hari=self.data_gadai["tenor_hari"],
                lokasi_gudang=self.data_gadai["lokasi_gudang"],
                kondisi_barang=self.data_gadai["kondisi_barang"]
            )
            self.data_gadai["hasil_pinjaman"] = res
            self.current_step = 9
            self._render_current_step()
            show_pesan_sukses(self, "Gadai Berhasil", f"Akad gadai nomor {res.get('no_kontrak', '')} sukses diterbitkan!")
        except PawnError as e:
            show_pesan_error(self, "Gagal Mengajukan Gadai", str(e))
        except Exception as e:
            show_pesan_error(self, "Error Eksekusi", str(e))

    def _reset_wizard(self):
        """Mereset state wizard untuk pengajuan baru."""
        self.current_step = 1
        self.data_gadai["nasabah"] = None
        self.data_gadai["jumlah_pinjaman"] = Decimal("0")
        self.data_gadai["hasil_pinjaman"] = None
        self._render_current_step()
