"""
Build a deployment staging folder for the Lonely Planet Travel Guide app (v2).

The repo carries print-resolution page scans and screenshots (~250 MB), far more
than a web page needs. This script copies the code, knowledge bases and embedding
model into `.deploy_build/`, re-encodes photos as web-sized JPEGs and quantises the
ONNX model to INT8 so the upload stays small. Originals are never modified.

Usage:
    python prepare_deploy.py
"""

from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
OUT = ROOT / ".deploy_build"
MAX_WIDTH = 900
JPEG_QUALITY = 82

CODE_FILES = [
    "app_simplified_original.py",
    "streamlit_app.py",
    "settings.py",
    "embedding_backend.py",
    "image_carousel.py",
    "image_service.py",
    "hotels_service.py",
    "hotel_pictures_service.py",
    "attractions_service.py",
    "restaurants_service.py",
    "city_selector.py",
    "weather_service.py",
    "world_map_selector.py",
    "map_selector.py",
    "travel_plan_designer.py",
    "requirements.txt",
    "README.md",
    "start.sh",
    "Animation rotate.webm",
]

ASSET_DIRS = ["knowledge_bases", "book_picture", "cover_picture"]
ASSET_FILES = ["web top background picture.jpg"]

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}


def _clean() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)


def _copy_code() -> None:
    for name in CODE_FILES:
        src = ROOT / name
        if src.exists():
            shutil.copy2(src, OUT / name)
    if (ROOT / ".streamlit").exists():
        shutil.copytree(ROOT / ".streamlit", OUT / ".streamlit", dirs_exist_ok=True)


def _copy_model() -> None:
    shutil.copytree(ROOT / "models", OUT / "models", dirs_exist_ok=True)
    _quantize_model_for_deploy()


def _quantize_model_for_deploy() -> None:
    """Swap the FP32 ONNX model for an INT8 copy in the staging folder (~23 MB)."""
    onnx_path = OUT / "models" / "all-MiniLM-L6-v2" / "model.onnx"
    try:
        from onnxruntime.quantization import QuantType, quantize_dynamic
    except ImportError:
        print("onnxruntime not available - deploying the FP32 model as-is")
        return

    tmp = onnx_path.with_suffix(".int8.tmp.onnx")
    quantize_dynamic(str(onnx_path), str(tmp), weight_type=QuantType.QInt8)
    onnx_path.unlink()
    tmp.rename(onnx_path)
    print(f"quantized deploy model: {onnx_path.stat().st_size / 1e6:.1f} MB (int8)")


def _convert_image(src: Path, dst: Path) -> None:
    """Resize to MAX_WIDTH and save as JPEG to keep the payload small."""
    with Image.open(src) as im:
        im = im.convert("RGB")
        if im.width > MAX_WIDTH:
            im = im.resize((MAX_WIDTH, round(im.height * MAX_WIDTH / im.width)), Image.LANCZOS)
        im.save(dst, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)


def _copy_images() -> None:
    """Copy data folders, converting photos to web-sized JPEGs."""
    for folder in ASSET_DIRS:
        src_root = ROOT / folder
        if not src_root.exists():
            continue
        if folder == "knowledge_bases":
            shutil.copytree(src_root, OUT / folder, dirs_exist_ok=True)
            continue
        for src in src_root.rglob("*"):
            if not src.is_file() or src.suffix.lower() not in IMAGE_EXT:
                continue
            dst = OUT / src.relative_to(ROOT)
            dst.parent.mkdir(parents=True, exist_ok=True)
            _convert_image(src, dst.with_suffix(".jpg"))

    for name in ASSET_FILES:
        src = ROOT / name
        if src.exists():
            # Keep the original filename/format: the app looks for the .png banner.
            with Image.open(src) as im:
                im = im.convert("RGB")
                if im.width > 1400:
                    im = im.resize((1400, round(im.height * 1400 / im.width)), Image.LANCZOS)
                im.save(OUT / name, optimize=True)


def _report() -> None:
    total = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
    print(f"staging folder: {OUT}")
    print(f"files: {sum(1 for p in OUT.rglob('*') if p.is_file())}, size: {total / 1e6:.1f} MB")


if __name__ == "__main__":
    _clean()
    _copy_code()
    _copy_model()
    _copy_images()
    _report()
