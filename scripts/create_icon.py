"""
Logo-Konverter: assets/logo.png  →  assets/logo.ico
Aufruf: python scripts/create_icon.py

Voraussetzung: Pillow (pip install Pillow)
Das Ergebnis (assets/logo.ico) wird automatisch vom Build-Prozess verwendet.
"""

from pathlib import Path
from PIL import Image

LOGO_PNG = Path(__file__).resolve().parent.parent / "assets" / "logo.png"
LOGO_ICO = LOGO_PNG.with_suffix(".ico")


def convert() -> None:
    if not LOGO_PNG.exists():
        raise FileNotFoundError(
            f"Logo nicht gefunden: {LOGO_PNG}\n"
            "Bitte das Logo als 'assets/logo.png' speichern und erneut ausführen."
        )

    img = Image.open(LOGO_PNG).convert("RGBA")

    # ICO mit mehreren Größen für saubere Darstellung in Windows
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    icons = []
    for size in sizes:
        resized = img.resize(size, Image.LANCZOS)
        icons.append(resized)

    icons[0].save(
        LOGO_ICO,
        format="ICO",
        sizes=[(i.width, i.height) for i in icons],
        append_images=icons[1:],
    )
    print(f"ICO erstellt: {LOGO_ICO}")


if __name__ == "__main__":
    convert()
