import io
import uuid

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps


def process_product_image(
    image_file,
    *,
    max_dimension: int = 1600,
    quality: int = 80,
) -> ContentFile:
    """
    Validates, strips EXIF metadata, resizes, and converts any uploaded image to optimized WebP.

    Security & Privacy constraints:
    - Real MIME validation (Pillow must open the file without error).
    - EXIF GPS/location data stripped completely.
    - Protection against decompression bombs (Image.MAX_IMAGE_PIXELS respected).
    - Lightweight WebP format for fast mobile networks in Guinea.
    """
    if not image_file:
        raise ValidationError("Aucun fichier image fourni.")

    try:
        # Seek to beginning in case file was partially read
        if hasattr(image_file, "seek"):
            image_file.seek(0)

        img = Image.open(image_file)
        img.verify()

        # Reopen for transformation after verify()
        if hasattr(image_file, "seek"):
            image_file.seek(0)
        img = Image.open(image_file)

        # Standardize orientation based on EXIF before stripping it
        img = ImageOps.exif_transpose(img) or img

    except Exception as exc:
        raise ValidationError("Le fichier téléversé n'est pas une image valide ou est corrompu.") from exc

    # Convert to RGB (or RGBA for transparent PNGs)
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        img_converted = img.convert("RGBA")
    else:
        img_converted = img.convert("RGB")

    # Resize if dimensions exceed max_dimension
    width, height = img_converted.size
    if width > max_dimension or height > max_dimension:
        img_converted.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

    # Save to in-memory WebP buffer (EXIF metadata is not included, stripping GPS data)
    buffer = io.BytesIO()
    img_converted.save(buffer, format="WEBP", quality=quality, optimize=True)
    buffer.seek(0)

    filename = f"{uuid.uuid4().hex}.webp"
    return ContentFile(buffer.getvalue(), name=filename)
