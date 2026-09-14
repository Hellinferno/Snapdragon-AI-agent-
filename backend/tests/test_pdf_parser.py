import tempfile
from pathlib import Path
import pytest
from pypdf import PageObject, PdfWriter

from app.services.pdf_parser import parse_pdf


def create_sample_pdf(file_path: Path, pages_text: list[str]) -> None:
    """Creates a basic valid PDF file with synthetic pages for testing."""
    writer = PdfWriter()
    for text in pages_text:
        # Create a blank page and add text annotation or content
        page = PageObject.create_blank_page(width=612, height=792)
        writer.add_page(page)

    writer.add_metadata({
        "/Title": "ScholarEdge Test Document",
        "/Author": "Research Team",
    })

    with open(file_path, "wb") as f:
        writer.write(f)


def test_pdf_parser_metadata_and_pages():
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        create_sample_pdf(tmp_path, ["Page 1", "Page 2", "Page 3"])
        parsed = parse_pdf(tmp_path)

        assert parsed.page_count == 3
        assert len(parsed.pages) == 3
        assert parsed.pages[0].page_number == 1
        assert parsed.pages[1].page_number == 2
        assert parsed.pages[2].page_number == 3
        assert parsed.title == "ScholarEdge Test Document"
        assert parsed.authors == "Research Team"
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def test_pdf_parser_nonexistent_file():
    with pytest.raises(FileNotFoundError):
        parse_pdf("non_existent_file_xyz.pdf")


def test_clean_extracted_text_repairs_surrogates():
    from app.services.pdf_parser import clean_extracted_text

    # Surrogate pair for U+1D465 (mathematical italic x), as pypdf emits it
    assert clean_extracted_text("f(𝑥) = 1") == "f(\U0001d465) = 1"
    # Lone surrogate becomes the replacement character and is UTF-8 encodable
    cleaned = clean_extracted_text("broken \ud835 glyph")
    assert cleaned == "broken � glyph"
    cleaned.encode("utf-8")
    assert clean_extracted_text("plain text") == "plain text"


def test_soft_hyphen_line_breaks_are_rejoined():
    from app.services.pdf_parser import SOFT_HYPHEN_BREAK

    text = "a super‐\nvised problem\nstrawberry Pop-\nTarts"
    assert SOFT_HYPHEN_BREAK.sub("", text) == "a supervised problem\nstrawberry Pop-\nTarts"
