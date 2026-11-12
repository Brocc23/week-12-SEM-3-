"""
Tampilan Penaksiran Barang Jaminan Pegadaian Digital Nusantara
Menyediakan kalkulator penaksiran multi-kategori (Emas, Kendaraan, Elektronik, Laptop, Lainnya)
sesuai rumus aktuaria dan LTV gadai dalam tata letak scrollable responsif.
"""

import tkinter as tk
from tkinter import ttk
from decimal import Decimal
from typing import Callable, Optional, Dict, Any

from pawn.ui.theme import (
    BG_CARD, BG_CARD_ALT, BG_MAIN, BORDER_COLOR, PRIMARY, PRIMARY_DARK,
    SECONDARY, SECONDARY_LIGHT, DANGER, SUCCESS, INFO, TEXT_MAIN, TEXT_SECONDARY, TEXT_MUTED, TEXT_WHITE,
    FONT_TITLE, FONT_HEADER, FONT_SECTION, FONT_BODY, FONT_BODY_BOLD,
    FONT_LABEL, FONT_SMALL, FONT_SMALL_BOLD, FONT_METRIC,
    format_rupiah, parse_rupiah, show_pesan_error
)
from pawn.ui.widgets import Card, StatCard, ScrollableFrame
try:
    from pawn.errors import PawnError
except ImportError:
    class PawnError(Exception): pass


