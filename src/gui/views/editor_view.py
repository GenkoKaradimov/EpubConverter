"""
Editor view: list of chapters/paragraphs (from Document), text field or image preview for selected node,
Add chapter / Remove / Move up-down; image Rotate and Crop. All code and comments in English.
"""

from __future__ import annotations

from pathlib import Path
from tkinter import Frame, Label, Listbox, Text, Button, Scrollbar, StringVar, Entry, Spinbox, Scale, Canvas, Menu, PanedWindow, BOTH, END, LEFT, RIGHT, TOP, BOTTOM, X, Y, W, N, S, E, Toplevel, HORIZONTAL
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

        # Two columns: list left, content right — resizable splitter
        content = Frame(self)
        content.pack(fill=BOTH, expand=True, pady=(0, 4))
        paned = PanedWindow(content, orient=HORIZONTAL, sashrelief="raised", sashwidth=8, bg="gray75")
        paned.pack(fill=BOTH, expand=True)

        # Left: list of nodes
        list_frame = Frame(paned)
        Label(list_frame, text="Chapters / paragraphs:").pack(anchor=W)
        list_scroll = Scrollbar(list_frame)
        list_scroll.pack(side=RIGHT, fill=Y)
        self._listbox = Listbox(list_frame, height=15, width=35, yscrollcommand=list_scroll.set, selectmode="single")
        self._listbox.pack(side=LEFT, fill=BOTH, expand=True)
        list_scroll.config(command=self._listbox.yview)
        self._listbox.bind("<<ListboxSelect>>", self._on_list_select)
        self._listbox.bind("<Button-3>", self._on_list_right_click)
        paned.add(list_frame, minsize=120, width=280)

        # Right: text or image panel (switch by selection)
        self._right_panel = Frame(paned)
        paned.add(self._right_panel, minsize=200)

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

        # Image panel (ImageNode): toolbar on top, image fills rest
        image_frame = Frame(self._right_panel)
        self._image_frame = image_frame
        # Toolbar: Rotate, Crop, Alt in one row
        toolbar = Frame(image_frame)
        toolbar.pack(side=TOP, fill=X, pady=(0, 4))
        Label(toolbar, text="Rotate:").pack(side=LEFT, padx=(0, 2))
        self._rotate_var = StringVar(value="0")
        self._rotate_spin = Spinbox(toolbar, from_=-360, to=360, width=6, textvariable=self._rotate_var, command=self._on_rotate_change)
        self._rotate_spin.pack(side=LEFT, padx=(0, 8))
        self._rotate_spin.bind("<Return>", lambda e: self._on_rotate_change())
        Button(toolbar, text="Crop...", command=self._on_crop_click).pack(side=LEFT, padx=(0, 8))
        Label(toolbar, text="Alt:").pack(side=LEFT, padx=(0, 2))
        self._alt_entry = Entry(toolbar, width=30)
        self._alt_entry.pack(side=LEFT, fill=X, expand=True, padx=(0, 4))
        self._alt_entry.bind("<KeyRelease>", self._on_alt_modified)
        # Image area: fills all space below toolbar
        self._image_label = Label(image_frame, text="(no image)", relief="sunken", bg="gray90")
        self._image_label.pack(side=TOP, fill=BOTH, expand=True)
        # Bind on frame only so resizing the image doesn't trigger a new Configure loop
        image_frame.bind("<Configure>", self._on_image_panel_configure)
        self._photo_ref: object = None  # keep reference so PhotoImage is not gc'd
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
        self._current_image_path: Path | None = None
        self._resize_after_id: str | None = None

    def _on_alt_modified(self, event: object) -> None:
        if self._showing_image:
            self._text_modified = True

    def _on_image_panel_configure(self, event: object) -> None:
        """Resize preview when image panel (frame) is resized by user (debounced)."""
        if not (self._showing_image and self._current_image_path and self._current_image_node):
            return
        if self._resize_after_id:
            try:
                self.after_cancel(self._resize_after_id)
            except Exception:
                pass
        self._resize_after_id = self.after(200, self._do_resize_preview)

    def _do_resize_preview(self) -> None:
        self._resize_after_id = None
        if self._current_image_path and self._current_image_node:
            self._update_image_preview(self._current_image_path, self._current_image_node)

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
        """Open graphical crop dialog: image preview with overlay and sliders. Clear region = keep, dimmed = crop out."""
        if not self._current_image_path or not self._current_image_node:
            return
        try:
            from PIL import Image
            from PIL import ImageTk
            from services.image_service import apply_transform, load_image
        except ImportError:
            return
        try:
            img_pil = load_image(self._current_image_path)
            img_pil = apply_transform(img_pil, self._current_image_node.rotation_degrees, None)
        except Exception:
            return
        iw, ih = img_pil.size
        if iw <= 0 or ih <= 0:
            return

        d = Toplevel(self)
        d.title("Crop – drag sliders or adjust; clear area is kept, dimmed area is cropped out")
        d.transient(self)
        d.grab_set()

        # Normalized crop rect (0-1): left, top, right, bottom
        rect = list(current_rect) if current_rect else [0.0, 0.0, 1.0, 1.0]
        rect[0] = max(0, min(rect[0], rect[2] - 0.05))
        rect[1] = max(0, min(rect[1], rect[3] - 0.05))
        rect[2] = min(1, max(rect[2], rect[0] + 0.05))
        rect[3] = min(1, max(rect[3], rect[1] + 0.05))

        canvas_w, canvas_h = 640, 480
        scale = min(canvas_w / iw, canvas_h / ih)
        if scale <= 0:
            scale = 1.0
        disp_w, disp_h = int(iw * scale), int(ih * scale)
        ox, oy = (canvas_w - disp_w) // 2, (canvas_h - disp_h) // 2

        # Resize image for display
        resample = getattr(Image, "Resampling", Image).LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS
        img_disp = img_pil.resize((disp_w, disp_h), resample)
        photo = ImageTk.PhotoImage(img_disp)

        canvas = Canvas(d, width=canvas_w, height=canvas_h, bg="gray40")
        canvas.pack(padx=8, pady=8)
        canvas.create_image(ox, oy, anchor="nw", image=photo)
        d._photo_keep = photo

        overlay_ids: list[int] = []

        def rect_to_canvas() -> tuple[float, float, float, float]:
            return (
                ox + rect[0] * disp_w,
                oy + rect[1] * disp_h,
                ox + rect[2] * disp_w,
                oy + rect[3] * disp_h,
            )

        def redraw_overlay() -> None:
            for oid in overlay_ids:
                canvas.delete(oid)
            overlay_ids.clear()
            x1, y1, x2, y2 = rect_to_canvas()
            # Dimmed strips (cropped-out areas) with stipple
            full = (ox, oy, ox + disp_w, oy + disp_h)
            strips = [
                (full[0], full[1], x1, full[3]),
                (x1, full[1], x2, y1),
                (x2, full[1], full[2], full[3]),
                (x1, y2, x2, full[3]),
            ]
            for (a, b, c, d) in strips:
                if c > a and d > b:
                    r = canvas.create_rectangle(a, b, c, d, fill="black", stipple="gray50", outline="")
                    overlay_ids.append(r)
            # Crop rectangle outline (kept area)
            overlay_ids.append(canvas.create_rectangle(x1, y1, x2, y2, outline="lime", width=2, dash=(4, 4)))

        def on_slider(_: object) -> None:
            left = left_scale.get() / 100.0
            top = top_scale.get() / 100.0
            right = right_scale.get() / 100.0
            bottom = bottom_scale.get() / 100.0
            if left >= right:
                right = min(1, left + 0.05)
            if top >= bottom:
                bottom = min(1, top + 0.05)
            rect[0], rect[1], rect[2], rect[3] = left, top, right, bottom
            redraw_overlay()

        sliders_frame = Frame(d)
        sliders_frame.pack(fill=X, padx=8, pady=4)
        Label(sliders_frame, text="Left %").grid(row=0, column=0, sticky=W, padx=(0, 4), pady=2)
        left_scale = Scale(sliders_frame, from_=0, to=100, orient=HORIZONTAL, length=180, command=on_slider)
        left_scale.set(rect[0] * 100)
        left_scale.grid(row=0, column=1, padx=(0, 16), pady=2)
        Label(sliders_frame, text="Right %").grid(row=0, column=2, sticky=W, padx=(0, 4), pady=2)
        right_scale = Scale(sliders_frame, from_=0, to=100, orient=HORIZONTAL, length=180, command=on_slider)
        right_scale.set(rect[2] * 100)
        right_scale.grid(row=0, column=3, padx=(0, 8), pady=2)
        Label(sliders_frame, text="Top %").grid(row=1, column=0, sticky=W, padx=(0, 4), pady=2)
        top_scale = Scale(sliders_frame, from_=0, to=100, orient=HORIZONTAL, length=180, command=on_slider)
        top_scale.set(rect[1] * 100)
        top_scale.grid(row=1, column=1, padx=(0, 16), pady=2)
        Label(sliders_frame, text="Bottom %").grid(row=1, column=2, sticky=W, padx=(0, 4), pady=2)
        bottom_scale = Scale(sliders_frame, from_=0, to=100, orient=HORIZONTAL, length=180, command=on_slider)
        bottom_scale.set(rect[3] * 100)
        bottom_scale.grid(row=1, column=3, padx=(0, 8), pady=2)

        redraw_overlay()

        def apply_crop() -> None:
            left = max(0, min(1, rect[0]))
            top = max(0, min(1, rect[1]))
            right = max(left + 0.01, min(1, rect[2]))
            bottom = max(top + 0.01, min(1, rect[3]))
            if self._presenter:
                self._presenter.on_crop((left, top, right, bottom))
            d.grab_release()
            d.destroy()

        btn_frame = Frame(d)
        btn_frame.pack(pady=8)
        Button(btn_frame, text="Apply", command=apply_crop).pack(side=LEFT, padx=4)
        Button(btn_frame, text="Cancel", command=lambda: (d.grab_release(), d.destroy())).pack(side=LEFT, padx=4)
        d.geometry("+%d+%d" % (self.winfo_rootx() + 50, self.winfo_rooty() + 50))

    def show_text_panel(self) -> None:
        self._showing_image = False
        self._current_image_node = None
        self._current_image_path = None
        self._image_frame.pack_forget()
        self._text_frame.pack(fill=BOTH, expand=True)

    def show_image_panel(self, image_path: Path, node: ImageNode) -> None:
        self._showing_image = True
        self._current_image_node = node
        self._current_image_path = image_path
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
            # Use parent frame size so we don't make the label grow (which would trigger Configure again)
            self._image_frame.update_idletasks()
            max_w = self._image_frame.winfo_width()
            max_h = self._image_frame.winfo_height()
            # Subtract toolbar height approx; ensure we never exceed a cap to avoid layout growth
            max_h = max(1, max_h - 40)
            max_w = min(max(1, max_w), 1400)
            max_h = min(max_h, 900)
            if max_w <= 1:
                max_w = 500
            if max_h <= 1:
                max_h = 400
            if w > max_w or h > max_h:
                ratio = min(max_w / w, max_h / h)
                new_w, new_h = max(1, int(w * ratio)), max(1, int(h * ratio))
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

    def _on_list_right_click(self, event: object) -> None:
        """Show context menu for the item under the cursor; select it first."""
        index = self._listbox.nearest(event.y)
        if index < 0 or index >= self._listbox.size():
            return
        self._listbox.selection_clear(0, END)
        self._listbox.selection_set(index)
        self._listbox.see(index)
        if self._presenter:
            self._presenter.on_selection(index)
        menu = Menu(self, tearoff=0)
        menu.add_command(label="Delete", command=self._on_context_delete)
        menu.add_command(label="Move up", command=self._on_context_move_up)
        menu.add_command(label="Move down", command=self._on_context_move_down)
        menu.add_command(label="Duplicate", command=self._on_context_duplicate)
        menu.add_separator()
        add_below_menu = Menu(menu, tearoff=0)
        add_below_menu.add_command(label="Title (chapter)", command=self._on_context_add_below_title)
        add_below_menu.add_command(label="Paragraph", command=self._on_context_add_below_paragraph)
        add_below_menu.add_command(label="Image...", command=self._on_context_add_below_image)
        add_below_menu.add_command(label="Image from clipboard", command=self._on_context_add_below_image_from_clipboard)
        menu.add_cascade(label="Add below", menu=add_below_menu)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _on_context_delete(self) -> None:
        if self._presenter:
            self._presenter.on_remove()

    def _on_context_move_up(self) -> None:
        if self._presenter:
            self._presenter.on_move_up()

    def _on_context_move_down(self) -> None:
        if self._presenter:
            self._presenter.on_move_down()

    def _on_context_duplicate(self) -> None:
        if self._presenter:
            self._presenter.on_duplicate()

    def _on_context_add_below_title(self) -> None:
        if self._presenter:
            self._presenter.on_add_below_title()

    def _on_context_add_below_paragraph(self) -> None:
        if self._presenter:
            self._presenter.on_add_below_paragraph()

    def _on_context_add_below_image(self) -> None:
        if self._presenter:
            self._presenter.on_add_below_image()

    def _on_context_add_below_image_from_clipboard(self) -> None:
        if self._presenter:
            self._presenter.on_add_below_image_from_clipboard()

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
