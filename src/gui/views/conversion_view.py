"""
Conversion view: PDF file picker, path display, Extract button, status message.
On success the presenter switches to editor view with the loaded document.
All code and comments in English.
"""

from __future__ import annotations

from tkinter import Frame, Label, Button, Entry, StringVar, filedialog
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gui.presenters import ConversionPresenter


class ConversionView(Frame):
    """
    First screen: choose PDF, show path, Extract button, status/progress message.
    """

    def __init__(self, parent: Frame, initial_path: str | None = None) -> None:
        super().__init__(parent)
        self._path_var = StringVar(value=initial_path or "")
        self._status_var = StringVar(value="")
        self._presenter: ConversionPresenter | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        Label(self, text="PDF file:", font=("", 10)).pack(anchor="w", pady=(0, 2))
        path_frame = Frame(self)
        path_frame.pack(fill="x", pady=(0, 8))
        self._entry = Entry(path_frame, textvariable=self._path_var, state="readonly", width=60)
        self._entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        Button(path_frame, text="Browse...", command=self._on_browse).pack(side="right")

        Button(self, text="Extract", command=self._on_extract, font=("", 10)).pack(anchor="w", pady=8)

        Label(self, text="Status:", font=("", 9)).pack(anchor="w", pady=(8, 2))
        self._status_label = Label(self, textvariable=self._status_var, font=("", 9), fg="gray", anchor="w", justify="left")
        self._status_label.pack(fill="x", pady=(0, 4))

    def _on_browse(self) -> None:
        path = filedialog.askopenfilename(
            title="Select PDF",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if path:
            self._path_var.set(path)

    def _on_extract(self) -> None:
        if self._presenter:
            self._presenter.on_extract()

    def set_presenter(self, presenter: ConversionPresenter) -> None:
        self._presenter = presenter

    def get_path(self) -> str:
        return self._path_var.get().strip()

    def set_path(self, path: str) -> None:
        self._path_var.set(path)

    def set_status(self, message: str) -> None:
        self._status_var.set(message)
