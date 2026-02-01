"""
Find and Replace dialog: Find what / Replace with fields, Match case, Wrap around,
Find Next, Replace, Replace All, Cancel. Behaves like Notepad; searches across all document elements.
"""

from __future__ import annotations

from tkinter import Tk, Toplevel, Frame, Label, Button, Entry, Checkbutton, BooleanVar, StringVar, W, E
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gui.presenters import EditorPresenter


class FindReplaceDialog:
    """
    Toplevel dialog for Find and Replace. Delegates Find Next / Replace / Replace All
    to EditorPresenter; operates on all document nodes (ContentNode.text, ImageNode.alt).
    """

    def __init__(self, root: Tk, editor_presenter: "EditorPresenter") -> None:
        self._root = root
        self._presenter = editor_presenter
        self._win = Toplevel(root)
        self._win.title("Find and Replace")
        self._win.transient(root)

        self._find_var = StringVar()
        self._replace_var = StringVar()
        self._match_case_var = BooleanVar(value=False)
        self._wrap_var = BooleanVar(value=True)

        self._build_ui()
        self._win.geometry("+%d+%d" % (root.winfo_rootx() + 80, root.winfo_rooty() + 80))

    def _build_ui(self) -> None:
        f = Frame(self._win, padx=12, pady=12)
        f.pack(fill="both", expand=True)

        row = 0
        Label(f, text="Find what:", font=("", 10)).grid(row=row, column=0, sticky=W, pady=(0, 4))
        row += 1
        find_entry = Entry(f, textvariable=self._find_var, width=36)
        find_entry.grid(row=row, column=0, columnspan=2, sticky=W + E, pady=(0, 8))
        find_entry.focus_set()
        row += 1

        Label(f, text="Replace with:", font=("", 10)).grid(row=row, column=0, sticky=W, pady=(0, 4))
        row += 1
        Entry(f, textvariable=self._replace_var, width=36).grid(row=row, column=0, columnspan=2, sticky=W + E, pady=(0, 8))
        row += 1

        cb_match = Checkbutton(f, text="Match case", variable=self._match_case_var)
        cb_match.grid(row=row, column=0, columnspan=2, sticky=W, pady=(0, 2))
        row += 1
        cb_wrap = Checkbutton(f, text="Wrap around", variable=self._wrap_var)
        cb_wrap.grid(row=row, column=0, columnspan=2, sticky=W, pady=(0, 12))
        row += 1

        btn_frame = Frame(f)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=(0, 0))
        Button(btn_frame, text="Find Next", command=self._on_find_next).pack(side="left", padx=(0, 8))
        Button(btn_frame, text="Replace", command=self._on_replace).pack(side="left", padx=(0, 8))
        Button(btn_frame, text="Replace All", command=self._on_replace_all).pack(side="left", padx=(0, 8))
        Button(btn_frame, text="Cancel", command=self._win.destroy).pack(side="left")

        self._win.protocol("WM_DELETE_WINDOW", self._win.destroy)

    def _on_find_next(self) -> None:
        find_text = self._find_var.get().strip()
        if not find_text:
            return
        found = self._presenter.find_next(
            find_text,
            match_case=self._match_case_var.get(),
            wrap=self._wrap_var.get(),
        )
        if not found:
            from tkinter import messagebox
            messagebox.showinfo("Find and Replace", "Cannot find \"%s\"." % find_text, parent=self._win)

    def _on_replace(self) -> None:
        find_text = self._find_var.get().strip()
        replace_text = self._replace_var.get()
        if not find_text:
            return
        self._presenter.replace_current(
            find_text,
            replace_text,
            match_case=self._match_case_var.get(),
        )

    def _on_replace_all(self) -> None:
        find_text = self._find_var.get().strip()
        replace_text = self._replace_var.get()
        if not find_text:
            return
        count = self._presenter.replace_all(
            find_text,
            replace_text,
            match_case=self._match_case_var.get(),
        )
        from tkinter import messagebox
        messagebox.showinfo("Find and Replace", "Replaced %d occurrence(s)." % count, parent=self._win)
