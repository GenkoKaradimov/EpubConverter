"""
Editor view: list of chapters/paragraphs (from Document), text field for selected node,
Add chapter / Remove / Move up-down; changes saved to Document in memory.
All code and comments in English.
"""

from __future__ import annotations

from tkinter import Frame, Label, Listbox, Text, Button, Scrollbar, StringVar, Entry, BOTH, END, LEFT, RIGHT, TOP, BOTTOM, X, Y, W, N, S, E
from typing import TYPE_CHECKING

from core.models.document import ContentNode, Document

if TYPE_CHECKING:
    from gui.presenters import EditorPresenter


def _node_label(node: ContentNode, max_chars: int = 60) -> str:
    prefix = "Ch" if node.level >= 1 else "P"
    short = node.text.strip()[:max_chars] + ("..." if len(node.text.strip()) > max_chars else "")
    return f"[{prefix}] {short}"


class EditorView(Frame):
    """
    Editor screen: list of nodes (chapters/paragraphs), text area for selected node,
    Add chapter, Remove, Move up/down. Optional search. Changes written to Document in memory.
    """

    def __init__(self, parent: Frame, document: Document) -> None:
        super().__init__(parent)
        self._document = document
        self._presenter: EditorPresenter | None = None
        self._nodes: list[ContentNode] = []
        self._list_var: StringVar | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        # Top: document title
        Label(self, text="Editor", font=("", 12, "bold")).pack(anchor=W, pady=(0, 4))
        meta = self._document.metadata
        Label(self, text=f"Document: {meta.title}", font=("", 10)).pack(anchor=W, pady=(0, 8))

        # Two columns: list left, text right
        content = Frame(self)
        content.pack(fill=BOTH, expand=True, pady=(0, 4))

        # Left: list of nodes
        list_frame = Frame(content)
        list_frame.pack(side=LEFT, fill=BOTH, expand=False, padx=(0, 8))
        Label(list_frame, text="Chapters / paragraphs:").pack(anchor=W)
        list_scroll = Scrollbar(list_frame)
        list_scroll.pack(side=RIGHT, fill=Y)
        self._listbox = Listbox(list_frame, height=15, width=45, yscrollcommand=list_scroll.set, selectmode="single")
        self._listbox.pack(side=LEFT, fill=BOTH, expand=True)
        list_scroll.config(command=self._listbox.yview)
        self._listbox.bind("<<ListboxSelect>>", self._on_list_select)

        # Right: text area for selected node
        text_frame = Frame(content)
        text_frame.pack(side=LEFT, fill=BOTH, expand=True)
        Label(text_frame, text="Content:").pack(anchor=W)
        text_scroll_y = Scrollbar(text_frame)
        text_scroll_y.pack(side=RIGHT, fill=Y)
        text_scroll_x = Scrollbar(text_frame, orient="horizontal")
        text_scroll_x.pack(side=BOTTOM, fill=X)
        self._text = Text(text_frame, wrap="word", width=40, height=15, undo=True,
                         yscrollcommand=text_scroll_y.set, xscrollcommand=text_scroll_x.set)
        self._text.pack(side=LEFT, fill=BOTH, expand=True)
        text_scroll_y.config(command=self._text.yview)
        text_scroll_x.config(command=self._text.xview)
        self._text.bind("<<Modified>>", self._on_text_modified)

        # Buttons
        btn_frame = Frame(self)
        btn_frame.pack(fill=X, pady=8)
        self._btn_add = Button(btn_frame, text="Add chapter", command=self._on_add_chapter)
        self._btn_add.pack(side=LEFT, padx=(0, 4))
        self._btn_remove = Button(btn_frame, text="Remove", command=self._on_remove)
        self._btn_remove.pack(side=LEFT, padx=(0, 4))
        self._btn_up = Button(btn_frame, text="Move up", command=self._on_move_up)
        self._btn_up.pack(side=LEFT, padx=(0, 4))
        self._btn_down = Button(btn_frame, text="Move down", command=self._on_move_down)
        self._btn_down.pack(side=LEFT, padx=(0, 4))
        self._btn_apply = Button(btn_frame, text="Apply", command=self._on_apply)
        self._btn_apply.pack(side=LEFT, padx=(0, 4))
        self._btn_export = Button(btn_frame, text="Export to EPUB", command=self._on_export_epub)
        self._btn_export.pack(side=LEFT, padx=(0, 4))

        # Search (optional)
        search_frame = Frame(self)
        search_frame.pack(fill=X, pady=(0, 4))
        Label(search_frame, text="Find:").pack(side=LEFT, padx=(0, 4))
        self._search_var = StringVar()
        self._search_entry = Entry(search_frame, textvariable=self._search_var, width=30)
        self._search_entry.pack(side=LEFT, padx=(0, 4))
        Button(search_frame, text="Find next", command=self._on_find_next).pack(side=LEFT)

        self.set_buttons_state(False)
        self._text_modified = False

    def _on_list_select(self, event: object) -> None:
        sel = self._listbox.curselection()
        if sel and self._presenter:
            self._presenter.on_selection(sel[0])

    def _on_text_modified(self, event: object) -> None:
        if self._text.cget("state") == "normal":
            self._text_modified = True

    def _on_add_chapter(self) -> None:
        if self._presenter:
            self._presenter.on_add_chapter()

    def _on_remove(self) -> None:
        if self._presenter:
            self._presenter.on_remove()

    def _on_move_up(self) -> None:
        if self._presenter:
            self._presenter.on_move_up()

    def _on_move_down(self) -> None:
        if self._presenter:
            self._presenter.on_move_down()

    def _on_apply(self) -> None:
        if self._presenter:
            self._presenter.on_apply()

    def _on_export_epub(self) -> None:
        if self._presenter:
            self._presenter.on_export_epub()

    def _on_find_next(self) -> None:
        if self._presenter:
            self._presenter.on_find_next()

    def set_presenter(self, presenter: "EditorPresenter") -> None:
        self._presenter = presenter

    def set_nodes(self, nodes: list[ContentNode]) -> None:
        self._nodes = nodes
        self._listbox.delete(0, END)
        for node in nodes:
            self._listbox.insert(END, _node_label(node))

    def get_selected_index(self) -> int | None:
        sel = self._listbox.curselection()
        return sel[0] if sel else None

    def set_selection(self, index: int) -> None:
        self._listbox.selection_clear(0, END)
        if 0 <= index < self._listbox.size():
            self._listbox.selection_set(index)
            self._listbox.see(index)

    def set_text(self, text: str) -> None:
        self._text_modified = False
        self._text.config(state="normal")
        self._text.delete("1.0", END)
        self._text.insert("1.0", text)
        self._text.edit_modified(False)

    def get_text(self) -> str:
        return self._text.get("1.0", END).rstrip("\n")

    def set_buttons_state(self, has_selection: bool) -> None:
        self._btn_remove.config(state="normal" if has_selection else "disabled")
        self._btn_up.config(state="normal" if has_selection else "disabled")
        self._btn_down.config(state="normal" if has_selection else "disabled")
        self._btn_apply.config(state="normal" if has_selection else "disabled")

    def focus_text(self) -> None:
        self._text.focus_set()

    def find_in_text(self, search: str) -> bool:
        """Find next occurrence of search in text; select it. Returns True if found."""
        if not search:
            return False
        start = self._text.search(search, "1.0", END, nocase=True)
        if not start:
            return False
        end = f"{start}+{len(search)}c"
        self._text.tag_remove("sel", "1.0", END)
        self._text.tag_add("sel", start, end)
        self._text.see(start)
        self._text.mark_set("insert", end)
        return True

    def get_search_query(self) -> str:
        return self._search_var.get().strip()

    def has_unsaved_text(self) -> bool:
        return self._text_modified

    def clear_text_modified(self) -> None:
        self._text_modified = False
        self._text.edit_modified(False)
