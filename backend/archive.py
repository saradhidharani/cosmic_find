
"""Bounded SPHEREx S3 observation index. No invented target matches."""
from __future__ import annotations
import json
import re
import threading
from pathlib import Path
from urllib.parse import quote

import requests
from astropy.io import fits
from astropy.wcs import WCS

BUCKET = "https://nasa-irsa-spherex.s3.amazonaws.com/"
SAMPLE_KEY = (
    "qr3/level2/2026W20_2A/l2b-v27-2026-267/1/"
    "level2_2026W20_2A_0001_1D1_spx_l2b-v27-2026-267.fits"
)

CACHE = Path(__file__).parent / "cache"
CACHE.mkdir(exist_ok=True)
INDEX_PATH = CACHE / "observation_index.json"
_LOCK = threading.Lock()

# Limited public-release subset, not a complete sky catalog.
SCAN_PREFIX = "qr3/level2/2026W20_2A/l2b-v27-2026-267/1/"


def range_bytes(key: str, start: int, end: int) -> bytes:
    if (
        not key.startswith("qr3/level2/")
        or not key.endswith(".fits")
        or ".." in key
    ):
        raise ValueError("Invalid observation key")

    response = requests.get(
        BUCKET + quote(key, safe="/"),
        headers={"Range": f"bytes={start}-{end}"},
        timeout=(15, 90),
    )
    response.raise_for_status()

    expected = end - start + 1

    if response.status_code != 206 or len(response.content) != expected:
        raise ValueError(
            "NASA did not return the requested FITS byte range"
        )

    return response.content


def _header(buffer: bytes, offset: int):
    cards = []

    for index in range(offset, len(buffer) - 79, 80):
        card = buffer[index:index + 80]
        cards.append(card)

        if card[:8] == b"END     ":
            used = index + 80 - offset
            padded = ((used + 2879) // 2880) * 2880

            return (
                fits.Header.fromstring(
                    b"".join(cards).decode("ascii"),
                    sep="",
                ),
                padded,
            )

    raise ValueError("FITS header exceeds initial read")


def inspect(key: str) -> dict:
    initial = range_bytes(key, 0, 131071)

    primary, primary_size = _header(initial, 0)

    if int(primary.get("NAXIS", 0)) != 0:
        raise ValueError("Unexpected primary FITS data layout")

    header, header_size = _header(initial, primary_size)

    if (
        header.get("EXTNAME", "").strip() != "IMAGE"
        or header.get("NAXIS") != 2
    ):
        raise ValueError("First FITS extension is not a 2D IMAGE")

    w = WCS(header).celestial

    nx = int(header["NAXIS1"])
    ny = int(header["NAXIS2"])

    center = w.all_pix2world(
        [[(nx - 1) / 2, (ny - 1) / 2]],
        0,
    )[0]

    corners = w.all_pix2world(
        [
            [0, 0],
            [nx - 1, 0],
            [nx - 1, ny - 1],
            [0, ny - 1],
        ],
        0,
    )

    detector_match = re.search(r"/([1-6])/", key)

    return {
        "id": key,
        "file_key": key,
        "source": "NASA/IPAC SPHEREx public S3",
        "dataset": "QR3",
        "observation_type": "Level 2",
        "observation_date": header.get("DATE-OBS"),
        "detector": (
            int(detector_match.group(1))
            if detector_match
            else None
        ),
        "width": nx,
        "height": ny,
        "center_ra": round(float(center[0]) % 360, 6),
        "center_dec": round(float(center[1]), 6),
        "corners": [
            [
                round(float(ra) % 360, 6),
                round(float(dec), 6),
            ]
            for ra, dec in corners
        ],
        "brightness_unit": header.get("BUNIT"),
        "bitpix": int(header["BITPIX"]),
        "bscale": float(header.get("BSCALE", 1)),
        "bzero": float(header.get("BZERO", 0)),
        "pixel_offset": primary_size + header_size,
        "pixel_bytes": (
            nx * ny * (abs(int(header["BITPIX"])) // 8)
        ),
        "header": header.tostring(
            sep="\n",
            endcard=True,
            padding=False,
        ),
    }


def load_index() -> list[dict]:
    if not INDEX_PATH.exists():
        return []

    try:
        value = json.loads(
            INDEX_PATH.read_text(encoding="utf-8")
        )
        return value if isinstance(value, list) else []

    except (ValueError, OSError):
        return []


def _save(records):
    tmp = INDEX_PATH.with_suffix(".json.tmp")

    tmp.write_text(
        json.dumps(records, indent=2),
        encoding="utf-8",
    )

    tmp.replace(INDEX_PATH)


def ensure_sample() -> list[dict]:
    with _LOCK:
        records = load_index()

        if not any(
            r["id"] == SAMPLE_KEY for r in records
        ):
            records.append(inspect(SAMPLE_KEY))
            _save(records)

        return records


def list_keys(limit=16):
    import xml.etree.ElementTree as ET

    response = requests.get(
        BUCKET,
        params={
            "list-type": "2",
            "prefix": SCAN_PREFIX,
            "max-keys": str(min(limit + 5, 100)),
        },
        timeout=(15, 30),
    )

    response.raise_for_status()

    root = ET.fromstring(response.content)

    ns = {
        "s3": "http://s3.amazonaws.com/doc/2006-03-01/"
    }

    keys = []

    for el in root.findall(
        ".//s3:Contents/s3:Key",
        ns,
    ):
        if el.text and el.text.endswith(".fits"):
            keys.append(el.text)

        if len(keys) >= limit:
            break

    return keys


def refresh_index(limit=16):
    limit = max(1, min(int(limit), 24))

    records = ensure_sample()
    keys = list_keys(limit)
    errors = []

    for key in keys:
        if any(r["id"] == key for r in records):
            continue

        try:
            record = inspect(key)

            with _LOCK:
                records = load_index()

                if not any(
                    r["id"] == key for r in records
                ):
                    records.append(record)
                    _save(records)

        except Exception as exc:
            errors.append({
                "key": key,
                "error": str(exc),
            })

    return {
        "indexed": len(load_index()),
        "scanned": len(keys),
        "errors": errors,
        "coverage": (
            "Limited subset: one QR3 week, processing "
            "version and detector; NOT the full "
            "SPHEREx archive"
        ),
    }


def contains(record, ra, dec):
    try:
        header = fits.Header.fromstring(
            record["header"],
            sep="\n",
        )

        w = WCS(header).celestial

        x, y = w.all_world2pix(
            [[float(ra), float(dec)]],
            0,
        )[0]

        return bool(
            0 <= x < record["width"]
            and 0 <= y < record["height"]
        )

    except Exception:
        return False


def public_record(record):
    excluded = (
        "header",
        "pixel_offset",
        "pixel_bytes",
        "bitpix",
        "bscale",
        "bzero",
    )

    return {
        k: v
        for k, v in record.items()
        if k not in excluded
    }
