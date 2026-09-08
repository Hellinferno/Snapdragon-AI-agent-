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
    demo_dir = settings.BASE_DIR / "data" / "demo_papers"
    if not demo_dir.exists() or len(list(demo_dir.glob("*.pdf"))) < 3:
        generate_demo_papers_script()

    doc_service = DocumentService(db)
    seeded_docs = 0

    paper_metadata = [
        {
            "filename": "paper_1_on_device_npu_ai.pdf",
            "title": "On-Device Neural Acceleration for Private Document Copilots",
            "authors": "Dr. Sarah Chen, Michael Vance (2025)",
        },
        {
            "filename": "paper_2_source_traceable_rag.pdf",
            "title": "Comparative Retrieval-Augmented Generation with Verifiable Citations",
            "authors": "Elena Rostova, Dr. Kenji Sato (2025)",
        },
        {
            "filename": "paper_3_active_recall_learning.pdf",
            "title": "Active-Recall Learning Systems: Pedagogical Synthesis of Complex Text",
            "authors": "Marcus Brody, Alicia Gomez (2024)",
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
    try:
        raw_bytes = fig_path.read_bytes()
        fig_record = await vision_service.save_raw_image(raw_bytes, fig_path.name)
        await vision_service.analyze_figure(fig_record.image_id)
        seeded_figures = 1
    except Exception as e:
        logger.warning("Could not seed demo figure: %s", e)

    return {
        "success": True,
        "message": f"Seeded {seeded_docs} demo research papers and {seeded_figures} architecture diagram.",
        "documents_seeded": seeded_docs,
        "figures_seeded": seeded_figures,
    }
