"""
Wakeel وکیل — FIR Analyzer Service
=====================================
Analyses First Information Reports (FIRs) filed under Pakistani law.

Pipeline:
  1. OCR  → pytesseract extracts Urdu+English text from image
  2. Parse → regex identifies PPC/CrPC section numbers
  3. Lookup → PPC_SECTIONS dict maps numbers to legal metadata
  4. Flags → procedural checklist (signature, date, seal, rights)
  5. AI   → Gemini Flash generates plain-Urdu explanation + rights

Usage:
    analyzer = FIRAnalyzer()
    text     = await analyzer.extract_text_from_image(image_bytes)
    result   = await analyzer.analyze_fir(text)
"""

import io
import re
import time
from typing import Any

import google.generativeai as genai
import pytesseract
from loguru import logger
from PIL import Image, ImageEnhance, ImageFilter

from config import settings
from models.schemas import FIRAnalysisResponse, FIRSection


# ─────────────────────────────────────────────────────────────────────────────
# PPC / Special Laws Knowledge Base
# ─────────────────────────────────────────────────────────────────────────────
# Structure per entry:
#   title          → official offence title (English)
#   title_ur       → Urdu title
#   min_punishment → minimum sentence
#   max_punishment → maximum sentence / penalty
#   bailable       → True if the accused can be granted bail as of right
#   cognizable     → True if police can arrest without a warrant
#   act            → legislation (default PPC = Pakistan Penal Code 1860)
#   description    → brief plain-English description

