"""
Standalone CLI: render a LaTeX math expression to SVG or PNG.
Run from project root:
  python scripts/render_latex.py "$\alpha + \beta$" -o formula.svg
  python scripts/render_latex.py -f formula.tex -o out.png
Requires matplotlib. All code and comments in English.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _render(latex: str, output_path: Path, fmt: str, dpi: int) -> None:
    from matplotlib.mathtext import math_to_image

    math_to_image(latex, str(output_path), format=fmt, dpi=dpi)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render LaTeX math expression to SVG or PNG using matplotlib.mathtext."
    )
    parser.add_argument(
        "latex",
        nargs="?",
        default=None,
        help="LaTeX expression (e.g. \"$\\\\alpha$\"). Omit if using -f.",
    )
    parser.add_argument(
        "-f",
        "--file",
        dest="file",
        type=Path,
        default=None,
        help="Read LaTeX from file instead of command line.",
    )
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        type=Path,
        help="Output path (e.g. formula.svg or formula.png). Format inferred from extension.",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=150,
        help="DPI for raster output (default: 150).",
    )
    args = parser.parse_args()

    if args.file is not None:
        if not args.file.exists():
            print(f"Error: file not found: {args.file}", file=sys.stderr)
            return 1
        latex = args.file.read_text(encoding="utf-8").strip()
    elif args.latex is not None:
        latex = args.latex.strip()
    else:
        print("Error: provide LaTeX expression as argument or use -f <file>.", file=sys.stderr)
        return 1

    if not latex:
        print("Error: LaTeX expression is empty.", file=sys.stderr)
        return 1

    ext = args.output.suffix.lower()
    if ext == ".svg":
        fmt = "svg"
    elif ext in (".png", ".jpg", ".jpeg", ".pdf", ".ps"):
        fmt = ext.lstrip(".")
        if fmt == "jpeg":
            fmt = "jpg"
    else:
        print(f"Error: output format not supported (use .svg, .png, .pdf, .ps). Got: {ext}", file=sys.stderr)
        return 1

    try:
        _render(latex, args.output, fmt, args.dpi)
    except ImportError as e:
        print("Error: matplotlib is required. Install with: pip install matplotlib", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
