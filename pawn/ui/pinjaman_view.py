"""
Tampilan Manajemen Pinjaman & Pembayaran Pegadaian Digital Nusantara
Menyediakan fitur detail pinjaman, kalkulasi kewajiban (pokok, bunga, denda, admin),
bayar angsuran waterfall, pelunasan penuh, perpanjangan tenor, dan pengambilan agunan.
"""

import tkinter as tk
from tkinter import ttk
from decimal import Decimal
from typing import Optional, Dict, Any, List

from pawn.ui.theme import (
    BG_CARD, BG_CARD_ALT, BG_MAIN, BORDER_COLOR, PRIMARY, PRIMARY_DARK,
    SECONDARY, SECONDARY_LIGHT, DANGER, SUCCESS, SUCCESS_LIGHT, INFO,
    TEXT_MAIN, TEXT_SECONDARY, TEXT_MUTED, TEXT_WHITE,
    FONT_TITLE, FONT_HEADER, FONT_SECTION, FONT_BODY, FONT_BODY_BOLD,
    FONT_LABEL, FONT_SMALL, FONT_SMALL_BOLD, FONT_METRIC,
    format_rupiah, parse_rupiah, format_date, show_konfirmasi, show_pesan_sukses, show_pesan_error
)
from pawn.ui.widgets import Card, StatCard, DataTable, FormDialog
try:
    from pawn.errors import PawnError
except ImportError:
    class PawnError(Exception): pass


