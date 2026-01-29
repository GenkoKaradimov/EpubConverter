"""
Editor view: shows loaded document (stub for Phase 5; full editor in Phase 6).
All code and comments in English.
"""

from __future__ import annotations

from tkinter import Frame, Label

from core.models.document import Document


class EditorView(Frame):
    """
    Editor screen: document title and summary. Full editing in Phase 6.
    """

    def __init__(self, parent: Frame, document: Document) -> None:
        super().__init__(parent)
        self._document = document
        self._build_ui()

    def _build_ui(self) -> None:
        meta = self._document.metadata
        title = meta.title
        flat = self._document.flat_list()
        count = len(flat)
        Label(self, text="Editor", font=("", 12, "bold")).pack(anchor="w", pady=(0, 4))
        Label(self, text=f"Document: {title}", font=("", 10)).pack(anchor="w", pady=2)
        Label(self, text=f"Nodes: {count}", font=("", 9), fg="gray").pack(anchor="w", pady=2)
        Label(self, text="(Full editing in Phase 6)", font=("", 9), fg="gray").pack(anchor="w", pady=8)
