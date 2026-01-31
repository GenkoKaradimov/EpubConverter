"""
Extract Document from EPUB using ebooklib: metadata, spine-ordered content, HTML parsing.
Fallback: parse container.xml + package.opf from ZIP or directory (e.g. pdf2epub / unzipped).
All code and comments in English. Supports images when images_dir is provided.
"""

from __future__ import annotations

import html.parser
import posixpath
import zipfile
from pathlib import Path
from typing import Any
from urllib.parse import unquote
import xml.etree.ElementTree as ET

from core.converters.base import BaseExtractor
from core.models.book_metadata import BookMetadata
from core.models.document import ContentItem, ContentNode, Document, ImageNode

try:
    import ebooklib
    from ebooklib import epub
except ImportError:
    ebooklib = None  # type: ignore[assignment]
    epub = None  # type: ignore[assignment]

try:
    from app.config import DEFAULT_LANGUAGE
except ImportError:
    DEFAULT_LANGUAGE = "en"

# Parsed block: (level, text) for text, or ("img", href, alt) for image
_HtmlBlock = tuple[int, str] | tuple[str, str, str | None]


def _first_metadata(book: Any, namespace: str, key: str) -> str | None:
    """Return first metadata value for (namespace, key) or None."""
    if epub is None:
        return None
    values = book.get_metadata(namespace, key)
    if not values or not isinstance(values, list):
        return None
    for v in values:
        if isinstance(v, (list, tuple)) and len(v) >= 1 and v[0]:
            return str(v[0]).strip()
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def _epub_metadata_to_book_metadata(book: Any) -> BookMetadata:
    """Build BookMetadata from EPUB Dublin Core and other metadata."""
    title = _first_metadata(book, "DC", "title") or "Untitled"
    language = _first_metadata(book, "DC", "language") or DEFAULT_LANGUAGE
    authors: list[str] = []
    creators = book.get_metadata("DC", "creator")
    if isinstance(creators, list):
        for c in creators:
            if isinstance(c, (list, tuple)) and len(c) >= 1 and c[0]:
                authors.append(str(c[0]).strip())
            elif isinstance(c, str) and c.strip():
                authors.append(c.strip())
    publisher = _first_metadata(book, "DC", "publisher")
    identifiers: dict[str, str] = {}
    idents = book.get_metadata("DC", "identifier")
    if isinstance(idents, list):
        for i in idents:
            if isinstance(i, (list, tuple)) and len(i) >= 1 and i[0]:
                val = str(i[0]).strip()
                # optional: use id from attrs if present
                attrs = i[1] if len(i) > 1 and isinstance(i[1], dict) else {}
                key = attrs.get("id", "identifier")
                identifiers[key] = val
            elif isinstance(i, str) and i.strip():
                identifiers["identifier"] = i.strip()
    return BookMetadata(
        title=title,
        language=language,
        authors=authors or None,
        publisher=publisher,
        identifiers=identifiers or None,
    )


class _HtmlContentParser(html.parser.HTMLParser):
    """Collect (level, text) for h1/h2/h3/p and ("img", src, alt) for img tags."""

    BLOCK_TAGS = {"h1", "h2", "h3", "p", "div", "section"}

    def __init__(self) -> None:
        super().__init__()
        self._blocks: list[_HtmlBlock] = []
        self._current_level: int | None = None
        self._current_text: list[str] = []

    @property
    def blocks(self) -> list[_HtmlBlock]:
        return self._blocks

    def _flush(self) -> None:
        if self._current_level is not None and self._current_text:
            text = " ".join(" ".join(self._current_text).split())
            if text:
                self._blocks.append((self._current_level, text))
        self._current_level = None
        self._current_text = []

    def _attr_dict(self, attrs: list[tuple[str, str | None]]) -> dict[str, str]:
        return {k.lower(): (v or "").strip() for k, v in attrs if v is not None}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag == "img":
            self._flush()
            ad = self._attr_dict(attrs)
            src = ad.get("src", "").strip()
            alt = ad.get("alt", "").strip() or None
            if src:
                self._blocks.append(("img", src, alt))
            return
        if tag == "h1":
            self._flush()
            self._current_level = 1
            self._current_text = []
        elif tag == "h2":
            self._flush()
            self._current_level = 2
            self._current_text = []
        elif tag == "h3":
            self._flush()
            self._current_level = 3
            self._current_text = []
        elif tag == "p":
            self._flush()
            self._current_level = 0
            self._current_text = []
        elif tag in ("div", "section") and self._current_level is None:
            self._current_level = 0
            self._current_text = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self.BLOCK_TAGS:
            self._flush()

    def handle_data(self, data: str) -> None:
        if self._current_level is not None and data:
            self._current_text.append(data)


