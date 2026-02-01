"""Quick test for latex_replace (no pytest required)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from core.models.document import Document, ContentNode
from core.models.book_metadata import BookMetadata
from services.latex_replace import replace_latex_alphabet, LATEX_TO_UNICODE

doc = Document(
    BookMetadata("T", "en"),
    [ContentNode("p0", "Value $\\beta$ here", 0)]
)
replace_latex_alphabet(doc)
expected = "Value \u03b2 here"
assert doc.flat_list()[0].text == expected, repr(doc.flat_list()[0].text)
print("latex_replace OK")
