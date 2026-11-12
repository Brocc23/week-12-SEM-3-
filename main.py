"""
Main Entry Point — Pegadaian Digital Nusantara (week_12)
Menginisialisasi sistem pangkalan data, menerapkan tema UI/UX, dan meluncurkan antarmuka pengguna.
"""

import sys
import tkinter as tk
from tkinter import ttk

from pawn.services.facade import Aplikasi
from pawn.ui.theme import configure_theme
from pawn.ui.login import LoginView
from pawn.ui.main_window import MainWindow


class AppLauncher:
    """Pengendali siklus hidup tampilan aplikasi (Login <-> Shell Utama)."""
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Pegadaian Digital Nusantara — Sistem Operasional Gadai Terpadu")
        self.root.geometry("1280x768")
        self.root.minsize(1080, 640)

        # Menerapkan Konfigurasi Tema Desain Terpadu
        configure_theme(self.root)

        # Inisialisasi Facade Aplikasi & Seed Database jika kosong
        self.facade = Aplikasi(db_path="pegadaian.db")
        try:
            from pawn.seed import seed_if_empty
            if hasattr(self.facade, "db"):
                seed_if_empty(self.facade.db)
        except Exception:
            pass

        self.current_screen = None
        self.show_login()

    def show_login(self):
        """Menampilkan form autentikasi login."""
        if self.current_screen:
            self.current_screen.destroy()

        self.current_screen = LoginView(
            self.root,
            facade=self.facade,
            on_login_success=self.show_main_window
        )
        self.current_screen.pack(fill="both", expand=True)

    def show_main_window(self, user: dict):
        """Menampilkan antarmuka utama setelah berhasil login."""
        if self.current_screen:
            self.current_screen.destroy()

        self.current_screen = MainWindow(
            self.root,
            facade=self.facade,
            on_logout=self.show_login
        )
        self.current_screen.pack(fill="both", expand=True)


def main():
    root = tk.Tk()
    launcher = AppLauncher(root)
    root.mainloop()


if __name__ == "__main__":
    main()