def _html_to_blocks(html_bytes: bytes) -> list[_HtmlBlock]:
    """Parse HTML body and return flat list of (level, text) or ('img', href, alt)."""
    try:
        html_str = html_bytes.decode("utf-8", errors="replace")
    except Exception:
        return []
    parser = _HtmlContentParser()
    try:
        parser.feed(html_str)
    except Exception:
        return []
    return parser.blocks


def _build_href_to_image_item(book: Any) -> dict[str, Any]:
    """Build map from normalized href / basename to image item for resolving img src."""
    if ebooklib is None:
        return {}
    href_to_item: dict[str, Any] = {}
    for item in book.get_items():
        if item.get_type() != ebooklib.ITEM_IMAGE:
            continue
        name = getattr(item, "file_name", None) or getattr(item, "fileName", "")
        if not name:
            continue
        name = name.replace("\\", "/")
        norm = posixpath.normpath(name)
        href_to_item[norm] = item
        base = posixpath.basename(norm)
        if base not in href_to_item:
            href_to_item[base] = item
    return href_to_item


def _extract_nodes_from_epub(
    book: Any,
    images_dir: Path | None,
) -> tuple[list[ContentItem], dict[str, Path]]:
    """Extract ContentNodes and ImageNodes in spine order; write images to images_dir if provided."""
    if ebooklib is None or epub is None:
        return [], {}
    all_nodes: list[ContentItem] = []
    images: dict[str, Path] = {}
    p_global = 0
    ch_global = 0
    img_global = 0
    href_to_item = _build_href_to_image_item(book) if images_dir is not None else {}
    if images_dir is not None:
        images_dir.mkdir(parents=True, exist_ok=True)

    spine = getattr(book, "spine", None) or []
    for entry in spine:
        item_id = entry[0] if isinstance(entry, (list, tuple)) else entry
        if isinstance(item_id, tuple):
            item_id = item_id[0] if item_id else ""
        item_id = str(item_id).strip()
        if not item_id or item_id.lower() == "nav":
            continue
        item = book.get_item_with_id(item_id)
        if item is None:
            continue
        if item.get_type() != ebooklib.ITEM_DOCUMENT:
            continue
        try:
            raw = item.get_content()
        except Exception:
            continue
        if not raw:
            continue
        doc_base = ""
        fn = getattr(item, "file_name", None) or getattr(item, "fileName", "")
        if fn:
            doc_base = posixpath.dirname(fn.replace("\\", "/"))
        blocks = _html_to_blocks(raw)
        for blk in blocks:
            if isinstance(blk[0], int):
                level, text = blk[0], blk[1]
                text_clean = text.strip()
                if not text_clean:
                    continue
                if level >= 1:
                    all_nodes.append(
                        ContentNode(id=f"ch_{ch_global}", text=text_clean, level=level)
                    )
                    ch_global += 1
                else:
                    all_nodes.append(
                        ContentNode(id=f"p_{p_global}", text=text_clean, level=0)
                    )
                    p_global += 1
            elif blk[0] == "img":
                _, href, alt = blk[0], blk[1], blk[2]
                if not href:
                    continue
                resolved = posixpath.normpath(
                    posixpath.join(doc_base, unquote(href).replace("\\", "/"))
                )
                img_item = href_to_item.get(resolved) or href_to_item.get(
                    posixpath.basename(resolved)
                )
                if img_item is None and images_dir is not None:
                    continue
                if img_item is not None and images_dir is not None:
                    try:
                        content = img_item.get_content()
                    except Exception:
                        content = None
                    if content and isinstance(content, bytes):
                        image_id = f"img_{img_global}"
                        img_global += 1
                        ext = _guess_image_ext(content)
                        file_path = images_dir / f"{image_id}{ext}"
                        file_path.write_bytes(content)
                        images[image_id] = file_path
                        node_id = f"img_node_{img_global - 1}"
                        all_nodes.append(ImageNode(id=node_id, image_id=image_id, alt=alt))
    return all_nodes, images


