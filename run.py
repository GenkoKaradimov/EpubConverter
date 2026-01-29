"""
Single-file launcher: run from project root with:
    python run.py
On Windows, if started with python.exe (console), re-launches with pythonw.exe
so no console window appears and closing a terminal does not kill the GUI.
No need to set PYTHONPATH. All code and comments in English.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Add src to path so "app" and "main" resolve when run from project root
_root = Path(__file__).resolve().parent
_src = _root / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))


def _is_console_python() -> bool:
    exe = Path(sys.executable).resolve().name.lower()
    return exe == "python.exe"


def _relaunch_without_console() -> None:
    py = Path(sys.executable).resolve()
    pythonw = py.parent / "pythonw.exe"
    if not pythonw.is_file():
        return
    os.chdir(_root)
    os.execv(str(pythonw), [str(pythonw), str(_root / "run.py")] + sys.argv[1:])
    sys.exit(0)


if __name__ == "__main__":
    if sys.platform == "win32" and _is_console_python():
        _relaunch_without_console()
    from launcher import run_launcher
    from main import main
    run_launcher(_root, main)
