
import requests
import xml.etree.ElementTree as ET

url = "https://nasa-irsa-spherex.s3.amazonaws.com/"

params = {
    "list-type": "2",
    "prefix": "qr3/level2/2026W20_2A/l2b-v27-2026-267/1/",
    "delimiter": "/",
    "max-keys": "10"
}

try:
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()

    root = ET.fromstring(response.content)
    ns = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}

    print("SUCCESS: Connected to NASA SPHEREx S3")
    print("Requested prefix:", params["prefix"])

    folders = root.findall(".//s3:CommonPrefixes/s3:Prefix", ns)
    files = root.findall(".//s3:Contents", ns)

    print("\nFolders:")
    for folder in folders:
        print(folder.text)

    print("\nFiles:")
    for file in files:
        name = file.find("s3:Key", ns).text
        size = int(file.find("s3:Size", ns).text)

        print(f"{name}")
        print(f"Size: {size / (1024 * 1024):.2f} MB\n")

    if not folders and not files:
        print("No objects found under this prefix.")

except Exception as e:
    print("ERROR:", type(e).__name__, str(e))
