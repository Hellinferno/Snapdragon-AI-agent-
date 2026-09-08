import re
from dataclasses import dataclass
from app.services.pdf_parser import ParsedPage


@dataclass
class GeneratedChunk:
    page_number: int
    chunk_index: int
    text: str
    section: str | None = None


# Pattern for common academic section headers
SECTION_HEADER_PATTERN = re.compile(
    r"^(?:\d+\.?\s+)?(abstract|introduction|background|related\s+work|method(?:ology)?|materials\s+and\s+methods|system\s+design|architecture|experiments?|results|discussion|conclusion(?:s)?|references)\b",
    re.IGNORECASE,
)


def _detect_section(text: str, current_section: str | None) -> str | None:
    """Detects section heading from lines in the text."""
    for line in text.splitlines():
        clean_line = line.strip()
        match = SECTION_HEADER_PATTERN.match(clean_line)
        if match:
            return match.group(0).strip().title()
    return current_section


def chunk_pages(
    pages: list[ParsedPage],
    chunk_size: int = 600,
    chunk_overlap: int = 100,
) -> list[GeneratedChunk]:
    """
    Splits pages into source-traceable chunks.
    Guarantees that each chunk retains its exact origin page number and section.
    """
    chunks: list[GeneratedChunk] = []
    global_chunk_index = 0
    current_section: str | None = None

    for page in pages:
        page_text = page.text.strip()
        if not page_text:
            continue

        # Check for section header on this page
        current_section = _detect_section(page_text, current_section)

        # Split text into paragraphs first to avoid awkward breaks
        paragraphs = [p.strip() for p in page_text.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [page_text]

        buffer = ""
        for para in paragraphs:
            # Check if this paragraph contains a new section header
            current_section = _detect_section(para, current_section)

            if len(buffer) + len(para) + 1 <= chunk_size:
                buffer = f"{buffer}\n\n{para}" if buffer else para
            else:
                # Flush current buffer if non-empty
                if buffer:
                    chunks.append(
                        GeneratedChunk(
                            page_number=page.page_number,
                            chunk_index=global_chunk_index,
                            text=buffer.strip(),
                            section=current_section,
                        )
                    )
                    global_chunk_index += 1

                # If the single paragraph is larger than chunk_size, split by sliding window
                if len(para) > chunk_size:
                    start = 0
                    while start < len(para):
                        end = min(start + chunk_size, len(para))
                        slice_text = para[start:end].strip()
                        if slice_text:
                            chunks.append(
                                GeneratedChunk(
                                    page_number=page.page_number,
                                    chunk_index=global_chunk_index,
                                    text=slice_text,
                                    section=current_section,
                                )
                            )
                            global_chunk_index += 1
                        if end >= len(para):
                            break
                        start += max(1, chunk_size - chunk_overlap)
                    buffer = ""
                else:
                    # Keep overlap if possible from previous buffer
                    if buffer and chunk_overlap > 0:
                        overlap_text = buffer[-chunk_overlap:]
                        buffer = f"{overlap_text}\n\n{para}"
                    else:
                        buffer = para

        # Flush any remaining buffer on this page
        if buffer:
            chunks.append(
                GeneratedChunk(
                    page_number=page.page_number,
                    chunk_index=global_chunk_index,
                    text=buffer.strip(),
                    section=current_section,
                )
            )
            global_chunk_index += 1

    return chunks