def _guess_image_ext(data: bytes) -> str:
    """Return file extension from image magic bytes."""
    if data.startswith(b"\x89PNG"):
        return ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return ".gif"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return ".webp"
    return ".png"


# --- Fallback extraction (ZIP or directory) for pdf2epub / non-ebooklib EPUBs ---

CONTAINER_NS = "urn:oasis:names:tc:opendocument:xmlns:container"
OPF_NS = "http://www.idpf.org/2007/opf"
DC_NS = "http://purl.org/dc/elements/1.1/"


def _parse_container_rootfile(container_xml_bytes: bytes) -> str:
    """Parse META-INF/container.xml and return first rootfile full-path (e.g. OPS/package.opf)."""
    root = ET.fromstring(container_xml_bytes)
    # rootfiles is in CONTAINER_NS
    rootfiles = root.find(f".//{{{CONTAINER_NS}}}rootfiles")
    if rootfiles is None:
        raise ValueError("container.xml: no rootfiles")
    rootfile = rootfiles.find(f"{{{CONTAINER_NS}}}rootfile")
    if rootfile is None:
        raise ValueError("container.xml: no rootfile")
    full_path = rootfile.get("full-path")
    if not full_path or not full_path.strip():
        raise ValueError("container.xml: rootfile missing full-path")
    return full_path.strip().replace("\\", "/")


def _parse_opf(opf_xml_bytes: bytes) -> tuple[dict[str, tuple[str, str]], list[str], dict[str, str]]:
    """
    Parse package.opf. Return (manifest, spine_ids, metadata).
    manifest: id -> (href, media_type)
    spine_ids: ordered list of item idrefs (content documents only, skip nav).
    metadata: title, language, authors (joined), publisher, identifier.
    """
    root = ET.fromstring(opf_xml_bytes)
    manifest: dict[str, tuple[str, str]] = {}
    for item in root.findall(".//{%s}item" % OPF_NS):
        item_id = item.get("id")
        href = item.get("href")
        media_type = (item.get("media-type") or "").strip()
        if item_id and href:
            manifest[item_id.strip()] = (href.replace("\\", "/"), media_type)

    spine_ids: list[str] = []
    spine = root.find(".//{%s}spine" % OPF_NS)
    if spine is not None:
        for itemref in spine.findall("{%s}itemref" % OPF_NS):
            idref = (itemref.get("idref") or "").strip()
            if idref and idref.lower() != "nav":
                spine_ids.append(idref)

    meta: dict[str, str] = {}
    # DC elements may have no namespace or dc namespace
    for tag, key in [
        ("{%s}title" % DC_NS, "title"),
        ("{%s}title" % "http://purl.org/dc/elements/1.1/", "title"),
        ("title", "title"),
        ("{%s}language" % DC_NS, "language"),
        ("{%s}language" % "http://purl.org/dc/elements/1.1/", "language"),
        ("language", "language"),
        ("{%s}publisher" % DC_NS, "publisher"),
        ("{%s}publisher" % "http://purl.org/dc/elements/1.1/", "publisher"),
        ("publisher", "publisher"),
        ("{%s}identifier" % DC_NS, "identifier"),
        ("{%s}identifier" % "http://purl.org/dc/elements/1.1/", "identifier"),
        ("identifier", "identifier"),
    ]:
        el = root.find(f".//{tag}")
        if el is not None and el.text and key not in meta:
            meta[key] = (el.text or "").strip()
    authors: list[str] = []
    for creator in root.findall(".//{%s}creator" % DC_NS):
        if creator is not None and creator.text and (creator.text or "").strip():
            authors.append((creator.text or "").strip())
    if authors:
        meta["authors"] = "|".join(authors)

    return manifest, spine_ids, meta


