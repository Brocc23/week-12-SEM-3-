"""
Tampilan Pengaturan & Administrasi Sistem Pegadaian Digital Nusantara
Khusus untuk peran ADMIN: Kelola Pengguna, Cabang Operasional, Parameter Aktuaria, Audit Log, dan Backup/Restore.
"""

import tkinter as tk
from tkinter import ttk, filedialog
from typing import Optional, Dict, Any, List

from pawn.ui.theme import (
    BG_CARD, BG_CARD_ALT, BG_MAIN, BORDER_COLOR, PRIMARY, PRIMARY_DARK,
    SECONDARY, DANGER, DANGER_LIGHT, SUCCESS, INFO, TEXT_MAIN, TEXT_SECONDARY, TEXT_MUTED, TEXT_WHITE,
    FONT_TITLE, FONT_HEADER, FONT_SECTION, FONT_BODY, FONT_BODY_BOLD,
    FONT_LABEL, FONT_SMALL, FONT_SMALL_BOLD,
    format_rupiah, format_date, show_konfirmasi, show_pesan_sukses, show_pesan_error
)
from pawn.ui.widgets import Card, DataTable, FormDialog, ScrollableFrame
try:
    from pawn.errors import PawnError
except ImportError:
    class PawnError(Exception): pass


class TambahPenggunaDialog(FormDialog):
    """Dialog pembuatan akun pengguna baru."""
    def __init__(self, parent, facade, on_success):
        super().__init__(parent, title="Tambah Pengguna Baru", width=520, height=480)
        self.facade = facade
        self.on_success = on_success
        self._build_form()

    def _build_form(self):
        # Username
        tk.Label(self.body, text="Username Pengguna *", font=FONT_LABEL, fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
        self.ent_user = ttk.Entry(self.body)
        self.ent_user.pack(fill="x", pady=(0, 12))

        # Kata Sandi
        tk.Label(self.body, text="Kata Sandi (Password) *", font=FONT_LABEL, fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
        self.ent_pass = ttk.Entry(self.body, show="•")
        self.ent_pass.pack(fill="x", pady=(0, 12))

        # Nama Lengkap
        tk.Label(self.body, text="Nama Lengkap Karyawan *", font=FONT_LABEL, fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
        self.ent_nama = ttk.Entry(self.body)
        self.ent_nama.pack(fill="x", pady=(0, 12))

        # Role
        tk.Label(self.body, text="Peran / Hak Akses (Role) *", font=FONT_LABEL, fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
        self.combo_role = ttk.Combobox(self.body, state="readonly", values=["PETUGAS", "PENAKSIR", "ADMIN"])
        self.combo_role.set("PETUGAS")
        self.combo_role.pack(fill="x", pady=(0, 12))

        # Cabang
        tk.Label(self.body, text="Kantor Cabang Penugasan", font=FONT_LABEL, fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
        
        self.cabang_map = {}
        cabang_options = ["SEMUA CABANG (KHUSUS ADMIN PUSAT)"]
        try:
            cabang_list = self.facade.daftar_cabang()
            for c in cabang_list:
                label = f"{c.get('kode')} - {c.get('nama')}"
                self.cabang_map[label] = c.get("id")
                cabang_options.append(label)
        except Exception:
            pass

        self.combo_cabang = ttk.Combobox(self.body, state="readonly", values=cabang_options)
        self.combo_cabang.set(cabang_options[1] if len(cabang_options) > 1 else cabang_options[0])
        self.combo_cabang.pack(fill="x", pady=(0, 12))

    def on_submit(self):
        user = self.ent_user.get().strip()
        pwd = self.ent_pass.get()
        nama = self.ent_nama.get().strip()
        role = self.combo_role.get()
        cabang_sel = self.combo_cabang.get()

        if not user or not pwd or not nama:
            self.show_error("Semua kolom bertanda * wajib diisi.")
            return

        cabang_id = self.cabang_map.get(cabang_sel, None)

        try:
            self.facade.tambah_pengguna(user, pwd, nama, role, cabang_id)
            show_pesan_sukses(self, "Pengguna Dibuat", f"Pengguna {user} ({role}) berhasil ditambahkan ke sistem.")
            self.on_success()
            self.destroy()
        except PawnError as e:
            self.show_error(str(e))
        except Exception as e:
            self.show_error(f"Gagal menambah pengguna: {str(e)}")


class TambahCabangDialog(FormDialog):
    """Dialog registrasi kantor cabang baru."""
    def __init__(self, parent, facade, on_success):
        super().__init__(parent, title="Tambah Kantor Cabang Baru", width=500, height=400)
        self.facade = facade
        self.on_success = on_success
        self._build_form()

    def _build_form(self):
        tk.Label(self.body, text="Kode Cabang (3-4 Huruf Unik, misal: JKT, SBY) *",
                 font=FONT_LABEL, fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
        self.ent_kode = ttk.Entry(self.body)
        self.ent_kode.pack(fill="x", pady=(0, 12))

        tk.Label(self.body, text="Nama Kantor Cabang *",
                 font=FONT_LABEL, fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
        self.ent_nama = ttk.Entry(self.body)
        self.ent_nama.pack(fill="x", pady=(0, 12))

        tk.Label(self.body, text="Alamat Lengkap Cabang *",
                 font=FONT_LABEL, fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
        self.ent_alamat = ttk.Entry(self.body)
        self.ent_alamat.pack(fill="x", pady=(0, 12))

    def on_submit(self):
        kode = self.ent_kode.get().strip().upper()
        nama = self.ent_nama.get().strip()
        alamat = self.ent_alamat.get().strip()

        if not kode or not nama or not alamat:
            self.show_error("Semua kolom wajib diisi.")
            return

        try:
            self.facade.tambah_cabang(kode, nama, alamat)
            show_pesan_sukses(self, "Cabang Ditambahkan", f"Kantor cabang {nama} ({kode}) sukses terdaftar.")
            self.on_success()
            self.destroy()
        except PawnError as e:
            self.show_error(str(e))
        except Exception as e:
            self.show_error(f"Gagal menambah cabang: {str(e)}")


class UbahParameterDialog(FormDialog):
    """Dialog pengubahan nilai parameter sistem / aktuaria."""
    def __init__(self, parent, facade, kunci: str, nilai_lama: str, on_success):
        super().__init__(parent, title=f"Ubah Parameter — {kunci}", width=480, height=320)
        self.facade = facade
        self.kunci = kunci
        self.on_success = on_success
        self._build_form(nilai_lama)

    def _build_form(self, nilai_lama):
        tk.Label(self.body, text=f"Kunci Parameter: {self.kunci}", font=FONT_LABEL,
                 fg=PRIMARY_DARK, bg=BG_CARD).pack(anchor="w", pady=(0, 12))

        tk.Label(self.body, text="Nilai Baru (Angka / Teks) *", font=FONT_LABEL,
                 fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
        self.ent_nilai = ttk.Entry(self.body, font=FONT_BODY)
        self.ent_nilai.insert(0, str(nilai_lama))
        self.ent_nilai.pack(fill="x", pady=(0, 14))
        self.ent_nilai.focus_set()

    def on_submit(self):
        val = self.ent_nilai.get().strip()
        if not val:
            self.show_error("Nilai parameter tidak boleh kosong.")
            return

        try:
            self.facade.ubah_parameter(self.kunci, val)
            show_pesan_sukses(self, "Parameter Diperbarui", f"Nilai untuk {self.kunci} telah diubah menjadi '{val}'.")
            self.on_success()
            self.destroy()
        except PawnError as e:
            self.show_error(str(e))
        except Exception as e:
            self.show_error(f"Gagal menyimpan parameter: {str(e)}")


class AdminView(tk.Frame):
    """Tampilan Pusat Pengendalian Administrator."""
    def __init__(self, parent, facade, **kwargs):
        super().__init__(parent, bg=BG_MAIN, padx=24, pady=20, **kwargs)
        self.facade = facade
        self._build_ui()
        self.refresh_all()

    def _build_ui(self):
        # 1. Header
        header = tk.Frame(self, bg=BG_MAIN)
        header.pack(fill="x", pady=(0, 16))

        tk.Label(header, text="⚙️ PENGATURAN & ADMINISTRASI SISTEM", font=FONT_HEADER,
                 fg=TEXT_MAIN, bg=BG_MAIN).pack(anchor="w")
        tk.Label(header, text="Konfigurasi akun staf, kantor cabang, parameter suku bunga/LTV, audit kepatuhan, serta cadangan database",
                 font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_MAIN).pack(anchor="w", pady=(2, 0))

        # 2. Notebook Tab
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True)

        self.tab_users = tk.Frame(self.tabs, bg=BG_MAIN, padx=12, pady=14)
        self.tabs.add(self.tab_users, text=" 👥 Pengguna & Staf ")
        self._build_tab_users()

        self.tab_cabang = tk.Frame(self.tabs, bg=BG_MAIN, padx=12, pady=14)
        self.tabs.add(self.tab_cabang, text=" 🏛️ Kantor Cabang ")
        self._build_tab_cabang()

        self.tab_param = tk.Frame(self.tabs, bg=BG_MAIN, padx=12, pady=14)
        self.tabs.add(self.tab_param, text=" ⚙️ Parameter Sistem ")
        self._build_tab_param()

        self.tab_audit = tk.Frame(self.tabs, bg=BG_MAIN, padx=12, pady=14)
        self.tabs.add(self.tab_audit, text=" 📜 Audit Log ")
        self._build_tab_audit()

        self.tab_backup = tk.Frame(self.tabs, bg=BG_MAIN, padx=12, pady=14)
        self.tabs.add(self.tab_backup, text=" 💾 Backup & Restore ")
        self._build_tab_backup()

    # --- TAB 1: PENGGUNA ---
    def _build_tab_users(self):
        top_bar = tk.Frame(self.tab_users, bg=BG_MAIN)
        top_bar.pack(fill="x", pady=(0, 12))

        ttk.Button(top_bar, text="➕ Tambah Pengguna Baru", style="Primary.TButton",
                   command=lambda: TambahPenggunaDialog(self, self.facade, self._refresh_users)).pack(side="left")

        # Action bar bawah (Di-pack ke bawah terlebih dahulu agar selalu tampil utuh)
        action_wrap = tk.Frame(self.tab_users, bg=BORDER_COLOR, padx=1, pady=1, highlightthickness=0, bd=0)
        action_wrap.pack(fill="x", side="bottom")
        action_bar = tk.Frame(action_wrap, bg=BG_CARD, padx=16, pady=12, highlightthickness=0, bd=0)
        action_bar.pack(fill="both", expand=True)

        self.lbl_user_info = tk.Label(action_bar, text="Pilih baris pengguna untuk mengubah status aktif/non-aktif.",
                                      font=FONT_BODY, fg=TEXT_MUTED, bg=BG_CARD)
        self.lbl_user_info.pack(side="left")

        self.btn_toggle_user = ttk.Button(action_bar, text="🔄 Ubah Status Aktif",
                                          style="Secondary.TButton", command=self._toggle_user_aktif, state="disabled")
        self.btn_toggle_user.pack(side="right")

        # Tabel Pengguna (Mengisi sisa ruang di atas)
        table_card = Card(self.tab_users, padx=16, pady=16)
        table_card.pack(fill="both", expand=True, pady=(0, 12))

        cols = [
            ("id", "ID", 60, "center"),
            ("username", "Username", 140, "w"),
            ("nama", "Nama Lengkap Staf", 180, "w"),
            ("role", "Peran (Role)", 120, "center"),
            ("cabang_id", "Cabang ID", 100, "center"),
            ("aktif", "Status Aktif", 100, "center"),
        ]
        self.tbl_users = DataTable(table_card.inner, columns=cols, stretch_col="nama",
                                   show_hsb=False,
                                   on_select=self._on_user_select)
        self.tbl_users.pack(fill="both", expand=True)

    def _on_user_select(self, row: Optional[Dict[str, Any]]):
        self.user_terpilih = row
        if row:
            st = "AKTIF" if str(row.get("aktif")) in ("1", "True") else "NON-AKTIF"
            self.lbl_user_info.config(text=f"Pengguna: {row.get('username')} ({row.get('nama')}) — Status: {st}")
            self.btn_toggle_user.config(state="normal")
        else:
            self.lbl_user_info.config(text="Pilih baris pengguna untuk mengubah status aktif/non-aktif.")
            self.btn_toggle_user.config(state="disabled")

    def _toggle_user_aktif(self):
        if not hasattr(self, "user_terpilih") or not self.user_terpilih:
            return
        uid = self.user_terpilih.get("id")
        cur_aktif = int(self.user_terpilih.get("aktif", 1))
        new_aktif = 0 if cur_aktif == 1 else 1

        pesan = f"Ubah status aktif pengguna '{self.user_terpilih.get('username')}' menjadi {new_aktif}?"
        if show_konfirmasi(self, "Konfirmasi Status", pesan):
            try:
                self.facade.ubah_aktif(uid, new_aktif)
                show_pesan_sukses(self, "Sukses", "Status pengguna berhasil diperbarui.")
                self._refresh_users()
            except PawnError as e:
                show_pesan_error(self, "Gagal", str(e))

    def _refresh_users(self):
        try:
            users = self.facade.daftar_pengguna()
            fmt = {
                "aktif": lambda v, r: "AKTIF" if str(v) in ("1", "True") else "NON-AKTIF"
            }
            self.tbl_users.set_data(users, formatters=fmt)
            self._on_user_select(None)
        except Exception:
            pass

    # --- TAB 2: CABANG ---
    def _build_tab_cabang(self):
        top_bar = tk.Frame(self.tab_cabang, bg=BG_MAIN)
        top_bar.pack(fill="x", pady=(0, 12))

        ttk.Button(top_bar, text="➕ Tambah Kantor Cabang", style="Primary.TButton",
                   command=lambda: TambahCabangDialog(self, self.facade, self._refresh_cabang)).pack(side="left")

        table_card = Card(self.tab_cabang, padx=16, pady=16)
        table_card.pack(fill="both", expand=True)

        cols = [
            ("id", "ID", 60, "center"),
            ("kode", "Kode Cabang", 110, "center"),
            ("nama", "Nama Kantor Cabang", 200, "w"),
            ("alamat", "Alamat Kantor", 280, "w"),
        ]
        self.tbl_cabang = DataTable(table_card.inner, columns=cols, stretch_col="alamat")
        self.tbl_cabang.pack(fill="both", expand=True)

    def _refresh_cabang(self):
        try:
            cabang = self.facade.daftar_cabang()
            self.tbl_cabang.set_data(cabang)
        except Exception:
            pass

    # --- TAB 3: PARAMETER SISTEM ---
    def _build_tab_param(self):
        # Action bar bawah (Di-pack ke bawah terlebih dahulu agar selalu tampil utuh)
        bar_wrap = tk.Frame(self.tab_param, bg=BORDER_COLOR, padx=1, pady=1, highlightthickness=0, bd=0)
        bar_wrap.pack(fill="x", side="bottom")
        bar = tk.Frame(bar_wrap, bg=BG_CARD, padx=16, pady=12, highlightthickness=0, bd=0)
        bar.pack(fill="both", expand=True)

        self.lbl_param_info = tk.Label(bar, text="Pilih salah satu parameter di atas untuk mengubah nilai.",
                                       font=FONT_BODY, fg=TEXT_MUTED, bg=BG_CARD)
        self.lbl_param_info.pack(side="left")

        self.btn_edit_param = ttk.Button(bar, text="✏️ Ubah Parameter",
                                         style="Secondary.TButton", command=self._edit_param, state="disabled")
        self.btn_edit_param.pack(side="right")

        # Tabel Parameter (Mengisi sisa ruang di atas)
        table_card = Card(self.tab_param, padx=16, pady=16)
        table_card.pack(fill="both", expand=True, pady=(0, 12))

        cols = [
            ("kunci", "Kunci Parameter Sistem", 260, "w"),
            ("nilai", "Nilai Setting Saat Ini", 260, "w"),
        ]
        self.tbl_param = DataTable(table_card.inner, columns=cols, stretch_col="kunci",
                                   on_select=self._on_param_select,
                                   on_double_click=self._on_param_double_click)
        self.tbl_param.pack(fill="both", expand=True)

    def _on_param_select(self, row: Optional[Dict[str, Any]]):
        self.param_terpilih = row
        if row:
            self.lbl_param_info.config(text=f"Parameter Terpilih: {row.get('kunci')} = {row.get('nilai')}")
            self.btn_edit_param.config(state="normal")
        else:
            self.lbl_param_info.config(text="Pilih salah satu parameter di atas untuk mengubah nilai.")
            self.btn_edit_param.config(state="disabled")

    def _on_param_double_click(self, row: Optional[Dict[str, Any]]):
        if row:
            self._edit_param()

    def _edit_param(self):
        if hasattr(self, "param_terpilih") and self.param_terpilih:
            k = self.param_terpilih.get("kunci", "")
            v = self.param_terpilih.get("nilai", "")
            UbahParameterDialog(self, self.facade, k, v, on_success=self._refresh_params)

    def _refresh_params(self):
        try:
            params = self.facade.daftar_parameter()
            self.tbl_param.set_data(params)
            self._on_param_select(None)
        except Exception:
            pass

    # --- TAB 4: AUDIT LOG ---
    def _build_tab_audit(self):
        top_bar = tk.Frame(self.tab_audit, bg=BG_MAIN)
        top_bar.pack(fill="x", pady=(0, 12))

        ttk.Button(top_bar, text="🔄 Segarkan Audit Log (500 Terbaru)", style="Secondary.TButton",
                   command=self._refresh_audit).pack(side="left")

        table_card = Card(self.tab_audit, padx=16, pady=16)
        table_card.pack(fill="both", expand=True)

        cols = [
            ("id", "ID", 60, "center"),
            ("waktu", "Waktu", 140, "center"),
            ("pengguna_id", "User ID", 80, "center"),
            ("aksi", "Aksi Operasional", 150, "w"),
            ("detail", "Detail Log Aktivitas", 340, "w"),
        ]
        self.tbl_audit = DataTable(table_card.inner, columns=cols, stretch_col="detail")
        self.tbl_audit.pack(fill="both", expand=True)

    def _refresh_audit(self):
        try:
            logs = self.facade.lihat_audit_log(limit=500)
            fmt = {
                "waktu": lambda v, r: format_date(v)
            }
            self.tbl_audit.set_data(logs, formatters=fmt)
        except Exception:
            pass

    # --- TAB 5: BACKUP & RESTORE ---
    def _build_tab_backup(self):
        scroll = ScrollableFrame(self.tab_backup, bg=BG_MAIN)
        scroll.pack(fill="both", expand=True)

        card = Card(scroll.scrollable_content, padx=24, pady=20)
        card.pack(fill="both", expand=True)

        tk.Label(card.inner, text="PEMELIHARAAN & PEMULIHAN PANGKALAN DATA (SQLITE)",
                 font=FONT_HEADER, fg=PRIMARY_DARK, bg=BG_CARD).pack(anchor="w", pady=(0, 8))

        desc = (
            "Fitur ini memungkinkan administrator untuk membuat salinan cadangan (backup) seluruh data sistem "
            "atau memulihkan (restore) pangkalan data SQLite ke kondisi snapshot sebelumnya. "
            "Pencadangan dilakukan secara aman menggunakan SQLite Backup API."
        )
        tk.Label(card.inner, text=desc, font=FONT_BODY, fg=TEXT_SECONDARY, bg=BG_CARD,
                 wraplength=640, justify="left").pack(anchor="w", pady=(0, 20))

        b_wrap = tk.Frame(card.inner, bg=BORDER_COLOR, padx=1, pady=1, highlightthickness=0, bd=0)
        b_wrap.pack(fill="x", pady=(0, 18))
        b_box = tk.Frame(b_wrap, bg=BG_CARD_ALT, padx=20, pady=16, highlightthickness=0, bd=0)
        b_box.pack(fill="both", expand=True)

        tk.Label(b_box, text="💾 Cadangkan Database Saat Ini (Backup)", font=FONT_LABEL,
                 fg=TEXT_MAIN, bg=BG_CARD_ALT).pack(anchor="w")
        tk.Label(b_box, text="Simpan seluruh tabel nasabah, pinjaman, barang jaminan, transaksi, dan audit log ke file cadangan (.db / .sqlite).",
                 font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_CARD_ALT).pack(anchor="w", pady=(4, 12))

        ttk.Button(b_box, text="Mulai Pencadangan Data (Backup)", style="Primary.TButton",
                   command=self._do_backup).pack(anchor="w")

        r_wrap = tk.Frame(card.inner, bg=BORDER_COLOR, padx=1, pady=1, highlightthickness=0, bd=0)
        r_wrap.pack(fill="x")
        r_box = tk.Frame(r_wrap, bg=DANGER_LIGHT, padx=20, pady=16, highlightthickness=0, bd=0)
        r_box.pack(fill="both", expand=True)

        tk.Label(r_box, text="⚠️ Pulihkan Database dari File Cadangan (Restore)", font=FONT_LABEL,
                 fg=DANGER, bg=DANGER_LIGHT).pack(anchor="w")
        tk.Label(r_box, text="PERINGATAN KRITIS: Memulihkan database akan MENIMPA seluruh database saat ini secara permanen! Seluruh data setelah waktu snapshot akan hilang.",
                 font=FONT_SMALL, fg=TEXT_MAIN, bg=DANGER_LIGHT).pack(anchor="w", pady=(4, 12))

        ttk.Button(r_box, text="Pilih File Cadangan & Pulihkan (Restore)", style="Danger.TButton",
                   command=self._do_restore).pack(anchor="w")

    def _do_backup(self):
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Pilih Lokasi File Cadangan Database",
            defaultextension=".db",
            filetypes=[("Database SQLite", "*.db *.sqlite"), ("Semua File", "*.*")]
        )
        if not path:
            return

        try:
            self.facade.backup_database(path)
            show_pesan_sukses(self, "Backup Sukses", f"Pangkalan data berhasil dicadangkan ke:\n{path}")
        except PawnError as e:
            show_pesan_error(self, "Gagal Backup", str(e))
        except Exception as e:
            show_pesan_error(self, "Error Backup", str(e))

    def _do_restore(self):
        pesan = (
            "PERINGATAN KRITIS:\n\n"
            "Tindakan restore akan menghapus dan menimpa database aktif dengan file cadangan yang dipilih.\n"
            "Seluruh transaksi yang belum dicadangkan akan hilang permanen.\n\n"
            "Apakah Anda yakin ingin melanjutkan proses pemulihan?"
        )
        if not show_konfirmasi(self, "Konfirmasi Restore Pangkalan Data", pesan):
            return

        path = filedialog.askopenfilename(
            parent=self,
            title="Pilih File Cadangan SQLite",
            filetypes=[("Database SQLite", "*.db *.sqlite"), ("Semua File", "*.*")]
        )
        if not path:
            return

        try:
            self.facade.restore_database(path)
            show_pesan_sukses(self, "Pemulihan Berhasil", "Database telah berhasil dipulihkan dari file cadangan.")
            self.refresh_all()
        except PawnError as e:
            show_pesan_error(self, "Gagal Restore", str(e))
        except Exception as e:
            show_pesan_error(self, "Error Restore", str(e))

    def refresh_all(self):
        """Menyegarkan seluruh tab admin."""
        self._refresh_users()
        self._refresh_cabang()
        self._refresh_params()
        self._refresh_audit()
