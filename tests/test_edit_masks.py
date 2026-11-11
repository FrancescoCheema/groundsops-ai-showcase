from io import BytesIO

import pytest
from PIL import Image, ImageDraw

from groundsops.images import InvalidImage, normalize_edit_mask


def _png(mode: str, pixels: list[int] | list[tuple[int, int, int, int]]) -> bytes:
    image = Image.new(mode, (2, 2))
    image.putdata(pixels)
    output = BytesIO()
    image.save(output, "PNG")
    return output.getvalue()


def test_edit_mask_is_thresholded_to_strict_black_and_white():
    source = _png(
        "RGBA",
        [(0, 0, 0, 255), (120, 120, 120, 255), (128, 128, 128, 255), (255, 255, 255, 255)],
    )

    normalized = normalize_edit_mask(source, (2, 2), 100)

    with Image.open(BytesIO(normalized)) as image:
        assert image.mode == "L"
        assert list(image.getdata()) == [0, 0, 255, 255]


def test_edit_mask_must_match_source_dimensions():
    source = _png("RGBA", [(0, 0, 0, 255)] * 3 + [(255, 255, 255, 255)])

    with pytest.raises(InvalidImage, match="dimensions must match"):
        normalize_edit_mask(source, (4, 4), 100)


@pytest.mark.parametrize(
    ("pixels", "message"),
    [([0, 0, 0, 0], "Paint at least"), ([255, 255, 255, 255], "entire photo")],
)
def test_edit_mask_requires_both_editable_and_protected_pixels(
    pixels: list[int], message: str
):
    source = _png("L", pixels)

    with pytest.raises(InvalidImage, match=message):
        normalize_edit_mask(source, (2, 2), 100)


def test_composite_edit_keeps_everything_outside_the_mask_identical():
    from groundsops.images import composite_edit

    source = Image.new("RGB", (64, 48), (120, 90, 60))
    generated = Image.new("RGB", (32, 24), (40, 200, 60))  # different size on purpose
    mask = Image.new("L", (64, 48), 0)
    ImageDraw.Draw(mask).rectangle((16, 12, 47, 35), fill=255)

    def png(image):
        stream = BytesIO()
        image.save(stream, format="PNG")
        return stream.getvalue()

    result = Image.open(BytesIO(composite_edit(png(source), png(generated), png(mask))))

    assert result.size == source.size
    for x in range(64):
        for y in range(48):
            if mask.getpixel((x, y)) == 0:
                assert result.getpixel((x, y)) == (120, 90, 60)
    assert result.getpixel((32, 24)) == (40, 200, 60)
