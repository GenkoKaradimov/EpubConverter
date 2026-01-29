# EpubConverter

Convert PDF to EPUB with user editing support. The GUI is built with **Tkinter**.

## Requirements

- Python 3.10+
- **PyMuPDF** (pip package name: `PyMuPDF`) – PDF extraction
- **ebooklib** – EPUB building

Install dependencies:

```bash
pip install -r requirements.txt
```

(If `pymupdf` fails to install, try `pip install PyMuPDF` with capital letters.)

## How to run

From the project root, set `PYTHONPATH` to `src` and run the main module:

```bash
# Windows (PowerShell)
$env:PYTHONPATH = "src"; python -m main

# Windows (cmd)
set PYTHONPATH=src && python -m main

# Linux / macOS
PYTHONPATH=src python -m main
```

Or run the script directly:

```bash
PYTHONPATH=src python src/main.py
```

## Usage

1. **Open PDF** – File → Open PDF… (or start by selecting a PDF).
2. **Extract** – Click “Extract” to parse the PDF into chapters and paragraphs. The editor opens with the extracted document.
3. **Edit** – Change text, add/remove/move chapters and paragraphs. Use “Apply” to save the current block to the document.
4. **Export EPUB** – File → Export EPUB… or click “Export to EPUB” in the editor. Choose a save location; the current document is written as a valid EPUB.
5. **Preview EPUB** – File → Preview EPUB opens the last exported EPUB in the system default reader (if available).

## Project structure

```
EpubConverter/
├── src/
│   ├── __init__.py
│   ├── main.py                    # Entry point; starts the application
│   │
│   ├── app/                       # Application core
│   │   ├── __init__.py
│   │   ├── application.py        # Main Application class – coordination, lifecycle
│   │   └── config.py             # Configuration (paths, settings)
│   │
│   ├── core/                      # Conversion business logic
│   │   ├── __init__.py
│   │   ├── converters/
│   │   │   ├── __init__.py
│   │   │   ├── base.py            # Abstract base converter (interface)
│   │   │   ├── pdf_extractor.py  # Extract text/structure from PDF
│   │   │   └── epub_builder.py   # Build EPUB from document data
│   │   ├── models/               # Domain models (non-UI)
│   │   │   ├── __init__.py
│   │   │   ├── document.py       # Document representation (chapters, paragraphs, metadata)
│   │   │   └── book_metadata.py  # Title, author, language, etc.
│   │   └── pipeline.py           # Orchestration: PDF → model → edit → EPUB
│   │
│   ├── gui/                       # Tkinter layer
│   │   ├── __init__.py
│   │   ├── main_window.py        # Main window, menus, layout
│   │   ├── views/                # Screens/panels
│   │   │   ├── __init__.py
│   │   │   ├── conversion_view.py   # File picker, options, start conversion
│   │   │   ├── editor_view.py       # Editor for extracted text/structure
│   │   │   └── preview_view.py      # (Optional) result preview
│   │   ├── widgets/              # Reusable GUI components
│   │   │   ├── __init__.py
│   │   │   └── ...
│   │   └── presenters.py         # Bind GUI ↔ core (or separate presenter modules)
│   │
│   └── services/                 # External services (future: OCR, models)
│       ├── __init__.py
│       ├── pdf_service.py        # Wrapper around PDF library (e.g. PyMuPDF, pdfplumber)
│       └── (future: ocr_service.py, model_service.py – stubs)
│
├── tests/
│   ├── __init__.py
│   ├── unit/
│   └── integration/
│
├── requirements.txt
├── README.md
└── .gitignore
```

### Design notes

- **Layered separation**: `core` has no dependency on Tkinter; `gui` calls `core` (converters, pipeline, models). A CLI or other UI could be added later.
- **Interfaces in `core`**: `base.py` defines the converter contract; new formats or steps (e.g. OCR as an extra converter or pipeline step) can be added without breaking existing code.
- **Domain models in `core/models`**: a single document/book model (chapters, paragraphs, metadata) is used for PDF extraction, editing, and EPUB output.
- **Pipeline**: one component orchestrates extract → populate model → (optional) user edit → EPUB build. OCR or model-based steps can be added as optional pipeline stages.
- **`services/`**: holds wrappers for external libraries (PDF, and later OCR/APIs). The rest of the code depends on abstractions for easier testing and extension.