PPC_SECTIONS: dict[str, dict[str, Any]] = {

    # ── Offences Against the Person ──────────────────────────────────────────
    "299": {
        "title": "Hurt — Definitions",
        "title_ur": "ایذا — تعریفات",
        "min_punishment": "N/A (definitional)",
        "max_punishment": "N/A (definitional)",
        "bailable": True,
        "cognizable": False,
        "act": "PPC",
        "description": "Defines categories of hurt (itlaf-i-udw, shajjah, etc.) under Qisas/Diyat.",
    },
    "300": {
        "title": "Murder — Qatl-i-Amd (Definition)",
        "title_ur": "قتلِ عمد — تعریف",
        "min_punishment": "N/A (definitional)",
        "max_punishment": "N/A (definitional)",
        "bailable": False,
        "cognizable": True,
        "act": "PPC",
        "description": "Defines intentional murder (Qatl-i-Amd). Punishment prescribed in s.302.",
    },
    "302": {
        "title": "Murder (Qatl-i-Amd) — Punishment",
        "title_ur": "قتلِ عمد — سزا",
        "min_punishment": "Death or imprisonment for life (if Wali waives Qisas)",
        "max_punishment": "Death (Qisas) or Diyat",
        "bailable": False,
        "cognizable": True,
        "act": "PPC",
        "description": (
            "Intentional killing of a human being. "
            "The most serious charge in Pakistani criminal law. "
            "Non-bailable; the accused will be remanded in custody."
        ),
    },
    "304": {
        "title": "Culpable Homicide Not Amounting to Murder",
        "title_ur": "غیر قصداً قتل",
        "min_punishment": "2 years imprisonment",
        "max_punishment": "25 years imprisonment or fine",
        "bailable": False,
        "cognizable": True,
        "act": "PPC",
        "description": "Killing without the intent required for murder under s.302.",
    },
    "307": {
        "title": "Attempt to Commit Qatl-i-Amd",
        "title_ur": "قتل کی کوشش",
        "min_punishment": "Diyat",
        "max_punishment": "Death (if grievous hurt caused)",
        "bailable": False,
        "cognizable": True,
        "act": "PPC",
        "description": "Attempted murder. Carries Diyat; may extend to death if serious injury results.",
    },
    "324": {
        "title": "Attempted Murder / Attempt to Cause Hurt",
        "title_ur": "قتل کی کوشش / ایذا پہنچانے کی کوشش",
        "min_punishment": "Diyat (monetary compensation)",
        "max_punishment": "Imprisonment for life",
        "bailable": False,
        "cognizable": True,
        "act": "PPC",
        "description": (
            "Attempting to commit an act with intention to cause hurt "
            "or with knowledge that hurt is likely to result. Non-bailable."
        ),
    },
    "34": {
        "title": "Acts Done by Several Persons in Furtherance of Common Intention",
        "title_ur": "مشترکہ ارادے کے تحت فعل",
        "min_punishment": "Same as principal offence",
        "max_punishment": "Same as principal offence",
        "bailable": False,
        "cognizable": True,
        "act": "PPC",
        "description": (
            "Joint liability provision. When two or more persons act together, "
            "each is liable as if they had committed the act alone."
        ),
    },
    "109": {
        "title": "Abetment",
        "title_ur": "اکسانا / اعانت",
        "min_punishment": "Same as principal offence",
        "max_punishment": "Same as principal offence",
        "bailable": False,
        "cognizable": True,
        "act": "PPC",
        "description": (
            "Instigating, conspiring, or intentionally aiding another to commit an offence. "
            "The abettor is punished as if they committed the act."
        ),
    },
    "149": {
        "title": "Every Member of an Unlawful Assembly Guilty of Offence",
        "title_ur": "غیر قانونی اجتماع",
        "min_punishment": "6 months",
        "max_punishment": "2 years or fine",
        "bailable": False,
        "cognizable": True,
        "act": "PPC",
        "description": "Members of an unlawful assembly share liability for any offence committed in pursuit of the common object.",
    },

    # ── Sexual Offences ───────────────────────────────────────────────────────
    "354": {
        "title": "Assault or Criminal Force to Woman with Intent to Outrage Her Modesty",
        "title_ur": "عورت کی آبرو کو ٹھیس پہنچانا",
        "min_punishment": "2 years imprisonment",
        "max_punishment": "10 years imprisonment and fine",
        "bailable": False,
        "cognizable": True,
        "act": "PPC",
        "description": (
            "Using criminal force against a woman intending to outrage her modesty. "
            "Non-bailable; police can arrest without warrant."
        ),
    },
    "376": {
        "title": "Rape (Zina-bil-Jabr)",
        "title_ur": "زنا بالجبر",
        "min_punishment": "10 years imprisonment and lashes (hadd) or tazir",
        "max_punishment": "Death or 25 years imprisonment",
        "bailable": False,
        "cognizable": True,
        "act": "PPC",
        "description": (
            "One of the most serious offences. Non-bailable. "
            "Investigation must be conducted sensitively; "
            "victim has the right to a female medical officer."
        ),
    },
    "377": {
        "title": "Unnatural Offences",
        "title_ur": "غیر فطری جرم",
        "min_punishment": "2 years imprisonment",
        "max_punishment": "Life imprisonment or death",
        "bailable": False,
        "cognizable": True,
        "act": "PPC",
        "description": "Carnal intercourse against the order of nature.",
    },

    # ── Property / Fraud ──────────────────────────────────────────────────────
    "380": {
        "title": "Theft in Dwelling House",
        "title_ur": "گھر میں چوری",
        "min_punishment": "1 year",
        "max_punishment": "7 years imprisonment and fine",
        "bailable": False,
        "cognizable": True,
        "act": "PPC",
        "description": "Theft committed inside a dwelling house or building used for the custody of property.",
    },
    "392": {
        "title": "Robbery",
        "title_ur": "ڈکیتی",
        "min_punishment": "4 years",
        "max_punishment": "10 years imprisonment and fine",
        "bailable": False,
        "cognizable": True,
        "act": "PPC",
        "description": "Theft or extortion with use or threat of force.",
    },
    "395": {
        "title": "Dacoity (Gang Robbery)",
        "title_ur": "ڈاکہ",
        "min_punishment": "10 years",
        "max_punishment": "Imprisonment for life",
        "bailable": False,
        "cognizable": True,
        "act": "PPC",
        "description": "Robbery committed by five or more persons. Non-bailable.",
    },
    "406": {
        "title": "Criminal Breach of Trust",
        "title_ur": "امانت میں خیانت",
        "min_punishment": "1 year or fine",
        "max_punishment": "3 years imprisonment and fine",
        "bailable": False,
        "cognizable": True,
        "act": "PPC",
        "description": "Dishonest misappropriation of property entrusted to the accused.",
    },
    "420": {
        "title": "Cheating and Dishonestly Inducing Delivery of Property (Fraud)",
        "title_ur": "دھوکہ دہی",
        "min_punishment": "1 year or fine",
        "max_punishment": "7 years imprisonment and fine",
        "bailable": False,
        "cognizable": True,
        "act": "PPC",
        "description": (
            "Fraudulently inducing another to deliver property or alter/destroy "
            "a valuable security. Very commonly charged in commercial disputes."
        ),
    },
    "468": {
        "title": "Forgery for Purpose of Cheating",
        "title_ur": "جعلسازی",
        "min_punishment": "1 year",
        "max_punishment": "7 years imprisonment and fine",
        "bailable": False,
        "cognizable": True,
        "act": "PPC",
        "description": "Making a false document intending it to be used for cheating.",
    },
    "471": {
        "title": "Using Forged Document as Genuine",
        "title_ur": "جعلی دستاویز استعمال کرنا",
        "min_punishment": "2 years",
        "max_punishment": "Same as forgery (s.465 onwards)",
        "bailable": False,
        "cognizable": True,
        "act": "PPC",
        "description": "Fraudulently or dishonestly using a forged document as genuine.",
    },
    "489-F": {
        "title": "Dishonoured Cheque",
        "title_ur": "بے قدر چیک",
        "min_punishment": "Fine equivalent to cheque amount",
        "max_punishment": "3 years imprisonment or fine or both",
        "bailable": True,
        "cognizable": False,
        "act": "PPC",
        "description": (
            "Issuing a cheque knowing it will be dishonoured. "
            "One of the few bailable financial offences. "
            "Very common in business disputes across Pakistan."
        ),
    },

    # ── Public Order / Intimidation ───────────────────────────────────────────
    "186": {
        "title": "Obstructing Public Servant in Discharge of Public Functions",
        "title_ur": "سرکاری افسر کو روکنا",
        "min_punishment": "Fine",
        "max_punishment": "3 months imprisonment or Rs 500 fine or both",
        "bailable": True,
        "cognizable": False,
        "act": "PPC",
        "description": "Voluntarily obstructing a public servant performing their duties.",
    },
    "447": {
        "title": "Criminal Trespass",
        "title_ur": "غیر قانونی داخلہ",
        "min_punishment": "Fine",
        "max_punishment": "3 months imprisonment or Rs 500 fine or both",
        "bailable": True,
        "cognizable": False,
        "act": "PPC",
        "description": (
            "Entering or remaining on property in another's possession "
            "with intent to commit an offence or intimidate. "
            "Bailable offence; commonly used in property disputes."
        ),
    },
    "448": {
        "title": "House Trespass",
        "title_ur": "گھر میں غیر قانونی داخلہ",
        "min_punishment": "Fine",
        "max_punishment": "1 year imprisonment or fine or both",
        "bailable": True,
        "cognizable": False,
        "act": "PPC",
        "description": "Criminal trespass committed in a human dwelling or place of worship.",
    },
    "452": {
        "title": "House Trespass After Preparation for Hurt / Assault",
        "title_ur": "مار پیٹ کی نیت سے گھر میں داخلہ",
        "min_punishment": "1 year",
        "max_punishment": "7 years imprisonment and fine",
        "bailable": False,
        "cognizable": True,
        "act": "PPC",
        "description": "House trespass with intent to cause hurt, assault, or wrongful restraint.",
    },
    "506": {
        "title": "Criminal Intimidation",
        "title_ur": "ڈرانا دھمکانا",
        "min_punishment": "Fine",
        "max_punishment": (
            "2 years imprisonment or fine or both (s.506 Part I); "
            "7 years if threat is to cause death or grievous hurt (Part II)"
        ),
        "bailable": True,
        "cognizable": False,
        "act": "PPC",
        "description": (
            "Threatening to cause injury to a person, their reputation, or property "
            "to cause alarm or compel them to do/abstain from an act. "
            "Part I is bailable; Part II (death threat) is non-bailable."
        ),
    },
    "511": {
        "title": "Punishment for Attempting to Commit Offences",
        "title_ur": "جرم کرنے کی کوشش",
        "min_punishment": "Varies (half the maximum for completed offence)",
        "max_punishment": "Up to half of maximum for the completed offence",
        "bailable": False,
        "cognizable": True,
        "act": "PPC",
        "description": "General attempt provision — applies when no specific attempt section exists.",
    },

    # ── Blasphemy / Religion (highly sensitive; handle with care) ─────────────
    "295-A": {
        "title": "Deliberate Acts Intended to Outrage Religious Feelings",
        "title_ur": "مذہبی جذبات کو ٹھیس پہنچانا",
        "min_punishment": "Fine",
        "max_punishment": "3 years imprisonment or fine or both",
        "bailable": False,
        "cognizable": True,
        "act": "PPC",
        "description": "Deliberate acts intended to outrage religious feelings of any class.",
    },
    "295-B": {
        "title": "Defiling the Holy Quran",
        "title_ur": "قرآن پاک کی بے حرمتی",
        "min_punishment": "Imprisonment for life",
        "max_punishment": "Imprisonment for life",
        "bailable": False,
        "cognizable": True,
        "act": "PPC",
        "description": "Wilful desecration of a copy of the Holy Quran.",
    },
    "295-C": {
        "title": "Use of Derogatory Remarks about the Prophet (PBUH)",
        "title_ur": "توہینِ رسالت",
        "min_punishment": "Death",
        "max_punishment": "Death",
        "bailable": False,
        "cognizable": True,
        "act": "PPC",
        "description": (
            "Use of derogatory remarks in respect of the Holy Prophet (PBUH). "
            "Mandatory death sentence. Extremely serious charge."
        ),
    },

    # ── PECA (Cyber Crime Act 2016) ────────────────────────────────────────────
    "PECA-10": {
        "title": "Cyber Stalking (PECA s.10)",
        "title_ur": "سائبر ہراسانی",
        "min_punishment": "1 year imprisonment",
        "max_punishment": "3 years imprisonment or Rs 1 million fine or both",
        "bailable": False,
        "cognizable": True,
        "act": "PECA 2016",
        "description": "Online stalking, harassment, or intimidation of a person.",
    },
    "PECA-20": {
        "title": "Online Defamation (PECA s.20)",
        "title_ur": "آن لائن بدنامی",
        "min_punishment": "Fine",
        "max_punishment": "3 years imprisonment or Rs 1 million fine or both",
        "bailable": False,
        "cognizable": True,
        "act": "PECA 2016",
        "description": "Intentionally and publicly exhibiting a false statement about another person online.",
    },
}

