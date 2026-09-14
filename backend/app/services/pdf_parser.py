import re
from dataclasses import dataclass, field
from pathlib import Path
from pypdf import PdfReader
from app.core.logging import logger


@dataclass
class ParsedPage:
    page_number: int
    text: str
    ocr_used: bool = False


@dataclass
class ParsedPDF:
    title: str | None = None
    authors: str | None = None
    page_count: int = 0
    pages: list[ParsedPage] = field(default_factory=list)


SOFT_HYPHEN_BREAK = re.compile(r"(?<=\w)[‐­]\n(?=\w)")


def clean_extracted_text(text: str) -> str:
    """Repairs surrogate code points pypdf emits for astral glyphs (e.g. math symbols).

    Valid surrogate pairs are recombined; lone surrogates become U+FFFD. Without this,
    SQLite rejects the text with UnicodeEncodeError and the whole document fails to index.
    """
    return text.encode("utf-16", "surrogatepass").decode("utf-16", "replace")


def parse_pdf(file_path: Path | str) -> ParsedPDF:
    """
    Extracts text page-by-page from a PDF file.
    Preserves page boundaries and extracts basic metadata.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF file does not exist: {path.name}")

    reader = PdfReader(str(path))
    num_pages = len(reader.pages)

    title: str | None = None
    authors: str | None = None

    if reader.metadata:
        if reader.metadata.title:
            title = str(reader.metadata.title).strip() or None
        if reader.metadata.author:
            authors = str(reader.metadata.author).strip() or None

    parsed_pages: list[ParsedPage] = []

    for idx, page in enumerate(reader.pages):
        page_num = idx + 1
        page_text = clean_extracted_text(page.extract_text() or "")
        # Normalize whitespace while preserving line structure
        normalized_text = "\n".join(
            line.strip() for line in page_text.splitlines() if line.strip()
        )
        # Re-join words split by typeset soft hyphens at line ends ("super‐\nvised")
        normalized_text = SOFT_HYPHEN_BREAK.sub("", normalized_text)
        parsed_pages.append(
            ParsedPage(
                page_number=page_num,
                text=normalized_text,
                ocr_used=False,
            )
        )

    logger.info("Successfully extracted %d pages from %s", num_pages, path.name)
    return ParsedPDF(
        title=title,
        authors=authors,
        page_count=num_pages,
        pages=parsed_pages,
    )
