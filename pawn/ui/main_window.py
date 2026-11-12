"""
Jendela Utama Aplikasi Pegadaian Digital Nusantara
Mengelola tata letak aplikasi: Sidebar Navigasi Dinamis berbasis Hak Akses (RBAC),
Header Informasi Pengguna & Simulasi Tanggal Operasional, serta Kontainer Tampilan Layar.
"""

import tkinter as tk
from tkinter import ttk
from datetime import date, datetime, timedelta
from typing import Callable, Optional, Dict, Any, Set

from pawn.ui.theme import (
    BG_CARD, BG_CARD_ALT, BG_MAIN, BG_SIDEBAR, BG_SIDEBAR_ACTIVE, BG_SIDEBAR_HOVER, BG_SIDEBAR_USER,
    BORDER_COLOR, PRIMARY, PRIMARY_LIGHT, PRIMARY_DARK, SECONDARY, SECONDARY_LIGHT, SECONDARY_DARK, DANGER, DANGER_LIGHT, DANGER_DARK,
    SUCCESS, SUCCESS_DARK, INFO, INFO_LIGHT, INFO_DARK, TEXT_MAIN, TEXT_SECONDARY, TEXT_MUTED, TEXT_WHITE,
    TEXT_SIDEBAR, TEXT_SIDEBAR_MUTED,
    FONT_TITLE, FONT_HEADER, FONT_SECTION, FONT_BODY, FONT_BODY_BOLD,
    FONT_LABEL, FONT_SMALL, FONT_SMALL_BOLD, FONT_SIDEBAR,
    format_date, show_konfirmasi, show_pesan_sukses, show_pesan_error
)
from pawn.ui.dashboard_view import DashboardView
from pawn.ui.nasabah_view import NasabahView
from pawn.ui.penaksiran_view import PenaksiranView
from pawn.ui.gadai_view import GadaiStepperView
from pawn.ui.pinjaman_view import PinjamanView
from pawn.ui.transaksi_view import TransaksiView
from pawn.ui.gudang_view import GudangView
from pawn.ui.lelang_view import LelangView
from pawn.ui.laporan_view import LaporanView
from pawn.ui.admin_view import AdminView
try:
    from pawn.errors import PawnError
except ImportError:
    class PawnError(Exception): pass


