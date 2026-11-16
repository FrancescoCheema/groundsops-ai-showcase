"""Find the parts of a requested lawn the model left as bare ground.

Inpainting models sometimes paint the new material as an island inside the selection
and leave a band of the old surface around it (a single "roll of sod" on bare soil).
For lawn this is easy to see in the pixels: grass is green-tinted in sun and shade,
soil and mulch are red-brown. The uncovered parts get a second, targeted pass.
"""

from io import BytesIO

from PIL import Image, ImageChops, ImageFilter

# Share of the selection that must be left uncovered before a second pass is worth it.
MIN_UNCOVERED_SHARE = 0.10
ANALYSIS_SIDE = 512
LAWN_GREEN_LEAD = 1.06


def _binary(image: Image.Image) -> Image.Image:
    return image.point(lambda value: 255 if value >= 128 else 0)


def _grow(mask: Image.Image, radius: int) -> Image.Image:
    grown = mask
    while radius > 0:
        step = min(radius, 7)
        grown = grown.filter(ImageFilter.MaxFilter(step * 2 + 1))
        radius -= step
    return grown


def lawn_refinement_masks(output: bytes, mask: bytes) -> tuple[bytes, bytes, float] | None:
    """Return (model mask, composite mask, uncovered share) when the lawn is incomplete.

    The model mask is the uncovered ground plus a margin, so the model sees lawn around
    it; the composite mask keeps the change inside the user's original selection.
    """
    with Image.open(BytesIO(output)) as image:
        picture = image.convert("RGB")
    with Image.open(BytesIO(mask)) as image:
        selection = _binary(image.convert("L"))
    if picture.size != selection.size:
        picture = picture.resize(selection.size, Image.Resampling.LANCZOS)

    full_size = selection.size
    scale = min(1.0, ANALYSIS_SIDE / max(full_size))
    small_size = (max(1, round(full_size[0] * scale)), max(1, round(full_size[1] * scale)))
    small_picture = picture.resize(small_size, Image.Resampling.BILINEAR)
    small_selection = _binary(selection.resize(small_size, Image.Resampling.NEAREST))

    red, green, _ = small_picture.split()
    # Lawn only where green clearly leads red, in sun or shade. Everything else in the
    # selection is still bare: brown soil, grey construction dirt, mulch, dead grass.
    boosted_red = red.point(lambda value: min(255, round(value * LAWN_GREEN_LEAD)))
    bare = _binary(ImageChops.subtract(boosted_red, green, scale=1.0, offset=128))
    bare = ImageChops.multiply(bare, small_selection)
    # Ignore specks: an opening keeps only real patches of ground.
    bare = bare.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))

    selected = small_selection.histogram()[255]
    uncovered = bare.histogram()[255]
    if not selected:
        return None
    share = uncovered / selected
    if share < MIN_UNCOVERED_SHARE:
        return None

    bare_full = _binary(bare.resize(full_size, Image.Resampling.NEAREST))
    margin = max(2, round(min(full_size) * 0.02))
    model_mask = _grow(bare_full, margin)
    composite_mask = ImageChops.multiply(_grow(bare_full, margin // 2), selection)

    model_out, composite_out = BytesIO(), BytesIO()
    model_mask.save(model_out, format="PNG")
    composite_mask.save(composite_out, format="PNG")
    return model_out.getvalue(), composite_out.getvalue(), share
