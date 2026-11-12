"""
Modul Tema dan Desain UI/UX Pegadaian Digital Nusantara
Desain Mellow, Simple & Modern (Light Scandinavian / Warm Minimalist):
- Canvas: Warm Linen #F6F4EF
- Cards: Pure White #FFFFFF dengan 1px border halus #E5E0D8 & padding lapang
- Sidebar: Light Warm Sand #EFEBE4 (TIDAK ADA blok hitam/gelap), pill aktif pastel sage #DDE7E2
- Buttons: Muted sage fill #5A8276 dengan teks putih; secondary putih dengan border pasir halus #D8D2C6
- Treeview: Light header #EFEBE4, baris lapang 36px, soft pastel sage selection #DDE7E2, TANPA garis hitam
- Teks: Dark Slate #242D35 (kontras > 11:1), secondary #4A5562, muted #606C78 (WCAG AAA)
"""

from decimal import Decimal
from datetime import date, datetime
import tkinter as tk
from tkinter import ttk, messagebox


# ==========================================
# PALET WARNA MELLOW & LIGHT MINIMALIST
# ==========================================
BG_MAIN = "#F6F4EF"           # Warm Linen Canvas - bersih, hangat, tenang
BG_CARD = "#FFFFFF"           # Putih murni untuk kartu & dialog
BG_CARD_ALT = "#FAF9F6"       # Sangat lembut untuk zebra rows & panel sekunder
BG_CARD_MUTED = "#F0EDE5"     # Soft warm sand untuk inset boxes

# Sidebar Terang (NO DARK BLOCKS)
BG_SIDEBAR = "#EFEBE4"        # Soft warm tone untuk sidebar
BG_SIDEBAR_HOVER = "#E5E0D6"  # Hover sidebar yang lembut
BG_SIDEBAR_ACTIVE = "#DDE7E2" # Pastel Sage Pill untuk menu aktif
BG_SIDEBAR_USER = "#E5E0D6"   # Kartu profil pengguna sidebar

# Warna Brand & Status (Muted / Low Saturation)
PRIMARY = "#5A8276"           # Muted Sage Teal - tombol utama & identitas
PRIMARY_HOVER = "#486B60"     # Sage lebih gelap untuk hover
PRIMARY_DARK = "#2E4D44"      # Deep Sage untuk judul & teks penting
PRIMARY_LIGHT = "#E4ECE8"     # Pastel Sage lembut

SECONDARY = "#C2785C"         # Mellow Terracotta / Soft Warm Amber
SECONDARY_HOVER = "#A86348"
SECONDARY_DARK = "#7D3E28"
SECONDARY_LIGHT = "#F9EBE6"   # Pastel Terracotta

DANGER = "#B85353"            # Dusty Rose - peringatan tenang tanpa agresivitas
DANGER_HOVER = "#9E4141"
DANGER_DARK = "#782A2A"
DANGER_LIGHT = "#F8E9E9"      # Pastel Dusty Rose

SUCCESS = "#4D7C5D"           # Muted Forest Sage Green
SUCCESS_DARK = "#285235"
SUCCESS_LIGHT = "#E5EFE7"     # Pastel Forest Green

INFO = "#5B7C99"              # Dusty Slate Blue
INFO_DARK = "#2E4E6B"
INFO_LIGHT = "#E7EFF5"        # Pastel Slate Blue

# Garis Pembatas (1px subtle warm sand - TIDAK PERNAH HITAM)
BORDER_COLOR = "#E5E0D8"      # 1px border kartu halus
BORDER_INPUT = "#D8D2C6"      # Garis input halus
BORDER_FOCUS = "#5A8276"      # Fokus sage

# Tipografi & Teks Kontras Tinggi (WCAG AA/AAA)
TEXT_MAIN = "#242D35"         # Dark Slate - teks utama kontras tinggi (> 11:1)
TEXT_SECONDARY = "#4A5562"    # Slate Grey - teks sekunder (> 6.5:1)
TEXT_MUTED = "#606C78"        # Medium Slate - teks pembantu (> 4.8:1)
TEXT_WHITE = "#FFFFFF"        # Teks putih untuk tombol utama
TEXT_SIDEBAR = "#2D3748"      # Teks gelap untuk sidebar terang
TEXT_SIDEBAR_MUTED = "#6B7480"# Teks sekunder sidebar terang

