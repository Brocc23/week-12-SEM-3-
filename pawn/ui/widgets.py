"""
Komponen Widget UI Reusable untuk Pegadaian Digital Nusantara
Menyediakan Kontainer Scrollable, Kartu Bersih Bebas Border Gelap, Tabel Data Ber-heading Sejajar, dan Stepper.
"""

import tkinter as tk
from tkinter import ttk
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional, Tuple

from pawn.ui.theme import (
    BG_CARD, BG_CARD_ALT, BG_CARD_MUTED, BG_MAIN, BORDER_COLOR, BORDER_INPUT,
    PRIMARY, PRIMARY_LIGHT, PRIMARY_DARK, SECONDARY, SECONDARY_LIGHT, SECONDARY_DARK,
    DANGER, DANGER_LIGHT, DANGER_DARK, SUCCESS, SUCCESS_LIGHT, SUCCESS_DARK,
    INFO, INFO_LIGHT, INFO_DARK,
    TEXT_MAIN, TEXT_SECONDARY, TEXT_MUTED, TEXT_WHITE,
    FONT_TITLE, FONT_HEADER, FONT_SECTION, FONT_BODY, FONT_BODY_BOLD,
    FONT_LABEL, FONT_SMALL, FONT_SMALL_BOLD, FONT_METRIC, FONT_BADGE,
    format_rupiah, format_date
)


class ScrollableFrame(tk.Frame):
    """
    Kontainer dengan kemampuan scrolling vertikal otomatis via Canvas.
    Mencegah formulir dan konten terpotong pada layar laptop (1366x768 / 1280x720).
    """
    def __init__(self, parent, bg: str = BG_MAIN, **kwargs):
        super().__init__(parent, bg=bg, highlightthickness=0, bd=0, **kwargs)
        
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, borderwidth=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_content = tk.Frame(self.canvas, bg=bg, highlightthickness=0, bd=0)

        self.scrollable_content.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self._window_id = self.canvas.create_window((0, 0), window=self.scrollable_content, anchor="nw")
        
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self.bind_mousewheel(self)
        self.bind_mousewheel(self.canvas)
        self.bind_mousewheel(self.scrollable_content)

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self._window_id, width=event.width)

    def bind_mousewheel(self, widget):
        widget.bind("<Enter>", lambda _: self._bind_wheel_events())
        widget.bind("<Leave>", lambda _: self._unbind_wheel_events())

    def _bind_wheel_events(self):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_wheel_events(self):
        self.canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event):
        if self.canvas.winfo_exists():
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


class Card(tk.Frame):
    """Komponen kartu putih bersih dengan border 1px warm sand halus dan padding 8px-scale."""
    def __init__(self, parent, bg: str = BG_CARD, border_color: str = BORDER_COLOR,
                 padx: int = 20, pady: int = 16, **kwargs):
        super().__init__(parent, bg=border_color, padx=1, pady=1, highlightthickness=0, bd=0, **kwargs)
        self.inner = tk.Frame(self, bg=bg, padx=padx, pady=pady, highlightthickness=0, bd=0)
        self.inner.pack(fill="both", expand=True)


class StatCard(tk.Frame):
    """Kartu metrik/KPI ringkasan dashboard dengan garis aksen warna modern."""
    def __init__(self, parent, title: str, value: str = "-", subtitle: str = "",
                 accent_color: str = PRIMARY, **kwargs):
        super().__init__(parent, bg=BORDER_COLOR, padx=1, pady=1, highlightthickness=0, bd=0, **kwargs)
        
        self.inner = tk.Frame(self, bg=BG_CARD, highlightthickness=0, bd=0)
        self.inner.pack(fill="both", expand=True)
        
        # Garis aksen vertikal di kiri kartu
        accent_bar = tk.Frame(self.inner, bg=accent_color, width=5, highlightthickness=0, bd=0)
        accent_bar.pack(side="left", fill="y")
        
        content = tk.Frame(self.inner, bg=BG_CARD, padx=18, pady=16, highlightthickness=0, bd=0)
        content.pack(side="left", fill="both", expand=True)
        
        self.lbl_title = tk.Label(content, text=title.upper(), font=FONT_SMALL_BOLD,
                                  fg=TEXT_MUTED, bg=BG_CARD, anchor="w")
        self.lbl_title.pack(fill="x")
        
        self.lbl_val = tk.Label(content, text=value, font=FONT_METRIC,
                                fg=TEXT_MAIN, bg=BG_CARD, anchor="w")
        self.lbl_val.pack(fill="x", pady=(4, 2))
        
        self.lbl_sub = tk.Label(content, text=subtitle, font=FONT_SMALL,
                                fg=TEXT_MUTED, bg=BG_CARD, anchor="w")
        self.lbl_sub.pack(fill="x")

    def update_value(self, val: str, subtitle: Optional[str] = None):
        self.lbl_val.config(text=val)
        if subtitle is not None:
            self.lbl_sub.config(text=subtitle)


