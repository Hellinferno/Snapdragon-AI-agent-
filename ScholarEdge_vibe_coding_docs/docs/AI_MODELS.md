# ScholarEdge — AI Model Strategy

## Principle

Models are implementation choices, not application contracts.

The application depends on provider interfaces. Models can be swapped without rewriting the research/learning layer.

## Planned capabilities

| Capability | Role | Priority |
|---|---|---|
| LLM | generation/reasoning | MVP |
| Embeddings | semantic retrieval | MVP |
| OCR | scanned documents | MVP/next |
| Vision-language | figures/screenshots | v1.5 |
| Speech-to-text | voice | v2 |
| Handwriting OCR | handwritten notes | v2 |

## Candidate Snapdragon models

Candidate models must be re-verified against the current Qualcomm AI Hub catalog before implementation.

Previously investigated candidates:
- Qwen3-4B-Instruct-2507 — generation
- MiniLM-v2 / all-MiniLM-L6-v2 — embeddings
- EasyOCR — OCR
- Qwen3-VL-4B-Instruct — vision-language
- TrOCR — handwriting OCR
- Whisper-Small — speech-to-text

These are candidates, not permanent dependencies.

## Model selection criteria

Evaluate:
1. Snapdragon device support;
2. runtime availability;
3. NPU/accelerator support;
4. model size;
5. memory footprint;
6. latency;
7. output quality;
8. quantization options;
9. licensing;
10. ease of local deployment.

## Development fallback

The development backend may use a lightweight local model or an explicitly configured external provider. The rest of the application must remain provider-agnostic.

## No hallucinated support

A model must not be described as Snapdragon/NPU compatible in project documentation until current deployment evidence exists.
