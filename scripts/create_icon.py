"""
Logo-Generator und -Konverter für Min Guata Lada.
Erstellt assets/logo.png (falls nicht vorhanden) und assets/logo.ico.
Aufruf: python scripts/create_icon.py

Voraussetzung: Pillow (pip install Pillow)
"""

from pathlib import Path
from PIL import Image, ImageDraw

LOGO_PNG = Path(__file__).resolve().parent.parent / "assets" / "logo.png"
LOGO_ICO = LOGO_PNG.with_suffix(".ico")


def _generate_logo(size: int = 256) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    m = int(size * 0.031)
    cx = cy = size // 2

    draw.ellipse([m, m, size - m, size - m], fill=(35, 131, 226, 255))
    inner_m = int(size * 0.109)
    draw.ellipse([inner_m, inner_m, size - inner_m, size - inner_m], fill=(255, 255, 255, 18))

    # Plate
    pr = int(size * 0.266)
    draw.ellipse([cx - pr, cy - pr, cx + pr, cy + pr], outline=(255, 255, 255, 230), width=max(4, size // 36))
    pr2 = int(size * 0.172)
    draw.ellipse([cx - pr2, cy - pr2, cx + pr2, cy + pr2], outline=(255, 255, 255, 150), width=max(2, size // 64))

    # Fork
    fx = cx - int(size * 0.344)
    tine_top = cy - int(size * 0.211)
    tine_bot = cy - int(size * 0.070)
    handle_bot = cy + int(size * 0.211)
    w = max(2, size // 64)
    for dx in (-int(size * 0.016), 0, int(size * 0.016)):
        draw.line([fx + dx, tine_top, fx + dx, tine_bot], fill=(255, 255, 255, 230), width=w)
    draw.line([fx, tine_bot, fx, handle_bot], fill=(255, 255, 255, 230), width=max(3, size // 42))

    # Knife
    kx = cx + int(size * 0.344)
    draw.line([kx, tine_top, kx, handle_bot], fill=(255, 255, 255, 230), width=max(3, size // 42))
    bw = int(size * 0.035)
    draw.polygon([(kx, tine_top), (kx + bw, tine_bot), (kx, tine_bot)], fill=(255, 255, 255, 230))

    return img


def create() -> None:
    LOGO_PNG.parent.mkdir(parents=True, exist_ok=True)
    if not LOGO_PNG.exists():
        img = _generate_logo(256)
        img.save(LOGO_PNG, "PNG")
        print(f"PNG erstellt: {LOGO_PNG}")
    else:
        img = Image.open(LOGO_PNG).convert("RGBA")
        print(f"PNG vorhanden: {LOGO_PNG}")

    ico_sizes = [16, 24, 32, 48, 64, 128, 256]
    frames = [img.resize((s, s), Image.LANCZOS) for s in ico_sizes]
    frames[0].save(
        LOGO_ICO,
        format="ICO",
        sizes=[(s, s) for s in ico_sizes],
        append_images=frames[1:],
    )
    print(f"ICO erstellt: {LOGO_ICO}")


if __name__ == "__main__":
    create()
