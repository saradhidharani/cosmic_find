
"""WCS-aligned temporal comparison of real NASA SPHEREx observations."""

import hashlib
import io
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from astropy.io import fits
from astropy.wcs import WCS

from archive import contains, load_index, range_bytes

CACHE = Path(__file__).parent / "cache" / "temporal"
CACHE.mkdir(parents=True, exist_ok=True)

SIZE = 256
MAX_FRAMES = 8


def _read_pixels(record):
    offset = int(record["pixel_offset"])
    size = int(record["pixel_bytes"])
    bitpix = int(record["bitpix"])

    dtypes = {
        8: ">u1",
        16: ">i2",
        32: ">i4",
        64: ">i8",
        -32: ">f4",
        -64: ">f8",
    }

    if bitpix not in dtypes:
        raise ValueError("Unsupported FITS pixel format")

    raw = range_bytes(
        record["file_key"],
        offset,
        offset + size - 1,
    )

    pixels = np.frombuffer(
        raw,
        dtype=np.dtype(dtypes[bitpix]),
    ).reshape(
        int(record["height"]),
        int(record["width"]),
    ).astype(np.float32)

    pixels *= float(record.get("bscale", 1))
    pixels += float(record.get("bzero", 0))

    return pixels


def _wcs(record):
    header = fits.Header.fromstring(
        record["header"],
        sep="\n",
    )
    return WCS(header).celestial


def _bilinear(pixels, x, y):
    height, width = pixels.shape

    x0 = np.floor(x).astype(np.int64)
    y0 = np.floor(y).astype(np.int64)

    valid = (
        (x0 >= 0)
        & (y0 >= 0)
        & (x0 + 1 < width)
        & (y0 + 1 < height)
    )

    output = np.full(x.shape, np.nan, dtype=np.float32)

    if not np.any(valid):
        return output

    xx = x0[valid]
    yy = y0[valid]

    dx = (x[valid] - xx).astype(np.float32)
    dy = (y[valid] - yy).astype(np.float32)

    p00 = pixels[yy, xx]
    p10 = pixels[yy, xx + 1]
    p01 = pixels[yy + 1, xx]
    p11 = pixels[yy + 1, xx + 1]

    values = (
        p00 * (1 - dx) * (1 - dy)
        + p10 * dx * (1 - dy)
        + p01 * (1 - dx) * dy
        + p11 * dx * dy
    )

    output[valid] = values

    return output


def _aligned_image(record, target_ra, target_dec, reference_wcs):
    pixels = _read_pixels(record)
    source_wcs = _wcs(record)

    ref_x, ref_y = reference_wcs.all_world2pix(
        [[target_ra, target_dec]],
        0,
    )[0]

    yy, xx = np.mgrid[0:SIZE, 0:SIZE]

    reference_x = xx + ref_x - (SIZE - 1) / 2
    reference_y = yy + ref_y - (SIZE - 1) / 2

    ra, dec = reference_wcs.all_pix2world(
        reference_x,
        reference_y,
        0,
    )

    source_x, source_y = source_wcs.all_world2pix(
        ra,
        dec,
        0,
    )

    return _bilinear(pixels, source_x, source_y)


def _render(image, low, high):
    valid = np.isfinite(image)

    normalized = np.zeros(image.shape, dtype=np.float32)

    if high > low:
        normalized[valid] = np.clip(
            (image[valid] - low) / (high - low),
            0,
            1,
        )

    stretched = np.arcsinh(8 * normalized) / np.arcsinh(8)

    return Image.fromarray(
        (stretched * 255).astype(np.uint8),
        mode="L",
    ).convert("RGB")


