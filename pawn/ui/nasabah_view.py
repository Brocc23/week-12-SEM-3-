"""
Tampilan Manajemen Nasabah Pegadaian Digital Nusantara
Menyediakan fitur pencarian, pendaftaran nasabah baru, ubah status, riwayat pinjaman, dan filter nasabah menunggak.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Dict, Any

from pawn.ui.theme import (
    BG_CARD, BG_CARD_ALT, BG_MAIN, BORDER_COLOR, PRIMARY, PRIMARY_DARK,
    SECONDARY, DANGER, SUCCESS, INFO, TEXT_MAIN, TEXT_SECONDARY, TEXT_MUTED, TEXT_WHITE, TEXT_SIDEBAR,
    FONT_TITLE, FONT_HEADER, FONT_SECTION, FONT_BODY, FONT_BODY_BOLD,
    FONT_LABEL, FONT_SMALL, FONT_SMALL_BOLD,
    show_konfirmasi, show_pesan_sukses, show_pesan_error, format_rupiah, format_date
)
from pawn.ui.widgets import Card, DataTable, FormDialog
try:
    from pawn.errors import PawnError
except ImportError:
    class PawnError(Exception): pass


class TambahNasabahDialog(FormDialog):
    """Dialog pendaftaran nasabah baru dengan validasi data dan form scrollable."""
    def __init__(self, parent, facade, on_success):
        super().__init__(parent, title="Pendaftaran Nasabah Baru", width=540, height=480)
        self.facade = facade
        self.on_success = on_success
        self._build_form()

    def _build_form(self):
        # NIK
        tk.Label(self.body, text="NIK (Nomor Induk Kependudukan 16 Digit) *",
                 font=FONT_LABEL, fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
        self.ent_nik = ttk.Entry(self.body, font=FONT_BODY)
        self.ent_nik.pack(fill="x", pady=(0, 12))

        # Nama Lengkap
        tk.Label(self.body, text="Nama Lengkap Nasabah (Sesuai KTP) *",
                 font=FONT_LABEL, fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
        self.ent_nama = ttk.Entry(self.body, font=FONT_BODY)
        self.ent_nama.pack(fill="x", pady=(0, 12))

        # Alamat Lengkap
        tk.Label(self.body, text="Alamat Domisili Lengkap *",
                 font=FONT_LABEL, fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
        self.ent_alamat = ttk.Entry(self.body, font=FONT_BODY)
        self.ent_alamat.pack(fill="x", pady=(0, 12))

        # Nomor Telepon / HP
        tk.Label(self.body, text="Nomor Telepon / WhatsApp Aktif *",
                 font=FONT_LABEL, fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
        self.ent_telepon = ttk.Entry(self.body, font=FONT_BODY)
        self.ent_telepon.pack(fill="x", pady=(0, 12))

        # Email
        tk.Label(self.body, text="Alamat Email (Opsional)",
                 font=FONT_LABEL, fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
        self.ent_email = ttk.Entry(self.body, font=FONT_BODY)
        self.ent_email.pack(fill="x", pady=(0, 12))

    def on_submit(self):
        nik = self.ent_nik.get().strip()
        nama = self.ent_nama.get().strip()
        alamat = self.ent_alamat.get().strip()
        telepon = self.ent_telepon.get().strip()
        email = self.ent_email.get().strip()

        # Validasi lokal ramah pengguna
        if not nik:
            self.show_error("NIK wajib diisi.")
            self.ent_nik.focus_set()
            return
        if len(nik) != 16 or not nik.isdigit():
            self.show_error("NIK harus berupa 16 digit angka sesuai KTP.")
            self.ent_nik.focus_set()
            return
        if not nama:
            self.show_error("Nama lengkap nasabah wajib diisi.")
            self.ent_nama.focus_set()
            return
        if not alamat:
            self.show_error("Alamat domisili nasabah wajib diisi.")
            self.ent_alamat.focus_set()
            return
        if not telepon:
            self.show_error("Nomor telepon wajib diisi.")
            self.ent_telepon.focus_set()
            return

        try:
            self.facade.tambah_nasabah(nik, nama, alamat, telepon, email)
            show_pesan_sukses(self, "Berhasil", "Data nasabah berhasil didaftarkan ke sistem.")
            self.on_success()
            self.destroy()
        except PawnError as e:
            self.show_error(str(e))
        except Exception as e:
            self.show_error(f"Gagal menyimpan nasabah: {str(e)}")


class RiwayatNasabahDialog(tk.Toplevel):
    """Dialog detail informasi dan riwayat transaksi/pinjaman nasabah."""
    def __init__(self, parent, facade, nasabah: Dict[str, Any]):
        super().__init__(parent)
        self.facade = facade
        self.nasabah = nasabah
        self.title(f"Riwayat Nasabah — {nasabah.get('nama', '')}")
        self.geometry("780x520")
        self.minsize(640, 420)
        self.configure(bg=BG_CARD)
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self._load_data()

    def _build_ui(self):
        # Profil Header
        top_bar = tk.Frame(self, bg=PRIMARY_DARK, padx=20, pady=16)
        top_bar.pack(fill="x")
        
        tk.Label(top_bar, text=f"👤 {self.nasabah.get('nama', '').upper()}",
                 font=FONT_HEADER, fg=TEXT_WHITE, bg=PRIMARY_DARK).pack(anchor="w")
        
        sub_info = (
            f"Kode: {self.nasabah.get('kode', '-')}  |  "
            f"NIK: {self.nasabah.get('nik', '-')}  |  "
            f"Status: {self.nasabah.get('status', 'AKTIF')}  |  "
            f"Telepon: {self.nasabah.get('telepon', '-')}"
        )
        tk.Label(top_bar, text=sub_info, font=FONT_SMALL, fg=TEXT_SIDEBAR, bg=PRIMARY_DARK).pack(anchor="w", pady=(4, 0))

        # Konten
        content = tk.Frame(self, bg=BG_MAIN, padx=20, pady=16)
        content.pack(fill="both", expand=True)

        tk.Label(content, text="DAFTAR KONTRAK GADAI & STATUS PINJAMAN",
                 font=FONT_LABEL, fg=TEXT_MAIN, bg=BG_MAIN).pack(anchor="w", pady=(0, 8))

        cols = [
            ("no_kontrak", "No. Kontrak", 140, "w"),
            ("barang", "Barang Jaminan", 140, "w"),
            ("pokok", "Plafon Pinjaman", 120, "e"),
            ("sisa_pokok", "Sisa Pokok", 120, "e"),
            ("tgl_jatuh_tempo", "Jatuh Tempo", 125, "center"),
            ("status", "Status", 100, "center"),
        ]
        self.table_kontrak = DataTable(content, columns=cols, stretch_col="barang")
        self.table_kontrak.pack(fill="both", expand=True)

        # Footer
        footer_wrap = tk.Frame(self, bg=BORDER_COLOR, highlightthickness=0, bd=0)
        footer_wrap.pack(fill="x", side="bottom")
        footer = tk.Frame(footer_wrap, bg=BG_CARD_ALT, padx=20, pady=12, highlightthickness=0, bd=0)
        footer.pack(fill="x", pady=(1, 0))
        ttk.Button(footer, text="Tutup", style="Secondary.TButton",
                   command=self.destroy).pack(side="right")

    def _load_data(self):
        try:
            nsb_id = self.nasabah.get("id")
            riwayat = self.facade.riwayat_nasabah(nsb_id)
            kontrak_list = riwayat if isinstance(riwayat, list) else riwayat.get("pinjaman", [])
            formatters = {
                "pokok": lambda v, r: format_rupiah(v),
                "sisa_pokok": lambda v, r: format_rupiah(v),
                "tgl_jatuh_tempo": lambda v, r: format_date(v)
            }
            self.table_kontrak.set_data(kontrak_list, formatters=formatters)
        except Exception:
            pass


class NasabahView(tk.Frame):
    """Tampilan utama Pengelolaan Nasabah."""
    def __init__(self, parent, facade, **kwargs):
        super().__init__(parent, bg=BG_MAIN, padx=24, pady=20, **kwargs)
        self.facade = facade
        self.mode_menunggak = False
        
        self._build_ui()
        self.refresh_data()

    def _build_ui(self):
        # 1. Header & Toolbar
        top_frame = tk.Frame(self, bg=BG_MAIN)
        top_frame.pack(fill="x", pady=(0, 16))

        title_box = tk.Frame(top_frame, bg=BG_MAIN)
        title_box.pack(side="left")

        tk.Label(title_box, text="DATA NASABAH & DEBITUR", font=FONT_HEADER,
                 fg=TEXT_MAIN, bg=BG_MAIN).pack(anchor="w")
        tk.Label(title_box, text="Kelola profil debitur, riwayat pinjaman kredit, dan pantau status kelayakan kredit",
                 font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_MAIN).pack(anchor="w", pady=(2, 0))

        btn_tambah = ttk.Button(top_frame, text="➕ Tambah Nasabah Baru", style="Primary.TButton",
                                command=self._buka_dialog_tambah)
        btn_tambah.pack(side="right")

        # 2. Filter Bar Card
        filter_card = Card(self, padx=16, pady=12)
        filter_card.pack(fill="x", pady=(0, 16))

        fb = tk.Frame(filter_card.inner, bg=BG_CARD)
        fb.pack(fill="x")

        tk.Label(fb, text="Cari Nasabah:", font=FONT_LABEL, fg=TEXT_MAIN, bg=BG_CARD).pack(side="left", padx=(0, 8))
        self.ent_cari = ttk.Entry(fb, width=28)
        self.ent_cari.pack(side="left", padx=(0, 8))
        self.ent_cari.bind("<Return>", lambda e: self.refresh_data())

        btn_cari = ttk.Button(fb, text="🔍 Cari", style="Secondary.TButton", command=self.refresh_data)
        btn_cari.pack(side="left", padx=(0, 12))

        self.btn_filter_tunggak = ttk.Button(fb, text="⚠️ Hanya Nasabah Menunggak",
                                             style="Secondary.TButton", command=self._toggle_mode_menunggak)
        self.btn_filter_tunggak.pack(side="left", padx=(0, 8))

        btn_reset = ttk.Button(fb, text="Tampilkan Semua", style="Secondary.TButton",
                               command=self._reset_filter)
        btn_reset.pack(side="left")

        # 3. Action Bar Bawah (Di-pack ke bawah terlebih dahulu agar selalu tampil utuh dan tombol tidak terpotong)
        bar_wrap = tk.Frame(self, bg=BORDER_COLOR, padx=1, pady=1, highlightthickness=0, bd=0)
        bar_wrap.pack(fill="x", side="bottom")
        self.action_bar = tk.Frame(bar_wrap, bg=BG_CARD, padx=18, pady=14, highlightthickness=0, bd=0)
        self.action_bar.pack(fill="both", expand=True)

        self.lbl_selected_info = tk.Label(self.action_bar, text="Pilih salah satu baris nasabah di tabel untuk melakukan tindakan operasional.",
                                          font=FONT_BODY, fg=TEXT_MUTED, bg=BG_CARD)
        self.lbl_selected_info.pack(side="left")

        self.btn_box_actions = tk.Frame(self.action_bar, bg=BG_CARD)
        self.btn_box_actions.pack(side="right")

        self.btn_riwayat = ttk.Button(self.btn_box_actions, text="📋 Riwayat Pinjaman",
                                      style="Secondary.TButton", command=self._lihat_riwayat, state="disabled")
        self.btn_riwayat.pack(side="left", padx=(0, 8))

        self.btn_status = ttk.Button(self.btn_box_actions, text="🔄 Ubah Status",
                                     style="Secondary.TButton", command=self._ubah_status, state="disabled")
        self.btn_status.pack(side="left", padx=(0, 8))

        self.btn_hapus = ttk.Button(self.btn_box_actions, text="🗑️ Hapus Nasabah",
                                    style="Danger.TButton", command=self._hapus_nasabah, state="disabled")
        self.btn_hapus.pack(side="left")

        # 4. Tabel Data Nasabah Card (Mengisi sisa ruang di atas secara proporsional)
        table_card = Card(self, padx=16, pady=16)
        table_card.pack(fill="both", expand=True, pady=(0, 14))

        cols = [
            ("kode", "Kode", 95, "center"),
            ("nik", "NIK KTP", 130, "center"),
            ("nama", "Nama Nasabah", 150, "w"),
            ("telepon", "No. Telepon", 110, "w"),
            ("alamat", "Alamat Domisili", 180, "w"),
            ("status", "Status", 85, "center"),
            ("tgl_daftar", "Terdaftar", 90, "center"),
        ]

        self.table = DataTable(table_card.inner, columns=cols, stretch_col="alamat",
                               show_hsb=False,
                               on_select=self._on_nasabah_selected,
                               on_double_click=self._on_nasabah_double_click)
        self.table.pack(fill="both", expand=True)

    def _on_nasabah_selected(self, row: Optional[Dict[str, Any]]):
        if row:
            nama = row.get("nama", "")
            kode = row.get("kode", "")
            status = row.get("status", "AKTIF")
            self.lbl_selected_info.config(text=f"Nasabah Terpilih: {nama} ({kode}) — Status: {status}")
            self.btn_riwayat.config(state="normal")
            self.btn_status.config(state="normal")
            self.btn_hapus.config(state="normal")
        else:
            self.lbl_selected_info.config(text="Pilih salah satu baris nasabah di tabel untuk melakukan tindakan operasional.")
            self.btn_riwayat.config(state="disabled")
            self.btn_status.config(state="disabled")
            self.btn_hapus.config(state="disabled")

    def _on_nasabah_double_click(self, row: Optional[Dict[str, Any]]):
        if row:
            self._lihat_riwayat()

    def _toggle_mode_menunggak(self):
        self.mode_menunggak = True
        self.refresh_data()

    def _reset_filter(self):
        self.mode_menunggak = False
        self.ent_cari.delete(0, tk.END)
        self.refresh_data()

    def _buka_dialog_tambah(self):
        TambahNasabahDialog(self, self.facade, on_success=self.refresh_data)

    def _lihat_riwayat(self):
        row = self.table.get_selected()
        if not row:
            return
        RiwayatNasabahDialog(self, self.facade, row)

    def _ubah_status(self):
        row = self.table.get_selected()
        if not row:
            return
        cur_status = row.get("status", "AKTIF")
        new_status = "DITANGGUHKAN" if cur_status == "AKTIF" else "AKTIF"
        
        pesan = f"Ubah status nasabah '{row.get('nama')}' dari {cur_status} menjadi {new_status}?"
        if show_konfirmasi(self, "Konfirmasi Ubah Status", pesan):
            try:
                self.facade.ubah_status_nasabah(row.get("id"), new_status)
                show_pesan_sukses(self, "Status Diperbarui", f"Status nasabah kini adalah {new_status}.")
                self.refresh_data()
            except PawnError as e:
                show_pesan_error(self, "Gagal Ubah Status", str(e))
            except Exception as e:
                show_pesan_error(self, "Error", str(e))

    def _hapus_nasabah(self):
        row = self.table.get_selected()
        if not row:
            return
        pesan = (f"Apakah Anda yakin ingin menghapus data nasabah '{row.get('nama')}' ({row.get('kode')})?\n\n"
                 "PERINGATAN: Tindakan ini tidak dapat dibatalkan!")
        if show_konfirmasi(self, "Konfirmasi Hapus Nasabah", pesan):
            try:
                self.facade.hapus_nasabah(row.get("id"))
                show_pesan_sukses(self, "Berhasil Dihapus", "Nasabah telah dihapus dari sistem.")
                self.refresh_data()
            except PawnError as e:
                show_pesan_error(self, "Gagal Hapus", str(e))
            except Exception as e:
                show_pesan_error(self, "Error", str(e))

    def refresh_data(self):
        """Memuat daftar nasabah sesuai filter yang aktif."""
        try:
            if self.mode_menunggak:
                data = self.facade.nasabah_menunggak()
            else:
                cari_txt = self.ent_cari.get().strip()
                data = self.facade.daftar_nasabah(cari_txt)
                
            formatters = {
                "tgl_daftar": lambda v, r: format_date(v)
            }
            self.table.set_data(data, formatters=formatters)
            self._on_nasabah_selected(None)
        except Exception:
            pass
