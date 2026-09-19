"""One-click demo dataset seeding endpoint for quick evaluation."""

import io
from pathlib import Path
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from PIL import Image, ImageDraw

from app.core.database import get_db
from app.core.config import settings
from app.core.logging import get_logger
from app.services.document_service import DocumentService
from app.services.vision_service import vision_service
from scripts.generate_demo_papers import main as generate_demo_papers_script

logger = get_logger(__name__)
router = APIRouter(prefix="/documents", tags=["Demo Seeding"])


# The sha256-pinned demo papers (see evaluation/datasets/demo_papers.json) live
# here when present locally; PDFs are kept out of git.
PINNED_DEMO_CORPUS = settings.BASE_DIR / "evaluation" / "corpus" / "demo_papers"


def resolve_demo_corpus_dir() -> Path:
    """Return the directory holding the demo papers.

    Prefers the local sha256-pinned evaluation corpus. Where it is absent (a fresh
    clone: PDFs are not in git), this generates a copy into gitignored runtime
    storage, so seeding a demo never writes into tracked paths.
    """
    if len(list(PINNED_DEMO_CORPUS.glob("*.pdf"))) >= 3:
        return PINNED_DEMO_CORPUS

    generated = settings.BASE_DIR / "data" / "demo_papers"
    if len(list(generated.glob("*.pdf"))) < 3:
        generate_demo_papers_script()
    return generated


def ensure_demo_figure(output_path: Path) -> Path:
    """Generate a clean synthetic architecture diagram for vision evaluation if missing."""
    if output_path.exists():
        return output_path

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (800, 450), color=(15, 23, 42))
    draw = ImageDraw.Draw(img)

    # Draw diagram pipeline blocks
    # Block 1: Input Document
    draw.rectangle([60, 160, 240, 280], fill=(30, 41, 59), outline=(56, 189, 248), width=2)
    # Block 2: Vector Store & NPU Embeddings
    draw.rectangle([310, 160, 490, 280], fill=(30, 41, 59), outline=(16, 185, 129), width=2)
    # Block 3: Grounded Assistant & LLM
    draw.rectangle([560, 160, 740, 280], fill=(30, 41, 59), outline=(168, 85, 247), width=2)

    # Connector arrows
    draw.line([240, 220, 310, 220], fill=(148, 163, 184), width=3)
    draw.line([490, 220, 560, 220], fill=(148, 163, 184), width=3)

    img.save(output_path, format="PNG")
    return output_path


@router.post("/seed_demo")
async def seed_demo_dataset(db: AsyncSession = Depends(get_db)):
    """
    Seeds 3 academic research papers and 1 system architecture diagram.
    Allows evaluators to instantly test all 5 studios with 1 click.
    """
    demo_dir = resolve_demo_corpus_dir()

    doc_service = DocumentService(db)
    seeded_docs = 0

    paper_metadata = [
        {
            "filename": "paper_1_clinical_multimodal_radiology.pdf",
            "title": "Clinical Multimodal Transformers for Diagnostic Radiology",
            "authors": "Dr. Elena Vance, MD, PhD (2025)",
        },
        {
            "filename": "paper_2_privacy_preserving_clinical_lm.pdf",
            "title": "Privacy-Preserving On-Device Clinical Language Models",
            "authors": "Prof. Marcus Thorne, MD (2025)",
        },
        {
            "filename": "paper_3_medical_education_active_recall.pdf",
            "title": "Formative Assessment and Active Recall in Medical Education",
            "authors": "Dr. Sarah Lin, MD (2024)",
        },
    ]

    for item in paper_metadata:
        pdf_file = demo_dir / item["filename"]
        if pdf_file.exists():
            try:
                res = await doc_service.process_local_pdf(
                    pdf_path=pdf_file,
                    title=item["title"],
                    authors=item["authors"],
                )
                if res.status in ("INDEXED", "PROCESSING"):
                    seeded_docs += 1
            except Exception as e:
                logger.warning("Could not seed %s: %s", pdf_file.name, e)

    # Seed demo figure for Vision studio
    demo_fig_dir = settings.BASE_DIR / "data" / "demo_figures"
    fig_path = demo_fig_dir / "system_architecture_pipeline.png"
    ensure_demo_figure(fig_path)

    seeded_figures = 0
    demo_figure = None
    try:
        raw_bytes = fig_path.read_bytes()
        fig_record = await vision_service.save_raw_image(raw_bytes, fig_path.name)
        await vision_service.analyze_figure(fig_record.image_id)
        demo_figure = fig_record.model_dump()
        seeded_figures = 1
    except Exception as e:
        logger.warning("Could not seed demo figure: %s", e)

    return {
        "success": True,
        "message": (
            f"Demo library ready: {seeded_docs} research papers indexed"
            + (" and 1 architecture diagram available in Vision Studio." if seeded_figures else ".")
        ),
        "documents_seeded": seeded_docs,
        "figures_seeded": seeded_figures,
        # The seeded figure, so the UI can open it in the Vision studio.
        "demo_figure": demo_figure,
    }