def analyze_region(ra, dec):
    ra = float(ra)
    dec = float(dec)

    if not 0 <= ra < 360 or not -90 <= dec <= 90:
        raise ValueError("Invalid celestial coordinates")

    records = [
        record
        for record in load_index()
        if contains(record, ra, dec)
    ]

    records.sort(
        key=lambda item: item.get("observation_date") or ""
    )

    if len(records) < 2:
        raise ValueError(
            "At least two overlapping observations are required"
        )

    records = records[:MAX_FRAMES]

    timestamps = {
        record.get("observation_date")
        for record in records
        if record.get("observation_date")
    }

    if len(timestamps) < 2:
        raise ValueError(
            "Observations must have different timestamps"
        )

    detectors = {
        record.get("detector")
        for record in records
    }

    if len(detectors) != 1:
        raise ValueError(
            "This comparison requires the same detector"
        )

    cache_key = hashlib.sha256(
        json.dumps(
            {
                "ra": ra,
                "dec": dec,
                "keys": [r["file_key"] for r in records],
                "size": SIZE,
                "version": 1,
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()[:20]

    folder = CACHE / cache_key
    metadata_file = folder / "analysis.json"

    if metadata_file.exists():
        return json.loads(
            metadata_file.read_text(encoding="utf-8")
        )

    folder.mkdir(parents=True, exist_ok=True)

    reference_wcs = _wcs(records[0])

    aligned = [
        _aligned_image(
            record,
            ra,
            dec,
            reference_wcs,
        )
        for record in records
    ]

    stack = np.stack(aligned)

    # Only compare pixels valid in every frame.
    common = np.all(np.isfinite(stack), axis=0)

    if np.count_nonzero(common) < SIZE * SIZE * 0.1:
        raise ValueError(
            "Insufficient common image coverage for comparison"
        )

    common_values = stack[:, common]

    # Use shared display limits to avoid independent frame scaling.
    low, high = np.percentile(
        common_values,
        [1, 99.5],
    )

    if high <= low:
        high = low + 1

    rendered = []
    frame_metadata = []

    for index, (record, image) in enumerate(
        zip(records, aligned)
    ):
        frame = _render(image, low, high)
        frame.save(folder / f"frame_{index}.png")

        rendered.append(frame)

        valid_values = image[common]

        frame_metadata.append({
            "index": index,
            "timestamp": record.get("observation_date"),
            "detector": record.get("detector"),
            "mean_brightness": round(
                float(np.mean(valid_values)), 6
            ),
            "median_brightness": round(
                float(np.median(valid_values)), 6
            ),
            "unit": record.get("brightness_unit"),
        })

    # Difference relative to the first observation.
    first = stack[0]
    last = stack[-1]

    difference = last - first

    difference[~common] = np.nan

    diff_values = difference[common]

    # Robust noise estimate from the difference distribution.
    median_difference = float(np.median(diff_values))

    mad = float(
        np.median(
            np.abs(diff_values - median_difference)
        )
    )

    robust_sigma = 1.4826 * mad

    if robust_sigma <= 0:
        robust_sigma = float(np.std(diff_values))

    if robust_sigma <= 0:
        robust_sigma = 1e-12

    threshold = 5 * robust_sigma

    candidate_mask = (
        common
        & (
            np.abs(difference - median_difference)
            > threshold
        )
    )

    # Visualize absolute residual differences.
    residual = np.zeros_like(difference)
    residual[common] = np.abs(
        difference[common] - median_difference
    )

    display_high = float(
        np.percentile(residual[common], 99.5)
    )

    if display_high <= 0:
        display_high = 1

    heat = np.clip(
        residual / display_high,
        0,
        1,
    )

    heat[~common] = 0

    rgb = np.zeros((SIZE, SIZE, 3), dtype=np.uint8)
    rgb[..., 0] = (heat * 255).astype(np.uint8)
    rgb[..., 1] = (heat * 80).astype(np.uint8)
    rgb[..., 2] = (heat * 35).astype(np.uint8)

    rgb[candidate_mask] = [255, 240, 80]

    Image.fromarray(rgb).save(
        folder / "difference.png"
    )

    # Timestamped animated GIF.
    gif_frames = []

    for index, frame in enumerate(rendered):
        canvas = Image.new(
            "RGB",
            (SIZE, SIZE + 36),
            "#080d1d",
        )

        canvas.paste(frame, (0, 0))

        draw = ImageDraw.Draw(canvas)

        timestamp = (
            frame_metadata[index]["timestamp"]
            or "Unknown timestamp"
        )

        draw.text(
            (8, SIZE + 10),
            timestamp[:23] + " UTC",
            fill="white",
        )

        gif_frames.append(canvas)

    gif_frames[0].save(
        folder / "timelapse.gif",
        save_all=True,
        append_images=gif_frames[1:],
        duration=900,
        loop=0,
        optimize=False,
    )

    candidate_count = int(
        np.count_nonzero(candidate_mask)
    )

    metadata = {
        "analysis_id": cache_key,
        "coordinates": {
            "ra": ra,
            "dec": dec,
        },
        "frame_count": len(records),
        "image_size": SIZE,
        "detector": records[0].get("detector"),
        "frames": frame_metadata,
        "comparison": {
            "reference_frame": 0,
            "compared_frame": len(records) - 1,
            "common_pixels": int(
                np.count_nonzero(common)
            ),
            "candidate_pixels": candidate_count,
            "candidate_fraction": round(
                candidate_count / np.count_nonzero(common),
                6,
            ),
            "median_difference": round(
                median_difference, 6
            ),
            "robust_sigma": round(
                robust_sigma, 6
            ),
            "threshold_sigma": 5,
        },
        "summary": (
            f"Analyzed {len(records)} real NASA SPHEREx "
            f"observations of RA {ra:.6f}, Dec {dec:.6f}. "
            f"All images were resampled onto a shared "
            f"celestial coordinate grid using FITS WCS. "
            f"The first and last observations contain "
            f"{candidate_count} pixels above a robust "
            f"5-sigma residual threshold within their "
            f"common coverage. These are candidate "
            f"image differences, not confirmed "
            f"astronomical changes. Instrumental noise, "
            f"point-spread-function differences, "
            f"calibration and resampling effects "
            f"may contribute."
        ),
        "limitations": (
            "Exploratory WCS-aligned pixel comparison only. "
            "No PSF matching, background matching, "
            "uncertainty propagation or artifact rejection. "
            "Pixel thresholding is not source detection."
        ),
    }

    metadata_file.write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    return metadata


def analysis_file(analysis_id, filename):
    if not (
        len(analysis_id) == 20
        and all(c in "0123456789abcdef" for c in analysis_id)
    ):
        raise ValueError("Invalid analysis ID")

    allowed = {
        "difference.png",
        "timelapse.gif",
    }

    if filename.startswith("frame_") and filename.endswith(".png"):
        number = filename[6:-4]

        if number.isdigit() and 0 <= int(number) < MAX_FRAMES:
            allowed.add(filename)

    if filename not in allowed:
        raise ValueError("Invalid analysis file")

    path = CACHE / analysis_id / filename

    if not path.is_file():
        raise FileNotFoundError("Analysis file not found")

    return path
