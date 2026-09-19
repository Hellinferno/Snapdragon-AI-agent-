import io

import numpy as np
from PIL import Image, ImageFilter

from app.providers.base import (
    OCRProvider,
    VisionAnalysisResult,
    VisionProvider,
    VisualQAResult,
)

# Longest side of the working copy used for pixel statistics.
ANALYSIS_MAX_SIDE = 512
# A colour must cover at least this share of pixels to count as "used" by the figure.
SIGNIFICANT_COLOUR_SHARE = 0.005
# Channel spread (0-255) below which a pixel is treated as grey.
GREY_CHANNEL_SPREAD = 12


def measure_image(image_bytes: bytes) -> dict:
    """Exact, reproducible pixel measurements of an image; nothing is inferred."""
    with Image.open(io.BytesIO(image_bytes)) as img:
        width, height = img.size
        mode = img.mode
        rgb = img.convert("RGB")
        rgb.thumbnail((ANALYSIS_MAX_SIDE, ANALYSIS_MAX_SIDE))

    pixels = np.asarray(rgb, dtype=np.int16)
    flat = pixels.reshape(-1, 3)
    luminance = np.asarray(rgb.convert("L"), dtype=np.float32)

    spread = flat.max(axis=1) - flat.min(axis=1)
    grey_share = float(np.mean(spread <= GREY_CHANNEL_SPREAD))

    # Quantise to 8 levels per channel so anti-aliasing does not inflate the palette.
    quantised = (flat // 32).astype(np.int32)
    codes = quantised[:, 0] * 64 + quantised[:, 1] * 8 + quantised[:, 2]
    counts = np.bincount(codes, minlength=512)
    shares = counts / counts.sum()
    dominant = int(np.argmax(shares))
    dominant_rgb = tuple(int(v) for v in np.median(flat[codes == dominant], axis=0))
    dominant_luma = 0.299 * dominant_rgb[0] + 0.587 * dominant_rgb[1] + 0.114 * dominant_rgb[2]

    edges = np.asarray(rgb.convert("L").filter(ImageFilter.FIND_EDGES), dtype=np.float32)

    return {
        "width": width,
        "height": height,
        "aspect_ratio": round(width / max(1, height), 2),
        "mode": mode,
        "brightness": float(luminance.mean()),
        "contrast": float(luminance.std()),
        "grey_share": grey_share,
        "background_share": float(shares[dominant]),
        "background_rgb": dominant_rgb,
        "background_luma": dominant_luma,
        "colour_count": int(np.sum(shares >= SIGNIFICANT_COLOUR_SHARE)),
        "edge_density": float(np.mean(edges > 40)),
    }


def categorise(m: dict) -> tuple[str, str]:
    """A coarse figure category from the measurements, with the rule that produced it."""
    if m["background_share"] >= 0.45 and m["colour_count"] <= 16:
        tone = "dark" if m["background_luma"] < 80 else "light" if m["background_luma"] > 175 else "mid-tone"
        return (
            "Line-art figure (chart, diagram or table)",
            f"{m['background_share']:.0%} of pixels share one flat {tone} background colour and only "
            f"{m['colour_count']} colours are used, which is typical of rendered charts, diagrams "
            "and tables; these three are not distinguished without a trained classifier.",
        )
    if m["grey_share"] >= 0.95:
        return (
            "Greyscale continuous-tone image (e.g. radiograph or micrograph)",
            f"{m['grey_share']:.0%} of pixels are grey and there is no dominant flat background, "
            "which is typical of scans and photographs rather than rendered figures.",
        )
    return (
        "Colour photograph or complex illustration",
        f"No flat background ({m['background_share']:.0%} max colour share) and "
        f"{m['colour_count']} colours in use.",
    )


def describe_measurements(m: dict) -> list[str]:
    colour_desc = "greyscale" if m["grey_share"] >= 0.95 else "colour"
    r, g, b = m["background_rgb"]
    return [
        f"Resolution {m['width']} x {m['height']} px, aspect ratio {m['aspect_ratio']}:1, "
        f"{colour_desc} ({m['mode']} mode).",
        f"Mean brightness {m['brightness']:.0f}/255; contrast (luminance standard deviation) "
        f"{m['contrast']:.1f}.",
        f"Dominant colour #{r:02x}{g:02x}{b:02x} covers {m['background_share']:.0%} of pixels; "
        f"{m['colour_count']} colours each cover at least {SIGNIFICANT_COLOUR_SHARE:.1%}.",
        f"Edge density {m['edge_density']:.1%} of pixels.",
    ]


NOT_READ_NOTICE = (
    "This analysis measures pixels only: it does not read the figure's text, axis labels, "
    "values or trends."
)


class DevelopmentVisionProvider(VisionProvider):
    """On-device figure analysis from measured pixel statistics.

    No neural model runs on this path. It reports what can be measured exactly
    (size, colour, brightness, contrast, background, edges) and a coarse category
    derived from those measurements by the explicit rules in :func:`categorise`.
    It has no confidence score because nothing here is probabilistic, and it
    never describes content (labels, values, trends) it cannot see.
    """

    @property
    def name(self) -> str:
        return "development-vision-heuristic"

    async def analyze_figure(self, image_bytes: bytes, filename: str) -> VisionAnalysisResult:
        m = measure_image(image_bytes)
        category, rule = categorise(m)
        clean_title = filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()
        return VisionAnalysisResult(
            figure_type=category,
            title=f"Figure: {clean_title}",
            summary=f"{category}, from measured pixel statistics. {NOT_READ_NOTICE}",
            observations=describe_measurements(m) + [f"Category rule: {rule}"],
            confidence=None,
        )

    async def answer_question(self, image_bytes: bytes, question: str, filename: str) -> VisualQAResult:
        m = measure_image(image_bytes)
        category, rule = categorise(m)
        measured = describe_measurements(m)
        q = question.lower()

        if any(w in q for w in ("resolution", "size", "dimension", "aspect", "pixels")):
            cues = [measured[0]]
            answer = measured[0]
        elif any(w in q for w in ("colour", "color", "bright", "contrast", "dark", "light")):
            cues = measured[1:3]
            answer = " ".join(cues)
        elif any(w in q for w in ("type", "kind", "category", "classif", "what is this")):
            cues = [f"Category rule: {rule}"]
            answer = f"Measured category: {category}. {rule}"
        else:
            cues = measured
            answer = (
                f"{NOT_READ_NOTICE} It cannot answer \"{question.strip()}\" from the image itself. "
                f"What it can measure: {category.lower()}; {measured[0]}"
            )

        return VisualQAResult(question=question, answer=answer, grounded_visual_cues=cues)


class DevelopmentOCRProvider(OCRProvider):
    """Placeholder: no OCR engine is bundled, so it extracts nothing rather than inventing text."""

    @property
    def name(self) -> str:
        return "development-ocr-unavailable"

    async def extract_text_from_image(self, image_bytes: bytes) -> str:
        return ""


vision_provider: VisionProvider = DevelopmentVisionProvider()
ocr_provider: OCRProvider = DevelopmentOCRProvider()
