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
        "Abstract\nOn-device neural network execution has become increasingly vital for privacy-sensitive research environments. In this paper, we explore how compact transformer models can run efficiently on modern NPU architectures.",
        "Introduction\nTraditional cloud-based retrieval-augmented generation exposes proprietary user documents to network latencies and security vulnerabilities. Our work proposes local vector indexing and quantized inference.",
        "Methodology\nWe benchmarked quantized INT4 embeddings across varied memory bandwidths. Document chunks are extracted with strict page boundaries preserved to enable verifiable citations.",
        "Results and Discussion\nEvaluation demonstrates a 4.2x reduction in end-to-end question answering latency compared to cloud fallbacks, with zero external network leakage.",
        "Conclusion\nLocal on-device copilots provide sufficient accuracy while strictly guaranteeing user data confidentiality.",
    ]

    paper_2 = [
        "Abstract\nComparative analysis of academic literature requires multi-document synthesis and precise evidence tracking. This study introduces an automated verification framework for scholarly summarization.",
        "Introduction\nResearchers frequently analyze dozens of peer-reviewed articles to identify methodological divergences. Without page-level grounding, hallucinations significantly degrade researcher trust.",
        "Methodology\nWe construct a bi-encoder retrieval pipeline paired with cross-encoder verification. Each retrieved chunk retains its source document ID, page index, and parent section header.",
        "Results\nAcross 50 cross-paper comparative queries, our system achieved 94.2% citation precision, completely eliminating fabricated bibliographic references.",
        "Conclusion\nSource-traceable RAG constitutes a fundamental prerequisite for scholarly AI assistants.",
    ]

    paper_3 = [
        "Abstract\nActive recall and spaced repetition dramatically accelerate academic learning. We investigate how structured quiz generation from local notes boosts concept retention in higher education.",
        "Introduction\nStudents are overwhelmed by dense technical papers. Transforming technical text into bite-sized explanations and formative quizzes promotes deeper conceptual understanding.",
        "System Design\nOur pipeline takes indexed document chunks and formulates multiple-choice and conceptual questions. Distractors are dynamically generated from neighboring topic clusters.",
        "Evaluation\nA double-blind user study with 40 graduate students showed a 38% increase in retention test scores when studying via interactive quizzes compared to passive reading.",
        "Conclusion\nAutomated formative assessment powered by on-device retrieval is a viable tool for university study workflows.",
    ]

    create_demo_pdf(demo_dir / "paper_1_on_device_npu_ai.pdf", "On-Device NPU Architectures for Private Research", "Dr. Elena Vance", paper_1)
    create_demo_pdf(demo_dir / "paper_2_source_traceable_rag.pdf", "Source-Traceable RAG in Scholarly Synthesis", "Prof. Marcus Thorne", paper_2)
    create_demo_pdf(demo_dir / "paper_3_active_recall_learning.pdf", "Formative Quiz Generation for Concept Retention", "Dr. Sarah Lin", paper_3)
    print("All demo papers successfully generated in data/demo_papers/")


if __name__ == "__main__":
    main()
