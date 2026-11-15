
import requests
from astropy.io import fits
from io import BytesIO
from astropy.wcs import WCS

bucket = "https://nasa-irsa-spherex.s3.amazonaws.com/"

file_key = (
    "qr3/level2/2026W20_2A/"
    "l2b-v27-2026-267/1/"
    "level2_2026W20_2A_0001_1D1_spx_l2b-v27-2026-267.fits"
)

url = bucket + file_key

print("Connecting to NASA SPHEREx S3...")
print("Reading the first 64 KB of the FITS file...")

try:
    response = requests.get(
        url,
        headers={"Range": "bytes=0-65535"},
        timeout=60
    )
    response.raise_for_status()

    print("HTTP Status:", response.status_code)
    print("Bytes received:", len(response.content))

    if response.status_code != 206:
        print("Server did not honor the Range request.")
        print("Skipping FITS parsing.")
    else:
        # A FITS header consists of 80-character cards,
        # padded to a multiple of 2880 bytes.
        # Read only the primary FITS header.
        # FITS header cards are 80 bytes each.
        header_bytes = bytearray()

        for i in range(0, len(response.content), 80):
            card = response.content[i:i + 80]

            if len(card) < 80:
                break

            header_bytes.extend(card)

            if card.startswith(b"END" + b" " * 5):
                break

        header = fits.Header.fromstring(
            header_bytes.decode("ascii"),
            sep=""
        )

        print("\n===== SPHEREx FITS HEADER =====")
        print(header)
        print("\n===== FITS EXTENSIONS =====")

        # Primary header occupies one 2880-byte FITS block.
        offset = 2880

        for extension_number in range(1, 4):
            try:
                extension_header = fits.Header.fromstring(
                    response.content[offset:].decode(
                        "ascii", errors="ignore"
                    ),
                    sep=""
                )

                print(f"\nExtension {extension_number}")
                print("EXTNAME:", extension_header.get("EXTNAME"))
                print("NAXIS:", extension_header.get("NAXIS"))
                print("NAXIS1:", extension_header.get("NAXIS1"))
                print("NAXIS2:", extension_header.get("NAXIS2"))
                print("DATE-OBS:", extension_header.get("DATE-OBS"))
                print("CRVAL1:", extension_header.get("CRVAL1"))
                print("CRVAL2:", extension_header.get("CRVAL2"))
                print("\n===== IMAGE WCS METADATA =====")

                for key in [
                    "CTYPE1", "CTYPE2",
                    "CRPIX1", "CRPIX2",
                    "CRVAL1", "CRVAL2",
                    "CD1_1", "CD1_2",
                    "CD2_1", "CD2_2",
                    "CDELT1", "CDELT2",
                    "CUNIT1", "CUNIT2",
                    "DATE-OBS", "MJD-OBS",
                    "EXPTIME", "BUNIT"
                ]:
                    print(f"{key}: {extension_header.get(key)}")

                print("\n===== COMPLETE WCS KEYWORDS =====")

                for key, value in extension_header.items():
                    if key.startswith((
                        "PC", "CD", "CR", "CTYP", "CUNI",
                        "A_", "B_", "AP_", "BP_"
                    )) or key in (
                        "A_ORDER", "B_ORDER",
                        "AP_ORDER", "BP_ORDER"
                    ):
                        print(f"{key}: {value}")


                print("\n===== SKY FOOTPRINT =====")

                wcs = WCS(extension_header, key=" ")

                width = extension_header["NAXIS1"]
                height = extension_header["NAXIS2"]

                # Pixel coordinates use zero-based indexing.
                corners = [
                    (0, 0),
                    (width - 1, 0),
                    (width - 1, height - 1),
                    (0, height - 1)
                ]

                for index, (x, y) in enumerate(corners, start=1):
                    ra, dec = wcs.all_pix2world(x, y, 0)
                    print(
                        f"Corner {index}: "
                        f"RA={ra:.6f}, Dec={dec:.6f}"
                    )

                center_ra, center_dec = wcs.all_pix2world(
                    (width - 1) / 2,
                    (height - 1) / 2,
                    0
                )

                print(
                    f"\nImage center: "
                    f"RA={center_ra:.6f}, "
                    f"Dec={center_dec:.6f}"
                )


                break

            except Exception as e:
                print("Could not parse extension:", e)
                break


except Exception as e:
    print("ERROR:", type(e).__name__, str(e))
