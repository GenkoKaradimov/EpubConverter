"""
Main Application class: config, GUI lifecycle, (later) current document and pipeline.
All code and comments in English.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.models.document import Document

try:
    from app import config
except ImportError:
    config = None  # type: ignore[assignment]


class Application:
    """
    Main application: init (load config), start/stop GUI, (later) access to current document and pipeline.
    """

    def __init__(self) -> None:
        if config:
            try:
                config.ensure_dirs()
            except OSError:
                pass  # e.g. sandbox or read-only home
        self._root = None
        self._current_document: Document | None = None

    @property
    def current_document(self) -> Document | None:
        """Current document after extraction or pipeline run; None until then."""
        return self._current_document

    def run_pipeline(self, pdf_path: Path | str, epub_path: Path | str | None = None) -> Path:
        """
        Run PDF -> extract -> build EPUB. Sets current_document. Returns path to created EPUB.
        Raises PipelineError on failure.
        """
        from core.pipeline import run_pipeline

        doc, out_path = run_pipeline(pdf_path, epub_path)
        self._current_document = doc
        return out_path

    def run(self) -> None:
        """Start the GUI (main loop). Blocks until window is closed."""
        try:
            import tkinter as tk
        except ImportError:
            return
        self._root = tk.Tk()
        self._root.title("EpubConverter")
        self._root.geometry("400x200")
        label = tk.Label(self._root, text="EpubConverter\n(GUI in Phase 5)", font=("", 12))
        label.pack(expand=True)
        self._root.protocol("WM_DELETE_WINDOW", self.stop)
        self._root.mainloop()

    def stop(self) -> None:
        """Stop the GUI (close main window)."""
        if self._root:
            try:
                self._root.quit()
                self._root.destroy()
            except Exception:
                pass
            self._root = None
