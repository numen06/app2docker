"""Resize landing page screenshots for ProductMockup."""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1] / "frontend" / "public" / "landing"

VARIANTS = {
    "dashboard": ("dashboard-raw.png", "dashboard.webp", 840, 472),
    "pipeline": ("pipeline-raw.png", "pipeline.webp", 480, 270),
    "team": ("team-raw.png", "team.webp", 480, 270),
    "deploy": ("deploy-raw.png", "deploy.webp", 480, 270),
}


def cover_crop(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    scale = max(target_w / img.width, target_h / img.height)
    new_w = round(img.width * scale)
    new_h = round(img.height * scale)
    resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    left = max(0, (new_w - target_w) // 2)
    top = 0
    return resized.crop((left, top, left + target_w, top + target_h))


def main() -> None:
    for _key, (raw_name, out_name, w, h) in VARIANTS.items():
        raw_path = ROOT / raw_name
        out_path = ROOT / out_name
        if not raw_path.exists():
            raise FileNotFoundError(raw_path)
        with Image.open(raw_path) as img:
            rgb = img.convert("RGB") if img.mode in ("RGBA", "P") else img
            cropped = cover_crop(rgb, w, h)
            cropped.save(out_path, "WEBP", quality=84, method=6)
            print(f"{out_name}: {w}x{h} ({out_path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
