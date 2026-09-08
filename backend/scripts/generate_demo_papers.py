"""
Generates 3 synthetic academic papers for ScholarEdge demonstration and benchmarking.
"""
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def create_demo_pdf(output_path: Path, title: str, author: str, pages_content: list[str]):
    c = canvas.Canvas(str(output_path), pagesize=letter)
    c.setTitle(title)
    c.setAuthor(author)

    for content in pages_content:
        lines = content.split("\n")
        y = 720
        # Title/header
        c.setFont("Helvetica-Bold", 14)
        c.drawString(72, y, lines[0])
        y -= 25

        c.setFont("Helvetica", 10)
        for line in lines[1:]:
            # Simple text wrap
            words = line.split(" ")
            current_line = ""
            for word in words:
                if len(current_line) + len(word) + 1 > 80:
                    c.drawString(72, y, current_line)
                    y -= 14
                    current_line = word
                else:
                    current_line = f"{current_line} {word}".strip()
            if current_line:
                c.drawString(72, y, current_line)
                y -= 14
            y -= 6
        c.showPage()

    c.save()
    print(f"Generated demo paper: {output_path.name}")


def main():
    demo_dir = Path(__file__).resolve().parent.parent / "data" / "demo_papers"
    demo_dir.mkdir(parents=True, exist_ok=True)

    paper_1 = [
        "Abstract\nInvestigates multimodal vision-language transformers for chest radiograph lesion localization and pneumonia detection. Demonstrates on-device edge inference to protect protected health information (PHI) under strict HIPAA regulations without external cloud transmission.",
        "Introduction\nHospital diagnostic workflows require automated radiograph triage without transmitting sensitive diagnostic imaging over insecure external networks. Local inference on edge clinical workstations ensures absolute data residency.",
        "Methodology & Architecture\nEvaluated a cross-attention vision-language backbone trained on multi-view chest X-rays. Document chunks and diagnostic bounding boxes preserve exact study slice and radiological report indices for verifiable provenance.",
        "Key Findings & Metrics\nAchieved 91.4% AUC on pneumonia detection and reduced diagnostic report latency to 420 ms per radiograph with zero cloud leakage of patient telemetry.",
        "Limitations & Future Work\nLimited generalization on low-dose portable bedside radiography units and pediatric cohorts under 12 years old. Multi-center validation remains ongoing.",
    ]

    paper_2 = [
        "Abstract\nExplores quantized 4-bit transformer deployment on clinical workstations for automated patient history summarization and discharge note generation. Strict source citations guarantee verifiable provenance.",
        "Introduction\nCentralized cloud clinical LLMs present unacceptable privacy risks for protected patient records and clinical trial dossiers. Local execution prevents proprietary health information from crossing hospital perimeter firewalls.",
        "Methodology & Architecture\nImplemented 4-bit INT4 quantization paired with strict page-level citation tracking. Every clinical summary sentence must map to an indexed patient encounter or laboratory report.",
        "Key Findings & Metrics\nAchieved 94.2% citation precision across 200 clinical summaries, eliminating hallucinated contraindications and reducing factual errors to 1.8%.",
        "Limitations & Future Work\nRequires minimum 8 GB memory on physician edge workstations. Complex multi-specialty surgical notes require further clinical annotation and domain adaptation.",
    ]

    paper_3 = [
        "Abstract\nAssesses the efficacy of automated clinical vignette synthesis, active-recall flashcards, and multiple-choice formative quizzes for medical resident training using local retrieval.",
        "Introduction\nMedical students face cognitive overload when synthesizing dense clinical practice guidelines and pharmacological trial reports. Interactive formative testing fosters deeper diagnostic retention.",
        "Methodology & Architecture\nOur system constructs case-grounded multiple-choice questions from peer-reviewed clinical guidelines, dynamically generating distractors from neighboring diagnostic differential categories.",
        "Key Findings & Metrics\nDouble-blind study across 60 medical residents showed a 34% improvement in 30-day clinical guideline retention scores compared to passive textbook review.",
        "Limitations & Future Work\nRelies on high-quality guideline indexing; rare genetic pathology differentials remain undersampled in the training distribution.",
    ]

    create_demo_pdf(demo_dir / "paper_1_clinical_multimodal_radiology.pdf", "Clinical Multimodal Transformers for Diagnostic Radiology", "Dr. Elena Vance, MD, PhD", paper_1)
    create_demo_pdf(demo_dir / "paper_2_privacy_preserving_clinical_lm.pdf", "Privacy-Preserving On-Device Clinical Language Models", "Prof. Marcus Thorne, MD", paper_2)
    create_demo_pdf(demo_dir / "paper_3_medical_education_active_recall.pdf", "Formative Assessment and Active Recall in Medical Education", "Dr. Sarah Lin, MD", paper_3)
    print("All Medical-AI demo papers successfully generated in data/demo_papers/")


if __name__ == "__main__":
    main()
