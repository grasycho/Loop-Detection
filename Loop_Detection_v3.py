"""
Loop Detection — Frame Duplicate / Loop Analyser
Supports video files and image sequences.

Dependencies:
    pip install customtkinter opencv-python pillow ImageHash numpy
"""

import csv
import json
import re
import threading
import time
from pathlib import Path

import cv2
import customtkinter as ctk
import imagehash
import numpy as np
import tkinter as tk
from PIL import Image, ImageTk
from tkinter import filedialog, messagebox


# ── Theme ──────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

ACCENT = "#4B9EFF"
ACCENT2 = "#7B61FF"
BG_DEEP = "#0E0E1A"
BG_CARD = "#16162A"
BG_MID = "#1E1E38"
BG_ROW_A = "#18182E"
BG_ROW_B = "#1C1C34"
TEXT_DIM = "#7777AA"
SUCCESS = "#3DDC84"
WARN = "#FFAA33"
ERROR = "#FF5555"
FONT_MONO = "Consolas"

VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".mxf", ".m4v"}
IMAGE_EXTS = {
    ".png", ".jpg", ".jpeg", ".tif", ".tiff",
    ".bmp", ".webp", ".dpx", ".exr"
}

HASH_METHODS = [
    "pHash (Perceptual)",
    "dHash (Difference)",
    "aHash (Average)",
    "wHash (Wavelet)",
]


def natural_sort_key(path):
    """Sort filenames naturally: frame_2 before frame_10."""
    return [
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", Path(path).name)
    ]


