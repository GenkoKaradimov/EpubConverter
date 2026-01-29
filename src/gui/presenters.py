"""
Presenters: wire GUI actions to core (extract, build). Conversion presenter for conversion view.
All code and comments in English.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from gui.views.conversion_view import ConversionView

if TYPE_CHECKING:
    from app.application import Application
    from gui.main_window import MainWindow


class ConversionPresenter:
    """
    Conversion view presenter: Extract button -> PdfExtractor.extract -> set document -> show editor view.
    """

    def __init__(self, view: ConversionView, app: "Application", main_window: "MainWindow") -> None:
        self._view = view
        self._app = app
        self._main_window = main_window

    def on_extract(self) -> None:
        path = self._view.get_path()
        if not path:
            self._view.set_status("Please select a PDF file.")
            return
        path_obj = Path(path)
        if not path_obj.exists():
            self._view.set_status(f"File not found: {path}")
            return
        self._view.set_status("Extracting...")
        self._view.update_idletasks()
        try:
            from core.converters.pdf_extractor import PdfExtractor

            document = PdfExtractor().extract(path_obj)
            self._app.set_current_document(document)
            self._view.set_status("")
            self._main_window.show_editor_view(document)
        except FileNotFoundError as e:
            self._view.set_status(f"File not found: {e}")
        except RuntimeError as e:
            self._view.set_status(f"Extraction failed (install PyMuPDF?): {e}")
        except Exception as e:
            self._view.set_status(f"Extraction failed: {e}")