# Section numbers that carry the death penalty or life imprisonment
CAPITAL_SECTIONS: frozenset[str] = frozenset({
    "302", "307", "376", "395", "295-B", "295-C",
})

# Rights that apply whenever ANY non-bailable offence is present
UNIVERSAL_RIGHTS_NON_BAILABLE: list[str] = [
    "آپ کو فوری طور پر گرفتاری کی وجہ بتانے کا حق ہے۔ (Article 10, Constitution of Pakistan)",
    "آپ کو اپنی پسند کا وکیل کرنے کا حق ہے — اگر وکیل نہیں کر سکتے تو سرکاری وکیل فراہم ہوگا۔",
    "24 گھنٹے کے اندر مجسٹریٹ کے سامنے پیش کیا جانا ضروری ہے۔ (Section 61 CrPC)",
    "پولیس ریمانڈ صرف مجسٹریٹ کے حکم سے دیا جا سکتا ہے — زیادہ سے زیادہ 15 دن۔",
    "آپ کو خود کے خلاف گواہی دینے پر مجبور نہیں کیا جا سکتا۔ (Article 13, Constitution)",
    "تشدد یا دھمکی سے لیا گیا اقرارِ جرم قابلِ قبول نہیں ہے۔ (Qanun-e-Shahadat Order, Art. 38)",
]