# ==========================================
# TIPOGRAFI ERGONAMIS (Segoe UI Modern)
# ==========================================
FONT_FAMILY = "Segoe UI"
FONT_TITLE = (FONT_FAMILY, 16, "bold")
FONT_HEADER = (FONT_FAMILY, 13, "bold")
FONT_SECTION = (FONT_FAMILY, 11, "bold")
FONT_BODY = (FONT_FAMILY, 10, "normal")
FONT_BODY_BOLD = (FONT_FAMILY, 10, "bold")
FONT_LABEL = (FONT_FAMILY, 10, "bold")
FONT_SMALL = (FONT_FAMILY, 9, "normal")
FONT_SMALL_BOLD = (FONT_FAMILY, 9, "bold")
FONT_METRIC = (FONT_FAMILY, 21, "bold")
FONT_SIDEBAR = (FONT_FAMILY, 10, "bold")
FONT_BADGE = (FONT_FAMILY, 9, "bold")


def format_rupiah(val) -> str:
    """Format angka/Decimal/str ke format mata uang Indonesia: Rp 1.234.567"""
    if val is None or val == "":
        return "Rp 0"
    try:
        d = Decimal(str(val))
        int_val = int(d)
        formatted = f"{int_val:,}".replace(",", ".")
        return f"Rp {formatted}"
    except Exception:
        return f"Rp {val}"


def parse_rupiah(text: str) -> Decimal:
    """Mengubah input teks 'Rp 1.250.000' atau '1250000' menjadi Decimal."""
    if not text:
        return Decimal("0")
    clean = str(text).replace("Rp", "").replace(".", "").replace(",", "").strip()
    try:
        return Decimal(clean or "0")
    except Exception:
        return Decimal("0")


def format_date(val) -> str:
    """Format tanggal ke string YYYY-MM-DD."""
    if val is None:
        return "-"
    if isinstance(val, (datetime, date)):
        return val.strftime("%Y-%m-%d")
    return str(val)