def _opf_metadata_to_book_metadata(meta: dict[str, str]) -> BookMetadata:
    """Build BookMetadata from OPF metadata dict (from _parse_opf)."""
    title = (meta.get("title") or "").strip() or "Untitled"
    language = (meta.get("language") or "").strip() or DEFAULT_LANGUAGE
    authors_str = meta.get("authors") or ""
    authors = [a.strip() for a in authors_str.split("|") if a.strip()] if authors_str else []
    publisher = (meta.get("publisher") or "").strip() or None
    ident = (meta.get("identifier") or "").strip()
    identifiers = {"identifier": ident} if ident else {}
    return BookMetadata(
        title=title,
        language=language,
        authors=authors if authors else None,
        publisher=publisher,
        identifiers=identifiers if identifiers else None,
    )


def _is_xhtml_media_type(media_type: str) -> bool:
    return "html" in media_type.lower() or "xhtml" in media_type.lower()


def _is_image_media_type(media_type: str) -> bool:
    return media_type.lower().startswith("image/")


def _nodes_from_opf(
    manifest: dict[str, tuple[str, str]],
    spine_ids: list[str],
    opf_dir: str,
    read_file: Any,
    images_dir: Path | None,
) -> tuple[list[ContentItem], dict[str, Path]]:
    """
    Build ContentItem list and images dict from OPF manifest/spine by reading HTML via read_file(href).
    read_file(href) returns bytes for path opf_dir/href. images_dir used to write image files.
    """
    all_nodes: list[ContentItem] = []
    images: dict[str, Path] = {}
    p_global = 0
    ch_global = 0
    img_global = 0

    # Map normalized href and basename -> manifest id for images (for resolving img src)
    image_href_to_id: dict[str, str] = {}
    for item_id, (href, mt) in manifest.items():
        if _is_image_media_type(mt):
            norm = posixpath.normpath(posixpath.join(opf_dir, href))
            image_href_to_id[norm] = item_id
            image_href_to_id[posixpath.basename(norm)] = item_id

    if images_dir is not None:
        images_dir.mkdir(parents=True, exist_ok=True)

    for item_id in spine_ids:
        entry = manifest.get(item_id)
        if not entry:
            continue
        href, media_type = entry
        if not _is_xhtml_media_type(media_type):
            continue
        full_ref = posixpath.normpath(posixpath.join(opf_dir, href))
        try:
            raw = read_file(full_ref)
        except Exception:
            continue
        if not raw:
            continue
        doc_base = posixpath.dirname(full_ref)
        blocks = _html_to_blocks(raw)
        for blk in blocks:
            if isinstance(blk[0], int):
                level, text = blk[0], blk[1]
                text_clean = text.strip()
                if not text_clean:
                    continue
                if level >= 1:
                    all_nodes.append(
                        ContentNode(id=f"ch_{ch_global}", text=text_clean, level=level)
                    )
                    ch_global += 1
                else:
                    all_nodes.append(
                        ContentNode(id=f"p_{p_global}", text=text_clean, level=0)
                    )
                    p_global += 1
            elif blk[0] == "img":
                _, img_href, alt = blk[0], blk[1], blk[2]
                if not img_href:
                    continue
                resolved = posixpath.normpath(
                    posixpath.join(doc_base, unquote(img_href).replace("\\", "/"))
                )
                # Resolve image: by full path or basename
                image_id_key = image_href_to_id.get(resolved) or image_href_to_id.get(
                    posixpath.basename(resolved)
                )
                if not image_id_key or images_dir is None:
                    continue
                img_entry = manifest.get(image_id_key)
                if not img_entry:
                    continue
                img_href_path = posixpath.normpath(posixpath.join(opf_dir, img_entry[0]))
                try:
                    content = read_file(img_href_path)
                except Exception:
                    continue
                if not content or not isinstance(content, bytes):
                    continue
                ext = _guess_image_ext(content)
                image_id = f"img_{img_global}"
                img_global += 1
                file_path = images_dir / f"{image_id}{ext}"
                file_path.write_bytes(content)
                images[image_id] = file_path
                node_id = f"img_node_{img_global - 1}"
                all_nodes.append(ImageNode(id=node_id, image_id=image_id, alt=alt))
    return all_nodes, images


