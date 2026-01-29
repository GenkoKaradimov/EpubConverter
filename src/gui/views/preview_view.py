"""
Preview view: open last exported EPUB in default reader or show message if none.
All code and comments in English.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from tkinter import Frame, Label, Button


def open_path_in_default_app(path: Path) -> bool:
    """Open path with the system default application. Returns True if attempted."""
    path = Path(path)
    if not path.exists():
        return False
    try:
        if sys.platform == "win32":
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
        return True
    except Exception:
        return False


class PreviewView(Frame):
    """
    Simple preview: show last exported path and button to open in default reader.
    """

    def __init__(self, parent: Frame, epub_path: Path | None) -> None:
        super().__init__(parent)
        self._path = epub_path
        self._build_ui()

    def _build_ui(self) -> None:
        Label(self, text="Preview", font=("", 12, "bold")).pack(anchor="w", pady=(0, 8))
        if self._path and self._path.exists():
            Label(self, text=f"Last exported: {self._path}", font=("", 10)).pack(anchor="w", pady=2)
            Button(self, text="Open in default reader", command=self._on_open).pack(anchor="w", pady=8)
        else:
            Label(self, text="No EPUB exported yet. Export from File → Export EPUB first.", font=("", 10)).pack(anchor="w", pady=2)

    def _on_open(self) -> None:
        if self._path:
            open_path_in_default_app(self._path)
