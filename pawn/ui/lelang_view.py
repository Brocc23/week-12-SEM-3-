"""
Tampilan Manajemen Jatuh Tempo & Lelang Agunan Pegadaian Digital Nusantara
Mengelola deteksi otomatis pinjaman kedaluwarsa, tahapan notifikasi debitur,
inisiasi lelang, dan eksekusi penyelesaian lelang (Surplus, Impas, Defisit).
"""

import tkinter as tk
from tkinter import ttk
from decimal import Decimal
from typing import Optional, Dict, Any, List

from pawn.ui.theme import (
    BG_CARD, BG_CARD_ALT, BG_MAIN, BORDER_COLOR, PRIMARY, PRIMARY_DARK,
    SECONDARY, SECONDARY_LIGHT, DANGER, DANGER_LIGHT, SUCCESS, SUCCESS_LIGHT,
    INFO, TEXT_MAIN, TEXT_SECONDARY, TEXT_MUTED, TEXT_WHITE,
    FONT_TITLE, FONT_HEADER, FONT_SECTION, FONT_BODY, FONT_BODY_BOLD,
    FONT_LABEL, FONT_SMALL, FONT_SMALL_BOLD, FONT_METRIC,
    format_rupiah, parse_rupiah, format_date, show_konfirmasi, show_pesan_sukses, show_pesan_error
)
from pawn.ui.widgets import Card, StatCard, DataTable, FormDialog
try:
    from pawn.errors import PawnError
except ImportError:
    class PawnError(Exception): pass


