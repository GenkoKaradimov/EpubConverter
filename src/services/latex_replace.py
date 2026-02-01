"""
Replace single LaTeX symbols (e.g. $\\beta$) with Unicode in document text/alt.
Used by LaTeX dialog for the \"alphabet\" action. Greek alphabet and common math symbols only; does not modify full formulas.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from core.models.document import Document

# Single-command LaTeX (no arguments) -> Unicode. Greek lowercase, Greek uppercase, common math.
LATEX_TO_UNICODE: dict[str, str] = {
    # Greek lowercase
    "alpha": "\u03b1",
    "beta": "\u03b2",
    "gamma": "\u03b3",
    "delta": "\u03b4",
    "epsilon": "\u03b5",
    "zeta": "\u03b6",
    "eta": "\u03b7",
    "theta": "\u03b8",
    "iota": "\u03b9",
    "kappa": "\u03ba",
    "lambda": "\u03bb",
    "mu": "\u03bc",
    "nu": "\u03bd",
    "xi": "\u03be",
    "pi": "\u03c0",
    "rho": "\u03c1",
    "sigma": "\u03c3",
    "tau": "\u03c4",
    "upsilon": "\u03c5",
    "phi": "\u03c6",
    "chi": "\u03c7",
    "psi": "\u03c8",
    "omega": "\u03c9",
    "varepsilon": "\u03b5",
    "vartheta": "\u03d1",
    "varpi": "\u03d6",
    "varrho": "\u03f1",
    "varsigma": "\u03c2",
    "varphi": "\u03d5",
    # Greek uppercase
    "Gamma": "\u0393",
    "Delta": "\u0394",
    "Theta": "\u0398",
    "Lambda": "\u039b",
    "Xi": "\u039e",
    "Pi": "\u03a0",
    "Sigma": "\u03a3",
    "Upsilon": "\u03a5",
    "Phi": "\u03a6",
    "Psi": "\u03a8",
    "Omega": "\u03a9",
    # Common math (no arguments)
    "infty": "\u221e",
    "partial": "\u2202",
    "nabla": "\u2207",
    "sum": "\u2211",
    "prod": "\u220f",
    "int": "\u222b",
    "pm": "\u00b1",
    "mp": "\u2213",
    "times": "\u00d7",
    "div": "\u00f7",
    "leq": "\u2264",
    "geq": "\u2265",
    "neq": "\u2260",
    "approx": "\u2248",
    "equiv": "\u2261",
    "cdot": "\u22c5",
    "ldots": "\u2026",
    "cdots": "\u22ef",
    "rightarrow": "\u2192",
    "leftarrow": "\u2190",
    "Rightarrow": "\u21d2",
    "Leftarrow": "\u21d0",
    "circ": "\u2218",
    "bullet": "\u2022",
}

# Build regex: $ \s* \command \s* $ for each command (escape backslash and command for regex).
_CMD_PATTERN = "|".join(re.escape(cmd) for cmd in sorted(LATEX_TO_UNICODE.keys(), key=len, reverse=True))
_RE_PATTERN = re.compile(r"\$\s*\\(" + _CMD_PATTERN + r")\s*\$")


def _replace_in_text(text: str) -> str:
    """Replace single LaTeX commands in $ ... $ with Unicode. Only whole $ \\command $ matches."""
    if not text:
        return text
    def repl(m: re.Match[str]) -> str:
        cmd = m.group(1)
        return LATEX_TO_UNICODE.get(cmd, m.group(0))
    return _RE_PATTERN.sub(repl, text)


def replace_latex_alphabet(
    document: "Document",
    progress_callback: Callable[[int, int], None] | None = None,
) -> None:
    """
    Replace single LaTeX symbols (e.g. $\\beta$) with Unicode in all document text and alt.
    Calls progress_callback(current_index, total) after each node if provided.
    """
    from core.models.document import ContentNode, ImageNode

    flat = document.flat_list()
    total = len(flat)
    for i, node in enumerate(flat):
        if isinstance(node, ContentNode):
            node.text = _replace_in_text(node.text)
        elif isinstance(node, ImageNode) and node.alt:
            node.alt = _replace_in_text(node.alt)
        if progress_callback is not None:
            progress_callback(i + 1, total)
