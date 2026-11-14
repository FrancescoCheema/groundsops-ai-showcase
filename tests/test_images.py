

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
