import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = 'C:/Program Files/Tesseract-OCR/tesseract.exe'

# Test 1 - version
print("Tesseract version:", pytesseract.get_tesseract_version())

# Test 2 - available languages
print("Languages:", pytesseract.get_languages())

# Test 3 - simple OCR
img = Image.new('RGB', (200, 50), color='white')
result = pytesseract.image_to_string(img, config='--oem 3 --psm 6 -l urd+eng')
print("OCR test passed:", repr(result))
