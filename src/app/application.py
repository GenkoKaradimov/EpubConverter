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
        self._last_export_path: Path | None = None

    @property
    def current_document(self) -> Document | None:
        """Current document after extraction or pipeline run; None until then."""
        return self._current_document

    @property
    def last_export_path(self) -> Path | None:
        """Path of the last successfully exported EPUB file; None until first export."""
        return self._last_export_path

    def set_current_document(self, document: Document | None) -> None:
        """Set the current document (e.g. after extraction)."""
        self._current_document = document

    def run_pipeline(self, pdf_path: Path | str, epub_path: Path | str | None = None) -> Path:
        """
        Run PDF -> extract -> build EPUB. Sets current_document. Returns path to created EPUB.
        Raises PipelineError on failure.
        """
        from core.pipeline import run_pipeline

        doc, out_path = run_pipeline(pdf_path, epub_path)
        self._current_document = doc
        return out_path

    def load_epub(self, epub_path: Path | str) -> Document:
        """
        Load an EPUB file into the current document. Sets current_document and returns it.
        Raises FileNotFoundError, RuntimeError on failure.
        """
        from core.converters.epub_extractor import EpubExtractor

        doc = EpubExtractor().extract(epub_path)
        self._current_document = doc
        return doc

    def build_epub(self, epub_path: Path | str) -> None:
        """Build current_document to EPUB file. Raises ValueError if empty/no document; RuntimeError/OSError on write failure."""
        if self._current_document is None:
            raise ValueError("No document loaded. Open a PDF or EPUB, or extract from PDF.")
        doc = self._current_document
        if not doc.flat_list():
            raise ValueError("Document has no content. Add chapters or paragraphs before export.")
        from core.converters.epub_builder import EpubBuilder

        EpubBuilder().build(doc, Path(epub_path))
        self._last_export_path = Path(epub_path)

    def run(self) -> None:
        """Start the GUI (main loop). Shows MainWindow with conversion view. Blocks until window is closed."""
        try:
            import tkinter as tk
        except ImportError:
            return
        self._root = tk.Tk()
        from gui.main_window import MainWindow

        self._main_window = MainWindow(self._root, self)
        self._main_window.show_conversion_view()
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