class PenaksiranView(tk.Frame):
    """Kalkulator dan Workbench Penaksir Barang Jaminan."""
    def __init__(self, parent, facade, navigate_to: Optional[Callable] = None, **kwargs):
        super().__init__(parent, bg=BG_MAIN, **kwargs)
        self.facade = facade
        self.navigate_to = navigate_to
        self.hasil_taksiran: Optional[Dict[str, Any]] = None

        self._build_ui()

    def _build_ui(self):
        # Gunakan ScrollableFrame agar form & hasil tidak terpotong di layar laptop
        scroll = ScrollableFrame(self, bg=BG_MAIN)
        scroll.pack(fill="both", expand=True)

        content = tk.Frame(scroll.scrollable_content, bg=BG_MAIN, padx=24, pady=20)
        content.pack(fill="both", expand=True)

        # 1. Header
        header = tk.Frame(content, bg=BG_MAIN)
        header.pack(fill="x", pady=(0, 16))

        tk.Label(header, text="⚖️ SIMULASI & KALKULATOR PENAKSIRAN AGUNAN",
                 font=FONT_HEADER, fg=TEXT_MAIN, bg=BG_MAIN).pack(anchor="w")
        tk.Label(header, text="Kalkulasi nilai pasar wajar, faktor penyusutan, dan batas maksimum pencairan pinjaman (LTV)",
                 font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_MAIN).pack(anchor="w", pady=(2, 0))

        # 2. Main Layout 2 Kolom (Kiri: Form Input, Kanan: Hasil Perhitungan)
        content_frame = tk.Frame(content, bg=BG_MAIN)
        content_frame.pack(fill="both", expand=True)
        content_frame.grid_columnconfigure(0, weight=3)
        content_frame.grid_columnconfigure(1, weight=2)

        # ------------------ KOLOM KIRI: FORM INPUT ------------------
        card_form = Card(content_frame, padx=20, pady=18)
        card_form.grid(row=0, column=0, sticky="nsew", padx=(0, 14))

        tk.Label(card_form.inner, text="PARAMETER & ATRIBUT BARANG AGUNAN",
                 font=FONT_SECTION, fg=PRIMARY_DARK, bg=BG_CARD).pack(anchor="w", pady=(0, 14))

        # Pilihan Kategori
        tk.Label(card_form.inner, text="Kategori Barang Agunan *", font=FONT_LABEL,
                 fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
        
        self.combo_kategori = ttk.Combobox(card_form.inner, state="readonly",
                                           values=["EMAS", "KENDARAAN", "ELEKTRONIK", "LAPTOP", "LAINNYA"])
        self.combo_kategori.set("EMAS")
        self.combo_kategori.pack(fill="x", pady=(0, 16))
        self.combo_kategori.bind("<<ComboboxSelected>>", lambda e: self._on_kategori_change())

        # Dynamic Field Container
        self.fields_container = tk.Frame(card_form.inner, bg=BG_CARD)
        self.fields_container.pack(fill="both", expand=True)

        self._render_category_fields("EMAS")

        # Tombol Hitung
        btn_calc = ttk.Button(card_form.inner, text="⚡ HITUNG NILAI TAKSIRAN",
                              style="Primary.TButton", command=self._hitung_taksiran)
        btn_calc.pack(fill="x", pady=(18, 0))

        # ------------------ KOLOM KANAN: HASIL KALKULASI ------------------
        card_result = Card(content_frame, padx=20, pady=18)
        card_result.grid(row=0, column=1, sticky="nsew")

        tk.Label(card_result.inner, text="RINGKASAN HASIL TAKSIRAN",
                 font=FONT_SECTION, fg=PRIMARY_DARK, bg=BG_CARD).pack(anchor="w", pady=(0, 14))

        # Card Nilai Taksiran
        self.stat_nilai_taksiran = StatCard(card_result.inner, title="Estimasi Nilai Agunan",
                                            value="Rp 0", subtitle="Nilai barang setelah faktor kondisi",
                                            accent_color=INFO)
        self.stat_nilai_taksiran.pack(fill="x", pady=(0, 12))

        # Card Plafon Maksimal
        self.stat_plafon = StatCard(card_result.inner, title="Maksimal Pinjaman (P-Max)",
                                    value="Rp 0", subtitle="Plafon tertinggi yang dapat disetujui",
                                    accent_color=SECONDARY)
        self.stat_plafon.pack(fill="x", pady=(0, 14))

        # Detail Box
        detail_wrap = tk.Frame(card_result.inner, bg=BORDER_COLOR, padx=1, pady=1, highlightthickness=0, bd=0)
        detail_wrap.pack(fill="x", pady=(0, 16))
        detail_box = tk.Frame(detail_wrap, bg=BG_CARD_ALT, padx=14, pady=12, highlightthickness=0, bd=0)
        detail_box.pack(fill="both", expand=True)

        self.lbl_rasio_persen = tk.Label(detail_box, text="Rasio Pinjaman (LTV): -", font=FONT_LABEL,
                                         fg=TEXT_MAIN, bg=BG_CARD_ALT)
        self.lbl_rasio_persen.pack(anchor="w")

        self.lbl_catatan_rumus = tk.Label(detail_box, text="Pilih kategori dan isi atribut untuk melihat rincian perhitungan aktuaria.",
                                          font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_CARD_ALT, wraplength=280, justify="left")
        self.lbl_catatan_rumus.pack(anchor="w", pady=(6, 0))

        # Tombol Lanjut ke Ajukan Gadai
        if self.navigate_to:
            self.btn_lanjut_gadai = ttk.Button(card_result.inner, text="➡️ Lanjut Ajukan Gadai Barang Ini",
                                               style="Accent.TButton", command=self._lanjut_ke_gadai, state="disabled")
            self.btn_lanjut_gadai.pack(fill="x")

    def _render_category_fields(self, kategori: str):
        """Membuat input dinamis sesuai kategori barang yang dipilih."""
        for w in self.fields_container.winfo_children():
            w.destroy()

        self.inputs = {}

        if kategori == "EMAS":
            tk.Label(self.fields_container, text="Berat Bersih Emas (Gram) *", font=FONT_LABEL,
                     fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
            ent_berat = ttk.Entry(self.fields_container)
            ent_berat.insert(0, "10.0")
            ent_berat.pack(fill="x", pady=(0, 12))
            self.inputs["berat"] = ent_berat

            tk.Label(self.fields_container, text="Kadar Kemurnian Emas (Karat) *", font=FONT_LABEL,
                     fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
            combo_kadar = ttk.Combobox(self.fields_container, state="readonly",
                                       values=["24", "22", "20", "18", "16", "14", "10"])
            combo_kadar.set("24")
            combo_kadar.pack(fill="x", pady=(0, 12))
            self.inputs["kadar"] = combo_kadar

            tk.Label(self.fields_container, text="* Mengacu pada harga pasar acuan emas per gram dari parameter sistem.",
                     font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_CARD).pack(anchor="w")

        elif kategori == "KENDARAAN":
            tk.Label(self.fields_container, text="Harga Pasar Wajar Kendaraan (Rp) *", font=FONT_LABEL,
                     fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
            ent_hp = ttk.Entry(self.fields_container)
            ent_hp.insert(0, "20000000")
            ent_hp.pack(fill="x", pady=(0, 12))
            self.inputs["harga_pasar"] = ent_hp

            tk.Label(self.fields_container, text="Tahun Pembuatan Kendaraan *", font=FONT_LABEL,
                     fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
            ent_tahun = ttk.Entry(self.fields_container)
            ent_tahun.insert(0, "2021")
            ent_tahun.pack(fill="x", pady=(0, 12))
            self.inputs["tahun"] = ent_tahun

            tk.Label(self.fields_container, text="Kondisi Fisik & Mesin Kendaraan *", font=FONT_LABEL,
                     fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
            combo_kondisi = ttk.Combobox(self.fields_container, state="readonly",
                                         values=["BAIK", "CUKUP", "BURUK"])
            combo_kondisi.set("BAIK")
            combo_kondisi.pack(fill="x", pady=(0, 12))
            self.inputs["kondisi"] = combo_kondisi

        elif kategori == "ELEKTRONIK":
            tk.Label(self.fields_container, text="Harga Beli / Pasar Baru (Rp) *", font=FONT_LABEL,
                     fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
            ent_hp = ttk.Entry(self.fields_container)
            ent_hp.insert(0, "5000000")
            ent_hp.pack(fill="x", pady=(0, 12))
            self.inputs["harga_pasar"] = ent_hp

            tk.Label(self.fields_container, text="Umur Pemakaian (Tahun) *", font=FONT_LABEL,
                     fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
            ent_umur = ttk.Entry(self.fields_container)
            ent_umur.insert(0, "1")
            ent_umur.pack(fill="x", pady=(0, 12))
            self.inputs["umur"] = ent_umur

            tk.Label(self.fields_container, text="Kondisi Fisik & Fungsi Perangkat *", font=FONT_LABEL,
                     fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
            combo_kondisi = ttk.Combobox(self.fields_container, state="readonly",
                                         values=["BAIK", "CUKUP", "BURUK"])
            combo_kondisi.set("BAIK")
            combo_kondisi.pack(fill="x", pady=(0, 12))
            self.inputs["kondisi"] = combo_kondisi

        elif kategori == "LAPTOP":
            tk.Label(self.fields_container, text="Harga Beli / Pasar Baru (Rp) *", font=FONT_LABEL,
                     fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
            ent_hp = ttk.Entry(self.fields_container)
            ent_hp.insert(0, "12000000")
            ent_hp.pack(fill="x", pady=(0, 12))
            self.inputs["harga_pasar"] = ent_hp

            tk.Label(self.fields_container, text="Spesifikasi Processor / GPU *", font=FONT_LABEL,
                     fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
            combo_spek = ttk.Combobox(self.fields_container, state="readonly",
                                      values=["LOW", "MID", "HIGH"])
            combo_spek.set("MID")
            combo_spek.pack(fill="x", pady=(0, 12))
            self.inputs["spesifikasi"] = combo_spek

            tk.Label(self.fields_container, text="Umur Pemakaian (Tahun) *", font=FONT_LABEL,
                     fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
            ent_umur = ttk.Entry(self.fields_container)
            ent_umur.insert(0, "1")
            ent_umur.pack(fill="x", pady=(0, 12))
            self.inputs["umur"] = ent_umur

            tk.Label(self.fields_container, text="Kondisi Fisik & Layar *", font=FONT_LABEL,
                     fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
            combo_kondisi = ttk.Combobox(self.fields_container, state="readonly",
                                         values=["BAIK", "CUKUP", "BURUK"])
            combo_kondisi.set("BAIK")
            combo_kondisi.pack(fill="x", pady=(0, 12))
            self.inputs["kondisi"] = combo_kondisi

        elif kategori == "LAINNYA":
            tk.Label(self.fields_container, text="Perkiraan Harga Pasar / Nilai Wajar (Rp) *", font=FONT_LABEL,
                     fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
            ent_hp = ttk.Entry(self.fields_container)
            ent_hp.insert(0, "3000000")
            ent_hp.pack(fill="x", pady=(0, 12))
            self.inputs["harga_pasar"] = ent_hp

            tk.Label(self.fields_container, text="Kondisi Fisik Barang *", font=FONT_LABEL,
                     fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
            combo_kondisi = ttk.Combobox(self.fields_container, state="readonly",
                                         values=["BAIK", "CUKUP", "BURUK"])
            combo_kondisi.set("BAIK")
            combo_kondisi.pack(fill="x", pady=(0, 12))
            self.inputs["kondisi"] = combo_kondisi

    def _on_kategori_change(self):
        kat = self.combo_kategori.get()
        self._render_category_fields(kat)

    def _hitung_taksiran(self):
        kat = self.combo_kategori.get()
        atribut = {}

        try:
            if kat == "EMAS":
                atribut["berat"] = Decimal(self.inputs["berat"].get().strip())
                atribut["kadar"] = int(self.inputs["kadar"].get().strip())
            elif kat == "KENDARAAN":
                atribut["harga_pasar"] = parse_rupiah(self.inputs["harga_pasar"].get())
                atribut["tahun"] = int(self.inputs["tahun"].get().strip())
                atribut["kondisi"] = self.inputs["kondisi"].get().strip()
            elif kat == "ELEKTRONIK":
                atribut["harga_pasar"] = parse_rupiah(self.inputs["harga_pasar"].get())
                atribut["umur"] = int(self.inputs["umur"].get().strip())
                atribut["kondisi"] = self.inputs["kondisi"].get().strip()
            elif kat == "LAPTOP":
                atribut["harga_pasar"] = parse_rupiah(self.inputs["harga_pasar"].get())
                atribut["spesifikasi"] = self.inputs["spesifikasi"].get().strip()
                atribut["umur"] = int(self.inputs["umur"].get().strip())
                atribut["kondisi"] = self.inputs["kondisi"].get().strip()
            elif kat == "LAINNYA":
                atribut["harga_pasar"] = parse_rupiah(self.inputs["harga_pasar"].get())
                atribut["kondisi"] = self.inputs["kondisi"].get().strip()

            res = self.facade.hitung_taksiran(kat, atribut)
            self.hasil_taksiran = res
            self.hasil_taksiran["jenis"] = kat
            self.hasil_taksiran["atribut"] = atribut

            nilai_taksiran = res.get("nilai_taksiran", 0)
            persen = res.get("persen", 0)
            maks_pinjaman = res.get("maks_pinjaman", 0)

            # Persentase format
            try:
                p_float = float(persen) * 100
                persen_str = f"{p_float:.0f}%"
            except Exception:
                persen_str = f"{persen}%"

            self.stat_nilai_taksiran.update_value(format_rupiah(nilai_taksiran))
            self.stat_plafon.update_value(format_rupiah(maks_pinjaman))
            self.lbl_rasio_persen.config(text=f"Rasio Pinjaman (LTV): {persen_str}")
            self.lbl_catatan_rumus.config(
                text=f"Kalkulasi berhasil untuk kategori {kat}. Maksimal plafon dana yang dapat dicairkan adalah {format_rupiah(maks_pinjaman)}."
            )

            if hasattr(self, "btn_lanjut_gadai"):
                self.btn_lanjut_gadai.config(state="normal")

        except PawnError as e:
            show_pesan_error(self, "Gagal Menaksir", str(e))
        except ValueError:
            show_pesan_error(self, "Format Angka Salah", "Pastikan seluruh kolom angka diisi dengan benar.")
        except Exception as e:
            show_pesan_error(self, "Error Perhitungan", str(e))

    def _lanjut_ke_gadai(self):
        if self.navigate_to and self.hasil_taksiran:
            self.navigate_to("gadai", preset=self.hasil_taksiran)