def configure_theme(root: tk.Tk) -> ttk.Style:
    """Menerapkan konfigurasi ttk.Style mellow bebas border hitam untuk seluruh aplikasi."""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    sand = BORDER_COLOR       # "#E5E0D8"
    sand_input = BORDER_INPUT # "#D8D2C6"

    # Gaya Dasar
    style.configure(".", background=BG_MAIN, foreground=TEXT_MAIN, font=FONT_BODY)
    
    # Frames
    style.configure("TFrame", background=BG_MAIN)
    style.configure("Card.TFrame", background=BG_CARD, relief="flat", borderwidth=0)
    style.configure("Sidebar.TFrame", background=BG_SIDEBAR)
    style.configure("TopBar.TFrame", background=BG_CARD)

    # Labels
    style.configure("TLabel", background=BG_MAIN, foreground=TEXT_MAIN, font=FONT_BODY)
    style.configure("Card.TLabel", background=BG_CARD, foreground=TEXT_MAIN, font=FONT_BODY)
    style.configure("CardTitle.TLabel", background=BG_CARD, foreground=TEXT_MAIN, font=FONT_SECTION)
    style.configure("CardMuted.TLabel", background=BG_CARD, foreground=TEXT_MUTED, font=FONT_SMALL)
    style.configure("CardMetric.TLabel", background=BG_CARD, foreground=PRIMARY_DARK, font=FONT_METRIC)
    style.configure("Error.TLabel", background=BG_CARD, foreground=DANGER, font=FONT_BODY_BOLD)
    style.configure("HeaderTitle.TLabel", background=BG_CARD, foreground=TEXT_MAIN, font=FONT_TITLE)
    style.configure("HeaderSub.TLabel", background=BG_CARD, foreground=TEXT_MUTED, font=FONT_SMALL)
    
    # Sidebar Labels (Light Sidebar)
    style.configure("SidebarBrand.TLabel", background=BG_SIDEBAR, foreground=TEXT_SIDEBAR, font=FONT_TITLE)
    style.configure("SidebarSub.TLabel", background=BG_SIDEBAR, foreground=SECONDARY, font=FONT_SMALL_BOLD)
    style.configure("SidebarUser.TLabel", background=BG_SIDEBAR_USER, foreground=TEXT_SIDEBAR, font=FONT_BODY_BOLD)
    style.configure("SidebarRole.TLabel", background=BG_SIDEBAR_USER, foreground=TEXT_SIDEBAR_MUTED, font=FONT_SMALL)

    # Buttons: Setting bordercolor/darkcolor/lightcolor to remove any black border!
    style.configure("TButton", font=FONT_BODY_BOLD, padding=[12, 6], relief="flat",
                    bordercolor=sand_input, darkcolor=sand_input, lightcolor=sand_input)
    
    # Primary Button (Muted Sage Fill)
    style.configure("Primary.TButton", background=PRIMARY, foreground=TEXT_WHITE, borderwidth=0,
                    font=FONT_BODY_BOLD, padding=[16, 8],
                    bordercolor=PRIMARY, darkcolor=PRIMARY, lightcolor=PRIMARY)
    style.map("Primary.TButton",
              background=[("active", PRIMARY_HOVER), ("disabled", sand)],
              bordercolor=[("active", PRIMARY_HOVER), ("disabled", sand)],
              foreground=[("disabled", TEXT_MUTED)])

    # Secondary Button (White Card with Soft Sand Border, NEVER black)
    style.configure("Secondary.TButton", background=BG_CARD, foreground=TEXT_SECONDARY,
                    borderwidth=1, relief="solid", font=FONT_BODY_BOLD, padding=[14, 7],
                    bordercolor=sand_input, darkcolor=sand_input, lightcolor=sand_input)
    style.map("Secondary.TButton",
              background=[("active", BG_CARD_MUTED), ("pressed", sand)],
              bordercolor=[("active", PRIMARY), ("pressed", PRIMARY)],
              foreground=[("active", TEXT_MAIN)])

    # Accent Button (Mellow Terracotta)
    style.configure("Accent.TButton", background=SECONDARY, foreground=TEXT_WHITE, borderwidth=0,
                    font=FONT_BODY_BOLD, padding=[16, 8],
                    bordercolor=SECONDARY, darkcolor=SECONDARY, lightcolor=SECONDARY)
    style.map("Accent.TButton",
              background=[("active", SECONDARY_HOVER), ("disabled", sand)],
              bordercolor=[("active", SECONDARY_HOVER), ("disabled", sand)])

    # Danger Button (Dusty Rose)
    style.configure("Danger.TButton", background=DANGER, foreground=TEXT_WHITE, borderwidth=0,
                    font=FONT_BODY_BOLD, padding=[14, 7],
                    bordercolor=DANGER, darkcolor=DANGER, lightcolor=DANGER)
    style.map("Danger.TButton",
              background=[("active", DANGER_HOVER), ("disabled", sand)],
              bordercolor=[("active", DANGER_HOVER), ("disabled", sand)])

    # Entry & Combobox: Soft bordercolor, no black
    style.configure("TEntry", fieldbackground=BG_CARD, foreground=TEXT_MAIN, padding=[8, 6],
                    bordercolor=sand_input, darkcolor=sand_input, lightcolor=sand_input)
    style.map("TEntry",
              bordercolor=[("focus", PRIMARY), ("active", PRIMARY)])

    style.configure("TCombobox", fieldbackground=BG_CARD, foreground=TEXT_MAIN, padding=[6, 5],
                    bordercolor=sand_input, darkcolor=sand_input, lightcolor=sand_input)
    style.map("TCombobox",
              bordercolor=[("focus", PRIMARY), ("active", PRIMARY)])

    # Notebook (Tabs)
    style.configure("TNotebook", background=BG_MAIN, borderwidth=0,
                    bordercolor=BG_MAIN, darkcolor=BG_MAIN, lightcolor=BG_MAIN)
    style.configure("TNotebook.Tab", background=BG_CARD_MUTED, foreground=TEXT_MUTED,
                    padding=[18, 8], font=FONT_BODY_BOLD, borderwidth=0,
                    bordercolor=sand, darkcolor=sand, lightcolor=sand)
    style.map("TNotebook.Tab",
              background=[("selected", BG_CARD)],
              foreground=[("selected", PRIMARY_DARK)],
              bordercolor=[("selected", sand)])

    # Treeview (Data Tables: Generous 36px rowheight, light sand header, soft pastel sage selection, NO black borders)
    style.configure("Treeview",
                    background=BG_CARD,
                    foreground=TEXT_MAIN,
                    fieldbackground=BG_CARD,
                    rowheight=36,
                    font=FONT_BODY,
                    borderwidth=0,
                    bordercolor=sand,
                    darkcolor=sand,
                    lightcolor=sand)
    style.configure("Treeview.Heading",
                    background="#EFEBE4",
                    foreground=TEXT_MAIN,
                    font=FONT_LABEL,
                    padding=[10, 8],
                    relief="flat",
                    bordercolor=sand,
                    darkcolor=sand,
                    lightcolor=sand)
    style.map("Treeview",
              background=[("selected", BG_SIDEBAR_ACTIVE)],
              foreground=[("selected", PRIMARY_DARK)])
    style.map("Treeview.Heading",
              background=[("active", "#E5E0D6")],
              bordercolor=[("active", sand)])

    return style


def show_konfirmasi(parent, judul: str, pesan: str) -> bool:
    """Kotak dialog konfirmasi aksi destruktif atau penting."""
    return messagebox.askyesno(judul, pesan, icon="warning", parent=parent)


def show_pesan_sukses(parent, judul: str, pesan: str) -> None:
    """Notifikasi sukses."""
    messagebox.showinfo(judul, pesan, parent=parent)


def show_pesan_error(parent, judul: str, pesan: str) -> None:
    """Notifikasi error dengan teks ramah pengguna."""
    messagebox.showerror(judul, pesan, parent=parent)
