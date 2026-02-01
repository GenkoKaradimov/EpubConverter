"""
Presenters: wire GUI actions to core (extract, build). Conversion and editor presenters.
All code and comments in English.
"""

from __future__ import annotations

import tempfile
import threading
from pathlib import Path
from tkinter import Button, Frame, Label, Toplevel
from tkinter import filedialog, messagebox
from typing import TYPE_CHECKING

from core.models.document import ContentItem, ContentNode, Document, ImageNode
from gui.views.conversion_view import ConversionView
from gui.views.editor_view import EditorView

if TYPE_CHECKING:
    from app.application import Application
    from gui.main_window import MainWindow


def _next_chapter_id(document: Document) -> str:
    """Return a unique id for a new chapter (ch_N)."""
    max_n = -1
    for node in document.root_nodes:
        if isinstance(node, ContentNode) and node.id.startswith("ch_"):
            try:
                n = int(node.id[3:])
                max_n = max(max_n, n)
            except ValueError:
                pass
    return f"ch_{max_n + 1}"


def _next_paragraph_id(document: Document) -> str:
    """Return a unique id for a new paragraph (p_N)."""
    max_n = -1
    for node in document.root_nodes:
        if isinstance(node, ContentNode) and node.id.startswith("p_"):
            try:
                n = int(node.id[2:])
                max_n = max(max_n, n)
            except ValueError:
                pass
    return f"p_{max_n + 1}"


def _next_image_id(document: Document) -> str:
    """Return a unique image_id for document.images (img_N)."""
    max_n = -1
    for key in document.images:
        if key.startswith("img_"):
            try:
                n = int(key[4:])
                max_n = max(max_n, n)
            except ValueError:
                pass
    return f"img_{max_n + 1}"


def _item_text(item: ContentItem) -> str:
    """Text or alt for display in the content area."""
    if isinstance(item, ImageNode):
        return item.alt or ""
    return item.text


def show_paragraph_to_image_result(
    converted: int,
    failed: int,
    errors: list[str],
    parent: object,
) -> None:
    """
    Show summary message and, if errors, a Toplevel with one Copy button per error.
    parent: a Tk widget or MainWindow (has _root) for messagebox parent and Toplevel parent.
    """
    root = getattr(parent, "_root", None)
    if root is None and hasattr(parent, "winfo_toplevel"):
        root = parent.winfo_toplevel()
    if root is None:
        root = parent
    if failed == 0 and converted == 0:
        messagebox.showinfo(
            "Paragraph to image",
            "No formula paragraphs found to convert.",
            parent=root,
        )
    elif failed == 0:
        messagebox.showinfo(
            "Paragraph to image",
            f"Success. {converted} paragraph(s) converted to images.",
            parent=root,
        )
    else:
        messagebox.showinfo(
            "Paragraph to image",
            f"Done. {converted} converted, {failed} failed.",
            parent=root,
        )
    if errors:
        win = Toplevel(root)
        win.title("Errors")
        win.transient(root)
        f = Frame(win, padx=12, pady=12)
        f.pack(fill="both", expand=True)
        Label(f, text="Errors (Copy = one error, Copy all = entire list):", font=("", 10, "bold")).pack(anchor="w")
        canvas_frame = Frame(f)
        canvas_frame.pack(fill="both", expand=True)
        for i, err_text in enumerate(errors):
            row = Frame(canvas_frame)
            row.pack(fill="x", pady=2)
            lbl = Label(row, text=err_text, wraplength=500, justify="left", font=("", 9))
            lbl.pack(side="left", fill="x", expand=True)
            def make_copy_cb(text: str) -> object:
                def cb() -> None:
                    root.clipboard_clear()
                    root.clipboard_append(text)
                return cb
            Button(row, text="Copy", command=make_copy_cb(err_text)).pack(side="right", padx=(8, 0))
        btn_frame = Frame(f)
        btn_frame.pack(pady=(12, 0))
        def copy_all_cb() -> None:
            root.clipboard_clear()
            root.clipboard_append("\n\n---\n\n".join(errors))
        Button(btn_frame, text="Copy all", command=copy_all_cb).pack(side="left", padx=(0, 8))
        Button(btn_frame, text="Close", command=win.destroy).pack(side="left")


