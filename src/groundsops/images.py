from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO

from PIL import Image, ImageChops, ImageFilter, ImageOps, UnidentifiedImageError


class InvalidImage(ValueError):
    pass


@dataclass(frozen=True)
class SanitizedImage:
    data: bytes
    media_type: str
    extension: str
    width: int
    height: int
    sha256: str


_FORMATS = {
    "JPEG": ("image/jpeg", "jpg"),
    "PNG": ("image/png", "png"),
    "WEBP": ("image/webp", "webp"),
}


def sanitize_image(data: bytes, max_pixels: int) -> SanitizedImage:
    try:
        with Image.open(BytesIO(data)) as source:
            if source.format not in _FORMATS:
                raise InvalidImage("Only JPEG, PNG and WebP images are supported")
            width, height = source.size
            if width < 1 or height < 1 or width * height > max_pixels:
                raise InvalidImage("Image dimensions are not allowed")
            source.load()
            image = ImageOps.exif_transpose(source)
            width, height = image.size
            media_type, extension = _FORMATS[source.format]
            output = BytesIO()
            if source.format == "JPEG":
                image.convert("RGB").save(output, "JPEG", quality=92, optimize=True)
            elif source.format == "PNG":
                image.save(output, "PNG", optimize=True)
            else:
                image.save(output, "WEBP", quality=92, method=4)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise InvalidImage("File is not a valid supported image") from exc

    sanitized = output.getvalue()
    return SanitizedImage(
        data=sanitized,
        media_type=media_type,
        extension=extension,
        width=width,
        height=height,
        sha256=sha256(sanitized).hexdigest(),
    )


def normalize_edit_mask(
    data: bytes,
    expected_size: tuple[int, int],
    max_pixels: int,
) -> bytes:
    """Return a strict opaque black-and-white PNG for an inpainting provider."""
    try:
        with Image.open(BytesIO(data)) as source:
            source.load()
            mask = ImageOps.exif_transpose(source).convert("L")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise InvalidImage("Mask is not a valid image") from exc

    if mask.size != expected_size:
        raise InvalidImage("Mask dimensions must match the source photo")
    if mask.width * mask.height > max_pixels:
        raise InvalidImage("Mask dimensions are not allowed")

    # Canvas exports can contain antialiasing and alpha. Thresholding removes both
    # ambiguities and gives FLUX Fill the exact contract it documents: black pixels
    # are protected and white pixels are editable.
    normalized = mask.point(lambda value: 255 if value >= 128 else 0, mode="1").convert("L")
    histogram = normalized.histogram()
    protected_pixels = histogram[0]
    editable_pixels = histogram[255]
    if editable_pixels == 0:
        raise InvalidImage("Paint at least one editable area")
    if protected_pixels == 0:
        raise InvalidImage("The edit mask cannot cover the entire photo")

    output = BytesIO()
    normalized.save(output, "PNG", optimize=True)
    return output.getvalue()


def composite_edit(source: bytes, generated: bytes, mask: bytes) -> bytes:
    """Blend a generated image into the original photo inside the edit mask only.

    The mask is eroded before feathering, so the soft transition sits just inside the
    selection and every pixel outside it is returned exactly as in the original.
    """
    with Image.open(BytesIO(source)) as image:
        original = image.convert("RGB")
    with Image.open(BytesIO(generated)) as image:
        edited = image.convert("RGB")
    with Image.open(BytesIO(mask)) as image:
        alpha = image.convert("L")
    if edited.size != original.size:
        edited = edited.resize(original.size, Image.Resampling.LANCZOS)
    if alpha.size != original.size:
        alpha = alpha.resize(original.size, Image.Resampling.NEAREST)
    radius = max(1, round(min(original.size) / 320))
    hard = alpha.point(lambda value: 255 if value >= 128 else 0)
    alpha = hard.filter(ImageFilter.MinFilter(radius * 2 + 1)).filter(
        ImageFilter.GaussianBlur(radius)
    )
    # Clamp to the original selection so the blur can never leak outside it.
    alpha = ImageChops.multiply(alpha, hard)
    output = BytesIO()
    Image.composite(edited, original, alpha).save(output, format="PNG", optimize=True)
    return output.getvalue()


def upscale_for_inpainting(
    image: bytes, media_type: str, mask: bytes, min_long_side: int = 1024
) -> tuple[bytes, str, bytes]:
    """Enlarge small photos (and their mask) before inpainting.

    FLUX Fill works at about one megapixel. Given a small photo, such as one saved from a
    Google Business listing, it paints textures far too large for the scene (fist-sized
    gravel, clumped grass). The result is scaled back down when composited.
    Returns ``(image, media_type, mask)``; images already large enough are unchanged.
    """
    try:
        with Image.open(BytesIO(image)) as source:
            source.load()
            original = source.convert("RGB")
    except (UnidentifiedImageError, OSError):
        return image, media_type, mask
    long_side = max(original.size)
    if long_side >= min_long_side:
        return image, media_type, mask
    scale = min_long_side / long_side
    size = (round(original.width * scale), round(original.height * scale))
    with Image.open(BytesIO(mask)) as source:
        enlarged_mask = source.convert("L").resize(size, Image.Resampling.NEAREST)
    image_out, mask_out = BytesIO(), BytesIO()
    original.resize(size, Image.Resampling.LANCZOS).save(image_out, format="PNG")
    enlarged_mask.save(mask_out, format="PNG")
    return image_out.getvalue(), "image/png", mask_out.getvalue()