class BayarAngsuranDialog(FormDialog):
    """Dialog pembayaran angsuran dengan pemilihan metode dan validasi jumlah."""
    def __init__(self, parent, facade, pinjaman: Dict[str, Any], kewajiban: Dict[str, Any], on_success):
        super().__init__(parent, title=f"Bayar Angsuran — {pinjaman.get('no_kontrak')}", width=520, height=440)
        self.facade = facade
        self.pinjaman = pinjaman
        self.kewajiban = kewajiban
        self.on_success = on_success
        self._build_form()

    def _build_form(self):
        total = self.kewajiban.get("total", 0)
        wrap_info = tk.Frame(self.body, bg=BORDER_COLOR, padx=1, pady=1, highlightthickness=0, bd=0)
        wrap_info.pack(fill="x", pady=(0, 16))
        info_frame = tk.Frame(wrap_info, bg=BG_CARD_ALT, padx=16, pady=12, highlightthickness=0, bd=0)
        info_frame.pack(fill="both", expand=True)

        tk.Label(info_frame, text=f"Total Kewajiban Tertunggak: {format_rupiah(total)}",
                 font=FONT_LABEL, fg=PRIMARY_DARK, bg=BG_CARD_ALT).pack(anchor="w")
        
        breakdown_txt = (
            f"Sisa Pokok: {format_rupiah(self.kewajiban.get('sisa_pokok', 0))}  |  "
            f"Bunga: {format_rupiah(self.kewajiban.get('bunga', 0))}  |  "
            f"Denda: {format_rupiah(self.kewajiban.get('denda', 0))}"
        )
        tk.Label(info_frame, text=breakdown_txt, font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_CARD_ALT).pack(anchor="w", pady=(2, 0))

        tk.Label(self.body, text="Jumlah Pembayaran Angsuran (Rp) *", font=FONT_LABEL,
                 fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
        self.ent_jumlah = ttk.Entry(self.body, font=FONT_BODY)
        self.ent_jumlah.pack(fill="x", pady=(0, 14))
        self.ent_jumlah.focus_set()

        tk.Label(self.body, text="Metode Pembayaran *", font=FONT_LABEL,
                 fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
        
        try:
            metodes = self.facade.daftar_metode()
        except Exception:
            metodes = ["TUNAI", "TRANSFER", "QRIS", "EWALLET"]
            
        self.combo_metode = ttk.Combobox(self.body, state="readonly", values=metodes)
        self.combo_metode.set(metodes[0] if metodes else "TUNAI")
        self.combo_metode.pack(fill="x", pady=(0, 14))

        tk.Label(self.body, text="* Pembayaran dialokasikan bertingkat (Waterfall): Biaya Admin ➔ Denda ➔ Bunga ➔ Pokok Pinjaman.",
                 font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_CARD, wraplength=440, justify="left").pack(anchor="w")

    def on_submit(self):
        jml = parse_rupiah(self.ent_jumlah.get())
        metode = self.combo_metode.get()

        if jml <= Decimal("0"):
            self.show_error("Jumlah pembayaran harus lebih besar dari Rp 0.")
            return

        no_kontrak = self.pinjaman.get("no_kontrak")
        try:
            tx = self.facade.bayar_angsuran(no_kontrak, jml, metode)
            show_pesan_sukses(
                self, "Pembayaran Berhasil",
                f"Angsuran sebesar {format_rupiah(jml)} sukses dibukukan via {metode}.\nNo. Bukti Transaksi: {tx.get('no_transaksi', '-')}"
            )
            self.on_success()
            self.destroy()
        except PawnError as e:
            self.show_error(str(e))
        except Exception as e:
            self.show_error(f"Gagal memproses pembayaran: {str(e)}")


class PelunasanDialog(FormDialog):
    """Dialog pelunasan penuh pinjaman gadai."""
    def __init__(self, parent, facade, pinjaman: Dict[str, Any], kewajiban: Dict[str, Any], on_success):
        super().__init__(parent, title=f"Pelunasan Penuh — {pinjaman.get('no_kontrak')}", width=520, height=440)
        self.facade = facade
        self.pinjaman = pinjaman
        self.kewajiban = kewajiban
        self.on_success = on_success
        self._build_form()

    def _build_form(self):
        total = self.kewajiban.get("total", 0)

        wrap_alert = tk.Frame(self.body, bg=BORDER_COLOR, padx=1, pady=1, highlightthickness=0, bd=0)
        wrap_alert.pack(fill="x", pady=(0, 16))
        alert_box = tk.Frame(wrap_alert, bg=SUCCESS_LIGHT, padx=16, pady=12, highlightthickness=0, bd=0)
        alert_box.pack(fill="both", expand=True)

        tk.Label(alert_box, text=f"TOTAL KEWAJIBAN PELUNASAN: {format_rupiah(total)}",
                 font=FONT_SECTION, fg=PRIMARY_DARK, bg=SUCCESS_LIGHT).pack(anchor="w")
        
        detail_txt = (
            f"Pokok: {format_rupiah(self.kewajiban.get('sisa_pokok', 0))}  |  "
            f"Bunga: {format_rupiah(self.kewajiban.get('bunga', 0))}  |  "
            f"Denda: {format_rupiah(self.kewajiban.get('denda', 0))}  |  "
            f"Admin: {format_rupiah(self.kewajiban.get('biaya_admin', 0))}"
        )
        tk.Label(alert_box, text=detail_txt, font=FONT_SMALL, fg=TEXT_MAIN, bg=SUCCESS_LIGHT).pack(anchor="w", pady=(4, 0))

        tk.Label(self.body, text="Nominal Pembayaran (Rp) *", font=FONT_LABEL,
                 fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
        self.ent_jumlah = ttk.Entry(self.body, font=FONT_BODY)
        self.ent_jumlah.insert(0, str(total))
        self.ent_jumlah.pack(fill="x", pady=(0, 14))

        tk.Label(self.body, text="Metode Pembayaran *", font=FONT_LABEL,
                 fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
        try:
            metodes = self.facade.daftar_metode()
        except Exception:
            metodes = ["TUNAI", "TRANSFER", "QRIS", "EWALLET"]
            
        self.combo_metode = ttk.Combobox(self.body, state="readonly", values=metodes)
        self.combo_metode.set(metodes[0] if metodes else "TUNAI")
        self.combo_metode.pack(fill="x", pady=(0, 14))

    def on_submit(self):
        jml = parse_rupiah(self.ent_jumlah.get())
        total_harus = Decimal(str(self.kewajiban.get("total", 0)))
        metode = self.combo_metode.get()

        if jml < total_harus:
            self.show_error(
                f"Nominal pembayaran ({format_rupiah(jml)}) kurang dari total kewajiban ({format_rupiah(total_harus)})."
            )
            return

        no_kontrak = self.pinjaman.get("no_kontrak")
        try:
            self.facade.lunasi(no_kontrak, jml, metode)
            show_pesan_sukses(
                self, "Pelunasan Berhasil",
                f"Pinjaman {no_kontrak} dinyatakan LUNAS!\nBarang agunan kini dapat diserahkan kembali kepada nasabah."
            )
            self.on_success()
            self.destroy()
        except PawnError as e:
            self.show_error(str(e))
        except Exception as e:
            self.show_error(f"Gagal pelunasan: {str(e)}")


class PerpanjangDialog(FormDialog):
    """Dialog perpanjangan tenor pinjaman gadai."""
    def __init__(self, parent, facade, pinjaman: Dict[str, Any], kewajiban: Dict[str, Any], on_success):
        super().__init__(parent, title=f"Perpanjangan Tenor — {pinjaman.get('no_kontrak')}", width=520, height=380)
        self.facade = facade
        self.pinjaman = pinjaman
        self.kewajiban = kewajiban
        self.on_success = on_success
        self._build_form()

    def _build_form(self):
        wrap_box = tk.Frame(self.body, bg=BORDER_COLOR, padx=1, pady=1, highlightthickness=0, bd=0)
        wrap_box.pack(fill="x", pady=(0, 16))
        box = tk.Frame(wrap_box, bg=BG_CARD_ALT, padx=16, pady=12, highlightthickness=0, bd=0)
        box.pack(fill="both", expand=True)

        count_perpanjang = self.pinjaman.get("jumlah_perpanjangan", 0)
        tk.Label(box, text=f"Jumlah Perpanjangan Sebelumnya: {count_perpanjang} Kali (Maksimal 2 Kali)",
                 font=FONT_LABEL, fg=TEXT_MAIN, bg=BG_CARD_ALT).pack(anchor="w")

        info_biaya = (
            "Perpanjangan tenor memerlukan pelunasan seluruh bunga berjalan, denda keterlambatan (bila ada), "
            "serta pembayaran biaya administrasi perpanjangan (1% dari pokok pinjaman)."
        )
        tk.Label(box, text=info_biaya, font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_CARD_ALT,
                 wraplength=440, justify="left").pack(anchor="w", pady=(6, 0))

        tk.Label(self.body, text="Metode Pembayaran Biaya Perpanjangan *", font=FONT_LABEL,
                 fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
        try:
            metodes = self.facade.daftar_metode()
        except Exception:
            metodes = ["TUNAI", "TRANSFER", "QRIS", "EWALLET"]
            
        self.combo_metode = ttk.Combobox(self.body, state="readonly", values=metodes)
        self.combo_metode.set(metodes[0] if metodes else "TUNAI")
        self.combo_metode.pack(fill="x", pady=(0, 14))

    def on_submit(self):
        metode = self.combo_metode.get()
        no_kontrak = self.pinjaman.get("no_kontrak")
        try:
            self.facade.perpanjang(no_kontrak, metode)
            show_pesan_sukses(
                self, "Perpanjangan Sukses",
                f"Tenor pinjaman {no_kontrak} berhasil diperpanjang!\nTanggal jatuh tempo baru telah disesuaikan."
            )
            self.on_success()
            self.destroy()
        except PawnError as e:
            self.show_error(str(e))
        except Exception as e:
            self.show_error(f"Gagal perpanjangan: {str(e)}")


class PinjamanView(tk.Frame):
    """Tampilan Operasional Daftar Pinjaman & Eksekusi Pembayaran."""
    def __init__(self, parent, facade, **kwargs):
        super().__init__(parent, bg=BG_MAIN, padx=24, pady=20, **kwargs)
        self.facade = facade
        self.pinjaman_terpilih: Optional[Dict[str, Any]] = None
        self.kewajiban_terpilih: Optional[Dict[str, Any]] = None

        self._build_ui()
        self.refresh_data()

    def _build_ui(self):
        # 1. Header
        header = tk.Frame(self, bg=BG_MAIN)
        header.pack(fill="x", pady=(0, 16))

        title_box = tk.Frame(header, bg=BG_MAIN)
        title_box.pack(side="left")

        tk.Label(title_box, text="KONTRAK PINJAMAN & PEMBAYARAN", font=FONT_HEADER,
                 fg=TEXT_MAIN, bg=BG_MAIN).pack(anchor="w")
        tk.Label(title_box, text="Kelola buku pinjaman kredit, detail kewajiban bunga/denda, angsuran, pelunasan, dan serah terima agunan",
                 font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_MAIN).pack(anchor="w", pady=(2, 0))

        # 2. Filter Bar Card
        filter_card = Card(self, padx=16, pady=12)
        filter_card.pack(fill="x", pady=(0, 16))

        fb = tk.Frame(filter_card.inner, bg=BG_CARD)
        fb.pack(fill="x")

        tk.Label(fb, text="Cari Kontrak/Nasabah:", font=FONT_LABEL, fg=TEXT_MAIN, bg=BG_CARD).pack(side="left", padx=(0, 6))
        self.ent_cari = ttk.Entry(fb, width=22)
        self.ent_cari.pack(side="left", padx=(0, 12))
        self.ent_cari.bind("<Return>", lambda e: self.refresh_data())

        tk.Label(fb, text="Status:", font=FONT_LABEL, fg=TEXT_MAIN, bg=BG_CARD).pack(side="left", padx=(0, 6))
        self.combo_status = ttk.Combobox(
            fb, state="readonly", width=18,
            values=["SEMUA", "AKTIF", "JATUH_TEMPO", "DALAM_PROSES_LELANG", "LUNAS", "TERLELANG", "DIKEMBALIKAN"]
        )
        self.combo_status.set("SEMUA")
        self.combo_status.pack(side="left", padx=(0, 12))
        self.combo_status.bind("<<ComboboxSelected>>", lambda e: self.refresh_data())

        ttk.Button(fb, text="🔍 Terapkan", style="Secondary.TButton",
                   command=self.refresh_data).pack(side="left", padx=(0, 8))

        ttk.Button(fb, text="Reset", style="Secondary.TButton",
                   command=self._reset_filter).pack(side="left")

        # 3. Detail Panel & Hub Aksi Bawah (Di-pack ke bawah terlebih dahulu agar selalu tampil utuh)
        self.detail_card = Card(self, padx=18, pady=14)
        self.detail_card.pack(fill="x", side="bottom")

        self.hub_frame = tk.Frame(self.detail_card.inner, bg=BG_CARD)
        self.hub_frame.pack(fill="x")

        # Kiri: Rincian Kewajiban
        wrap_kewajiban = tk.Frame(self.hub_frame, bg=BORDER_COLOR, padx=1, pady=1, highlightthickness=0, bd=0)
        wrap_kewajiban.pack(side="left", fill="both", expand=True, padx=(0, 14))
        self.kewajiban_box = tk.Frame(wrap_kewajiban, bg=BG_CARD_ALT, padx=16, pady=12, highlightthickness=0, bd=0)
        self.kewajiban_box.pack(fill="both", expand=True)

        self.lbl_kewajiban_title = tk.Label(self.kewajiban_box, text="PILIH SALAH SATU PINJAMAN DI ATAS",
                                            font=FONT_SECTION, fg=TEXT_MUTED, bg=BG_CARD_ALT)
        self.lbl_kewajiban_title.pack(anchor="w")

        self.lbl_kewajiban_detail = tk.Label(self.kewajiban_box, text="Klik salah satu baris untuk melihat rincian sisa kewajiban dan mengaktifkan tombol aksi.",
                                             font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_CARD_ALT)
        self.lbl_kewajiban_detail.pack(anchor="w", pady=(4, 0))

        # Kanan: Tombol-tombol Aksi Operasional
        self.action_box = tk.Frame(self.hub_frame, bg=BG_CARD)
        self.action_box.pack(side="right")

        self.btn_angsur = ttk.Button(self.action_box, text="💵 Bayar Angsuran",
                                     style="Primary.TButton", command=self._buka_bayar_angsuran, state="disabled")
        self.btn_angsur.pack(fill="x", pady=2)

        self.btn_lunasi = ttk.Button(self.action_box, text="🏁 Pelunasan Penuh",
                                     style="Accent.TButton", command=self._buka_pelunasan, state="disabled")
        self.btn_lunasi.pack(fill="x", pady=2)

        self.btn_perpanjang = ttk.Button(self.action_box, text="⏳ Perpanjang Tenor",
                                         style="Secondary.TButton", command=self._buka_perpanjangan, state="disabled")
        self.btn_perpanjang.pack(fill="x", pady=2)

        self.btn_ambil = ttk.Button(self.action_box, text="📦 Ambil Barang Jaminan",
                                    style="Secondary.TButton", command=self._ambil_barang, state="disabled")
        self.btn_ambil.pack(fill="x", pady=2)

        # 4. Main Split View (Tabel Pinjaman mengisi ruang tengah yang tersisa)
        table_card = Card(self, padx=16, pady=16)
        table_card.pack(fill="both", expand=True, pady=(0, 14))

        cols = [
            ("no_kontrak", "No. Kontrak", 125, "w"),
            ("nasabah_nama", "Nama Nasabah", 135, "w"),
            ("barang_nama", "Agunan", 120, "w"),
            ("pokok", "Plafon", 105, "e"),
            ("sisa_pokok", "Sisa Pokok", 105, "e"),
            ("tgl_jatuh_tempo", "Jatuh Tempo", 110, "center"),
            ("jumlah_perpanjangan", "Perpanjang", 75, "center"),
            ("status", "Status", 90, "center"),
        ]

        self.table = DataTable(table_card.inner, columns=cols, stretch_col="nasabah_nama",
                               show_hsb=False,
                               on_select=self._on_pinjaman_selected)
        self.table.pack(fill="both", expand=True)

    def _reset_filter(self):
        self.ent_cari.delete(0, tk.END)
        self.combo_status.set("SEMUA")
        self.refresh_data()

    def _on_pinjaman_selected(self, row: Optional[Dict[str, Any]]):
        self.pinjaman_terpilih = row
        if not row:
            self.lbl_kewajiban_title.config(text="PILIH SALAH SATU PINJAMAN DI ATAS", fg=TEXT_MUTED)
            self.lbl_kewajiban_detail.config(text="Klik salah satu baris untuk melihat rincian kewajiban.")
            self.btn_angsur.config(state="disabled")
            self.btn_lunasi.config(state="disabled")
            self.btn_perpanjang.config(state="disabled")
            self.btn_ambil.config(state="disabled")
            return

        no_kontrak = row.get("no_kontrak", "")
        status = str(row.get("status", "")).upper()

        try:
            self.kewajiban_terpilih = self.facade.hitung_kewajiban(no_kontrak)
            total = self.kewajiban_terpilih.get("total", 0)
            pokok = self.kewajiban_terpilih.get("sisa_pokok", 0)
            bunga = self.kewajiban_terpilih.get("bunga", 0)
            admin = self.kewajiban_terpilih.get("biaya_admin", 0)
            denda = self.kewajiban_terpilih.get("denda", 0)

            self.lbl_kewajiban_title.config(
                text=f"{no_kontrak}  —  TOTAL KEWAJIBAN: {format_rupiah(total)}",
                fg=PRIMARY_DARK
            )
            self.lbl_kewajiban_detail.config(
                text=f"Sisa Pokok: {format_rupiah(pokok)}  |  Bunga: {format_rupiah(bunga)}  |  Denda: {format_rupiah(denda)}  |  Admin: {format_rupiah(admin)}"
            )
        except Exception:
            self.lbl_kewajiban_title.config(text=f"{no_kontrak} (Status: {status})", fg=TEXT_MAIN)
            self.lbl_kewajiban_detail.config(text="Kalkulasi kewajiban otomatis dari sistem.")

        if status in ("AKTIF", "JATUH_TEMPO"):
            self.btn_angsur.config(state="normal")
            self.btn_lunasi.config(state="normal")
            self.btn_perpanjang.config(state="normal")
            self.btn_ambil.config(state="disabled")
        elif status == "LUNAS":
            self.btn_angsur.config(state="disabled")
            self.btn_lunasi.config(state="disabled")
            self.btn_perpanjang.config(state="disabled")
            self.btn_ambil.config(state="normal")
        else:
            self.btn_angsur.config(state="disabled")
            self.btn_lunasi.config(state="disabled")
            self.btn_perpanjang.config(state="disabled")
            self.btn_ambil.config(state="disabled")

    def _buka_bayar_angsuran(self):
        if self.pinjaman_terpilih and self.kewajiban_terpilih:
            BayarAngsuranDialog(self, self.facade, self.pinjaman_terpilih, self.kewajiban_terpilih,
                                on_success=self.refresh_data)

    def _buka_pelunasan(self):
        if self.pinjaman_terpilih and self.kewajiban_terpilih:
            PelunasanDialog(self, self.facade, self.pinjaman_terpilih, self.kewajiban_terpilih,
                            on_success=self.refresh_data)

    def _buka_perpanjangan(self):
        if self.pinjaman_terpilih and self.kewajiban_terpilih:
            PerpanjangDialog(self, self.facade, self.pinjaman_terpilih, self.kewajiban_terpilih,
                             on_success=self.refresh_data)

    def _ambil_barang(self):
        if not self.pinjaman_terpilih:
            return
        no_kontrak = self.pinjaman_terpilih.get("no_kontrak")
        pesan = (f"Konfirmasi penyerahan barang jaminan untuk kontrak {no_kontrak}?\n\n"
                 "Pastikan identitas nasabah telah diverifikasi dan fisik barang diserahkan dalam keadaan baik. "
                 "Status barang akan diubah menjadi DIKEMBALIKAN.")
        if show_konfirmasi(self, "Serah Terima Agunan", pesan):
            try:
                self.facade.ambil_barang(no_kontrak)
                show_pesan_sukses(self, "Barang Diserahkan", f"Barang jaminan untuk {no_kontrak} resmi diserahkan kembali kepada nasabah.")
                self.refresh_data()
            except PawnError as e:
                show_pesan_error(self, "Gagal Ambil Barang", str(e))
            except Exception as e:
                show_pesan_error(self, "Error", str(e))

    def refresh_data(self):
        """Memuat daftar pinjaman sesuai filter."""
        try:
            status_filter = self.combo_status.get()
            status_param = None if status_filter == "SEMUA" else status_filter
            cari_param = self.ent_cari.get().strip()

            data = self.facade.daftar_pinjaman(status=status_param, cari=cari_param)
            formatters = {
                "pokok": lambda v, r: format_rupiah(v),
                "sisa_pokok": lambda v, r: format_rupiah(v),
                "tgl_jatuh_tempo": lambda v, r: format_date(v)
            }
            self.table.set_data(data, formatters=formatters)
            self._on_pinjaman_selected(None)
        except Exception:
            pass
