from io import BytesIO

from PIL import Image, ImageDraw

from groundsops.evaluation import evaluate_generation
from groundsops.inference_providers import ImageGenerationRequest, MockImageGenerationProvider


def _png(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_mock_provider_passes_the_same_quality_gate_as_the_business_workflow():
    source = Image.new("RGB", (64, 64), (90, 160, 90))
    mask = Image.new("L", source.size, 0)
    ImageDraw.Draw(mask).rectangle((16, 16, 47, 47), fill=255)

    result = MockImageGenerationProvider().generate(
        ImageGenerationRequest(
            image=_png(source),
            image_media_type="image/png",
            mask=_png(mask),
            prompt="Create a photorealistic landscape concept for the selected area.",
        )
    )
    evaluation = evaluate_generation(
        _png(source),
        result.image,
        _png(mask),
    )

    assert evaluation.passed, evaluation.failure_reasons
    assert evaluation.masked_change_ratio >= evaluation.masked_change_threshold
    assert evaluation.protected_change_ratio <= evaluation.protected_change_threshold
    assert "blank_or_flat_mask_output" not in evaluation.failure_reasons