class SimulasiTanggalDialog(tk.Toplevel):
    """Dialog untuk mengubah tanggal simulasi sistem (uji coba jatuh tempo & bunga)."""
    def __init__(self, parent, facade, on_updated: Callable):
        super().__init__(parent)
        self.facade = facade
        self.on_updated = on_updated
        self.title("Simulasi Tanggal Operasional")
        self.geometry("480x400")
        self.minsize(440, 360)
        self.configure(bg=BG_CARD)
        self.transient(parent)
        self.grab_set()

        # Posisi di tengah
        try:
            x = parent.winfo_rootx() + (parent.winfo_width() - 480) // 2
            y = parent.winfo_rooty() + (parent.winfo_height() - 400) // 2
            self.geometry(f"+{max(20, x)}+{max(20, y)}")
        except Exception:
            pass

        self._build_ui()

    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg=PRIMARY_DARK, padx=20, pady=14)
        hdr.pack(fill="x")
        tk.Label(hdr, text="📅 PENGATURAN TANGGAL SIMULASI SISTEM", font=FONT_HEADER, fg=TEXT_WHITE, bg=PRIMARY_DARK).pack(anchor="w")

        body = tk.Frame(self, bg=BG_CARD, padx=24, pady=20)
        body.pack(fill="both", expand=True)

        try:
            cur_date = self.facade.hari_ini()
        except Exception:
            cur_date = date.today()

        # Active date pill
        date_wrap = tk.Frame(body, bg=BORDER_COLOR, padx=1, pady=1, highlightthickness=0, bd=0)
        date_wrap.pack(fill="x", pady=(0, 16))
        date_pill = tk.Frame(date_wrap, bg=BG_CARD_ALT, padx=16, pady=12, highlightthickness=0, bd=0)
        date_pill.pack(fill="both", expand=True)

        tk.Label(date_pill, text="Tanggal Operasional Aktif Saat Ini:", font=FONT_SMALL,
                 fg=TEXT_MUTED, bg=BG_CARD_ALT).pack(anchor="w")
        tk.Label(date_pill, text=format_date(cur_date), font=FONT_HEADER,
                 fg=PRIMARY_DARK, bg=BG_CARD_ALT).pack(anchor="w", pady=(2, 0))

        tk.Label(body, text="Pintasan Majukan Waktu Simulasi:", font=FONT_LABEL,
                 fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 6))

        quick_box = tk.Frame(body, bg=BG_CARD, highlightthickness=0, bd=0)
        quick_box.pack(fill="x", pady=(0, 16))

        quick_buttons = [
            ("Hari Ini Riil", 0),
            ("+15 Hari", 15),
            ("+30 Hari", 30),
            ("+120 Hari", 120),
            ("+135 Hari (Grace)", 135),
        ]
        for label, days in quick_buttons:
            btn = tk.Button(
                quick_box, text=label, font=FONT_SMALL_BOLD, bg=BG_CARD_ALT,
                fg=TEXT_MAIN, relief="flat", bd=0, highlightthickness=0, padx=10, pady=5, cursor="hand2",
                command=lambda d=days: self._set_quick_days(d)
            )
            btn.pack(side="left", padx=3, pady=2)

        # Input Custom Tanggal
        tk.Label(body, text="Atau Masukkan Tanggal Manual (YYYY-MM-DD):",
                 font=FONT_LABEL, fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
        self.ent_tgl = ttk.Entry(body, font=FONT_BODY)
        self.ent_tgl.insert(0, format_date(cur_date))
        self.ent_tgl.pack(fill="x", pady=(0, 20))

        # Footer Buttons (Soft top border)
        footer_wrap = tk.Frame(self, bg=BORDER_COLOR, highlightthickness=0, bd=0)
        footer_wrap.pack(fill="x", side="bottom")
        footer = tk.Frame(footer_wrap, bg=BG_CARD_ALT, padx=20, pady=14, highlightthickness=0, bd=0)
        footer.pack(fill="x", pady=(1, 0))

        ttk.Button(footer, text="Batal", style="Secondary.TButton",
                   command=self.destroy).pack(side="right", padx=(8, 0))

        ttk.Button(footer, text="Terapkan Tanggal", style="Primary.TButton",
                   command=self._simpan_tanggal).pack(side="right")

    def _set_quick_days(self, days: int):
        real_today = date.today()
        if days == 0:
            target_date = real_today
        else:
            target_date = real_today + timedelta(days=days)
        self.ent_tgl.delete(0, tk.END)
        self.ent_tgl.insert(0, target_date.strftime("%Y-%m-%d"))

    def _simpan_tanggal(self):
        txt = self.ent_tgl.get().strip()
        try:
            parts = [int(p) for p in txt.split("-")]
            target = date(parts[0], parts[1], parts[2])
            self.facade.set_tanggal_simulasi(target)
            show_pesan_sukses(self, "Tanggal Diperbarui", f"Tanggal sistem disetel ke: {target.strftime('%Y-%m-%d')}")
            self.on_updated()
            self.destroy()
        except Exception:
            show_pesan_error(self, "Format Tanggal Salah", "Gunakan format YYYY-MM-DD (contoh: 2026-11-13).")


class MainWindow(tk.Frame):
    """Jendela Shell Utama dengan Sidebar Dinamis RBAC dan Layout Fleksibel."""
    def __init__(self, parent, facade, on_logout: Callable, **kwargs):
        super().__init__(parent, bg=BG_MAIN, **kwargs)
        self.facade = facade
        self.on_logout = on_logout
        
        self.current_view_key: Optional[str] = None
        self.view_instances: Dict[str, tk.Widget] = {}
        self.sidebar_buttons: Dict[str, tk.Button] = {}

        self._load_user_profile()
        self._build_ui()
        self.navigate_to("dashboard")

    def _load_user_profile(self):
        """Memuat hak akses dan profil pengguna aktif."""
        self.active_user = getattr(self.facade, "pengguna_aktif", None)
        if callable(self.active_user):
            self.active_user = self.active_user()

        try:
            self.permissions: Set[str] = self.facade.hak_akses()
        except Exception:
            self.permissions = set()

    def _build_ui(self):
        # 1. Sidebar Navigasi Kiri (Lebar 250px)
        self.sidebar = tk.Frame(self, bg=BG_SIDEBAR, width=250)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Brand Logo & Nama (Clean, calm typography without heavy emoji)
        brand_frame = tk.Frame(self.sidebar, bg=BG_SIDEBAR, padx=20, pady=22, highlightthickness=0, bd=0)
        brand_frame.pack(fill="x")

        tk.Label(brand_frame, text="PEGADAIAN", font=FONT_TITLE,
                 fg=PRIMARY_DARK, bg=BG_SIDEBAR).pack(anchor="w")
        tk.Label(brand_frame, text="Digital Nusantara • v2.0", font=FONT_SMALL_BOLD,
                 fg=SECONDARY, bg=BG_SIDEBAR).pack(anchor="w", pady=(2, 0))

        # Profil Pengguna Aktif (No outline, soft #E5E0D6 fill)
        user_card = tk.Frame(self.sidebar, bg=BG_SIDEBAR_USER, padx=14, pady=12, highlightthickness=0, bd=0)
        user_card.pack(fill="x", padx=12, pady=(0, 18))

        user_name = self.active_user.get("nama", "Pengguna") if self.active_user else "Pengguna"
        user_role = self.active_user.get("role", "STAF") if self.active_user else "STAF"
        cabang_id = self.active_user.get("cabang_id") if self.active_user else None
        cabang_str = f"Cabang #{cabang_id}" if cabang_id else "Semua Cabang"

        tk.Label(user_card, text=user_name, font=FONT_BODY_BOLD,
                 fg=TEXT_SIDEBAR, bg=BG_SIDEBAR_USER).pack(anchor="w")
        
        # Role Badge Pill (Pastel fill & dark text)
        role_frame = tk.Frame(user_card, bg=BG_SIDEBAR_USER, highlightthickness=0, bd=0)
        role_frame.pack(anchor="w", pady=(4, 0))

        role_bg = PRIMARY_LIGHT if user_role == "PETUGAS" else (SECONDARY_LIGHT if user_role == "ADMIN" else INFO_LIGHT)
        role_fg = PRIMARY_DARK if user_role == "PETUGAS" else (SECONDARY_DARK if user_role == "ADMIN" else INFO_DARK)
        
        role_badge = tk.Label(role_frame, text=f" {user_role} ", font=FONT_SMALL_BOLD,
                              bg=role_bg, fg=role_fg, padx=6, pady=2, relief="flat", bd=0)
        role_badge.pack(side="left")

        tk.Label(role_frame, text=f"  {cabang_str}", font=FONT_SMALL,
                 fg=TEXT_SIDEBAR_MUTED, bg=BG_SIDEBAR_USER).pack(side="left")

        # Kontainer Daftar Menu Navigasi (Filtered by hak_akses())
        self.nav_container = tk.Frame(self.sidebar, bg=BG_SIDEBAR, highlightthickness=0, bd=0)
        self.nav_container.pack(fill="both", expand=True, padx=8)

        self._build_sidebar_menu()

        # Tombol Keluar (Logout) di Bawah Sidebar: Ghost style borderless dengan teks terracotta
        bottom_box = tk.Frame(self.sidebar, bg=BG_SIDEBAR, padx=12, pady=18, highlightthickness=0, bd=0)
        bottom_box.pack(fill="x", side="bottom")

        btn_logout = tk.Button(
            bottom_box, text="Keluar (Logout)", font=FONT_SIDEBAR,
            bg=BG_SIDEBAR, fg=SECONDARY, activebackground=BG_SIDEBAR_HOVER,
            activeforeground=SECONDARY_DARK, relief="flat", bd=0, highlightthickness=0,
            padx=14, pady=8, anchor="w", cursor="hand2", command=self._do_logout
        )
        btn_logout.pack(fill="x")

        # 2. Area Konten Kanan (Header Atas + View Container)
        self.right_container = tk.Frame(self, bg=BG_MAIN, highlightthickness=0, bd=0)
        self.right_container.pack(side="right", fill="both", expand=True)

        # Header Atas (White bar dengan 1px bottom border halus BORDER_COLOR)
        self.header_bar = tk.Frame(self.right_container, bg=BORDER_COLOR, highlightthickness=0, bd=0)
        self.header_bar.pack(fill="x")

        header_inner = tk.Frame(self.header_bar, bg=BG_CARD, padx=24, pady=14, highlightthickness=0, bd=0)
        header_inner.pack(fill="x", pady=(0, 1))

        self.lbl_page_title = tk.Label(header_inner, text="Dashboard", font=FONT_HEADER,
                                       fg=PRIMARY_DARK, bg=BG_CARD)
        self.lbl_page_title.pack(side="left")

        # Kontrol Simulasi Tanggal di Kanan Header
        date_box = tk.Frame(header_inner, bg=BG_CARD, highlightthickness=0, bd=0)
        date_box.pack(side="right")

        self.lbl_simulasi_date = tk.Label(date_box, text="Tanggal Operasional: -", font=FONT_BODY_BOLD,
                                          fg=TEXT_MAIN, bg=BG_CARD)
        self.lbl_simulasi_date.pack(side="left", padx=(0, 12))

        btn_sim_tgl = ttk.Button(date_box, text="Ubah Tanggal", style="Secondary.TButton",
                                 command=self._buka_simulasi_tanggal)
        btn_sim_tgl.pack(side="left")

        self._update_header_date()

        # Wadah Tampilan Layar Dinamis
        self.content_area = tk.Frame(self.right_container, bg=BG_MAIN, highlightthickness=0, bd=0)
        self.content_area.pack(fill="both", expand=True)

    def _build_sidebar_menu(self):
        """Menyusun item sidebar bersih tanpa emoji berat."""
        all_menus = [
            ("dashboard", "Dashboard", None),
            ("nasabah", "Data Nasabah", "nasabah.kelola"),
            ("penaksiran", "Penaksiran Agunan", "taksir"),
            ("gadai", "Ajukan Gadai (9 Langkah)", "gadai"),
            ("pinjaman", "Kontrak & Angsuran", "bayar"),
            ("transaksi", "Riwayat Transaksi", "bayar"),
            ("gudang", "Logistik Gudang", "gadai"),
            ("lelang", "Jatuh Tempo & Lelang", "lelang"),
            ("laporan", "Laporan Keuangan", "laporan"),
            ("admin", "Pengaturan & Admin", "admin"),
        ]

        is_admin = ("admin" in self.permissions) or (self.active_user and self.active_user.get("role") == "ADMIN")

        for key, label, perm in all_menus:
            allowed = False
            if perm is None:
                allowed = True
            elif is_admin:
                allowed = True
            elif perm in self.permissions:
                allowed = True

            if not allowed:
                continue

            btn = tk.Button(
                self.nav_container,
                text=label,
                font=FONT_SIDEBAR,
                bg=BG_SIDEBAR,
                fg=TEXT_SIDEBAR,
                activebackground=BG_SIDEBAR_ACTIVE,
                activeforeground=PRIMARY_DARK,
                relief="flat",
                anchor="w",
                padx=14,
                pady=8,
                cursor="hand2",
                command=lambda k=key: self.navigate_to(k)
            )
            btn.pack(fill="x", pady=2)
            self.sidebar_buttons[key] = btn

    def _update_header_date(self):
        try:
            d = self.facade.hari_ini()
            self.lbl_simulasi_date.config(text=f"📅 Tanggal Operasional: {format_date(d)}")
        except Exception:
            self.lbl_simulasi_date.config(text=f"📅 Tanggal Operasional: {format_date(date.today())}")

    def _buka_simulasi_tanggal(self):
        SimulasiTanggalDialog(self, self.facade, on_updated=self._on_date_updated)

    def _on_date_updated(self):
        self._update_header_date()
        if self.current_view_key in self.view_instances:
            v = self.view_instances[self.current_view_key]
            if hasattr(v, "refresh_data"):
                v.refresh_data()

    def navigate_to(self, view_key: str, **extra_args):
        """Beralih ke layar tampilan tertentu."""
        # Update warna tombol sidebar (Pastel Sage Pill untuk aktif)
        for k, btn in self.sidebar_buttons.items():
            if k == view_key:
                btn.config(bg=BG_SIDEBAR_ACTIVE, fg=PRIMARY_DARK, relief="flat")
            else:
                btn.config(bg=BG_SIDEBAR, fg=TEXT_SIDEBAR, relief="flat")

        # Sembunyikan view yang lama
        for v in self.content_area.winfo_children():
            v.pack_forget()

        titles = {
            "dashboard": "Dashboard Operasional & Ringkasan Eksekutif",
            "nasabah": "Manajemen Nasabah & Rekam Debitur",
            "penaksiran": "Kalkulator Aktuaria & Workbench Penaksir",
            "gadai": "Alur 9-Langkah Pengajuan Akad Gadai Baru",
            "pinjaman": "Daftar Pinjaman, Angsuran & Pelunasan",
            "transaksi": "Audit Buku & Riwayat Transaksi Kas",
            "gudang": "Logistik Gudang & Brankas Penyimpanan Agunan",
            "lelang": "Jatuh Tempo, Notifikasi & Eksekusi Lelang",
            "laporan": "Laporan Keuangan Laba Rugi & Portofolio Agunan",
            "admin": "Pengaturan Sistem & Administrasi Pangkalan Data"
        }
        self.lbl_page_title.config(text=titles.get(view_key, view_key.capitalize()))
        self.current_view_key = view_key

        # Re-create or reuse view
        if view_key == "dashboard":
            view = DashboardView(self.content_area, self.facade, navigate_to=self.navigate_to)
        elif view_key == "nasabah":
            view = NasabahView(self.content_area, self.facade)
        elif view_key == "penaksiran":
            view = PenaksiranView(self.content_area, self.facade, navigate_to=self.navigate_to)
        elif view_key == "gadai":
            preset = extra_args.get("preset")
            view = GadaiStepperView(self.content_area, self.facade, navigate_to=self.navigate_to, preset=preset)
        elif view_key == "pinjaman":
            view = PinjamanView(self.content_area, self.facade)
        elif view_key == "transaksi":
            view = TransaksiView(self.content_area, self.facade)
        elif view_key == "gudang":
            view = GudangView(self.content_area, self.facade)
        elif view_key == "lelang":
            view = LelangView(self.content_area, self.facade)
        elif view_key == "laporan":
            view = LaporanView(self.content_area, self.facade)
        elif view_key == "admin":
            view = AdminView(self.content_area, self.facade)
        else:
            view = tk.Label(self.content_area, text=f"Layar {view_key} belum tersedia.", bg=BG_MAIN)

        self.view_instances[view_key] = view
        view.pack(fill="both", expand=True)

    def _do_logout(self):
        if show_konfirmasi(self, "Konfirmasi Keluar", "Apakah Anda yakin ingin keluar dari sistem?"):
            try:
                self.facade.logout()
            except Exception:
                pass
            self.on_logout()
