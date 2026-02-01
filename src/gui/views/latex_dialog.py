"""
LaTeX dialog: checkboxes (Alphabet, Separate formulas, Merge), descriptions, Start/Close.
On Start: block dialog, progress bar, worker thread; run in order Alphabet -> Merge -> Separate; on done: unblock and refresh editor.
"""

from __future__ import annotations

import threading
from tkinter import Tk, Toplevel, Frame, Label, Button, Checkbutton, BooleanVar, W, E
from tkinter import ttk, messagebox
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.application import Application
    from gui.main_window import MainWindow

ALPHABET_DESCRIPTION = (
    "Replaces single LaTeX symbols like $\\beta$ with Unicode characters (e.g. β) "
    "in all paragraphs and headings. Greek alphabet and common math symbols. Does not modify full formulas."
)
SEPARATE_DESCRIPTION = (
    "Splits paragraphs that contain LaTeX formulas into several paragraphs so that each formula is alone in one paragraph. Order is preserved."
)
MERGE_DESCRIPTION = (
    "Merges two, three, four... consecutive paragraphs into one. Paragraphs that are entirely a formula are left separate."
)
TO_IMAGES_DESCRIPTION = (
    "Replaces each paragraph that is entirely LaTeX (e.g. $...$) with a PNG image of the formula. Requires matplotlib."
)


