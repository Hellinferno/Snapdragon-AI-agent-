from app.services.chunker import chunk_pages
from app.services.pdf_parser import ParsedPage


def test_chunking_preserves_page_numbers():
    pages = [
        ParsedPage(page_number=1, text="This is page one content explaining neural networks."),
        ParsedPage(page_number=2, text="This is page two content detailing on-device inference."),
        ParsedPage(page_number=3, text="This is page three with conclusions and future research."),
    ]

    chunks = chunk_pages(pages, chunk_size=100, chunk_overlap=20)
    assert len(chunks) == 3
    assert chunks[0].page_number == 1
    assert "page one" in chunks[0].text
    assert chunks[1].page_number == 2
    assert "page two" in chunks[1].text
    assert chunks[2].page_number == 3
    assert "page three" in chunks[2].text


def test_chunking_section_detection():
    pages = [
        ParsedPage(
            page_number=1,
            text="Abstract\nThis paper introduces an on-device architecture for private research.",
        ),
        ParsedPage(
            page_number=2,
            text="Methodology\nWe evaluate document parsing and local retrieval latency.",
        ),
    ]

    chunks = chunk_pages(pages, chunk_size=200, chunk_overlap=20)
    assert len(chunks) >= 2
    assert chunks[0].section is not None
    assert "Abstract" in chunks[0].section
    assert chunks[1].section is not None
    assert "Methodology" in chunks[1].section


def test_chunking_empty_pages_ignored():
    pages = [
        ParsedPage(page_number=1, text=""),
        ParsedPage(page_number=2, text="   \n   "),
        ParsedPage(page_number=3, text="Valid content here."),
    ]

    chunks = chunk_pages(pages, chunk_size=200, chunk_overlap=20)
    assert len(chunks) == 1
    assert chunks[0].page_number == 3
    assert chunks[0].text == "Valid content here."


def test_chunking_long_paragraph_splits_with_overlap():
    long_text = "Word " * 200  # ~1000 chars
    pages = [ParsedPage(page_number=1, text=long_text)]

    chunks = chunk_pages(pages, chunk_size=300, chunk_overlap=50)
    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.page_number == 1
        assert len(chunk.text) <= 350
