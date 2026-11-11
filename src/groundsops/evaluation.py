import time
from dataclasses import dataclass
from io import BytesIO

from PIL import Image, UnidentifiedImageError

from groundsops.material_intent import resolve_material_intent

EVALUATOR_VERSION = "material-aware-v2"


@dataclass(frozen=True)
class EvaluationResult:
    evaluator_version: str
    dimensions_match: bool
    masked_change_ratio: float
    protected_change_ratio: float
    masked_change_threshold: float
    protected_change_threshold: float
    pixel_change_threshold: float
    passed: bool
    failure_reasons: list[str]
    evaluation_latency_ms: int


def _failed_result(started, reason, masked_change_min, protected_change_max,
                   pixel_change_threshold, *, dimensions_match=False):
    return EvaluationResult(
        EVALUATOR_VERSION, dimensions_match, 0.0, 0.0, masked_change_min,
        protected_change_max, pixel_change_threshold, False, [reason],
        round((time.perf_counter() - started) * 1000),
    )


def _is_green(pixel: tuple[int, int, int]) -> bool:
    red, green, blue = pixel
    return green >= 45 and green >= red * 1.08 and green >= blue * 1.08


def _is_brown(pixel: tuple[int, int, int]) -> bool:
    red, green, blue = pixel
    return red >= 45 and red >= green * 1.08 and green >= blue * 1.05


def _is_neutral(pixel: tuple[int, int, int]) -> bool:
    maximum = max(pixel)
    return maximum >= 35 and maximum - min(pixel) <= max(18, maximum * 0.22)


def evaluate_generation(
    source_bytes: bytes,
    output_bytes: bytes,
    mask_bytes: bytes,
    *,
    prompt: str = "",
    masked_change_min: float = 0.20,
    protected_change_max: float = 0.08,
    pixel_change_threshold: float = 0.05,
) -> EvaluationResult:
    """Verify boundary preservation, meaningful texture, and known material intent."""
    started = time.perf_counter()
    try:
        with Image.open(BytesIO(source_bytes)) as image:
            source = image.convert("RGB")
        with Image.open(BytesIO(output_bytes)) as image:
            output = image.convert("RGB")
        with Image.open(BytesIO(mask_bytes)) as image:
            mask = image.convert("L")
    except (UnidentifiedImageError, OSError):
        return _failed_result(
            started, "image_decode_failed", masked_change_min,
            protected_change_max, pixel_change_threshold,
        )

    if source.size != output.size or source.size != mask.size:
        return _failed_result(
            started, "dimension_mismatch", masked_change_min,
            protected_change_max, pixel_change_threshold,
        )

    masked_total = masked_changed = near_white = 0
    green_pixels = brown_pixels = neutral_pixels = 0
    protected_total = protected_changed = 0
    luminance_sum = luminance_squared_sum = 0.0
    source_pixels = source.load()
    output_pixels = output.load()
    mask_pixels = mask.load()
    change_cutoff = pixel_change_threshold * 255

    for y in range(source.height):
        for x in range(source.width):
            source_pixel = source_pixels[x, y]
            output_pixel = output_pixels[x, y]
            difference = sum(
                abs(a - b) for a, b in zip(source_pixel, output_pixel, strict=True)
            ) / 3
            changed = difference > change_cutoff
            if mask_pixels[x, y] > 127:
                masked_total += 1
                masked_changed += int(changed)
                near_white += int(min(output_pixel) >= 245)
                green_pixels += int(_is_green(output_pixel))
                brown_pixels += int(_is_brown(output_pixel))
                neutral_pixels += int(_is_neutral(output_pixel))
                luminance = sum(output_pixel) / 3
                luminance_sum += luminance
                luminance_squared_sum += luminance * luminance
            else:
                protected_total += 1
                protected_changed += int(changed)

    if masked_total == 0:
        return _failed_result(
            started, "mask_has_no_editable_pixels", masked_change_min,
            protected_change_max, pixel_change_threshold, dimensions_match=True,
        )

    masked_ratio = masked_changed / masked_total
    protected_ratio = protected_changed / protected_total if protected_total else 0.0
    mean_luminance = luminance_sum / masked_total
    variance = max(0.0, luminance_squared_sum / masked_total - mean_luminance**2)
    failure_reasons: list[str] = []
    if masked_ratio < masked_change_min:
        failure_reasons.append("insufficient_masked_change")
    if protected_ratio > protected_change_max:
        failure_reasons.append("excessive_protected_change")
    if near_white / masked_total > 0.90 or variance**0.5 < 2.0:
        failure_reasons.append("blank_or_flat_mask_output")

    intent = resolve_material_intent(prompt)
    if intent:
        coverage = {
            "grass": green_pixels / masked_total,
            "mulch": brown_pixels / masked_total,
            "gravel": neutral_pixels / masked_total,
            "pavers": neutral_pixels / masked_total,
        }[intent.key]
        minimum = 0.45 if intent.key == "grass" else 0.30
        if coverage < minimum:
            failure_reasons.append(f"requested_{intent.key}_not_detected")

    return EvaluationResult(
        EVALUATOR_VERSION, True, masked_ratio, protected_ratio,
        masked_change_min, protected_change_max, pixel_change_threshold,
        not failure_reasons, failure_reasons,
        round((time.perf_counter() - started) * 1000),
    )
