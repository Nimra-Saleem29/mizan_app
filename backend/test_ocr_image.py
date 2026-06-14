"""
Test OCR with a real image to diagnose the FIR analyzer issue.
Place any image file in the same folder and update IMAGE_PATH below.
"""
import sys
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import io

pytesseract.pytesseract.tesseract_cmd = 'C:/Program Files/Tesseract-OCR/tesseract.exe'

# ── Test with a real image ────────────────────────────────────────────────────
# Change this to the path of any image on your computer
IMAGE_PATH = r"C:\Users\dures\Downloads\234644-fir_rabwah_june-1313701432-640x480.jpg"

try:
    print(f"Opening image: {IMAGE_PATH}")
    with open(IMAGE_PATH, 'rb') as f:
        image_bytes = f.read()
    print(f"File size: {len(image_bytes):,} bytes")

    # Replicate exact preprocessing from fir_analyzer.py
    img = Image.open(io.BytesIO(image_bytes))
    print(f"Image mode: {img.mode}, size: {img.size}")

    if img.mode != "RGB":
        img = img.convert("RGB")
    img = img.convert("L")
    img = ImageEnhance.Contrast(img).enhance(2.0)
    img = ImageEnhance.Sharpness(img).enhance(2.0)

    width, height = img.size
    if width < 1000:
        scale = 1000 / width
        img = img.resize(
            (int(width * scale), int(height * scale)),
            Image.LANCZOS,
        )
        print(f"Upscaled to: {img.size}")

    img = img.filter(ImageFilter.MedianFilter(size=3))

    custom_config = "--oem 3 --psm 6 -l urd+eng"
    print("Running OCR...")
    text = pytesseract.image_to_string(img, config=custom_config)
    print(f"OCR extracted {len(text.strip())} characters")
    print("First 300 chars:", repr(text[:300]))

except FileNotFoundError:
    print(f"ERROR: Image not found at {IMAGE_PATH}")
    print("Update IMAGE_PATH in this script to point to your FIR image.")
except Exception as exc:
    print(f"ERROR: {type(exc).__name__}: {exc}")
    import traceback
    traceback.print_exc()