# ── Tooltip ────────────────────────────────────────────────────────────────────
class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, _=None):
        if self.tip:
            return

        x = self.widget.winfo_rootx() + 24
        y = self.widget.winfo_rooty() + 24
        self.tip = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(
            tw,
            text=self.text,
            background="#1A1A3A",
            foreground="white",
            relief="flat",
            font=(FONT_MONO, 9),
            padx=8,
            pady=5,
        ).pack()

    def hide(self, _=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


# ── Result table ───────────────────────────────────────────────────────────────
class ResultTable(ctk.CTkScrollableFrame):
    COL_WIDTHS = [80, 80, 80, 260, 120]
    HEADERS = ["Group", "Count", "First", "All Frames", "Similarity"]

    def __init__(self, master, **kw):
        super().__init__(master, fg_color=BG_CARD, **kw)
        self._rows = []
        self._draw_header()

    def _draw_header(self):
        hdr = ctk.CTkFrame(self, fg_color=BG_MID, corner_radius=6)
        hdr.pack(fill="x", padx=4, pady=(4, 0))

        for i, (header, width) in enumerate(zip(self.HEADERS, self.COL_WIDTHS)):
            ctk.CTkLabel(
                hdr,
                text=header,
                width=width,
                font=ctk.CTkFont(family=FONT_MONO, size=11, weight="bold"),
                text_color=ACCENT,
                anchor="w",
            ).grid(
                row=0,
                column=i,
                padx=(8 if i == 0 else 2, 2),
                pady=6,
                sticky="w",
            )

    def clear(self):
        for row in self._rows:
            row.destroy()
        self._rows.clear()

    def add_row(self, group_idx, frame_indices, similarity_pct):
        bg = BG_ROW_A if group_idx % 2 == 0 else BG_ROW_B
        row = ctk.CTkFrame(self, fg_color=bg, corner_radius=4)
        row.pack(fill="x", padx=4, pady=1)
        self._rows.append(row)

        count = len(frame_indices)
        first = frame_indices[0]
        all_frames = ", ".join(str(frame) for frame in frame_indices[:12])
        if len(frame_indices) > 12:
            all_frames += f" … (+{len(frame_indices) - 12})"

        sim_color = (
            SUCCESS if similarity_pct >= 95
            else WARN if similarity_pct >= 80
            else ERROR
        )

        values = [
            str(group_idx + 1),
            str(count),
            str(first),
            all_frames,
            f"{similarity_pct:.1f}%",
        ]
        colors = [None, None, None, None, sim_color]

        for i, (value, width, color) in enumerate(
            zip(values, self.COL_WIDTHS, colors)
        ):
            ctk.CTkLabel(
                row,
                text=value,
                width=width,
                font=ctk.CTkFont(family=FONT_MONO, size=11),
                text_color=color or "white",
                anchor="w",
            ).grid(
                row=0,
                column=i,
                padx=(8 if i == 0 else 2, 2),
                pady=4,
                sticky="w",
            )


# ── Main application ───────────────────────────────────────────────────────────
class LoopDetectorApp:
    def __init__(self, root: ctk.CTk):
        self.root = root
        self.root.title("Loop Detection  ·  Frame Duplicate Analyser")
        self.root.geometry("780x920")
        self.root.resizable(False, False)
        self.root.configure(fg_color=BG_DEEP)

        self.files = []
        self.is_video = False
        self.cancel_flag = threading.Event()
        self.results = {}
        self._start_time = 0.0

        self._build_ui()

    # ── UI ─────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        hdr = ctk.CTkFrame(
            self.root,
            fg_color=BG_CARD,
            corner_radius=0,
            height=68,
        )
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        ctk.CTkLabel(
            hdr,
            text="⬡  LOOP DETECTION",
            font=ctk.CTkFont(family=FONT_MONO, size=18, weight="bold"),
            text_color=ACCENT,
        ).pack(side="left", padx=24)

        ctk.CTkLabel(
            hdr,
            text="frame duplicate analyser",
            font=ctk.CTkFont(family=FONT_MONO, size=11),
            text_color=TEXT_DIM,
        ).pack(side="left")

        self.theme_btn = ctk.CTkButton(
            hdr,
            text="☀ Light",
            width=80,
            height=28,
            fg_color="transparent",
            border_width=1,
            border_color="#2A2A4A",
            text_color=TEXT_DIM,
            font=ctk.CTkFont(size=11),
            command=self._toggle_theme,
        )
        self.theme_btn.pack(side="right", padx=16)

        body = ctk.CTkScrollableFrame(
            self.root,
            fg_color=BG_DEEP,
            scrollbar_button_color=BG_MID,
        )
        body.pack(fill="both", expand=True)

        # INPUT
        self._section(body, "📂  INPUT")
        in_card = self._card(body)

        btn_row = ctk.CTkFrame(in_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(14, 6))

        ctk.CTkButton(
            btn_row,
            text="Select Video",
            width=130,
            height=36,
            fg_color=ACCENT,
            hover_color="#3A8EEF",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._select_video,
        ).pack(side="left")

        ctk.CTkButton(
            btn_row,
            text="Select Image Sequence",
            width=180,
            height=36,
            fg_color="transparent",
            border_width=1,
            border_color=ACCENT,
            text_color=ACCENT,
            hover_color="#1A2A3A",
            font=ctk.CTkFont(size=13),
            command=self._select_images,
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            btn_row,
            text="Select Image Folder",
            width=160,
            height=36,
            fg_color="transparent",
            border_width=1,
            border_color=ACCENT2,
            text_color=ACCENT2,
            hover_color="#1A1A3A",
            font=ctk.CTkFont(size=13),
            command=self._select_image_folder,
        ).pack(side="left")

        self.info_label = ctk.CTkLabel(
            in_card,
            text="No files loaded",
            font=ctk.CTkFont(family=FONT_MONO, size=11),
            text_color=TEXT_DIM,
            justify="left",
            wraplength=700,
        )
        self.info_label.pack(anchor="w", padx=16, pady=(0, 14))

        # DETECTION SETTINGS
        self._section(body, "⚙  DETECTION SETTINGS")
        cfg_card = self._card(body)
        grid = ctk.CTkFrame(cfg_card, fg_color="transparent")
        grid.pack(fill="x", padx=16, pady=14)

        ctk.CTkLabel(
            grid,
            text="Hash Method:",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_DIM,
        ).grid(row=0, column=0, sticky="w", padx=(0, 8))

        self.hash_var = ctk.StringVar(value=HASH_METHODS[0])
        ctk.CTkOptionMenu(
            grid,
            values=HASH_METHODS,
            variable=self.hash_var,
            width=200,
            fg_color=BG_MID,
            button_color=ACCENT,
            font=ctk.CTkFont(size=12),
        ).grid(row=0, column=1, padx=(0, 24), sticky="w")

        ctk.CTkLabel(
            grid,
            text="Hash Size:",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_DIM,
        ).grid(row=0, column=2, sticky="w", padx=(0, 8))

        self.hash_size_var = ctk.StringVar(value="16")
        hash_size_menu = ctk.CTkOptionMenu(
            grid,
            values=["8", "12", "16", "24", "32"],
            variable=self.hash_size_var,
            width=80,
            fg_color=BG_MID,
            button_color=ACCENT,
            font=ctk.CTkFont(size=12),
        )
        hash_size_menu.grid(row=0, column=3, sticky="w")
        Tooltip(hash_size_menu, "Larger = more precise but slower.")

        ctk.CTkLabel(
            grid,
            text="Threshold:",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_DIM,
        ).grid(row=1, column=0, sticky="w", pady=(12, 0), padx=(0, 8))

        self.threshold_var = ctk.IntVar(value=5)
        threshold_row = ctk.CTkFrame(grid, fg_color="transparent")
        threshold_row.grid(
            row=1,
            column=1,
            columnspan=2,
            sticky="w",
            pady=(12, 0),
        )

        self.threshold_slider = ctk.CTkSlider(
            threshold_row,
            from_=0,
            to=30,
            number_of_steps=30,
            variable=self.threshold_var,
            width=200,
            fg_color=BG_MID,
            progress_color=ACCENT,
            command=lambda value: self._update_threshold_label(int(round(value))),
        )
        self.threshold_slider.pack(side="left")

        self.threshold_val_lbl = ctk.CTkLabel(
            threshold_row,
            text="5",
            font=ctk.CTkFont(family=FONT_MONO, size=12),
            text_color=ACCENT,
            width=28,
        )
        self.threshold_val_lbl.pack(side="left", padx=8)

        ctk.CTkLabel(
            threshold_row,
            text="(0 = exact match, higher = more permissive)",
            font=ctk.CTkFont(size=10),
            text_color=TEXT_DIM,
        ).pack(side="left")

        ctk.CTkLabel(
            grid,
            text="Frame Skip:",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_DIM,
        ).grid(row=2, column=0, sticky="w", pady=(12, 0), padx=(0, 8))

        skip_row = ctk.CTkFrame(grid, fg_color="transparent")
        skip_row.grid(
            row=2,
            column=1,
            columnspan=3,
            sticky="w",
            pady=(12, 0),
        )

        self.skip_var = ctk.StringVar(value="1 (every frame)")
        ctk.CTkOptionMenu(
            skip_row,
            values=["1 (every frame)", "2", "3", "4", "5", "10"],
            variable=self.skip_var,
            width=170,
            fg_color=BG_MID,
            button_color=ACCENT,
            font=ctk.CTkFont(size=12),
        ).pack(side="left")

        ctk.CTkLabel(
            skip_row,
            text="  Analyse every Nth frame",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_DIM,
        ).pack(side="left")

        ctk.CTkLabel(
            grid,
            text="Frame Range:",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_DIM,
        ).grid(row=3, column=0, sticky="w", pady=(12, 0), padx=(0, 8))

        range_row = ctk.CTkFrame(grid, fg_color="transparent")
        range_row.grid(
            row=3,
            column=1,
            columnspan=3,
            sticky="w",
            pady=(12, 0),
        )

        ctk.CTkLabel(
            range_row,
            text="Start:",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_DIM,
        ).pack(side="left", padx=(0, 4))

        self.range_start_var = ctk.StringVar(value="0")
        ctk.CTkEntry(
            range_row,
            textvariable=self.range_start_var,
            width=70,
            fg_color=BG_MID,
            border_color="#2A2A4A",
        ).pack(side="left")

        ctk.CTkLabel(
            range_row,
            text="  End (0 = all):",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_DIM,
        ).pack(side="left", padx=(8, 4))

        self.range_end_var = ctk.StringVar(value="0")
        ctk.CTkEntry(
            range_row,
            textvariable=self.range_end_var,
            width=70,
            fg_color=BG_MID,
            border_color="#2A2A4A",
        ).pack(side="left")

        cb_row = ctk.CTkFrame(cfg_card, fg_color="transparent")
        cb_row.pack(fill="x", padx=16, pady=(0, 14))

        self.consec_only_var = ctk.BooleanVar(value=False)
        consec_cb = ctk.CTkCheckBox(
            cb_row,
            text="Consecutive duplicates only",
            variable=self.consec_only_var,
            fg_color=ACCENT,
            border_color="#333355",
            font=ctk.CTkFont(size=12),
        )
        consec_cb.pack(side="left", padx=(0, 20))
        Tooltip(
            consec_cb,
            "Only compare consecutive sampled frames. Useful for adjacent repeats and seams.",
        )

        self.export_thumbs_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            cb_row,
            text="Export thumbnails of duplicates",
            variable=self.export_thumbs_var,
            fg_color=ACCENT2,
            border_color="#333355",
            font=ctk.CTkFont(size=12),
        ).pack(side="left", padx=(0, 20))

        self.show_first_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            cb_row,
            text="Preview first duplicate",
            variable=self.show_first_var,
            fg_color=ACCENT,
            border_color="#333355",
            font=ctk.CTkFont(size=12),
        ).pack(side="left")

        # PROGRESS
        self._section(body, "⬡  PROGRESS")
        prog_card = self._card(body)

        self.progress_bar = ctk.CTkProgressBar(
            prog_card,
            height=14,
            corner_radius=7,
            fg_color=BG_MID,
            progress_color=ACCENT,
        )
        self.progress_bar.pack(fill="x", padx=20, pady=(16, 6))
        self.progress_bar.set(0)

        stat_row = ctk.CTkFrame(prog_card, fg_color="transparent")
        stat_row.pack(fill="x", padx=20, pady=(0, 14))

        self.pct_lbl = ctk.CTkLabel(
            stat_row,
            text="0%",
            font=ctk.CTkFont(family=FONT_MONO, size=11),
            text_color=ACCENT,
        )
        self.pct_lbl.pack(side="left")

        self.status_lbl = ctk.CTkLabel(
            stat_row,
            text="Ready",
            font=ctk.CTkFont(family=FONT_MONO, size=11),
            text_color=TEXT_DIM,
        )
        self.status_lbl.pack(side="left", padx=12)

        self.eta_lbl = ctk.CTkLabel(
            stat_row,
            text="",
            font=ctk.CTkFont(family=FONT_MONO, size=11),
            text_color=TEXT_DIM,
        )
        self.eta_lbl.pack(side="right")

        # PREVIEW
        self._section(body, "🖼  DUPLICATE PREVIEW")
        prev_card = self._card(body)

        self.preview_label = ctk.CTkLabel(
            prev_card,
            text="No preview yet.",
            font=ctk.CTkFont(family=FONT_MONO, size=11),
            text_color=TEXT_DIM,
            height=100,
        )
        self.preview_label.pack(pady=10)

        # RESULTS
        self._section(body, "📋  RESULTS")
        self.result_table = ResultTable(body, height=200)
        self.result_table.pack(fill="x", padx=20, pady=6)

        self.result_summary = ctk.CTkLabel(
            body,
            text="",
            font=ctk.CTkFont(family=FONT_MONO, size=12),
            text_color=TEXT_DIM,
        )
        self.result_summary.pack(anchor="w", padx=20, pady=(4, 0))

        # BUTTONS
        btn_row2 = ctk.CTkFrame(body, fg_color="transparent")
        btn_row2.pack(pady=16, padx=20, fill="x")

        self.analyse_btn = ctk.CTkButton(
            btn_row2,
            text="▶  ANALYSE",
            width=160,
            height=46,
            fg_color=ACCENT,
            hover_color="#3A8EEF",
            font=ctk.CTkFont(size=14, weight="bold"),
            state="disabled",
            command=self._start_analysis,
        )
        self.analyse_btn.pack(side="left")

        self.cancel_btn = ctk.CTkButton(
            btn_row2,
            text="■  Cancel",
            width=100,
            height=46,
            fg_color="transparent",
            border_width=1,
            border_color=ERROR,
            text_color=ERROR,
            hover_color="#2A1010",
            font=ctk.CTkFont(size=13),
            state="disabled",
            command=self._cancel,
        )
        self.cancel_btn.pack(side="left", padx=8)

        self.export_csv_btn = ctk.CTkButton(
            btn_row2,
            text="⬇ Export CSV",
            width=130,
            height=46,
            fg_color="transparent",
            border_width=1,
            border_color=ACCENT2,
            text_color=ACCENT2,
            hover_color="#1A1A3A",
            font=ctk.CTkFont(size=13),
            state="disabled",
            command=self._export_csv,
        )
        self.export_csv_btn.pack(side="left", padx=8)

        self.export_json_btn = ctk.CTkButton(
            btn_row2,
            text="⬇ Export JSON",
            width=140,
            height=46,
            fg_color="transparent",
            border_width=1,
            border_color=ACCENT2,
            text_color=ACCENT2,
            hover_color="#1A1A3A",
            font=ctk.CTkFont(size=13),
            state="disabled",
            command=self._export_json,
        )
        self.export_json_btn.pack(side="left", padx=8)

        ctk.CTkButton(
            btn_row2,
            text="✕  Quit",
            width=90,
            height=46,
            fg_color="transparent",
            border_width=1,
            border_color="#333355",
            text_color=TEXT_DIM,
            hover_color="#1A1A2A",
            font=ctk.CTkFont(size=13),
            command=self.root.quit,
        ).pack(side="right")

        ctk.CTkLabel(body, text="", height=10).pack()

    # ── UI helpers ─────────────────────────────────────────────────────────────
    def _section(self, parent, text):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(14, 2))

        ctk.CTkLabel(
            row,
            text=text,
            font=ctk.CTkFont(family=FONT_MONO, size=11, weight="bold"),
            text_color=TEXT_DIM,
        ).pack(side="left")

        ctk.CTkFrame(
            row,
            height=1,
            fg_color="#2A2A4A",
        ).pack(side="left", fill="x", expand=True, padx=(10, 0))

    def _card(self, parent):
        card = ctk.CTkFrame(
            parent,
            fg_color=BG_CARD,
            corner_radius=14,
            border_width=1,
            border_color="#2A2A4A",
        )
        card.pack(fill="x", padx=20, pady=6)
        return card

    def _toggle_theme(self):
        mode = "Light" if ctk.get_appearance_mode() == "Dark" else "Dark"
        ctk.set_appearance_mode(mode)
        self.theme_btn.configure(
            text=f"{'☀' if mode == 'Dark' else '🌙'} "
                 f"{'Light' if mode == 'Dark' else 'Dark'}"
        )

    def _update_threshold_label(self, value):
        self.threshold_val_lbl.configure(text=str(value))

    def _set_status(self, text, color=TEXT_DIM):
        self.status_lbl.configure(text=text, text_color=color)

    # ── File loading ───────────────────────────────────────────────────────────
    def _select_video(self):
        path = filedialog.askopenfilename(
            title="Select Video",
            filetypes=[
                ("Video files", "*.mp4 *.avi *.mov *.mkv *.webm *.mxf *.m4v"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return

        self.files = [Path(path)]
        self.is_video = True
        self._show_video_info(path)
        self.analyse_btn.configure(state="normal")

    def _select_images(self):
        paths = filedialog.askopenfilenames(
            title="Select Image Frames",
            filetypes=[
                (
                    "Images",
                    "*.png *.jpg *.jpeg *.tif *.tiff *.bmp *.webp *.dpx *.exr",
                ),
                ("All files", "*.*"),
            ],
        )
        if not paths:
            return

        self.files = sorted(
            (Path(path) for path in paths),
            key=natural_sort_key,
        )
        self.is_video = False
        self._show_image_info()
        self.analyse_btn.configure(state="normal")

    def _select_image_folder(self):
        folder = filedialog.askdirectory(title="Select Folder of Image Frames")
        if not folder:
            return

        folder_path = Path(folder)
        self.files = sorted(
            (
                path
                for path in folder_path.iterdir()
                if path.is_file() and path.suffix.lower() in IMAGE_EXTS
            ),
            key=natural_sort_key,
        )

        if not self.files:
            messagebox.showerror("Error", "No compatible images found in folder.")
            return

        self.is_video = False
        self._show_image_info()
        self.analyse_btn.configure(state="normal")

    def _show_video_info(self, path):
        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            cap.release()
            messagebox.showerror(
                "Error",
                "OpenCV could not open this video file.",
            )
            self.files = []
            self.analyse_btn.configure(state="disabled")
            return

        fps = cap.get(cv2.CAP_PROP_FPS)
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = total / fps if fps else 0

        codec = int(cap.get(cv2.CAP_PROP_FOURCC))
        codec_str = "".join(
            chr((codec >> (8 * i)) & 0xFF)
            for i in range(4)
        ).strip()

        size_mb = Path(path).stat().st_size / (1024 * 1024)
        cap.release()

        self.info_label.configure(
            text=(
                f"🎬  {Path(path).name}  ·  {width}×{height}  ·  "
                f"{fps:.3f} fps  ·  {total} frames  ·  {duration:.2f}s  ·  "
                f"{codec_str or 'Unknown'}  ·  {size_mb:.1f} MB"
            ),
            text_color=SUCCESS,
        )

    def _show_image_info(self):
        count = len(self.files)
        extensions = {path.suffix.lower() for path in self.files}

        self.info_label.configure(
            text=(
                f"🖼  {count} image(s) loaded  ·  "
                f"Types: {', '.join(sorted(extensions))}"
            ),
            text_color=SUCCESS,
        )

    # ── Hash computation ───────────────────────────────────────────────────────
    def _compute_hash(self, frame_bgr):
        try:
            if frame_bgr is None:
                return None

            pil = Image.fromarray(
                cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            )

            method = self.hash_var.get()
            size = int(self.hash_size_var.get())

            if "pHash" in method:
                return imagehash.phash(pil, hash_size=size)
            if "dHash" in method:
                return imagehash.dhash(pil, hash_size=size)
            if "aHash" in method:
                return imagehash.average_hash(pil, hash_size=size)
            if "wHash" in method:
                return imagehash.whash(pil, hash_size=size)

        except Exception as error:
            print(f"Hash error: {error}")

        return None

    @staticmethod
    def _max_hash_distance(hash_size):
        """Maximum Hamming distance for the selected hash size."""
        return hash_size * hash_size

    @staticmethod
    def _similarity_from_distance(distance, max_distance):
        if max_distance <= 0:
            return 100.0
        similarity = 100.0 * (1.0 - (distance / max_distance))
        return max(0.0, min(100.0, similarity))

    def _build_group(self, frame_hash, frame_idx, frame_data):
        return {
            "hash": frame_hash,
            "frames": [frame_idx],
            "last_idx": frame_idx,
            "distances": [0],
            "frame_data": frame_data,
        }

    def _add_to_matching_group(
        self,
        hash_groups,
        frame_hash,
        frame_idx,
        frame_data,
        threshold,
    ):
        """Find the closest compatible group and append the frame."""
        best_group = None
        best_distance = None

        for group in hash_groups:
            distance = frame_hash - group["hash"]
            if distance <= threshold:
                if best_distance is None or distance < best_distance:
                    best_group = group
                    best_distance = distance

        if best_group is None:
            hash_groups.append(
                self._build_group(frame_hash, frame_idx, frame_data)
            )
            return

        best_group["frames"].append(frame_idx)
        best_group["last_idx"] = frame_idx
        best_group["distances"].append(best_distance)

    def _add_consecutive_match(
        self,
        hash_groups,
        previous_hash,
        previous_group,
        frame_hash,
        frame_idx,
        frame_data,
        threshold,
    ):
        """
        Consecutive mode compares only the current sampled frame with the
        immediately preceding sampled frame.
        """
        if previous_hash is None:
            group = self._build_group(frame_hash, frame_idx, frame_data)
            hash_groups.append(group)
            return frame_hash, group

        distance = frame_hash - previous_hash

        if distance <= threshold:
            group = previous_group
            group["frames"].append(frame_idx)
            group["last_idx"] = frame_idx
            group["distances"].append(distance)
        else:
            group = self._build_group(frame_hash, frame_idx, frame_data)
            hash_groups.append(group)

        return frame_hash, group

    # ── Analysis orchestration ─────────────────────────────────────────────────
    def _start_analysis(self):
        if not self.files:
            return

        self.cancel_flag.clear()
        self.result_table.clear()
        self.results = {}
        self.result_summary.configure(text="")
        self.preview_label.configure(image=None, text="No preview yet.")
        self.preview_label._image_ref = None

        self.analyse_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.export_csv_btn.configure(state="disabled")
        self.export_json_btn.configure(state="disabled")

        self.progress_bar.set(0)
        self.pct_lbl.configure(text="0%")
        self.eta_lbl.configure(text="")
        self._set_status("Starting…", ACCENT)
        self._start_time = time.time()

        threading.Thread(
            target=self._analysis_worker,
            daemon=True,
        ).start()

    def _cancel(self):
        self.cancel_flag.set()
        self._set_status("Cancelling…", WARN)

    def _parse_range(self, total):
        try:
            start = max(0, int(self.range_start_var.get()))
            end = int(self.range_end_var.get())

            start = min(start, total)
            end = total if end <= 0 else min(end, total)

            if end < start:
                start, end = end, start

            return start, end

        except ValueError:
            return 0, total

    def _get_skip(self):
        value = self.skip_var.get().split()[0]
        try:
            return max(1, int(value))
        except ValueError:
            return 1

    def _analysis_worker(self):
        try:
            if self.is_video:
                self._analyse_video()
            else:
                self._analyse_images()
        except Exception as error:
            self.root.after(0, self._analysis_error, str(error))

    def _analyse_video(self):
        cap = cv2.VideoCapture(str(self.files[0]))

        if not cap.isOpened():
            self.root.after(
                0,
                self._analysis_error,
                "OpenCV could not open the selected video.",
            )
            return

        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        skip = self._get_skip()
        start, end = self._parse_range(total)

        if start >= end:
            cap.release()
            self.root.after(
                0,
                self._analysis_error,
                "The selected frame range is empty.",
            )
            return

        cap.set(cv2.CAP_PROP_POS_FRAMES, start)

        threshold = int(self.threshold_var.get())
        consecutive_only = self.consec_only_var.get()
        hash_groups = []

        previous_hash = None
        previous_group = None

        frame_idx = start
        processed = 0
        sampled_total = len(range(start, end, skip))

        while frame_idx < end:
            if self.cancel_flag.is_set():
                break

            ret, frame = cap.read()
            if not ret:
                break

            current_idx = frame_idx
            frame_idx += 1

            if (current_idx - start) % skip != 0:
                continue

            frame_hash = self._compute_hash(frame)
            if frame_hash is not None:
                preview_data = frame.copy() if len(hash_groups) < 500 else None

                if consecutive_only:
                    previous_hash, previous_group = self._add_consecutive_match(
                        hash_groups,
                        previous_hash,
                        previous_group,
                        frame_hash,
                        current_idx,
                        preview_data,
                        threshold,
                    )
                else:
                    self._add_to_matching_group(
                        hash_groups,
                        frame_hash,
                        current_idx,
                        preview_data,
                        threshold,
                    )

            processed += 1
            pct = processed / sampled_total if sampled_total else 1.0
            elapsed = time.time() - self._start_time
            remaining = max(0, sampled_total - processed)
            eta = elapsed / processed * remaining if processed else 0.0
            timecode = self._frames_to_tc(current_idx, fps)

            self.root.after(
                0,
                self._update_progress,
                pct,
                current_idx,
                total,
                eta,
                timecode,
            )

        cap.release()

        if self.cancel_flag.is_set():
            self.root.after(0, self._finish_cancelled)
            return

        duplicates = [
            group for group in hash_groups
            if len(group["frames"]) > 1
        ]

        self.root.after(0, self._finish, duplicates, fps)

    def _analyse_images(self):
        total = len(self.files)
        skip = self._get_skip()
        start, end = self._parse_range(total)

        if start >= end:
            self.root.after(
                0,
                self._analysis_error,
                "The selected frame range is empty.",
            )
            return

        threshold = int(self.threshold_var.get())
        consecutive_only = self.consec_only_var.get()
        hash_groups = []

        previous_hash = None
        previous_group = None

        sampled_indices = list(range(start, end, skip))
        sampled_total = len(sampled_indices)

        for processed, index in enumerate(sampled_indices, start=1):
            if self.cancel_flag.is_set():
                break

            path = self.files[index]
            frame = cv2.imread(str(path), cv2.IMREAD_COLOR)

            if frame is not None:
                frame_hash = self._compute_hash(frame)

                if frame_hash is not None:
                    preview_data = (
                        frame.copy() if len(hash_groups) < 500 else None
                    )

                    if consecutive_only:
                        previous_hash, previous_group = self._add_consecutive_match(
                            hash_groups,
                            previous_hash,
                            previous_group,
                            frame_hash,
                            index,
                            preview_data,
                            threshold,
                        )
                    else:
                        self._add_to_matching_group(
                            hash_groups,
                            frame_hash,
                            index,
                            preview_data,
                            threshold,
                        )

            pct = processed / sampled_total if sampled_total else 1.0
            elapsed = time.time() - self._start_time
            remaining = max(0, sampled_total - processed)
            eta = elapsed / processed * remaining if processed else 0.0

            self.root.after(
                0,
                self._update_progress,
                pct,
                index,
                total,
                eta,
                path.name,
            )

        if self.cancel_flag.is_set():
            self.root.after(0, self._finish_cancelled)
            return

        duplicates = [
            group for group in hash_groups
            if len(group["frames"]) > 1
        ]

        self.root.after(0, self._finish, duplicates, None)

    # ── UI updates ─────────────────────────────────────────────────────────────
    def _update_progress(self, pct, frame_idx, total, eta, label):
        pct = max(0.0, min(1.0, pct))
        self.progress_bar.set(pct)
        self.pct_lbl.configure(text=f"{int(pct * 100)}%")

        eta_str = f"ETA: {int(eta)}s" if eta > 1 else ""
        self.status_lbl.configure(
            text=f"Frame {frame_idx}/{total}  {label}",
            text_color=ACCENT,
        )
        self.eta_lbl.configure(text=eta_str)

    def _finish_cancelled(self):
        elapsed = time.time() - self._start_time
        self.cancel_btn.configure(state="disabled")
        self.analyse_btn.configure(state="normal")
        self.eta_lbl.configure(text="")
        self._set_status(
            f"Cancelled after {elapsed:.1f}s.",
            WARN,
        )
        self.result_summary.configure(
            text="Analysis cancelled. Partial results were discarded.",
            text_color=WARN,
        )

    def _group_similarity(self, group):
        distances = group.get("distances", [])
        if len(distances) <= 1:
            return 100.0

        average_distance = sum(distances[1:]) / (len(distances) - 1)
        max_distance = self._max_hash_distance(
            int(self.hash_size_var.get())
        )
        return self._similarity_from_distance(
            average_distance,
            max_distance,
        )

    def _finish(self, duplicates, fps):
        self.progress_bar.set(1.0)
        self.pct_lbl.configure(text="100%")

        elapsed = time.time() - self._start_time
        self.cancel_btn.configure(state="disabled")
        self.analyse_btn.configure(state="normal")
        self.eta_lbl.configure(text="")

        if not duplicates:
            self._set_status("✓ No duplicate frames found.", SUCCESS)
            self.result_summary.configure(
                text="No duplicates detected.",
                text_color=SUCCESS,
            )
            messagebox.showinfo(
                "Result",
                "No duplicate or looping frames detected.",
            )
            return

        self.results = {
            str(index): {
                "frames": group["frames"],
                "similarity": round(self._group_similarity(group), 2),
            }
            for index, group in enumerate(duplicates)
        }

        total_duplicate_frames = sum(
            len(group["frames"])
            for group in duplicates
        )

        self._set_status(
            (
                f"✓ Done in {elapsed:.1f}s — "
                f"{len(duplicates)} group(s), "
                f"{total_duplicate_frames} frames"
            ),
            SUCCESS,
        )

        self.result_summary.configure(
            text=(
                f"{len(duplicates)} duplicate group(s)  ·  "
                f"{total_duplicate_frames} total frames  ·  "
                f"{elapsed:.1f}s elapsed"
            ),
            text_color=SUCCESS,
        )

        self.result_table.clear()

        for index, group in enumerate(duplicates):
            similarity = self._group_similarity(group)
            self.result_table.add_row(
                index,
                group["frames"],
                similarity,
            )

        self.export_csv_btn.configure(state="normal")
        self.export_json_btn.configure(state="normal")

        if (
            self.show_first_var.get()
            and duplicates[0].get("frame_data") is not None
        ):
            self._show_preview(
                duplicates[0]["frame_data"],
                duplicates[0]["frames"],
            )

        if self.export_thumbs_var.get():
            self._export_thumbnails(duplicates)

    def _analysis_error(self, message):
        self.cancel_btn.configure(state="disabled")
        self.analyse_btn.configure(state="normal")
        self.eta_lbl.configure(text="")
        self._set_status("Analysis failed.", ERROR)
        self.result_summary.configure(
            text=f"Error: {message}",
            text_color=ERROR,
        )
        messagebox.showerror("Analysis Error", message)

    def _show_preview(self, frame_bgr, frame_indices):
        try:
            rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            pil = Image.fromarray(rgb)
            pil.thumbnail((680, 180), Image.LANCZOS)
            tk_image = ImageTk.PhotoImage(pil)

            self.preview_label.configure(
                image=tk_image,
                text=(
                    "First duplicate group — "
                    f"frames: {frame_indices[:6]}"
                ),
                compound="top",
            )
            self.preview_label._image_ref = tk_image

        except Exception as error:
            self.preview_label.configure(
                image=None,
                text=f"Preview error: {error}",
            )

    # ── Export ─────────────────────────────────────────────────────────────────
    def _export_csv(self):
        if not self.results:
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
        )
        if not path:
            return

        with open(path, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(
                ["Group", "Frame Count", "Frame Indices", "Similarity"]
            )

            for key, result in self.results.items():
                frames = result["frames"]
                writer.writerow(
                    [
                        int(key) + 1,
                        len(frames),
                        " ".join(str(frame) for frame in frames),
                        f'{result["similarity"]:.2f}%',
                    ]
                )

        messagebox.showinfo(
            "Exported",
            f"CSV saved to:\n{path}",
        )

    def _export_json(self):
        if not self.results:
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
        )
        if not path:
            return

        data = {
            f"group_{int(key) + 1}": value
            for key, value in self.results.items()
        }

        with open(path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)

        messagebox.showinfo(
            "Exported",
            f"JSON saved to:\n{path}",
        )

    def _export_thumbnails(self, duplicates):
        folder = filedialog.askdirectory(
            title="Select Thumbnail Output Folder"
        )
        if not folder:
            return

        output_dir = Path(folder) / "loop_thumbnails"
        output_dir.mkdir(exist_ok=True)

        saved = 0
        for index, group in enumerate(duplicates):
            frame_data = group.get("frame_data")
            if frame_data is None:
                continue

            try:
                rgb = cv2.cvtColor(
                    frame_data,
                    cv2.COLOR_BGR2RGB,
                )
                pil = Image.fromarray(rgb)
                pil.thumbnail((320, 180), Image.LANCZOS)

                pil.save(
                    output_dir / (
                        f"group_{index + 1:04d}_"
                        f"frame{group['frames'][0]}.jpg"
                    ),
                    quality=90,
                )
                saved += 1

            except Exception as error:
                print(f"Thumbnail export error: {error}")

        messagebox.showinfo(
            "Thumbnails",
            f"Saved {saved} thumbnail(s) to:\n{output_dir}",
        )

    # ── Utilities ──────────────────────────────────────────────────────────────
    @staticmethod
    def _frames_to_tc(frame, fps):
        if not fps:
            return str(frame)

        total_seconds = int(frame / fps)
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        return (
            f"{hours:02d}:"
            f"{minutes:02d}:"
            f"{seconds:02d}"
        )


if __name__ == "__main__":
    root = ctk.CTk()
    app = LoopDetectorApp(root)
    root.mainloop()
