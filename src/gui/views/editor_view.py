"""
Editor view: list of chapters/paragraphs (from Document), text field or image preview for selected node,
Add chapter / Remove / Move up-down; image Rotate and Crop. All code and comments in English.
"""

from __future__ import annotations

from pathlib import Path
from tkinter import Frame, Label, Listbox, Text, Button, Scrollbar, StringVar, Entry, Spinbox, BOTH, END, LEFT, RIGHT, TOP, BOTTOM, X, Y, W, N, S, E, Toplevel
from typing import TYPE_CHECKING

from core.models.document import ContentItem, ContentNode, Document, ImageNode

if TYPE_CHECKING:
    from gui.presenters import EditorPresenter


def _node_label(node: ContentItem, max_chars: int = 60) -> str:
    if isinstance(node, ImageNode):
        label = node.alt or node.image_id
        short = (label[:max_chars] + "...") if len(label) > max_chars else label
        return f"[Img] {short}"
    prefix = "Ch" if node.level >= 1 else "P"
    text = node.text.strip()
    short = (text[:max_chars] + "...") if len(text) > max_chars else text
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
        self._nodes: list[ContentItem] = []
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

        # Right: text or image panel (switch by selection)
        self._right_panel = Frame(content)
        self._right_panel.pack(side=LEFT, fill=BOTH, expand=True)

        # Text panel (ContentNode)
        text_frame = Frame(self._right_panel)
        self._text_frame = text_frame
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

        # Image panel (ImageNode): preview, alt, rotate, crop
        image_frame = Frame(self._right_panel)
        self._image_frame = image_frame
        Label(image_frame, text="Image:").pack(anchor=W)
        self._image_label = Label(image_frame, text="(no image)", width=40, height=12, relief="sunken", bg="gray90")
        self._image_label.pack(anchor=W, pady=(0, 4))
        self._photo_ref: object = None  # keep reference so PhotoImage is not gc'd
        Label(image_frame, text="Alt text:").pack(anchor=W)
        self._alt_entry = Entry(image_frame, width=50)
        self._alt_entry.pack(fill=X, pady=(0, 4))
        self._alt_entry.bind("<KeyRelease>", self._on_alt_modified)
        rot_frame = Frame(image_frame)
        rot_frame.pack(anchor=W, pady=4)
        Label(rot_frame, text="Rotate (degrees):").pack(side=LEFT, padx=(0, 4))
        self._rotate_var = StringVar(value="0")
        self._rotate_spin = Spinbox(rot_frame, from_=-360, to=360, width=6, textvariable=self._rotate_var, command=self._on_rotate_change)
        self._rotate_spin.pack(side=LEFT, padx=(0, 4))
        self._rotate_spin.bind("<Return>", lambda e: self._on_rotate_change())
        Button(image_frame, text="Crop...", command=self._on_crop_click).pack(anchor=W, pady=4)
        self._text_frame.pack(fill=BOTH, expand=True)

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
        self._showing_image = False
        self._current_image_node: ImageNode | None = None

    def _on_alt_modified(self, event: object) -> None:
        if self._showing_image:
            self._text_modified = True

    def _on_rotate_change(self) -> None:
        if self._presenter and self._current_image_node is not None:
            try:
                deg = float(self._rotate_var.get())
            except ValueError:
                return
            self._presenter.on_rotate(deg)

    def _on_crop_click(self) -> None:
        if self._presenter and self._current_image_node is not None:
            self._presenter.on_crop_dialog(self._open_crop_dialog)

    def _open_crop_dialog(self, current_rect: tuple[float, float, float, float] | None) -> None:
        """Open Toplevel with Left, Top, Right, Bottom (0-100%). On Apply call presenter.on_crop."""
        d = Toplevel(self)
        d.title("Crop (0-100%)")
        d.transient(self)
        left_var = StringVar(value=str(int((current_rect[0] if current_rect else 0) * 100)))
        top_var = StringVar(value=str(int((current_rect[1] if current_rect else 0) * 100)))
        right_var = StringVar(value=str(int((current_rect[2] if current_rect else 1) * 100)))
        bottom_var = StringVar(value=str(int((current_rect[3] if current_rect else 1) * 100)))
        f = Frame(d, padx=10, pady=10)
        f.pack()
        Label(f, text="Left %:").grid(row=0, column=0, sticky=W, pady=2)
        Entry(f, textvariable=left_var, width=6).grid(row=0, column=1, padx=4, pady=2)
        Label(f, text="Top %:").grid(row=1, column=0, sticky=W, pady=2)
        Entry(f, textvariable=top_var, width=6).grid(row=1, column=1, padx=4, pady=2)
        Label(f, text="Right %:").grid(row=2, column=0, sticky=W, pady=2)
        Entry(f, textvariable=right_var, width=6).grid(row=2, column=1, padx=4, pady=2)
        Label(f, text="Bottom %:").grid(row=3, column=0, sticky=W, pady=2)
        Entry(f, textvariable=bottom_var, width=6).grid(row=3, column=1, padx=4, pady=2)

        def apply_crop() -> None:
            try:
                left = float(left_var.get()) / 100.0
                top = float(top_var.get()) / 100.0
                right = float(right_var.get()) / 100.0
                bottom = float(bottom_var.get()) / 100.0
                if not (0 <= left < right <= 1 and 0 <= top < bottom <= 1):
                    return
                if self._presenter:
                    self._presenter.on_crop((left, top, right, bottom))
            except ValueError:
                pass
            d.destroy()

        Button(d, text="Apply", command=apply_crop).pack(pady=8)
        d.geometry("+%d+%d" % (self.winfo_rootx() + 50, self.winfo_rooty() + 50))

    def show_text_panel(self) -> None:
        self._showing_image = False
        self._current_image_node = None
        self._image_frame.pack_forget()
        self._text_frame.pack(fill=BOTH, expand=True)

    def show_image_panel(self, image_path: Path, node: ImageNode) -> None:
        self._showing_image = True
        self._current_image_node = node
        self._text_frame.pack_forget()
        self._image_frame.pack(fill=BOTH, expand=True)
        self._rotate_var.set(str(int(node.rotation_degrees)))
        self._alt_entry.delete(0, END)
        self._alt_entry.insert(0, node.alt or "")
        self._text_modified = False
        self._update_image_preview(image_path, node)

    def _update_image_preview(self, image_path: Path, node: ImageNode) -> None:
        try:
            from PIL import Image
            from PIL import ImageTk
            from services.image_service import apply_transform, load_image
        except ImportError:
            self._image_label.config(image="", text="(Pillow required for preview)")
            return
        try:
            img = load_image(image_path)
            img = apply_transform(img, node.rotation_degrees, node.crop_rect)
            w, h = img.size
            max_w, max_h = 400, 400
            if w > max_w or h > max_h:
                ratio = min(max_w / w, max_h / h)
                new_w, new_h = int(w * ratio), int(h * ratio)
                resample = getattr(Image, "Resampling", Image).LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS
                img = img.resize((new_w, new_h), resample)
            self._photo_ref = ImageTk.PhotoImage(img)
            self._image_label.config(image=self._photo_ref, text="")
        except Exception:
            self._image_label.config(image="", text="(failed to load image)")

    def set_image_preview_from_node(self, image_path: Path, node: ImageNode) -> None:
        """Refresh image preview after rotate/crop change."""
        self._update_image_preview(image_path, node)

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

    def set_nodes(self, nodes: list[ContentItem]) -> None:
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
        if self._showing_image:
            self._alt_entry.delete(0, END)
            self._alt_entry.insert(0, text or "")
        else:
            self._text.config(state="normal")
            self._text.delete("1.0", END)
            self._text.insert("1.0", text)
            self._text.edit_modified(False)

    def get_text(self) -> str:
        if self._showing_image:
            return self._alt_entry.get().strip()
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
