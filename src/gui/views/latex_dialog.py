"""
LaTeX dialog: actions (Alphabet), description, Start/Close. On Start: block dialog, progress bar, worker thread; on done: unblock and refresh editor.
"""

from __future__ import annotations

import threading
from tkinter import Tk, Toplevel, Frame, Label, Button, Radiobutton, StringVar, W, E
from tkinter import ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.application import Application
    from gui.main_window import MainWindow

ALPHABET_DESCRIPTION = (
    "Replaces single LaTeX symbols like $\\beta$ with Unicode characters (e.g. β) "
    "in all paragraphs and headings. Greek alphabet and common math symbols. Does not modify full formulas."
)


class LatexDialog:
    """Toplevel dialog: LaTeX actions (Alphabet), description, progress bar, Start and Close buttons."""

    def __init__(self, root: Tk, app: "Application", main_window: "MainWindow") -> None:
        self._root = root
        self._app = app
        self._main_window = main_window
        self._win = Toplevel(root)
        self._win.title("LaTeX")
        self._win.transient(root)
        self._action_var = StringVar(value="alphabet")
        self._progress: ttk.Progressbar | None = None
        self._progress_label: Label | None = None
        self._progress_frame: Frame | None = None
        self._btn_close: Button | None = None
        self._btn_start: Button | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        f = Frame(self._win, padx=12, pady=12)
        f.pack(fill="both", expand=True)

        Label(f, text="Action:", font=("", 10, "bold")).grid(row=0, column=0, sticky=W, pady=(0, 4))
        rb = Radiobutton(f, text="Alphabet", variable=self._action_var, value="alphabet")
        rb.grid(row=1, column=0, columnspan=2, sticky=W, pady=(0, 8))

        Label(f, text="Description:", font=("", 10, "bold")).grid(row=2, column=0, sticky=W, pady=(0, 4))
        desc = Label(f, text=ALPHABET_DESCRIPTION, wraplength=400, justify="left")
        desc.grid(row=3, column=0, columnspan=2, sticky=W, pady=(0, 12))

        self._progress_frame = Frame(f)
        self._progress_frame.grid(row=4, column=0, columnspan=2, sticky=W + E, pady=(0, 8))
        self._progress = ttk.Progressbar(self._progress_frame, maximum=100, value=0, mode="determinate")
        self._progress.pack(fill="x", expand=True)
        self._progress_label = Label(self._progress_frame, text="")
        self._progress_label.pack(anchor=W)
        self._progress_frame.grid_remove()

        btn_frame = Frame(f)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=(8, 0))
        self._btn_start = Button(btn_frame, text="Start", command=self._on_start)
        self._btn_start.pack(side="left", padx=(0, 8))
        self._btn_close = Button(btn_frame, text="Close", command=self._win.destroy)
        self._btn_close.pack(side="left")

    def _on_start(self) -> None:
        if self._action_var.get() != "alphabet":
            return
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
        total = len(doc.flat_list())
        if total == 0:
            self._progress["value"] = 100
            self._progress_label.config(text="100 %")
            self._done()
            return

        def progress_cb(current: int, tot: int) -> None:
            pct = int(100 * current / tot) if tot else 0
            self._root.after(0, lambda: self._update_progress(pct))

        def run() -> None:
            from services.latex_replace import replace_latex_alphabet
            replace_latex_alphabet(doc, progress_callback=progress_cb)
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
        self._main_window.refresh_editor_view()
