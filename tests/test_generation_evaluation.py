from io import BytesIO

from PIL import Image

from groundsops.evaluation import evaluate_generation


def image_bytes(pixels, size=(4, 4), mode="RGB") -> bytes:
    image = Image.new(mode, size)
    image.putdata(pixels)
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def test_grass_request_passes_with_green_texture_inside_mask():
    source = [(120, 90, 60)] * 16
    grass = [(30, 100 + index * 3, 35) for index in range(8)]
    output = grass + source[8:]
    mask = [255] * 8 + [0] * 8

    result = evaluate_generation(
        image_bytes(source), image_bytes(output), image_bytes(mask, mode="L"), prompt="grass"
    )

    assert result.passed is True


def test_grass_request_rejects_dirt_even_when_mask_changed_correctly():
    source = [(200, 200, 200)] * 16
    dirt = [(90 + index, 60 + index, 35) for index in range(8)]
    output = dirt + source[8:]
    mask = [255] * 8 + [0] * 8

    result = evaluate_generation(
        image_bytes(source), image_bytes(output), image_bytes(mask, mode="L"), prompt="install sod"
    )

    assert result.passed is False
    assert "requested_grass_not_detected" in result.failure_reasons


def test_white_polygon_is_rejected():
    source = [(80, 70, 60)] * 16
    output = [(255, 255, 255)] * 8 + source[8:]
    mask = [255] * 8 + [0] * 8

    result = evaluate_generation(
        image_bytes(source), image_bytes(output), image_bytes(mask, mode="L"), prompt="grass"
    )

    assert result.passed is False
    assert "blank_or_flat_mask_output" in result.failure_reasons


def test_paver_request_rejects_green_lawn_output():
    source = [(120, 90, 60)] * 16
    grass = [(25, 110 + index, 30) for index in range(8)]
    output = grass + source[8:]
    mask = [255] * 8 + [0] * 8

    result = evaluate_generation(
        image_bytes(source),
        image_bytes(output),
        image_bytes(mask, mode="L"),
        prompt="charcoal pavers",
    )

    assert result.passed is False
    assert "requested_pavers_not_detected" in result.failure_reasons