class SelesaikanLelangDialog(FormDialog):
    """Dialog penyelesaian lelang barang jaminan dengan kalkulasi surplus/defisit."""
    def __init__(self, parent, facade, pinjaman: Dict[str, Any], on_success):
        super().__init__(parent, title=f"Eksekusi Hasil Lelang — {pinjaman.get('no_kontrak')}", width=540, height=480)
        self.facade = facade
        self.pinjaman = pinjaman
        self.on_success = on_success
        self._build_form()

    def _build_form(self):
        no_kontrak = self.pinjaman.get("no_kontrak")
        
        try:
            kewajiban = self.facade.hitung_kewajiban(no_kontrak)
            self.total_kewajiban = Decimal(str(kewajiban.get("total", 0)))
        except Exception:
            self.total_kewajiban = Decimal("0")

        box_wrap = tk.Frame(self.body, bg=BORDER_COLOR, padx=1, pady=1, highlightthickness=0, bd=0)
        box_wrap.pack(fill="x", pady=(0, 16))
        box = tk.Frame(box_wrap, bg=BG_CARD_ALT, padx=16, pady=12, highlightthickness=0, bd=0)
        box.pack(fill="both", expand=True)

        tk.Label(box, text=f"Total Kewajiban Tertunggak: {format_rupiah(self.total_kewajiban)}",
                 font=FONT_SECTION, fg=DANGER, bg=BG_CARD_ALT).pack(anchor="w")
        tk.Label(box, text=f"Barang: {self.pinjaman.get('barang_nama', '-')}  |  Debitur: {self.pinjaman.get('nasabah_nama', '-')}",
                 font=FONT_SMALL, fg=TEXT_MAIN, bg=BG_CARD_ALT).pack(anchor="w", pady=(2, 0))

        tk.Label(self.body, text="Harga Terjual Lelang (Rp) *", font=FONT_LABEL,
                 fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
        self.ent_harga = ttk.Entry(self.body, font=FONT_BODY)
        self.ent_harga.pack(fill="x", pady=(0, 10))
        self.ent_harga.focus_set()
        self.ent_harga.bind("<KeyRelease>", lambda e: self._on_harga_change())

        # Live calculation preview box
        calc_wrap = tk.Frame(self.body, bg=BORDER_COLOR, padx=1, pady=1, highlightthickness=0, bd=0)
        calc_wrap.pack(fill="x", pady=(0, 14))
        self.calc_box = tk.Frame(calc_wrap, bg=BG_CARD_ALT, padx=14, pady=12, highlightthickness=0, bd=0)
        self.calc_box.pack(fill="both", expand=True)

        self.lbl_selisih = tk.Label(self.calc_box, text="Selisih Hasil: -", font=FONT_LABEL,
                                    fg=TEXT_MAIN, bg=BG_CARD_ALT)
        self.lbl_selisih.pack(anchor="w")

        self.lbl_status_hasil = tk.Label(self.calc_box, text="Masukkan nominal harga penjualan lelang untuk menghitung surplus/defisit.",
                                         font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_CARD_ALT, wraplength=440, justify="left")
        self.lbl_status_hasil.pack(anchor="w", pady=(4, 0))

    def _on_harga_change(self):
        try:
            harga = parse_rupiah(self.ent_harga.get())
            selisih = harga - self.total_kewajiban

            if selisih > 0:
                self.lbl_selisih.config(text=f"Selisih: +{format_rupiah(selisih)} (SURPLUS)", fg=SUCCESS)
                self.lbl_status_hasil.config(
                    text=f"Kelebihan dana sebesar {format_rupiah(selisih)} merupakan Hak Nasabah yang wajib dikembalikan."
                )
            elif selisih < 0:
                defisit = abs(selisih)
                self.lbl_selisih.config(text=f"Selisih: -{format_rupiah(defisit)} (DEFISIT)", fg=DANGER)
                self.lbl_status_hasil.config(
                    text=f"Kekurangan dana sebesar {format_rupiah(defisit)} dicatat sebagai Kerugian Lelang Pegadaian."
                )
            else:
                self.lbl_selisih.config(text=f"Selisih: {format_rupiah(0)} (IMPAS)", fg=INFO)
                self.lbl_status_hasil.config(text="Hasil lelang tepat menutup seluruh kewajiban tanpa sisa/kekurangan.")
        except Exception:
            pass

    def on_submit(self):
        harga = parse_rupiah(self.ent_harga.get())
        if harga <= Decimal("0"):
            self.show_error("Harga lelang harus lebih besar dari Rp 0.")
            return

        no_kontrak = self.pinjaman.get("no_kontrak")
        try:
            res = self.facade.selesaikan_lelang(no_kontrak, harga)
            hasil = res.get("hasil", "SELESAI")
            hak = res.get("hak_nasabah", 0)
            rugi = res.get("kerugian", 0)

            msg = f"Lelang untuk kontrak {no_kontrak} berhasil diselesaikan!\nHasil: {hasil}\n"
            if hasil == "SURPLUS":
                msg += f"Hak Nasabah: {format_rupiah(hak)}"
            elif hasil == "DEFISIT":
                msg += f"Kerugian Pegadaian: {format_rupiah(rugi)}"
            else:
                msg += "Seluruh kewajiban terpenuhi pas (IMPAS)."

            show_pesan_sukses(self, "Lelang Selesai", msg)
            self.on_success()
            self.destroy()
        except PawnError as e:
            self.show_error(str(e))
        except Exception as e:
            self.show_error(f"Gagal menyelesaikan lelang: {str(e)}")


class LelangView(tk.Frame):
    """Tampilan Manajemen Jatuh Tempo, Notifikasi, dan Pelaksanaan Lelang."""
    def __init__(self, parent, facade, **kwargs):
        super().__init__(parent, bg=BG_MAIN, padx=24, pady=20, **kwargs)
        self.facade = facade
        self._build_ui()
        self.refresh_data()

    def _build_ui(self):
        # 1. Header & Tombol Deteksi Cepat
        header = tk.Frame(self, bg=BG_MAIN)
        header.pack(fill="x", pady=(0, 16))

        title_box = tk.Frame(header, bg=BG_MAIN)
        title_box.pack(side="left")

        tk.Label(title_box, text="⏰ JATUH TEMPO & MANAJEMEN LELANG AGUNAN", font=FONT_HEADER,
                 fg=TEXT_MAIN, bg=BG_MAIN).pack(anchor="w")
        tk.Label(title_box, text="Otomasi deteksi kredit macet, penertiban surat peringatan berjenjang, dan eksekusi penjualan lelang",
                 font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_MAIN).pack(anchor="w", pady=(2, 0))

        btn_deteksi = ttk.Button(header, text="⚡ Jalankan Deteksi Jatuh Tempo",
                                 style="Accent.TButton", command=self._jalankan_deteksi)
        btn_deteksi.pack(side="right")

        # 2. Tab Notebook
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True)

        self.tab_jatuh_tempo = tk.Frame(self.tabs, bg=BG_MAIN, padx=12, pady=14)
        self.tabs.add(self.tab_jatuh_tempo, text=" ⚠️ Pinjaman Jatuh Tempo ")
        self._build_tab_jatuh_tempo()

        self.tab_siap_lelang = tk.Frame(self.tabs, bg=BG_MAIN, padx=12, pady=14)
        self.tabs.add(self.tab_siap_lelang, text=" 🔨 Proses Lelang Berjalan ")
        self._build_tab_siap_lelang()

        self.tab_riwayat_lelang = tk.Frame(self.tabs, bg=BG_MAIN, padx=12, pady=14)
        self.tabs.add(self.tab_riwayat_lelang, text=" 📜 Riwayat Lelang Selesai ")
        self._build_tab_riwayat_lelang()

    # --- TAB 1: PINJAMAN JATUH TEMPO ---
    def _build_tab_jatuh_tempo(self):
        table_card = Card(self.tab_jatuh_tempo, padx=16, pady=16)
        table_card.pack(fill="both", expand=True, pady=(0, 14))

        cols = [
            ("no_kontrak", "No. Kontrak", 140, "w"),
            ("nasabah_nama", "Nama Nasabah", 160, "w"),
            ("barang_nama", "Barang Jaminan", 140, "w"),
            ("sisa_pokok", "Sisa Pokok", 120, "e"),
            ("tgl_jatuh_tempo", "Jatuh Tempo", 130, "center"),
            ("status", "Status", 100, "center"),
        ]
        self.tbl_jatuh_tempo = DataTable(table_card.inner, columns=cols, stretch_col="nasabah_nama",
                                         on_select=self._on_select_jt)
        self.tbl_jatuh_tempo.pack(fill="both", expand=True)

        # Action bar
        bar_wrap = tk.Frame(self.tab_jatuh_tempo, bg=BORDER_COLOR, padx=1, pady=1, highlightthickness=0, bd=0)
        bar_wrap.pack(fill="x")
        bar = tk.Frame(bar_wrap, bg=BG_CARD, padx=16, pady=12, highlightthickness=0, bd=0)
        bar.pack(fill="both", expand=True)

        self.lbl_info_jt = tk.Label(bar, text="Pilih kontrak jatuh tempo di atas untuk memberikan notifikasi.",
                                    font=FONT_BODY, fg=TEXT_MUTED, bg=BG_CARD)
        self.lbl_info_jt.pack(side="left")

        actions = tk.Frame(bar, bg=BG_CARD)
        actions.pack(side="right")

        self.btn_notif = ttk.Button(actions, text="📩 Kirim Notifikasi (Tahap 1 / 2)",
                                    style="Secondary.TButton", command=self._kirim_notif, state="disabled")
        self.btn_notif.pack(side="left", padx=(0, 8))

        self.btn_mulai_lelang = ttk.Button(actions, text="🔨 Mulai Proses Lelang",
                                           style="Danger.TButton", command=self._mulai_lelang, state="disabled")
        self.btn_mulai_lelang.pack(side="left")

    def _on_select_jt(self, row: Optional[Dict[str, Any]]):
        self.jt_terpilih = row
        if row:
            self.lbl_info_jt.config(text=f"Kontrak Terpilih: {row.get('no_kontrak')} ({row.get('nasabah_nama')})")
            self.btn_notif.config(state="normal")
            self.btn_mulai_lelang.config(state="normal")
        else:
            self.lbl_info_jt.config(text="Pilih kontrak jatuh tempo di atas untuk tindakan.")
            self.btn_notif.config(state="disabled")
            self.btn_mulai_lelang.config(state="disabled")

    def _kirim_notif(self):
        if not hasattr(self, "jt_terpilih") or not self.jt_terpilih:
            return
        no_kontrak = self.jt_terpilih.get("no_kontrak")
        try:
            res = self.facade.kirim_notifikasi_lelang(no_kontrak)
            tahap = res.get("tahap", "-")
            show_pesan_sukses(
                self, "Notifikasi Terkirim",
                f"Surat Peringatan Lelang Tahap {tahap} untuk kontrak {no_kontrak} berhasil diterbitkan dan dicatat."
            )
            self.refresh_data()
        except PawnError as e:
            show_pesan_error(self, "Gagal Kirim Notifikasi", str(e))
        except Exception as e:
            show_pesan_error(self, "Error", str(e))

    def _mulai_lelang(self):
        if not hasattr(self, "jt_terpilih") or not self.jt_terpilih:
            return
        no_kontrak = self.jt_terpilih.get("no_kontrak")
        pesan = (f"Apakah Anda yakin ingin memindahkan kontrak {no_kontrak} ke proses lelang publik?\n\n"
                 "Pastikan masa tenggang dan tahapan notifikasi debitur telah terpenuhi.")
        if show_konfirmasi(self, "Mulai Lelang", pesan):
            try:
                self.facade.mulai_proses_lelang(no_kontrak)
                show_pesan_sukses(self, "Lelang Dimulai", f"Kontrak {no_kontrak} kini berstatus DALAM_PROSES_LELANG.")
                self.refresh_data()
            except PawnError as e:
                show_pesan_error(self, "Gagal Memulai Lelang", str(e))
            except Exception as e:
                show_pesan_error(self, "Error", str(e))

    # --- TAB 2: PROSES LELANG BERJALAN ---
    def _build_tab_siap_lelang(self):
        table_card = Card(self.tab_siap_lelang, padx=16, pady=16)
        table_card.pack(fill="both", expand=True, pady=(0, 14))

        cols = [
            ("no_kontrak", "No. Kontrak", 140, "w"),
            ("nasabah_nama", "Nama Nasabah", 160, "w"),
            ("barang_nama", "Barang Agunan", 150, "w"),
            ("sisa_pokok", "Sisa Pokok", 120, "e"),
            ("status", "Status", 140, "center"),
        ]
        self.tbl_siap_lelang = DataTable(table_card.inner, columns=cols, stretch_col="barang_nama",
                                         on_select=self._on_select_sl)
        self.tbl_siap_lelang.pack(fill="both", expand=True)

        bar_wrap = tk.Frame(self.tab_siap_lelang, bg=BORDER_COLOR, padx=1, pady=1, highlightthickness=0, bd=0)
        bar_wrap.pack(fill="x")
        bar = tk.Frame(bar_wrap, bg=BG_CARD, padx=16, pady=12, highlightthickness=0, bd=0)
        bar.pack(fill="both", expand=True)

        self.lbl_info_sl = tk.Label(bar, text="Pilih agunan lelang untuk eksekusi penjualan.",
                                    font=FONT_BODY, fg=TEXT_MUTED, bg=BG_CARD)
        self.lbl_info_sl.pack(side="left")

        self.btn_eksekusi_lelang = ttk.Button(bar, text="🔨 Selesaikan & Eksekusi Lelang",
                                              style="Primary.TButton", command=self._buka_eksekusi_lelang, state="disabled")
        self.btn_eksekusi_lelang.pack(side="right")

    def _on_select_sl(self, row: Optional[Dict[str, Any]]):
        self.sl_terpilih = row
        if row:
            self.lbl_info_sl.config(text=f"Agunan Siap Lelang: {row.get('barang_nama')} ({row.get('no_kontrak')})")
            self.btn_eksekusi_lelang.config(state="normal")
        else:
            self.lbl_info_sl.config(text="Pilih agunan lelang untuk eksekusi penjualan.")
            self.btn_eksekusi_lelang.config(state="disabled")

    def _buka_eksekusi_lelang(self):
        if hasattr(self, "sl_terpilih") and self.sl_terpilih:
            SelesaikanLelangDialog(self, self.facade, self.sl_terpilih, on_success=self.refresh_data)

    # --- TAB 3: RIWAYAT LELANG SELESAI ---
    def _build_tab_riwayat_lelang(self):
        table_card = Card(self.tab_riwayat_lelang, padx=16, pady=16)
        table_card.pack(fill="both", expand=True)

        cols = [
            ("pinjaman_id", "ID Pinjaman", 80, "center"),
            ("harga_lelang", "Harga Terjual", 130, "e"),
            ("total_kewajiban", "Kewajiban", 130, "e"),
            ("selisih", "Selisih", 120, "e"),
            ("hasil", "Hasil", 95, "center"),
            ("hak_nasabah", "Hak Nasabah", 120, "e"),
            ("kerugian", "Rugi Pegadaian", 120, "e"),
            ("tanggal", "Tanggal Lelang", 100, "center"),
        ]
        self.tbl_riwayat_lelang = DataTable(table_card.inner, columns=cols, stretch_col="selisih")
        self.tbl_riwayat_lelang.pack(fill="both", expand=True)

    def _jalankan_deteksi(self):
        """Memanggil deteksi_jatuh_tempo() untuk mengecek pinjaman yang melewati hari ini."""
        try:
            count = self.facade.deteksi_jatuh_tempo()
            show_pesan_sukses(
                self, "Deteksi Selesai",
                f"Proses deteksi selesai. Ditemukan {count} pinjaman yang jatuh tempo dan statusnya diperbarui."
            )
            self.refresh_data()
        except PawnError as e:
            show_pesan_error(self, "Gagal Deteksi", str(e))
        except Exception as e:
            show_pesan_error(self, "Error", str(e))

    def refresh_data(self):
        """Memuat ulang ketiga tab lelang."""
        try:
            fmt_money = {
                "sisa_pokok": lambda v, r: format_rupiah(v),
                "harga_lelang": lambda v, r: format_rupiah(v),
                "total_kewajiban": lambda v, r: format_rupiah(v),
                "selisih": lambda v, r: format_rupiah(v),
                "hak_nasabah": lambda v, r: format_rupiah(v),
                "kerugian": lambda v, r: format_rupiah(v),
                "tgl_jatuh_tempo": lambda v, r: format_date(v),
                "tanggal": lambda v, r: format_date(v)
            }

            list_jt = self.facade.daftar_pinjaman(status="JATUH_TEMPO")
            self.tbl_jatuh_tempo.set_data(list_jt, formatters=fmt_money)
            self._on_select_jt(None)

            list_sl = self.facade.daftar_pinjaman(status="DALAM_PROSES_LELANG")
            self.tbl_siap_lelang.set_data(list_sl, formatters=fmt_money)
            self._on_select_sl(None)

            list_rl = self.facade.daftar_lelang()
            self.tbl_riwayat_lelang.set_data(list_rl, formatters=fmt_money)

        except Exception:
            pass
