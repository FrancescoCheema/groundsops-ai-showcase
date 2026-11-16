

def test_small_photos_are_enlarged_for_inpainting_with_matching_mask():
    from io import BytesIO

    from PIL import Image

    from groundsops.images import upscale_for_inpainting

    def png(image):
        out = BytesIO()
        image.save(out, format="PNG")
        return out.getvalue()

    photo = png(Image.new("RGB", (382, 510), (90, 120, 60)))
    mask_image = Image.new("L", (382, 510), 0)
    mask_image.paste(255, (0, 255, 382, 510))
    image, media_type, mask = upscale_for_inpainting(photo, "image/png", png(mask_image))

    with Image.open(BytesIO(image)) as enlarged, Image.open(BytesIO(mask)) as enlarged_mask:
        assert enlarged.size == enlarged_mask.size == (767, 1024)
        assert set(enlarged_mask.getdata()) == {0, 255}
    assert media_type == "image/png"

    large = png(Image.new("RGB", (1600, 1200)))
    large_mask = png(Image.new("L", (1600, 1200)))
    assert upscale_for_inpainting(large, "image/jpeg", large_mask) == (
        large,
        "image/jpeg",
        large_mask,
    )


def test_inpainting_mask_is_grown_and_bad_input_passes_through():
    from io import BytesIO

    from PIL import Image, ImageDraw

    from groundsops.images import expand_mask_for_inpainting

    mask = Image.new("L", (400, 300), 0)
    ImageDraw.Draw(mask).rectangle((100, 100, 199, 199), fill=255)
    stream = BytesIO()
    mask.save(stream, format="PNG")
    grown = Image.open(BytesIO(expand_mask_for_inpainting(stream.getvalue()))).convert("L")

    margin = round(300 * 0.06)
    assert grown.getpixel((100 - margin, 150)) == 255
    assert grown.getpixel((100 - margin - 2, 150)) == 0
    assert grown.getpixel((150, 150)) == 255
    assert expand_mask_for_inpainting(b"not an image") == b"not an image"
