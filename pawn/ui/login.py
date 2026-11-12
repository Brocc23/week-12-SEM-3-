"""
Tampilan Login Pegadaian Digital Nusantara
Menyediakan form autentikasi modern, pesan validasi ramah, dan kartu kredensial seed akun demo.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from pawn.ui.theme import (
    BG_CARD, BG_CARD_ALT, BG_MAIN, BG_SIDEBAR, BORDER_COLOR, BORDER_INPUT,
    PRIMARY, PRIMARY_HOVER, PRIMARY_DARK, SECONDARY, DANGER, DANGER_LIGHT,
    SUCCESS, INFO, TEXT_MAIN, TEXT_SECONDARY, TEXT_MUTED, TEXT_WHITE,
    FONT_TITLE, FONT_HEADER, FONT_SECTION, FONT_BODY, FONT_BODY_BOLD,
    FONT_LABEL, FONT_SMALL, FONT_SMALL_BOLD
)
from pawn.ui.widgets import ScrollableFrame
try:
    from pawn.errors import PawnError
except ImportError:
    class PawnError(Exception): pass


class LoginView(tk.Frame):
    """Layar autentikasi login pengguna dengan desain card modern."""
    def __init__(self, parent, facade, on_login_success: Callable, **kwargs):
        super().__init__(parent, bg=BG_MAIN, **kwargs)
        self.facade = facade
        self.on_login_success = on_login_success
        self._build_ui()

    def _build_ui(self):
        # Wadah tengah presisi di atas kanvas warm linen
        center_wrapper = tk.Frame(self, bg=BG_MAIN)
        center_wrapper.place(relx=0.5, rely=0.5, anchor="center")

        # Kartu Login Utama (Pure White dengan border warm-sand 1px)
        card_border = tk.Frame(center_wrapper, bg=BORDER_COLOR, padx=1, pady=1)
        card_border.pack()

        card = tk.Frame(card_border, bg=BG_CARD, padx=44, pady=36, width=480)
        card.pack()

        # Header Logo & Identitas
        brand_icon = tk.Label(card, text="🏛️", font=("Segoe UI", 32), fg=PRIMARY, bg=BG_CARD)
        brand_icon.pack(pady=(0, 2))

        lbl_title = tk.Label(card, text="PEGADAIAN DIGITAL NUSANTARA",
                             font=FONT_HEADER, fg=PRIMARY_DARK, bg=BG_CARD)
        lbl_title.pack(pady=(0, 2))

        lbl_sub = tk.Label(card, text="Sistem Manajemen & Operasional Gadai Terpadu",
                           font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_CARD)
        lbl_sub.pack(pady=(0, 20))

        # Banner Error Validasi (Hidden by default)
        self.lbl_error = tk.Label(card, text="", font=FONT_SMALL_BOLD, fg=DANGER,
                                  bg=DANGER_LIGHT, padx=12, pady=8, anchor="w", wraplength=400)

        # Field Username
        tk.Label(card, text="Username Pengguna", font=FONT_LABEL, fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
        self.ent_user = ttk.Entry(card, width=38, font=FONT_BODY)
        self.ent_user.pack(fill="x", pady=(0, 14))
        self.ent_user.focus_set()

        # Field Password
        tk.Label(card, text="Kata Sandi (Password)", font=FONT_LABEL, fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w", pady=(0, 4))
        
        pwd_box = tk.Frame(card, bg=BG_CARD)
        pwd_box.pack(fill="x", pady=(0, 6))

        self.ent_pass = ttk.Entry(pwd_box, show="•", width=34, font=FONT_BODY)
        self.ent_pass.pack(side="left", fill="x", expand=True)

        self.show_pass_var = tk.BooleanVar(value=False)
        chk_show = tk.Checkbutton(card, text="Tampilkan Sandi", variable=self.show_pass_var,
                                  bg=BG_CARD, font=FONT_SMALL, fg=TEXT_MUTED, activebackground=BG_CARD,
                                  command=self._toggle_show_pass)
        chk_show.pack(anchor="w", pady=(0, 18))

        # Enter key triggers login
        self.ent_user.bind("<Return>", lambda e: self.ent_pass.focus_set())
        self.ent_pass.bind("<Return>", lambda e: self._do_login())

        # Tombol Masuk Utama
        self.btn_login = ttk.Button(card, text="MASUK KE SISTEM", style="Primary.TButton",
                                    command=self._do_login)
        self.btn_login.pack(fill="x", pady=(0, 20))

        # -------------------------------------------------------------
        # Petunjuk Akun Demo Seed (Mempermudah Penguji)
        # -------------------------------------------------------------
        hint_wrap = tk.Frame(card, bg=BORDER_COLOR, padx=1, pady=1, highlightthickness=0, bd=0)
        hint_wrap.pack(fill="x")
        hint_card = tk.Frame(hint_wrap, bg=BG_CARD_ALT, padx=16, pady=14, highlightthickness=0, bd=0)
        hint_card.pack(fill="both", expand=True)

        tk.Label(hint_card, text="Akun Demo (Klik untuk Mengisi Otomatis):",
                 font=FONT_SMALL_BOLD, fg=TEXT_SECONDARY, bg=BG_CARD_ALT).pack(anchor="w", pady=(0, 8))

        demo_accounts = [
            ("ADMIN PUSAT", "admin", "admin123", PRIMARY_DARK),
            ("PETUGAS CAB. JAKARTA", "petugas1", "petugas123", PRIMARY),
            ("PENAKSIR CAB. JAKARTA", "penaksir1", "penaksir123", INFO),
            ("PETUGAS CAB. BANDUNG", "petugas2", "petugas123", PRIMARY),
            ("PENAKSIR CAB. BANDUNG", "penaksir2", "penaksir123", INFO),
        ]

        for role_tag, u, p, tag_color in demo_accounts:
            btn_demo = tk.Button(
                hint_card,
                text=f"  [{role_tag}]  {u}  (sandi: {p})",
                font=FONT_SMALL,
                bg=BG_CARD,
                fg=TEXT_MAIN,
                activebackground=BORDER_COLOR,
                relief="flat",
                bd=0,
                highlightthickness=0,
                anchor="w",
                padx=10,
                pady=5,
                cursor="hand2",
                command=lambda user=u, pwd=p: self._fill_credentials(user, pwd)
            )
            btn_demo.pack(fill="x", pady=2)

    def _toggle_show_pass(self):
        if self.show_pass_var.get():
            self.ent_pass.config(show="")
        else:
            self.ent_pass.config(show="•")

    def _fill_credentials(self, username: str, password: str):
        self.ent_user.delete(0, tk.END)
        self.ent_user.insert(0, username)
        self.ent_pass.delete(0, tk.END)
        self.ent_pass.insert(0, password)
        self.lbl_error.pack_forget()

    def _do_login(self):
        username = self.ent_user.get().strip()
        password = self.ent_pass.get()

        if not username:
            self._show_error("Username wajib diisi.")
            self.ent_user.focus_set()
            return
        if not password:
            self._show_error("Kata sandi wajib diisi.")
            self.ent_pass.focus_set()
            return

        try:
            user = self.facade.login(username, password)
            self.lbl_error.pack_forget()
            self.on_login_success(user)
        except PawnError as e:
            self._show_error(str(e))
        except Exception as e:
            self._show_error(f"Gagal login: {str(e)}")

    def _show_error(self, message: str):
        self.lbl_error.config(text=f"⚠️ {message}")
        self.lbl_error.pack(fill="x", pady=(0, 14), before=self.ent_user)