class DataTable(tk.Frame):
    """
    Tabel Data berbasis ttk.Treeview dengan dukungan zebra striping,
    status pill badges berwarna pastel, header sejajar kolom data, dan tinggi baris lapang 36px.
    """
    def __init__(self, parent, columns: List[Tuple[str, str, int, str]],
                 show_row_index: bool = False, on_select: Optional[Callable] = None,
                 on_double_click: Optional[Callable] = None, stretch_col: Optional[str] = None,
                 show_vsb: bool = True, show_hsb: bool = True, height: Optional[int] = None, **kwargs):
        super().__init__(parent, bg=BG_CARD, highlightthickness=0, bd=0, **kwargs)
        self.columns_config = columns
        self.show_row_index = show_row_index
        self.on_select = on_select
        self.on_double_click = on_double_click
        self.stretch_col = stretch_col
        self.show_vsb = show_vsb
        self.show_hsb = show_hsb
        self.table_height = height
        
        self._raw_data: List[Dict[str, Any]] = []
        self._sort_reverse: Dict[str, bool] = {}

        self._build_ui()

    def _build_ui(self):
        col_ids = [col[0] for col in self.columns_config]
        
        table_frame = tk.Frame(self, bg=BG_CARD, highlightthickness=0, bd=0)
        table_frame.pack(fill="both", expand=True)
        
        tree_kwargs = {"columns": col_ids, "show": "headings", "selectmode": "browse"}
        if self.table_height:
            tree_kwargs["height"] = self.table_height

        self.tree = ttk.Treeview(table_frame, **tree_kwargs)
        
        if self.show_vsb:
            vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
            self.tree.configure(yscrollcommand=vsb.set)
            vsb.grid(row=0, column=1, sticky="ns")
        
        if self.show_hsb:
            hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
            self.tree.configure(xscrollcommand=hsb.set)
            hsb.grid(row=1, column=0, sticky="ew")
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        # Konfigurasi Kolom & Header (Header sejajar dengan kolom data)
        for col_id, col_text, col_width, col_anchor in self.columns_config:
            stretch = (col_id == self.stretch_col) if self.stretch_col else (col_width >= 160)
            self.tree.heading(col_id, text=col_text, anchor=col_anchor,
                              command=lambda c=col_id: self._sort_by_column(c))
            self.tree.column(col_id, width=col_width, minwidth=max(60, col_width // 2),
                             anchor=col_anchor, stretch=stretch)

        # Zebra row tags & Badge highlights
        self.tree.tag_configure("evenrow", background=BG_CARD, foreground=TEXT_MAIN)
        self.tree.tag_configure("oddrow", background=BG_CARD_ALT, foreground=TEXT_MAIN)
        
        # Status Badge Styling (Pastel fill dengan teks lebih gelap kontras tinggi)
        self.tree.tag_configure("status_danger", background=DANGER_LIGHT, foreground=DANGER_DARK)
        self.tree.tag_configure("status_success", background=SUCCESS_LIGHT, foreground=SUCCESS_DARK)
        self.tree.tag_configure("status_warning", background=SECONDARY_LIGHT, foreground=SECONDARY_DARK)
        self.tree.tag_configure("status_info", background=INFO_LIGHT, foreground=INFO_DARK)

        # Event bindings
        if self.on_select:
            self.tree.bind("<<TreeviewSelect>>", lambda e: self.on_select(self.get_selected()))
        if self.on_double_click:
            self.tree.bind("<Double-1>", lambda e: self.on_double_click(self.get_selected()))

        self.lbl_empty = tk.Label(self, text="Tidak ada data untuk ditampilkan",
                                  font=FONT_BODY, fg=TEXT_MUTED, bg=BG_CARD, pady=28)

    def set_data(self, data: List[Dict[str, Any]], formatters: Optional[Dict[str, Callable]] = None):
        """Memuat data baru ke tabel dengan zebra striping dan format custom."""
        self._raw_data = list(data)
        self.clear()
        
        if not self._raw_data:
            self.lbl_empty.place(relx=0.5, rely=0.5, anchor="center")
            return
        else:
            self.lbl_empty.place_forget()

        fmt_map = formatters or {}
        
        for idx, row in enumerate(self._raw_data):
            vals = []
            for col_id, _, _, _ in self.columns_config:
                val = row.get(col_id, "")
                if col_id in fmt_map:
                    val = fmt_map[col_id](val, row)
                vals.append(val)
            
            tag = "oddrow" if idx % 2 == 1 else "evenrow"
            
            status_val = str(row.get("status", "")).upper()
            if status_val in ("JATUH_TEMPO", "DEFISIT", "GAGAL", "DITANGGUHKAN"):
                tag = "status_danger"
            elif status_val in ("LUNAS", "SURPLUS", "BERHASIL", "AKTIF"):
                tag = "status_success"
            elif status_val in ("DALAM_PROSES_LELANG", "TERLELANG"):
                tag = "status_warning"
            elif status_val in ("TERGADAI", "DIKEMBALIKAN"):
                tag = "status_info"
                
            self.tree.insert("", "end", iid=str(idx), values=vals, tags=(tag,))

    def get_selected(self) -> Optional[Dict[str, Any]]:
        """Mengembalikan dictionary data baris yang dipilih."""
        selected_ids = self.tree.selection()
        if not selected_ids:
            return None
        idx_str = selected_ids[0]
        try:
            idx = int(idx_str)
            if 0 <= idx < len(self._raw_data):
                return self._raw_data[idx]
        except Exception:
            pass
        return None

    def clear(self):
        """Mengosongkan semua baris pada tabel."""
        for item in self.tree.get_children():
            self.tree.delete(item)

    def _sort_by_column(self, col_id: str):
        """Mengurutkan data berdasarkan kolom saat header diklik."""
        if not self._raw_data:
            return
        reverse = self._sort_reverse.get(col_id, False)
        self._sort_reverse[col_id] = not reverse

        def sort_key(item):
            v = item.get(col_id)
            if v is None:
                return ""
            if isinstance(v, (int, float, Decimal)):
                return v
            try:
                return float(str(v).replace("Rp", "").replace(".", "").replace(",", "").strip())
            except Exception:
                return str(v).lower()

        self._raw_data.sort(key=sort_key, reverse=reverse)
        self.set_data(self._raw_data)


class FormDialog(tk.Toplevel):
    """
    Dialog modal form modern dengan scrollable body dan border halus 1px bebas garis hitam.
    """
    def __init__(self, parent, title: str, width: int = 540, height: int = 500):
        super().__init__(parent)
        self.title(title)
        self.geometry(f"{width}x{height}")
        self.minsize(460, 380)
        self.configure(bg=BG_CARD)
        self.transient(parent)
        self.grab_set()

        try:
            x = parent.winfo_rootx() + (parent.winfo_width() - width) // 2
            y = parent.winfo_rooty() + (parent.winfo_height() - height) // 2
            self.geometry(f"+{max(20, x)}+{max(20, y)}")
        except Exception:
            pass

        # 1. Header Dialog
        header = tk.Frame(self, bg=PRIMARY_DARK, padx=22, pady=16, highlightthickness=0, bd=0)
        header.pack(fill="x")
        tk.Label(header, text=title, font=FONT_HEADER, fg=TEXT_WHITE, bg=PRIMARY_DARK).pack(anchor="w")

        # 2. Banner Error Validasi
        self.error_banner = tk.Label(self, text="", font=FONT_BODY_BOLD, fg=DANGER_DARK,
                                     bg=DANGER_LIGHT, padx=16, pady=8, anchor="w", wraplength=width-50)

        # 3. Footer Tombol Aksi (Dengan 1px top border halus)
        footer_wrap = tk.Frame(self, bg=BORDER_COLOR, highlightthickness=0, bd=0)
        footer_wrap.pack(fill="x", side="bottom")

        footer = tk.Frame(footer_wrap, bg=BG_CARD_ALT, padx=20, pady=14, highlightthickness=0, bd=0)
        footer.pack(fill="x", pady=(1, 0))

        self.btn_batal = ttk.Button(footer, text="Batal", style="Secondary.TButton", command=self.destroy)
        self.btn_batal.pack(side="right", padx=(10, 0))

        self.btn_submit = ttk.Button(footer, text="Simpan", style="Primary.TButton", command=self.on_submit)
        self.btn_submit.pack(side="right")

        # 4. Scrollable Form Body Container
        self.scroll_container = ScrollableFrame(self, bg=BG_CARD)
        self.scroll_container.pack(fill="both", expand=True)
        
        self.body = tk.Frame(self.scroll_container.scrollable_content, bg=BG_CARD, padx=24, pady=20, highlightthickness=0, bd=0)
        self.body.pack(fill="both", expand=True)

    def show_error(self, message: str):
        self.error_banner.config(text=f"⚠️ {message}")
        self.error_banner.pack(fill="x", before=self.scroll_container)

    def hide_error(self):
        self.error_banner.pack_forget()

    def on_submit(self):
        self.destroy()


class StepperWidget(tk.Frame):
    """
    Indikator progres visual 9-Langkah Alur Gadai.
    Desain bersih dan responsif, dengan status selesai (hijau), aktif (sage), dan antrean (sand).
    """
    def __init__(self, parent, steps: List[str], current_step: int = 1, **kwargs):
        super().__init__(parent, bg=BG_CARD, padx=12, pady=10, highlightthickness=0, bd=0, **kwargs)
        self.steps = steps
        self.current_step = current_step
        self._build_ui()

    def _build_ui(self):
        for widget in self.winfo_children():
            widget.destroy()

        container = tk.Frame(self, bg=BG_CARD, highlightthickness=0, bd=0)
        container.pack(fill="x", expand=True)

        for i, name in enumerate(self.steps, start=1):
            col_frame = tk.Frame(container, bg=BG_CARD, highlightthickness=0, bd=0)
            col_frame.pack(side="left", expand=True, fill="x")

            if i < self.current_step:
                bg_badge = SUCCESS
                fg_badge = TEXT_WHITE
                badge_text = "✓"
                lbl_color = TEXT_SECONDARY
                lbl_font = FONT_SMALL_BOLD
            elif i == self.current_step:
                bg_badge = PRIMARY
                fg_badge = TEXT_WHITE
                badge_text = str(i)
                lbl_color = PRIMARY_DARK
                lbl_font = FONT_SMALL_BOLD
            else:
                bg_badge = BORDER_INPUT
                fg_badge = TEXT_MUTED
                badge_text = str(i)
                lbl_color = TEXT_MUTED
                lbl_font = FONT_SMALL

            top_row = tk.Frame(col_frame, bg=BG_CARD, highlightthickness=0, bd=0)
            top_row.pack(fill="x")

            circle = tk.Label(top_row, text=f" {badge_text} ", font=FONT_BADGE,
                              bg=bg_badge, fg=fg_badge, width=3, relief="flat", bd=0)
            circle.pack(anchor="center")

            title_lbl = tk.Label(col_frame, text=f"{i}. {name}", font=lbl_font,
                                 fg=lbl_color, bg=BG_CARD, wraplength=95, justify="center")
            title_lbl.pack(anchor="center", pady=(4, 0))

    def set_step(self, step: int):
        self.current_step = step
        self._build_ui()
