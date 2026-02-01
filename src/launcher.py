"""
Launcher splash: shows before the main app. Cross-platform placeholder with title;
if dependencies are missing, shows "Installing dependencies..." and runs pip, then starts the app.
All code and comments in English.
"""

from __future__ import annotations

import subprocess
import sys
import threading
from pathlib import Path
from typing import Callable

# Tkinter is in the stdlib on all platforms
import tkinter as tk
from tkinter import font as tkfont

# Splash size (fixed, OS-independent)
SPLASH_W = 560
SPLASH_H = 380
OVERLAY_HEIGHT = 72
APP_TITLE = "EpubConverter"


def _check_dependencies() -> bool:
    """Return True if app dependencies (PyMuPDF, ebooklib) are importable."""
    try:
        import importlib.util
        for name in ("pymupdf", "ebooklib"):
            spec = importlib.util.find_spec(name)
            if spec is None:
                return False
        return True
    except Exception:
        return False


def _install_dependencies(project_root: Path) -> bool:
    """Run pip install -r requirements.txt; return True on success."""
    req = project_root / "requirements.txt"
    if not req.is_file():
        return False
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req), "-q"],
            check=True,
            capture_output=True,
            cwd=str(project_root),
            creationflags=creationflags,
        )
        return True
    except Exception:
        return False
    except subprocess.CalledProcessError:
        return False


def _center_on_screen(root: tk.Tk) -> None:
    """Center the window on the primary screen (OS-independent)."""
    root.update_idletasks()
    w = root.winfo_reqwidth()
    h = root.winfo_reqheight()
    try:
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
    except tk.TclError:
        sw, sh = 800, 600
    x = max(0, (sw - w) // 2)
    y = max(0, (sh - h) // 2)
    root.geometry(f"+{x}+{y}")


def run_launcher(project_root: Path, on_ready: Callable[[], None]) -> None:
    """
    Show splash window (placeholder with title). If deps missing, show
    "Installing dependencies..." and pip install; then call on_ready() (start main app).
    """
    root = tk.Tk()
    root.title(APP_TITLE)
    root.resizable(False, False)
    root.configure(bg="#1a1a24")

    # Remove window decoration for a cleaner splash (optional); keep for closing/minimize on some OS
    # root.overrideredirect(True)

    # Main content frame
    main_frame = tk.Frame(root, bg="#1a1a24", width=SPLASH_W, height=SPLASH_H)
    main_frame.pack(fill=tk.BOTH, expand=True)
    main_frame.pack_propagate(False)

    # Content area: placeholder with title
    canvas = tk.Canvas(
        main_frame,
        width=SPLASH_W,
        height=SPLASH_H,
        bg="#1a1a24",
        highlightthickness=0,
    )
    canvas.pack(fill=tk.BOTH, expand=True)
    canvas.create_rectangle(0, 0, SPLASH_W, SPLASH_H, fill="#252532", outline="")
    try:
        title_font = tkfont.Font(family="Segoe UI", size=28, weight="bold")
    except tk.TclError:
        title_font = tkfont.Font(size=28, weight="bold")
    try:
        sub_font = tkfont.Font(family="Segoe UI", size=14)
    except tk.TclError:
        sub_font = tkfont.Font(size=14)
    canvas.create_text(SPLASH_W // 2, SPLASH_H // 2 - 20, text=APP_TITLE, fill="#e8e8f0", font=title_font)
    canvas.create_text(SPLASH_W // 2, SPLASH_H // 2 + 24, text="PDF → EPUB", fill="#9090a0", font=sub_font)

    # Overlay bar for status
    overlay = tk.Frame(main_frame, height=OVERLAY_HEIGHT, bg="#1a1a24")
    overlay.place(x=0, y=SPLASH_H - OVERLAY_HEIGHT, width=SPLASH_W, height=OVERLAY_HEIGHT)
    try:
        status_font = tkfont.Font(family="Segoe UI", size=13)
    except tk.TclError:
        status_font = tkfont.Font(size=13)
    overlay_label = tk.Label(overlay, text="", fg="#c0c0d0", bg="#1a1a24", font=status_font)
    overlay_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

    def set_status(text: str) -> None:
        overlay_label.config(text=text)
        root.update_idletasks()

    def install_then_ready() -> None:
        set_status("Installing dependencies...")
        ok = _install_dependencies(project_root)
        set_status("Ready." if ok else "Install failed. Check console.")
        root.after(1200, _close_and_run)

    def _close_and_run() -> None:
        try:
            root.destroy()
        except tk.TclError:
            pass
        on_ready()

    def maybe_install_and_run() -> None:
        if _check_dependencies():
            set_status("Starting...")
            root.after(800, _close_and_run)
        else:
            thread = threading.Thread(target=install_then_ready, daemon=True)
            thread.start()

    root.after(400, maybe_install_and_run)
    _center_on_screen(root)
    root.geometry(f"{SPLASH_W}x{SPLASH_H + 0}")
    root.mainloop()