class EditorPresenter:
    """
    Editor presenter: wire view and Document. Read on show, write on Apply or selection change.
    Export to EPUB via main_window.request_export_epub().
    """

    def __init__(self, view: EditorView, document: Document, main_window: "MainWindow") -> None:
        self._view = view
        self._document = document
        self._main_window = main_window
        self._current_index: int | None = None

    def _show_node(self, index: int) -> None:
        """Show text or image panel for node at index."""
        nodes = self._document.flat_list()
        if index < 0 or index >= len(nodes):
            self._view.show_text_panel()
            self._view.set_text("")
            return
        node = nodes[index]
        if isinstance(node, ImageNode):
            path = self._document.images.get(node.image_id)
            if path and path.exists():
                self._view.show_image_panel(path, node)
            else:
                self._view.show_text_panel()
                self._view.set_text(_item_text(node))
        else:
            self._view.show_text_panel()
            self._view.set_text(_item_text(node))

    def on_show(self) -> None:
        """Populate list from document and select first node if any."""
        nodes = self._document.flat_list()
        self._view.set_nodes(nodes)
        if nodes:
            self._view.set_selection(0)
            self._show_node(0)
            self._view.set_buttons_state(True)
            self._current_index = 0
        else:
            self._view.show_text_panel()
            self._view.set_text("")
            self._view.set_buttons_state(False)
            self._current_index = None

    def _save_current_to_node(self) -> None:
        """Write view text/alt to the currently selected node in document."""
        if self._current_index is None:
            return
        nodes = self._document.flat_list()
        if 0 <= self._current_index < len(nodes):
            node = nodes[self._current_index]
            text = self._view.get_text()
            if isinstance(node, ImageNode):
                node.alt = text or None
            else:
                node.text = text
        self._view.clear_text_modified()

    def on_selection(self, index: int) -> None:
        """Save current text/alt to previous node, then load selected node (text or image panel)."""
        self._save_current_to_node()
        nodes = self._document.flat_list()
        if 0 <= index < len(nodes):
            self._current_index = index
            self._show_node(index)
            self._view.set_buttons_state(True)
        else:
            self._current_index = None
            self._view.show_text_panel()
            self._view.set_buttons_state(False)

    def on_apply(self) -> None:
        """Save current text to selected node."""
        self._save_current_to_node()

    def on_export_epub(self) -> None:
        """Trigger Export EPUB (file dialog and build) via main window."""
        self._save_current_to_node()
        self._main_window.request_export_epub()

    def on_add_chapter(self) -> None:
        """Add a new chapter node to document and refresh list."""
        new_id = _next_chapter_id(self._document)
        node = ContentNode(id=new_id, text="New Chapter", level=1)
        self._document.root_nodes.append(node)
        nodes = self._document.flat_list()
        self._view.set_nodes(nodes)
        idx = len(nodes) - 1
        self._current_index = idx
        self._view.set_selection(idx)
        self._view.show_text_panel()
        self._view.set_text(node.text)
        self._view.set_buttons_state(True)
        self._view.focus_text()

    def on_remove(self) -> None:
        """Remove selected node from document and refresh list."""
        idx = self._view.get_selected_index()
        if idx is None:
            return
        nodes = self._document.flat_list()
        if 0 <= idx < len(nodes):
            node = nodes[idx]
            self._document.root_nodes.remove(node)
            nodes = self._document.flat_list()
            self._view.set_nodes(nodes)
            self._current_index = None
            if nodes:
                new_idx = min(idx, len(nodes) - 1)
                self._view.set_selection(new_idx)
                self._show_node(new_idx)
                self._current_index = new_idx
            else:
                self._view.show_text_panel()
                self._view.set_text("")
                self._view.set_buttons_state(False)

    def on_move_up(self) -> None:
        """Move selected node up in root_nodes."""
        idx = self._view.get_selected_index()
        if idx is None or idx <= 0:
            return
        nodes = self._document.root_nodes
        nodes[idx], nodes[idx - 1] = nodes[idx - 1], nodes[idx]
        self._view.set_nodes(self._document.flat_list())
        self._view.set_selection(idx - 1)
        self._current_index = idx - 1

    def on_move_down(self) -> None:
        """Move selected node down in root_nodes."""
        idx = self._view.get_selected_index()
        nodes = self._document.root_nodes
        if idx is None or idx >= len(nodes) - 1:
            return
        nodes[idx], nodes[idx + 1] = nodes[idx + 1], nodes[idx]
        self._view.set_nodes(self._document.flat_list())
        self._view.set_selection(idx + 1)
        self._current_index = idx + 1

    def on_duplicate(self) -> None:
        """Duplicate the selected node and insert it right below; select the new node."""
        idx = self._view.get_selected_index()
        if idx is None:
            return
        nodes = self._document.root_nodes
        if idx < 0 or idx >= len(nodes):
            return
        node = nodes[idx]
        if isinstance(node, ContentNode):
            new_id = _next_chapter_id(self._document) if node.level >= 1 else _next_paragraph_id(self._document)
            clone = ContentNode(id=new_id, text=node.text, level=node.level)
        else:
            assert isinstance(node, ImageNode)
            clone = ImageNode(
                id=f"{node.id}_copy",
                image_id=node.image_id,
                alt=node.alt,
                rotation_degrees=node.rotation_degrees,
                crop_rect=node.crop_rect,
                is_formula=node.is_formula,
            )
        nodes.insert(idx + 1, clone)
        self._view.set_nodes(self._document.flat_list())
        self._view.set_selection(idx + 1)
        self._current_index = idx + 1
        self._show_node(idx + 1)

    def on_add_below_title(self) -> None:
        """Insert a new chapter (title) below the selected item."""
        idx = self._view.get_selected_index()
        if idx is None:
            idx = -1
        new_id = _next_chapter_id(self._document)
        node = ContentNode(id=new_id, text="New Chapter", level=1)
        self._document.root_nodes.insert(idx + 1, node)
        self._view.set_nodes(self._document.flat_list())
        self._view.set_selection(idx + 1)
        self._current_index = idx + 1
        self._show_node(idx + 1)
        self._view.set_buttons_state(True)
        self._view.set_text(node.text)
        self._view.focus_text()

    def on_add_below_paragraph(self) -> None:
        """Insert a new paragraph below the selected item."""
        idx = self._view.get_selected_index()
        if idx is None:
            idx = -1
        new_id = _next_paragraph_id(self._document)
        node = ContentNode(id=new_id, text="", level=0)
        self._document.root_nodes.insert(idx + 1, node)
        self._view.set_nodes(self._document.flat_list())
        self._view.set_selection(idx + 1)
        self._current_index = idx + 1
        self._show_node(idx + 1)
        self._view.set_buttons_state(True)
        self._view.set_text("")
        self._view.focus_text()

    def on_add_below_image(self) -> None:
        """Ask for an image file, then insert a new image node below the selected item."""
        root = getattr(self._main_window, "_root", None)
        if not root:
            return
        path_str = filedialog.askopenfilename(
            parent=root,
            title="Select image",
            filetypes=[
                ("Images", "*.png *.jpg *.jpeg *.gif *.webp"),
                ("All files", "*.*"),
            ],
        )
        if not path_str:
            return
        path = Path(path_str)
        if not path.exists():
            return
        idx = self._view.get_selected_index()
        if idx is None:
            idx = -1
        image_id = _next_image_id(self._document)
        self._document.images[image_id] = path
        node_id = f"img_node_{image_id}"
        node = ImageNode(id=node_id, image_id=image_id, alt=None)
        self._document.root_nodes.insert(idx + 1, node)
        self._view.set_nodes(self._document.flat_list())
        self._view.set_selection(idx + 1)
        self._current_index = idx + 1
        self._show_node(idx + 1)
        self._view.set_buttons_state(True)

    def on_add_below_image_from_clipboard(self) -> None:
        """Get image from clipboard, save to file, then insert new image node below the selected item."""
        try:
            from PIL import ImageGrab
        except ImportError:
            root = getattr(self._main_window, "_root", None)
            if root:
                messagebox.showinfo("Clipboard", "Pillow is required for clipboard images.", parent=root)
            return
        img = ImageGrab.grabclipboard()
        if img is None:
            root = getattr(self._main_window, "_root", None)
            if root:
                messagebox.showinfo("Clipboard", "No image in clipboard.", parent=root)
            return
        idx = self._view.get_selected_index()
        if idx is None:
            idx = -1
        image_id = _next_image_id(self._document)
        clip_dir = Path(tempfile.gettempdir()) / "EpubConverter" / "clipboard"
        clip_dir.mkdir(parents=True, exist_ok=True)
        path = clip_dir / f"{image_id}.png"
        try:
            img.save(str(path), "PNG")
        except OSError:
            root = getattr(self._main_window, "_root", None)
            if root:
                messagebox.showerror("Clipboard", "Failed to save clipboard image.", parent=root)
            return
        self._document.images[image_id] = path
        node_id = f"img_node_{image_id}"
        node = ImageNode(id=node_id, image_id=image_id, alt=None)
        self._document.root_nodes.insert(idx + 1, node)
        self._view.set_nodes(self._document.flat_list())
        self._view.set_selection(idx + 1)
        self._current_index = idx + 1
        self._show_node(idx + 1)
        self._view.set_buttons_state(True)

    def on_separate_formulas(self) -> None:
        """Run separate_formulas on the document and refresh the list."""
        from services.latex_merge import separate_formulas

        separate_formulas(self._document)
        idx = self._view.get_selected_index()
        self._view.set_nodes(self._document.flat_list())
        if idx is not None and idx >= len(self._document.flat_list()):
            idx = max(0, len(self._document.flat_list()) - 1)
        if idx is not None:
            self._view.set_selection(idx)
            self._current_index = idx
            self._show_node(idx)
        self._main_window.refresh_editor_view()

    def on_paragraph_to_image(self) -> None:
        """Convert only the selected paragraph to image (if it is entirely a LaTeX formula)."""
        from services.latex_to_image import MATHTEXT_AVAILABLE, convert_single_paragraph_to_image

        root = getattr(self._main_window, "_root", None)
        if not root:
            return
        idx = self._view.get_selected_index()
        if idx is None:
            messagebox.showinfo(
                "Paragraph to image",
                "Select an item first.",
                parent=root,
            )
            return
        if not MATHTEXT_AVAILABLE:
            messagebox.showinfo(
                "Paragraph to image",
                "matplotlib is required. Install with: pip install matplotlib",
                parent=root,
            )
            return
        converted, failed, errors = convert_single_paragraph_to_image(self._document, idx)
        show_paragraph_to_image_result(converted, failed, errors, self._main_window)
        self._view.set_nodes(self._document.flat_list())
        if idx >= len(self._document.flat_list()):
            idx = max(0, len(self._document.flat_list()) - 1)
        self._view.set_selection(idx)
        self._current_index = idx
        self._show_node(idx)
        self._main_window.refresh_editor_view()

    def on_rotate(self, degrees: float) -> None:
        """Set rotation on current ImageNode and refresh preview."""
        if self._current_index is None:
            return
        nodes = self._document.flat_list()
        if 0 <= self._current_index < len(nodes):
            node = nodes[self._current_index]
            if isinstance(node, ImageNode):
                node.rotation_degrees = degrees
                path = self._document.images.get(node.image_id)
                if path and path.exists():
                    self._view.set_image_preview_from_node(path, node)

    def on_crop(self, crop_rect: tuple[float, float, float, float]) -> None:
        """Set crop rect on current ImageNode and refresh preview."""
        if self._current_index is None:
            return
        nodes = self._document.flat_list()
        if 0 <= self._current_index < len(nodes):
            node = nodes[self._current_index]
            if isinstance(node, ImageNode):
                node.crop_rect = crop_rect
                path = self._document.images.get(node.image_id)
                if path and path.exists():
                    self._view.set_image_preview_from_node(path, node)

    def on_crop_dialog(self, open_dialog: "object") -> None:
        """Open crop dialog; open_dialog(current_rect) is called by view, we pass node's crop_rect."""
        if self._current_index is None:
            return
        nodes = self._document.flat_list()
        if 0 <= self._current_index < len(nodes):
            node = nodes[self._current_index]
            if isinstance(node, ImageNode):
                open_dialog(node.crop_rect)

    def on_find_next(self) -> None:
        """Find next occurrence of search string in text area."""
        query = self._view.get_search_query()
        self._view.find_in_text(query)


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
        self._view.set_status("Extracting... (please wait)")
        self._view.update_idletasks()
        root = getattr(self._main_window, "_root", None)
        if not root:
            self._view.set_status("UI not ready.")
            return

        def do_extract() -> None:
            try:
                from core.converters.pdf_extractor import PdfExtractor

                images_dir = path_obj.parent / (path_obj.stem + "_images")
                document = PdfExtractor().extract(path_obj, images_dir=images_dir)
                def on_success() -> None:
                    self._app.set_current_document(document)
                    self._view.set_status("")
                    self._main_window.show_editor_view(document)
                root.after(0, on_success)
            except FileNotFoundError as e:
                root.after(0, lambda: self._view.set_status(f"File not found: {e}"))
            except RuntimeError as e:
                root.after(0, lambda: self._view.set_status(f"Extraction failed (install PyMuPDF?): {e}"))
            except Exception as e:
                root.after(0, lambda err=e: self._view.set_status(f"Extraction failed: {err}"))

        threading.Thread(target=do_extract, daemon=True).start()