class LatexDialog:
    """Toplevel dialog: LaTeX checkboxes (Alphabet, Separate formulas, Merge), descriptions, progress bar, Start and Close buttons."""

    def __init__(self, root: Tk, app: "Application", main_window: "MainWindow") -> None:
        self._root = root
        self._app = app
        self._main_window = main_window
        self._win = Toplevel(root)
        self._win.title("LaTeX")
        self._win.transient(root)
        self._alphabet_var = BooleanVar(value=True)
        self._separate_var = BooleanVar(value=False)
        self._merge_var = BooleanVar(value=False)
        self._to_images_var = BooleanVar(value=False)
        self._progress: ttk.Progressbar | None = None
        self._progress_label: Label | None = None
        self._progress_frame: Frame | None = None
        self._btn_close: Button | None = None
        self._btn_start: Button | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        f = Frame(self._win, padx=12, pady=12)
        f.pack(fill="both", expand=True)

        row = 0
        Label(f, text="Actions:", font=("", 10, "bold")).grid(row=row, column=0, sticky=W, pady=(0, 4))
        row += 1
        cb1 = Checkbutton(f, text="Alphabet", variable=self._alphabet_var)
        cb1.grid(row=row, column=0, columnspan=2, sticky=W, pady=(0, 2))
        row += 1
        Label(f, text=ALPHABET_DESCRIPTION, wraplength=400, justify="left", font=("", 9)).grid(row=row, column=0, columnspan=2, sticky=W, padx=(20, 0), pady=(0, 8))
        row += 1
        cb2 = Checkbutton(f, text="Separate formulas", variable=self._separate_var)
        cb2.grid(row=row, column=0, columnspan=2, sticky=W, pady=(0, 2))
        row += 1
        Label(f, text=SEPARATE_DESCRIPTION, wraplength=400, justify="left", font=("", 9)).grid(row=row, column=0, columnspan=2, sticky=W, padx=(20, 0), pady=(0, 8))
        row += 1
        cb3 = Checkbutton(f, text="Merge", variable=self._merge_var)
        cb3.grid(row=row, column=0, columnspan=2, sticky=W, pady=(0, 2))
        row += 1
        Label(f, text=MERGE_DESCRIPTION, wraplength=400, justify="left", font=("", 9)).grid(row=row, column=0, columnspan=2, sticky=W, padx=(20, 0), pady=(0, 8))
        row += 1
        cb4 = Checkbutton(f, text="Convert formula paragraphs to images", variable=self._to_images_var)
        cb4.grid(row=row, column=0, columnspan=2, sticky=W, pady=(0, 2))
        row += 1
        Label(f, text=TO_IMAGES_DESCRIPTION, wraplength=400, justify="left", font=("", 9)).grid(row=row, column=0, columnspan=2, sticky=W, padx=(20, 0), pady=(0, 12))
        row += 1

        self._progress_frame = Frame(f)
        self._progress_frame.grid(row=row, column=0, columnspan=2, sticky=W + E, pady=(0, 8))
        self._progress = ttk.Progressbar(self._progress_frame, maximum=100, value=0, mode="determinate")
        self._progress.pack(fill="x", expand=True)
        self._progress_label = Label(self._progress_frame, text="")
        self._progress_label.pack(anchor=W)
        self._progress_frame.grid_remove()
        row += 1

        btn_frame = Frame(f)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=(8, 0))
        self._btn_start = Button(btn_frame, text="Start", command=self._on_start)
        self._btn_start.pack(side="left", padx=(0, 8))
        self._btn_close = Button(btn_frame, text="Close", command=self._win.destroy)
        self._btn_close.pack(side="left")

    def _on_start(self) -> None:
        do_alphabet = self._alphabet_var.get()
        do_merge = self._merge_var.get()
        do_separate = self._separate_var.get()
        do_to_images = self._to_images_var.get()
        if not (do_alphabet or do_merge or do_separate or do_to_images):
            messagebox.showinfo("LaTeX", "Select at least one action.")
            return
        if do_to_images:
            from services.latex_to_image import MATHTEXT_AVAILABLE
            if not MATHTEXT_AVAILABLE:
                messagebox.showinfo(
                    "LaTeX",
                    "Convert formula paragraphs to images requires matplotlib. Install with: pip install matplotlib",
                    parent=self._win,
                )
                do_to_images = False
        doc = self._app.current_document
        if not doc:
            return
        self._btn_start.config(state="disabled")
        self._btn_close.config(state="disabled")
        self._win.protocol("WM_DELETE_WINDOW", lambda: None)
        if self._progress_frame:
            self._progress_frame.grid()
        self._progress["value"] = 0
        self._progress_label.config(text="0 %")
        self._did_to_images = do_to_images
        self._to_images_result: list[tuple[int, int, list[str]] | None] = [None]

        n_phases = sum([do_alphabet, do_merge, do_separate, do_to_images])
        phase_size = 100 // n_phases if n_phases else 100
        current_phase = [0]

        def progress_cb(current: int, tot: int) -> None:
            pct = int(100 * current / tot) if tot else 0
            base = current_phase[0] * phase_size
            total_pct = min(100, base + (pct * phase_size // 100) if tot else base + phase_size)
            self._root.after(0, lambda: self._update_progress(total_pct))

        def run() -> None:
            try:
                if do_alphabet:
                    from services.latex_replace import replace_latex_alphabet
                    replace_latex_alphabet(doc, progress_callback=progress_cb)
                current_phase[0] += 1
                if do_merge:
                    from services.latex_merge import merge_paragraphs
                    def merge_cb(c: int, t: int) -> None:
                        progress_cb(c, t)
                    merge_paragraphs(doc, progress_callback=merge_cb)
                current_phase[0] += 1
                if do_separate:
                    from services.latex_merge import separate_formulas
                    def sep_cb(c: int, t: int) -> None:
                        progress_cb(c, t)
                    separate_formulas(doc, progress_callback=sep_cb)
                current_phase[0] += 1
                if do_to_images:
                    from services.latex_to_image import convert_formula_paragraphs_to_images
                    def to_img_cb(c: int, t: int) -> None:
                        progress_cb(c, t)
                    self._to_images_result[0] = convert_formula_paragraphs_to_images(doc, progress_callback=to_img_cb)
            finally:
                self._root.after(0, self._done)

        threading.Thread(target=run, daemon=True).start()

    def _update_progress(self, pct: int) -> None:
        if self._progress is not None:
            self._progress["value"] = pct
        if self._progress_label is not None:
            self._progress_label.config(text=f"{pct} %")

    def _done(self) -> None:
        self._progress["value"] = 100
        self._progress_label.config(text="100 %")
        self._btn_start.config(state="normal")
        self._btn_close.config(state="normal")
        self._win.protocol("WM_DELETE_WINDOW", self._win.destroy)
        if getattr(self, "_did_to_images", False) and self._to_images_result[0] is not None:
            from gui.presenters import show_paragraph_to_image_result
            converted, failed, errors = self._to_images_result[0]
            show_paragraph_to_image_result(converted, failed, errors, self._win)
        self._main_window.refresh_editor_view()
