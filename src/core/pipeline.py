"""
Pipeline: PDF path -> extract Document -> (future: edit) -> build EPUB.
Single class/function for the full flow; errors propagated with clear messages.
All code and comments in English.
"""

from __future__ import annotations

from pathlib import Path

from core.converters.epub_builder import EpubBuilder
from core.converters.pdf_extractor import PdfExtractor
from core.models.document import Document


class PipelineError(Exception):
    """Raised when a pipeline step fails; message describes the step and cause."""

    pass


def run_pipeline(
    pdf_path: Path | str,
    epub_path: Path | str | None = None,
) -> tuple[Document, Path]:
    """
    Run the full flow: extract PDF -> Document -> build EPUB.
    Returns (document, epub_path). Raises PipelineError with clear message on failure.
    """
    pdf_path = Path(pdf_path)
    if epub_path is None:
        epub_path = pdf_path.with_suffix(".epub")
    else:
        epub_path = Path(epub_path)

    if not pdf_path.exists():
        raise PipelineError(f"PDF not found: {pdf_path}")

    try:
        document = PdfExtractor().extract(pdf_path)
    except FileNotFoundError as e:
        raise PipelineError(f"PDF not found: {e}") from e
    except RuntimeError as e:
        raise PipelineError(f"PDF extraction failed (missing dependency?): {e}") from e
    except Exception as e:
        raise PipelineError(f"PDF extraction failed: {e}") from e

    # Future: user editing step here (document may be modified)

    try:
        EpubBuilder().build(document, epub_path)
    except RuntimeError as e:
        raise PipelineError(f"EPUB build failed (missing dependency?): {e}") from e
    except Exception as e:
        raise PipelineError(f"EPUB build failed: {e}") from e

    return document, epub_path