UNIVERSAL_RIGHTS_BAILABLE: list[str] = [
    "ضمانت قابل جرم ہے — آپ ضمانت کے حقدار ہیں۔ پولیس ضمانت دینے سے انکار نہیں کر سکتی۔",
    "آپ کو گرفتاری کی وجہ بتانے کا حق ہے۔",
    "آپ اپنا وکیل کر سکتے ہیں۔",
]


# ─────────────────────────────────────────────────────────────────────────────
# Gemini client (module-level singleton, lazy-init)
# ─────────────────────────────────────────────────────────────────────────────
_gemini_model = None


def _get_gemini():
    """Lazy-initialises the Gemini Flash model. Thread-safe via GIL."""
    global _gemini_model
    if _gemini_model is None:
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY not set in environment.")
        genai.configure(api_key=settings.GEMINI_API_KEY)
        _gemini_model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            generation_config=genai.GenerationConfig(
                temperature=settings.GEMINI_TEMPERATURE,
                max_output_tokens=settings.GEMINI_MAX_TOKENS,
            ),
            safety_settings=[
                {"category": "HARM_CATEGORY_HATE_SPEECH",       "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ],
        )
    return _gemini_model


# ─────────────────────────────────────────────────────────────────────────────
# FIRAnalyzer
# ─────────────────────────────────────────────────────────────────────────────
class FIRAnalyzer:
    """
    Analyses Pakistani FIR documents through OCR, static analysis,
    and Gemini-powered plain-language explanation.
    """

    # ── Regex patterns for section extraction ─────────────────────────────────
    # Matches all common ways a section number appears in a Pakistani FIR:
    #   English  : "Section 302", "section 302/34", "u/s 302", "u/s. 302",
    #              "under section 302", "U/S 302 PPC"
    #   Urdu     : "دفعہ ۳۰۲", "دفعہ 302" (both Urdu and Arabic-Indic digits)
    #   PECA     : "PECA 20", "Section 20 PECA"
    _SECTION_PATTERNS: list[re.Pattern] = [
        # English variants
        re.compile(
            r'\b(?:u/s\.?|under\s+section|section)\s+'
            r'(\d{2,3}(?:-[A-F])?(?:/\d{2,3}(?:-[A-F])?)*)',
            re.IGNORECASE,
        ),
        # Standalone "302 PPC" or "302/34 PPC"
        re.compile(
            r'\b(\d{2,3}(?:-[A-F])?)(?:/(\d{2,3}(?:-[A-F])?))*\s+(?:PPC|CrPC|PECA|MPA)',
            re.IGNORECASE,
        ),
        # Urdu: دفعہ followed by Arabic or ASCII digits
        re.compile(
            r'دفعہ\s+([0-9\u06F0-\u06F9]{2,3}(?:-[A-F])?)',
            re.IGNORECASE,
        ),
        # PECA-specific: "PECA s.10" / "PECA section 20"
        re.compile(
            r'PECA\s+(?:s\.|section\s+)?(\d{1,2})',
            re.IGNORECASE,
        ),
    ]

    # Urdu Arabic-Indic → ASCII digit map
    _URDU_DIGIT_MAP = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")

    # ── Procedural flag patterns ───────────────────────────────────────────────
    _FLAG_CHECKS: list[tuple[str, list[re.Pattern], str]] = [
        (
            "signature_missing",
            [
                re.compile(r'دستخط|signature|signed|فریادی کے دستخط', re.IGNORECASE),
            ],
            "فریادی کا دستخط نہیں ملا — یہ FIR ناقص ہو سکتی ہے۔ "
            "(Complainant signature not found — FIR may be incomplete.)",
        ),
        (
            "date_missing",
            [
                re.compile(r'\b\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}\b'),            # 01/01/2024
                re.compile(r'\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4}\b', re.IGNORECASE),
                re.compile(r'تاریخ|مورخہ'),                                          # Urdu date label
                re.compile(r'\b\d{4}\b'),                                            # bare year
            ],
            "FIR میں تاریخ درج نہیں — یہ قانونی خامی ہے۔ "
            "(No date found in FIR — this is a procedural defect.)",
        ),
        (
            "station_seal_missing",
            [
                re.compile(r'مہر|seal|stamp|تھانہ', re.IGNORECASE),
            ],
            "پولیس اسٹیشن کی مہر یا سیل نظر نہیں آئی — دستاویز کی تصدیق ضروری ہے۔ "
            "(Police station seal/stamp not detected — document authenticity unverified.)",
        ),
        (
            "fir_number_missing",
            [
                re.compile(r'FIR\s*No\.?\s*\d+|مقدمہ\s+نمبر|کیس\s+نمبر', re.IGNORECASE),
            ],
            "FIR نمبر درج نہیں — رجسٹریشن میں مسئلہ ہو سکتا ہے۔ "
            "(FIR number not found — registration may be incomplete.)",
        ),
    ]

    # ── Metadata extraction patterns ──────────────────────────────────────────
    _FIR_NUMBER_RE    = re.compile(r'FIR\s*No\.?\s*(\d+)', re.IGNORECASE)
    _CASE_NUMBER_RE   = re.compile(r'(?:مقدمہ|کیس)\s+نمبر\s+([0-9\u06F0-\u06F9]+)')
    _DATE_RE          = re.compile(r'(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})')
    _STATION_RE       = re.compile(r'(?:تھانہ|police\s+station)[:\s]+([^\n،,]{3,40})', re.IGNORECASE)
    _DISTRICT_RE      = re.compile(r'(?:ضلع|district)[:\s]+([^\n،,]{3,30})', re.IGNORECASE)

    # ─────────────────────────────────────────────────────────────────────────
    def extract_text_from_image(self, image_bytes: bytes) -> str:
        """
        Runs Tesseract OCR on a raw image (JPEG/PNG/TIFF bytes).

        Pre-processing pipeline applied before OCR:
          1. Open with Pillow — handles any supported format
          2. Convert to RGB → then Grayscale (L mode)
          3. Enhance contrast ×2.0  — FIR documents are often faded
          4. Sharpen once           — improves character edges
          5. Upscale if small       — Tesseract accuracy drops below 300 DPI
          6. Run tesseract with urd+eng + PSM 6 (uniform block of text)

        Returns the extracted text string (may be empty on very poor images).
        """
        start = time.perf_counter()

        try:
            img = Image.open(io.BytesIO(image_bytes))
        except Exception as exc:
            raise ValueError(f"Cannot decode image: {exc}") from exc

        # ── 1. Normalise colour mode ──────────────────────────────────────────
        if img.mode != "RGB":
            img = img.convert("RGB")

        # ── 2. Grayscale ──────────────────────────────────────────────────────
        img = img.convert("L")

        # ── 3. Contrast enhancement ───────────────────────────────────────────
        img = ImageEnhance.Contrast(img).enhance(2.0)

        # ── 4. Sharpness ──────────────────────────────────────────────────────
        img = ImageEnhance.Sharpness(img).enhance(2.0)

        # ── 5. Upscale small images (< 1000px wide → poor OCR) ───────────────
        width, height = img.size
        if width < 1000:
            scale = 1000 / width
            img = img.resize(
                (int(width * scale), int(height * scale)),
                Image.LANCZOS,
            )
            logger.debug(f"[OCR] Upscaled from {width}px → {img.size[0]}px")

        # ── 6. Optional: light noise reduction ───────────────────────────────
        img = img.filter(ImageFilter.MedianFilter(size=3))

        # ── 7. Tesseract OCR ─────────────────────────────────────────────────
        pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD

        custom_config = (
            "--oem 3 "     # LSTM + legacy engine
            "--psm 6 "     # Assume a single uniform block of text
            "-l urd+eng"   # Urdu + English language packs
        )

        try:
            text: str = pytesseract.image_to_string(img, config=custom_config)
        except Exception as exc:
            raise RuntimeError(f"Tesseract OCR failed: {exc}") from exc

        elapsed = round((time.perf_counter() - start) * 1000)
        char_count = len(text.strip())
        logger.info(f"[OCR] Extracted {char_count} chars in {elapsed}ms")

        return text

    # ─────────────────────────────────────────────────────────────────────────
    def identify_ppc_sections(self, text: str) -> list[str]:
        """
        Scans OCR'd text and extracts PPC/PECA section numbers.

        Handles:
          - English: "Section 302", "u/s 302/34 PPC", "under section 489-F"
          - Urdu:    "دفعہ ۳۰۲" (Urdu-Indic digits auto-converted to ASCII)
          - Compound: "302/34/109" (split on slash — each is a separate section)
          - PECA:    "PECA s.20"

        Returns a deduplicated list of section numbers (e.g. ["302", "34", "109"]).
        """
        # Normalise Urdu digits → ASCII before regex matching
        normalised = text.translate(self._URDU_DIGIT_MAP)

        found: set[str] = set()

        for pattern in self._SECTION_PATTERNS:
            for match in pattern.finditer(normalised):
                # Group 0 may contain slashes — split compound sections
                raw = match.group(1) if match.lastindex else match.group(0)
                for part in re.split(r'[/,\s]+', raw):
                    section = part.strip().upper()
                    if section and re.match(r'^\d{2,3}(-[A-F])?$|^PECA-\d+$', section):
                        found.add(section)

        # Also check for bare section numbers already embedded in PECA context
        for peca_match in re.finditer(r'PECA\s*[-–]?\s*(\d{1,2})', normalised, re.IGNORECASE):
            found.add(f"PECA-{peca_match.group(1)}")

        logger.debug(f"[FIR] Identified sections: {sorted(found)}")
        return sorted(found)

    # ─────────────────────────────────────────────────────────────────────────
    def _check_procedural_flags(self, text: str) -> list[str]:
        """
        Checks the OCR text against a list of procedural requirements.
        Returns a list of warning strings for any missing elements.
        """
        flags: list[str] = []
        for _flag_id, patterns, warning_message in self._FLAG_CHECKS:
            # Flag is raised if NONE of the expected patterns match
            found = any(p.search(text) for p in patterns)
            if not found:
                flags.append(warning_message)
        return flags

    # ─────────────────────────────────────────────────────────────────────────
    def _extract_fir_metadata(self, text: str) -> dict[str, str | None]:
        """Extracts structured fields from the raw FIR text."""
        normalised = text.translate(self._URDU_DIGIT_MAP)

        def _first(pattern: re.Pattern) -> str | None:
            m = pattern.search(normalised)
            return m.group(1).strip() if m else None

        return {
            "fir_number":     _first(self._FIR_NUMBER_RE) or _first(self._CASE_NUMBER_RE),
            "date":           _first(self._DATE_RE),
            "police_station": _first(self._STATION_RE),
            "district":       _first(self._DISTRICT_RE),
        }

    # ─────────────────────────────────────────────────────────────────────────
    async def _generate_plain_explanation(
        self,
        text: str,
        sections: list[FIRSection],
        flags: list[str],
    ) -> str:
        """
        Calls Gemini Flash to produce a 3-4 sentence plain-Urdu explanation
        of the FIR suitable for a non-lawyer Pakistani citizen.

        Falls back to a template-based explanation if Gemini is unavailable.
        """
        section_summary = "; ".join(
            f"دفعہ {s.section_number} ({s.title})" for s in sections
        ) or "کوئی معروف دفعہ نہیں ملی"

        bailable_status = (
            "ضمانت نہ ملنے والا جرم (Non-Bailable)"
            if any(not s.bailable for s in sections)
            else "ضمانت مل سکتی ہے (Bailable)"
        )

        prompt = f"""آپ پاکستانی قانون کے ماہر ہیں۔ نیچے ایک FIR (First Information Report) کا متن دیا گیا ہے۔
براہ کرم اس FIR کی سادہ اردو میں 3 سے 4 جملوں میں وضاحت کریں جو ایک عام پاکستانی شہری سمجھ سکے۔

درج ذیل نکات شامل کریں:
1. FIR میں کون سا الزام لگایا گیا ہے۔
2. ملزم کی قانونی حیثیت (ضمانت ہو سکتی ہے یا نہیں): {bailable_status}
3. ملزم کو کیا کرنا چاہیے (وکیل کریں، ضمانت درخواست وغیرہ)۔

دفعات: {section_summary}

FIR متن (اوّل 800 حروف):
{text[:800]}

صرف اردو میں جواب دیں۔ قانونی اصطلاحات سے بچیں۔ 3-4 جملے کافی ہیں۔"""

        try:
            model = _get_gemini()
            response = model.generate_content(prompt)
            explanation = response.text.strip()
            logger.info(f"[FIR] Gemini explanation generated ({len(explanation)} chars)")
            return explanation

        except Exception as exc:
            logger.warning(f"[FIR] Gemini unavailable — using template fallback: {exc}")
            # Template fallback — always works, less personalised
            section_list = "، ".join(f"دفعہ {s.section_number}" for s in sections)
            return (
                f"اس FIR میں {section_list or 'کچھ'} دفعات کے تحت الزام لگایا گیا ہے۔ "
                f"یہ کیس {bailable_status} ہے۔ "
                "آپ کو فوری طور پر کسی تجربہ کار وکیل سے رابطہ کرنا چاہیے "
                "تاکہ ضمانت کی درخواست اور دیگر قانونی اقدامات کیے جا سکیں۔"
            )

    # ─────────────────────────────────────────────────────────────────────────
    async def analyze_fir(self, text: str) -> FIRAnalysisResponse:
        """
        Full FIR analysis pipeline from raw text.

        Steps:
          1. Extract PPC section numbers via regex
          2. Look up each section in PPC_SECTIONS knowledge base
          3. Build FIRSection objects (unknown sections get a generic entry)
          4. Run procedural flag checks
          5. Extract FIR metadata (number, date, station, district)
          6. Generate plain-Urdu explanation via Gemini Flash
          7. Determine bailability and capital charge status
          8. Assemble and return FIRAnalysisResponse

        Args:
            text: OCR-extracted or directly provided FIR text

        Returns:
            FIRAnalysisResponse — fully populated analysis
        """
        start = time.perf_counter()
        logger.info(f"[FIR] analyze_fir() called on {len(text)} chars")

        # ── 1. Identify sections ──────────────────────────────────────────────
        section_numbers = self.identify_ppc_sections(text)
        logger.info(f"[FIR] Sections found: {section_numbers}")

        # ── 2 & 3. Build FIRSection objects ───────────────────────────────────
        fir_sections: list[FIRSection] = []
        for num in section_numbers:
            info = PPC_SECTIONS.get(num)
            if info:
                fir_sections.append(FIRSection(
                    section_number=num,
                    act=info["act"],
                    title=info["title"],
                    min_punishment=info["min_punishment"],
                    max_punishment=info["max_punishment"],
                    bailable=info["bailable"],
                    cognizable=info["cognizable"],
                    explanation=info["description"],
                ))
            else:
                # Section found in text but not yet in our knowledge base
                logger.warning(f"[FIR] Unknown section: {num} — using generic entry")
                fir_sections.append(FIRSection(
                    section_number=num,
                    act="PPC/Other",
                    title=f"Section {num} (details not in local database)",
                    min_punishment="Refer to statute",
                    max_punishment="Refer to statute",
                    bailable=False,   # default to caution: non-bailable
                    cognizable=True,
                    explanation=(
                        f"دفعہ {num} کی تفصیل ڈیٹا بیس میں موجود نہیں۔ "
                        "براہ کرم کسی وکیل سے رابطہ کریں۔"
                    ),
                ))

        # ── 4. Procedural flags ───────────────────────────────────────────────
        flags = self._check_procedural_flags(text)

        # ── 5. Metadata extraction ────────────────────────────────────────────
        metadata = self._extract_fir_metadata(text)

        # ── 6. Plain explanation (Gemini or fallback) ─────────────────────────
        plain_explanation = await self._generate_plain_explanation(
            text, fir_sections, flags
        )

        # ── 7. Bailability & severity ─────────────────────────────────────────
        is_bailable = all(s.bailable for s in fir_sections) if fir_sections else True
        has_capital = any(
            s.section_number in CAPITAL_SECTIONS for s in fir_sections
        )

        # ── 8. Rights list ────────────────────────────────────────────────────
        your_rights = (
            UNIVERSAL_RIGHTS_NON_BAILABLE
            if not is_bailable
            else UNIVERSAL_RIGHTS_BAILABLE
        )

        elapsed = round((time.perf_counter() - start) * 1000)
        logger.info(
            f"[FIR] Analysis complete in {elapsed}ms — "
            f"sections={len(fir_sections)}, flags={len(flags)}, "
            f"bailable={is_bailable}, capital={has_capital}"
        )

        return FIRAnalysisResponse(
            sections=fir_sections,
            plain_explanation=plain_explanation,
            flags=flags,
            is_bailable=is_bailable,
            has_capital_charge=has_capital,
            fir_metadata=metadata,
            your_rights=your_rights,
        )
