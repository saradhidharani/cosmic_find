
"""Render actual SPHEREx FITS pixels as a cached grayscale PNG."""

from pathlib import Path
from io import BytesIO
import hashlib

import numpy as np
from astropy.io import fits
from PIL import Image

from archive import range_bytes, inspect, SAMPLE_KEY

CACHE = Path(__file__).parent / "cache"
CACHE.mkdir(exist_ok=True)


def generate_observation_image(
    key=SAMPLE_KEY,
    record=None,
):
    """
    Download the FITS image data using HTTP byte ranges.

    The image is rendered from real NASA pixel values,
    not generated or simulated astronomy imagery.
    """
    if record is None:
        record = inspect(key)

    cache_name = (
        hashlib.sha256(key.encode("utf-8"))
        .hexdigest()[:20] + ".png"
    )

    output = CACHE / cache_name

    if output.exists() and output.stat().st_size > 0:
        return str(output)

    offset = int(record["pixel_offset"])
    size = int(record["pixel_bytes"])

    if size <= 0 or size > 100_000_000:
        raise ValueError("Unsupported FITS image size")

    raw = range_bytes(
        key,
        offset,
        offset + size - 1,
    )

    bitpix = int(record["bitpix"])

    types = {
        8: ">u1",
        16: ">i2",
        32: ">i4",
        64: ">i8",
        -32: ">f4",
        -64: ">f8",
    }

    if bitpix not in types:
        raise ValueError(
            f"Unsupported FITS BITPIX: {bitpix}"
        )

    pixels = np.frombuffer(
        raw,
        dtype=np.dtype(types[bitpix]),
    ).reshape(
        int(record["height"]),
        int(record["width"]),
    )

    pixels = pixels.astype(np.float64)

    pixels = (
        pixels * float(record.get("bscale", 1))
        + float(record.get("bzero", 0))
    )

    finite = np.isfinite(pixels)

    if not finite.any():
        raise ValueError(
            "No valid pixels in NASA observation"
        )

    valid = pixels[finite]

    low, high = np.percentile(
        valid,
        [1, 99.5],
    )

    if high <= low:
        high = low + 1

    normalized = np.clip(
        (pixels - low) / (high - low),
        0,
        1,
    )

    normalized[~finite] = 0

    # Asinh stretch reveals faint infrared structures.
    stretched = np.arcsinh(
        8 * normalized
    ) / np.arcsinh(8)

    image_data = (
        stretched * 255
    ).astype(np.uint8)

    image = Image.fromarray(
        image_data,
        mode="L",
    )

    image.save(
        output,
        format="PNG",
        optimize=True,
    )

    return str(output)