def _extract_from_directory(root_dir: Path, images_dir: Path | None) -> Document:
    """Extract Document from an unzipped EPUB directory (mimetype, META-INF, OPS/...)."""

    container_path = root_dir / "META-INF" / "container.xml"
    if not container_path.is_file():
        raise RuntimeError(f"Not an unzipped EPUB: missing {container_path}")
    container_xml = container_path.read_bytes()
    opf_rel_path = _parse_container_rootfile(container_xml)
    opf_path = root_dir / opf_rel_path
    if not opf_path.is_file():
        raise RuntimeError(f"OPF not found: {opf_path}")
    opf_xml = opf_path.read_bytes()
    manifest, spine_ids, meta = _parse_opf(opf_xml)
    opf_dir_str = opf_rel_path.replace("\\", "/")
    if "/" in opf_dir_str:
        opf_dir_str = posixpath.dirname(opf_dir_str)
    else:
        opf_dir_str = ""

    def read_file(href_or_path: str) -> bytes:
        # href_or_path is path inside root_dir (e.g. OPS/s00000-beta.xhtml)
        full = root_dir / href_or_path
        if not full.is_file():
            raise FileNotFoundError(str(full))
        return full.read_bytes()

    root_nodes, images = _nodes_from_opf(
        manifest, spine_ids, opf_dir_str, read_file, images_dir
    )
    metadata = _opf_metadata_to_book_metadata(meta)
    return Document(metadata=metadata, root_nodes=root_nodes, images=images)


def _extract_from_zip(zip_path: Path, images_dir: Path | None) -> Document:
    """Extract Document from EPUB ZIP when ebooklib fails (e.g. mimetype compressed)."""

    with zipfile.ZipFile(zip_path, "r") as zf:
        try:
            container_xml = zf.read("META-INF/container.xml")
        except KeyError:
            raise RuntimeError("Invalid EPUB: no META-INF/container.xml in archive") from None
        opf_rel_path = _parse_container_rootfile(container_xml)
        try:
            opf_xml = zf.read(opf_rel_path)
        except KeyError:
            raise RuntimeError(f"Invalid EPUB: OPF not in archive: {opf_rel_path}") from None
        manifest, spine_ids, meta = _parse_opf(opf_xml)
        opf_dir_str = opf_rel_path.replace("\\", "/")
        if "/" in opf_dir_str:
            opf_dir_str = posixpath.dirname(opf_dir_str)
        else:
            opf_dir_str = ""

        def read_file(member_path: str) -> bytes:
            # member_path is path inside zip (e.g. OPS/s00000-beta.xhtml)
            normalized = member_path.replace("\\", "/")
            try:
                return zf.read(normalized)
            except KeyError:
                raise FileNotFoundError(normalized) from None

        root_nodes, images = _nodes_from_opf(
            manifest, spine_ids, opf_dir_str, read_file, images_dir
        )
    metadata = _opf_metadata_to_book_metadata(meta)
    return Document(metadata=metadata, root_nodes=root_nodes, images=images)


class EpubExtractor(BaseExtractor):
    """Extract a Document from an EPUB file or unzipped folder. Uses ebooklib first; fallback to ZIP/directory parsing for pdf2epub-style EPUBs."""

    def extract(self, path: Path | str, images_dir: Path | str | None = None) -> Document:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"EPUB not found: {path}")
        idir = Path(images_dir) if images_dir is not None else None

        if path.is_dir():
            return _extract_from_directory(path, idir)

        if epub is None:
            raise RuntimeError("ebooklib is not installed; install with: pip install ebooklib")
        try:
            book = epub.read_epub(str(path))
        except FileNotFoundError:
            raise
        except Exception:
            try:
                return _extract_from_zip(path, idir)
            except Exception as e:
                raise RuntimeError(f"Failed to read EPUB (ebooklib and fallback failed): {e}") from e
        metadata = _epub_metadata_to_book_metadata(book)
        root_nodes, images = _extract_nodes_from_epub(book, idir)
        return Document(metadata=metadata, root_nodes=root_nodes, images=images)
