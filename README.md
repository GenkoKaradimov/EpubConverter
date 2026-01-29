# EpubConverter

Convert PDF to EPUB with user editing support. The GUI is built with **Tkinter**.

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
