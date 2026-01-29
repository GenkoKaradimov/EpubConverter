"""
Main Tkinter window: menus (File, Help), container for views that can be swapped.
All code and comments in English.
"""

from __future__ import annotations

from tkinter import Tk, Frame, Menu, messagebox, filedialog
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.application import Application
    from core.models.document import Document


class MainWindow:
    """
    Main window: menus (File: Open PDF, Export EPUB, Exit; Help: About),
    container frame for views. Minimal layout; long operations run in main thread for now.
    """

    def __init__(self, root: Tk, app: Application) -> None:
        self._root = root
        self._app = app
        self._container: Frame | None = None
        self._current_view_frame: Frame | None = None

        self._root.title("EpubConverter")
        self._root.geometry("600x400")
        self._root.minsize(400, 300)

        self._build_menus()
        self._build_container()
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_menus(self) -> None:
        menubar = Menu(self._root)
        self._root.config(menu=menubar)

        file_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open PDF...", command=self._on_open_pdf)
        file_menu.add_command(label="Export EPUB...", command=self._on_export_epub)
        file_menu.add_command(label="Preview EPUB", command=self._on_preview_epub)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_close)

        help_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._on_about)

    def _build_container(self) -> None:
        self._container = Frame(self._root, padx=10, pady=10)
        self._container.pack(fill="both", expand=True)

    def _clear_container(self) -> None:
        if self._current_view_frame:
            self._current_view_frame.destroy()
            self._current_view_frame = None

    def show_conversion_view(self, initial_path: str | None = None) -> None:
        """Show the conversion view (PDF picker, Extract). Optionally set initial PDF path."""
        self._clear_container()
        from gui.views.conversion_view import ConversionView
        from gui.presenters import ConversionPresenter

        self._current_view_frame = Frame(self._container)
        self._current_view_frame.pack(fill="both", expand=True)
        view = ConversionView(self._current_view_frame, initial_path=initial_path)
        view.pack(fill="both", expand=True)
        presenter = ConversionPresenter(view, self._app, self)
        view.set_presenter(presenter)

    def show_editor_view(self, document: Document) -> None:
        """Show the editor view with the loaded document."""
        self._clear_container()
        from gui.views.editor_view import EditorView
        from gui.presenters import EditorPresenter

        self._current_view_frame = Frame(self._container)
        self._current_view_frame.pack(fill="both", expand=True)
        view = EditorView(self._current_view_frame, document)
        view.pack(fill="both", expand=True)
        presenter = EditorPresenter(view, document, self)
        view.set_presenter(presenter)
        presenter.on_show()

    def _on_open_pdf(self) -> None:
        path = filedialog.askopenfilename(
            title="Open PDF",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if path:
            self.show_conversion_view(initial_path=path)

    def request_export_epub(self) -> None:
        """Show save dialog and build EPUB from current document. Clear success/error messages."""
        if not self._app.current_document:
            messagebox.showinfo("Export EPUB", "No document loaded. Extract a PDF first.")
            return
        path = filedialog.asksaveasfilename(
            title="Export EPUB",
            defaultextension=".epub",
            filetypes=[("EPUB files", "*.epub"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            self._app.build_epub(path)
            messagebox.showinfo("Export EPUB", f"Saved to:\n{path}")
        except ValueError as e:
            messagebox.showwarning("Export EPUB", str(e))
        except (OSError, RuntimeError) as e:
            messagebox.showerror("Export EPUB", f"Failed to save EPUB:\n{e}")
        except Exception as e:
            messagebox.showerror("Export EPUB", f"Unexpected error:\n{e}")

    def _on_export_epub(self) -> None:
        self.request_export_epub()

    def _on_preview_epub(self) -> None:
        path = self._app.last_export_path
        if not path or not path.exists():
            messagebox.showinfo("Preview EPUB", "No EPUB exported yet. Export from File → Export EPUB first.")
            return
        try:
            from gui.views.preview_view import open_path_in_default_app
            if open_path_in_default_app(path):
                messagebox.showinfo("Preview EPUB", f"Opening:\n{path}")
            else:
                messagebox.showerror("Preview EPUB", f"File not found or could not open:\n{path}")
        except Exception as e:
            messagebox.showerror("Preview EPUB", f"Failed to open:\n{e}")

    def _on_about(self) -> None:
        messagebox.showinfo(
            "About EpubConverter",
            "EpubConverter\nConvert PDF to EPUB with user editing.\nBuilt with Tkinter.",
        )

    def _on_close(self) -> None:
        self._root.quit()
        self._root.destroy()
