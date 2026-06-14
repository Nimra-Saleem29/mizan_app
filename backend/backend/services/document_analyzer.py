"""
Wakeel وکیل — Document Analyzer Service
==========================================
Analyses Pakistani legal documents: rent agreements, employment contracts,
court notices, property deeds, loan agreements, eviction notices, and more.

Pipeline:
  1. OCR       → reuses FIRAnalyzer.extract_text_from_image (Tesseract urd+eng)
  2. Classify  → keyword-based document type detection
  3. Extract   → regex entity extraction (parties, dates, amounts, duration)
  4. Risk scan → rule-based flag detection per document type
  5. Explain   → Gemini Flash generates plain-Urdu explanation per flag + summary

Usage:
    analyzer = DocumentAnalyzer()
    result   = await analyzer.analyze_document(image_bytes=...) # from camera
    result   = await analyzer.analyze_document(text=...)        # pre-digitised
"""

import re
import time
from typing import Any, Optional

import google.generativeai as genai
from loguru import logger

from config import settings
from models.schemas import DocumentAnalysisResponse, FavourableClause, RiskFlag
from services.fir_analyzer import FIRAnalyzer   # reuse OCR pipeline


# ─────────────────────────────────────────────────────────────────────────────
# Document type catalogue
# ─────────────────────────────────────────────────────────────────────────────
DOCUMENT_TYPES: dict[str, dict[str, str]] = {
    "rent_agreement": {
        "label_en": "Rent Agreement",
        "label_ur": "کرایہ نامہ",
        "icon": "🏠",
        "description": "Tenancy / lease agreement between landlord and tenant",
    },
    "employment_contract": {
        "label_en": "Employment Contract",
        "label_ur": "ملازمت کا معاہدہ",
        "icon": "💼",
        "description": "Job contract between employer and employee",
    },
    "court_notice": {
        "label_en": "Court Notice / Summons",
        "label_ur": "عدالتی نوٹس / سمن",
        "icon": "⚖️",
        "description": "Summons, warrant, or notice issued by a court",
    },
    "property_deed": {
        "label_en": "Property Deed / Registry",
        "label_ur": "بیع نامہ / رجسٹری",
        "icon": "📜",
        "description": "Sale deed, transfer deed, or fard (land record)",
    },
    "loan_agreement": {
        "label_en": "Loan Agreement",
        "label_ur": "قرض نامہ",
        "icon": "💰",
        "description": "Personal or commercial loan / financing agreement",
    },
    "eviction_notice": {
        "label_en": "Eviction Notice",
        "label_ur": "بے دخلی نوٹس",
        "icon": "🚪",
        "description": "Notice to vacate a rented or occupied property",
    },
    "power_of_attorney": {
        "label_en": "Power of Attorney",
        "label_ur": "وکالت نامہ",
        "icon": "✍️",
        "description": "Legal authorisation for one party to act for another",
    },
    "affidavit": {
        "label_en": "Affidavit",
        "label_ur": "حلفنامہ",
        "icon": "📋",
        "description": "Sworn written statement for legal proceedings",
    },
    "nda": {
        "label_en": "Non-Disclosure Agreement",
        "label_ur": "رازداری معاہدہ",
        "icon": "🔒",
        "description": "Confidentiality agreement between parties",
    },
    "partnership_deed": {
        "label_en": "Partnership Deed",
        "label_ur": "شراکت نامہ",
        "icon": "🤝",
        "description": "Business partnership agreement",
    },
    "general_legal_document": {
        "label_en": "General Legal Document",
        "label_ur": "عمومی قانونی دستاویز",
        "icon": "📄",
        "description": "Legal document — type could not be automatically determined",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Gemini singleton
# ─────────────────────────────────────────────────────────────────────────────
_gemini_model = None


def _get_gemini():
    global _gemini_model
    if _gemini_model is None:
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY not configured.")
        genai.configure(api_key=settings.GEMINI_API_KEY)
        _gemini_model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            generation_config=genai.GenerationConfig(
                temperature=settings.GEMINI_TEMPERATURE,
                max_output_tokens=settings.GEMINI_MAX_TOKENS,
            ),
        )
    return _gemini_model


# ─────────────────────────────────────────────────────────────────────────────
# DocumentAnalyzer
# ─────────────────────────────────────────────────────────────────────────────
class DocumentAnalyzer:
    """
    Analyses Pakistani legal documents for document type, key entities,
    risk flags, and produces a plain-Urdu explanation via Gemini Flash.
    """

    # Shared OCR engine (Tesseract urd+eng via FIRAnalyzer)
    _ocr = FIRAnalyzer()

    # ── Urdu digit normalisation ──────────────────────────────────────────────
    _URDU_DIGIT_MAP = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")

    # ─────────────────────────────────────────────────────────────────────────
    # METHOD 1: detect_document_type
    # ─────────────────────────────────────────────────────────────────────────

    # Each entry: (doc_type_key, [keyword list])
    # Keywords are checked case-insensitively against the full text.
    # Order matters — first match wins.
    _TYPE_RULES: list[tuple[str, list[str]]] = [
        ("eviction_notice", [
            "eviction", "vacate", "quit notice", "بے دخلی", "خالی کرو",
            "notice to vacate", "خالی کریں", "مکان خالی",
        ]),
        ("court_notice", [
            "عدالت", "court", "summons", "سمن", "notice of hearing",
            "تاریخ پیشی", "حاضر ہوں", "فاضل عدالت", "مجلس",
            "plaintiff", "defendant", "petitioner", "respondent",
        ]),
        ("rent_agreement", [
            "کرایہ", "kiraya", "rent agreement", "tenancy", "landlord",
            "tenant", "مالک مکان", "کرایہ دار", "monthly rent",
            "ماہانہ کرایہ", "lease", "پٹہ",
        ]),
        ("employment_contract", [
            "ملازمت", "employment", "employee", "employer", "salary",
            "تنخواہ", "designation", "عہدہ", "job title", "probation",
            "notice period", "appointment letter", "offer letter",
        ]),
        ("loan_agreement", [
            "قرض", "loan", "borrower", "lender", "repayment",
            "installment", "قسط", "interest", "سود", "markup",
            "مارک اپ", "finance", "principal amount",
        ]),
        ("property_deed", [
            "زمین", "property", "sale deed", "بیع نامہ", "registry",
            "رجسٹری", "fard", "فرد", "khasra", "خسرہ", "patwari",
            "patwari number", "deed of transfer", "مربع", "marla", "kanal",
        ]),
        ("power_of_attorney", [
            "وکالت نامہ", "power of attorney", "attorney", "authorise",
            "authorize", "attorney in fact", "general power",
        ]),
        ("affidavit", [
            "حلفنامہ", "affidavit", "sworn", "حلف", "deponent",
            "solemn affirmation", "before me",
        ]),
        ("nda", [
            "non-disclosure", "confidentiality", "razi dari", "رازداری",
            "proprietary information", "trade secret",
        ]),
        ("partnership_deed", [
            "شراکت", "partnership", "partner", "profit sharing",
            "منافع", "joint venture", "firm",
        ]),
    ]

    def detect_document_type(self, text: str) -> str:
        """
        Classifies the document using ordered keyword matching.

        Strategy: each document type has a priority-ordered list of
        keywords. We normalise the text to lowercase and check for any
        keyword hit. First match wins. Falls back to 'general_legal_document'.

        Args:
            text: OCR-extracted or raw document text

        Returns:
            One of the DOCUMENT_TYPES keys.
        """
        lower = text.lower()

        for doc_type, keywords in self._TYPE_RULES:
            if any(kw.lower() in lower for kw in keywords):
                logger.debug(f"[DocAnalyzer] Detected type: {doc_type}")
                return doc_type

        logger.debug("[DocAnalyzer] Could not classify — using general_legal_document")
        return "general_legal_document"

    # ─────────────────────────────────────────────────────────────────────────
    # METHOD 2: extract_entities
    # ─────────────────────────────────────────────────────────────────────────

    # Pakistani name patterns: 2-4 capitalised words (English), or
    # Urdu names after keywords like "between", "مابین", "درمیان"
    _NAME_PATTERNS: list[re.Pattern] = [
        # "between [Name] and [Name]" — English
        re.compile(
            r'\bbetween\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\s+and\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})',
        ),
        # "Mr./Mrs./M/s [Name]" — title-prefixed names
        re.compile(
            r'\b(?:Mr\.|Mrs\.|Ms\.|M/s\.?|Messrs\.?)\s+([A-Z][a-zA-Z\s]{2,40}?)(?=,|\.|s/o|w/o|d/o|\n)',
        ),
        # "hereinafter" pattern — "John Smith hereinafter"
        re.compile(
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\s+hereinafter',
        ),
        # S/O, W/O, D/O pattern (Son/Wife/Daughter of) — Pakistani ID format
        re.compile(
            r'([A-Z][a-zA-Z\s]{2,30}?)\s+[SsWwDd]/[Oo]\.?\s+[A-Z][a-zA-Z\s]{2,30}',
        ),
    ]

    # Amount patterns: Rs., PKR, روپے
    _AMOUNT_PATTERNS: list[re.Pattern] = [
        re.compile(r'(?:Rs\.?|PKR|روپے|rupees)\s*([0-9,]+(?:\.[0-9]{1,2})?)', re.IGNORECASE),
        re.compile(r'([0-9,]+)\s*(?:rupees|روپے)', re.IGNORECASE),
    ]

    # Date patterns: DD/MM/YYYY, DD-MM-YYYY, written months
    _DATE_PATTERNS: list[re.Pattern] = [
        re.compile(r'\b(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\b'),
        re.compile(
            r'\b(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|'
            r'September|October|November|December)\s+\d{4})\b',
            re.IGNORECASE,
        ),
        re.compile(r'\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4})\b', re.IGNORECASE),
        re.compile(r'(مورخہ\s*\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})'),
    ]

    # Duration patterns: "6 months", "2 years", "ایک سال"
    _DURATION_PATTERNS: list[re.Pattern] = [
        re.compile(r'(\d+)\s*(month|months|year|years|سال|ماہ|مہینہ)', re.IGNORECASE),
        re.compile(r'(one|two|three|four|five|six|seven|eight|nine|ten)\s*(month|months|year|years)', re.IGNORECASE),
        re.compile(r'(ایک|دو|تین|چار|پانچ|چھ|سات|آٹھ|نو|دس)\s*(سال|ماہ|مہینہ)'),
    ]

    def extract_entities(self, text: str) -> dict[str, Any]:
        """
        Extracts structured entities from the document text using regex.

        Returns a dict with:
          parties:   list of party names found
          dates:     list of date strings found
          amounts:   list of monetary amounts (as strings)
          duration:  list of time period mentions
          raw_text_preview: first 200 chars for context
        """
        normalised = text.translate(self._URDU_DIGIT_MAP)

        # ── Parties ───────────────────────────────────────────────────────────
        parties: list[str] = []
        for pattern in self._NAME_PATTERNS:
            for match in pattern.finditer(normalised):
                for group in match.groups():
                    if group:
                        cleaned = group.strip()
                        if len(cleaned) >= 4 and cleaned not in parties:
                            parties.append(cleaned)

        # ── Amounts ───────────────────────────────────────────────────────────
        amounts: list[str] = []
        for pattern in self._AMOUNT_PATTERNS:
            for match in pattern.finditer(normalised):
                raw_amount = match.group(1).replace(",", "")
                try:
                    # Format nicely: 50000 → "Rs. 50,000"
                    num = float(raw_amount)
                    formatted = f"Rs. {num:,.0f}"
                    if formatted not in amounts:
                        amounts.append(formatted)
                except ValueError:
                    pass

        # ── Dates ─────────────────────────────────────────────────────────────
        dates: list[str] = []
        for pattern in self._DATE_PATTERNS:
            for match in pattern.finditer(normalised):
                d = match.group(1).strip()
                if d not in dates:
                    dates.append(d)

        # ── Duration ──────────────────────────────────────────────────────────
        durations: list[str] = []
        for pattern in self._DURATION_PATTERNS:
            for match in pattern.finditer(normalised):
                full = match.group(0).strip()
                if full not in durations:
                    durations.append(full)

        result = {
            "parties":           parties[:6],    # cap at 6 names
            "dates":             dates[:10],
            "amounts":           amounts[:8],
            "duration":          durations[:5],
            "raw_text_preview":  text[:200].strip(),
        }

        logger.debug(
            f"[DocAnalyzer] Entities — parties:{len(parties)} "
            f"dates:{len(dates)} amounts:{len(amounts)} duration:{len(durations)}"
        )
        return result

    # ─────────────────────────────────────────────────────────────────────────
    # METHOD 3: detect_risk_flags
    # ─────────────────────────────────────────────────────────────────────────

    # Rule structure:
    #   (flag_id, [trigger patterns], risk_level, short_urdu_label,
    #    doc_types_it_applies_to or None for all)
    _RISK_RULES: list[tuple[str, list[re.Pattern], str, str, Optional[list[str]]]] = [

        # ── Universal — applies to every document type ────────────────────────
        (
            "no_notice_termination",
            [re.compile(r'without\s+(?:prior\s+)?notice|بغیر\s+نوٹس|without\s+warning', re.IGNORECASE)],
            "high",
            "بغیر نوٹس کے برطرفی یا فسخ کی شرط",
            None,
        ),
        (
            "no_witness_signatures",
            [re.compile(r'witness|گواہ|shahid', re.IGNORECASE)],
            "medium",
            "گواہوں کے دستخط موجود نہیں",
            None,
        ),
        (
            "unilateral_amendment",
            [re.compile(
                r'(?:party\s+of\s+the\s+first\s+part|landlord|employer)\s+(?:may|can|shall|will)\s+(?:at\s+any\s+time\s+)?(?:amend|change|modify|alter)',
                re.IGNORECASE,
            )],
            "high",
            "یکطرفہ شرائط تبدیل کرنے کا حق",
            None,
        ),
        (
            "no_termination_clause",
            [re.compile(r'terminat|فسخ|ختم\s+کرنے|end\s+of\s+contract|notice\s+period', re.IGNORECASE)],
            "medium",
            "معاہدہ ختم کرنے کی شرط موجود نہیں",
            None,
        ),
        (
            "governing_law_missing",
            [re.compile(r'governing\s+law|jurisdiction|دائرہ\s+اختیار|متعلقہ\s+عدالت', re.IGNORECASE)],
            "low",
            "کس عدالت کا دائرہ اختیار ہوگا — درج نہیں",
            None,
        ),

        # ── Employment-specific ────────────────────────────────────────────────
        (
            "excessive_penalty",
            [re.compile(
                r'(?:penalty|fine|deduction|کٹوتی|جرمانہ)\s+(?:of\s+)?(?:more\s+than\s+)?(?:[3-9]|[1-9]\d)\s+(?:month|months)',
                re.IGNORECASE,
            )],
            "high",
            "3 ماہ سے زیادہ تنخواہ کٹوتی کی شرط",
            ["employment_contract"],
        ),
        (
            "no_overtime_clause",
            [re.compile(r'overtime|اوور\s*ٹائم|extra\s+hours|اضافی\s+اوقات', re.IGNORECASE)],
            "medium",
            "اوور ٹائم معاوضے کا ذکر نہیں",
            ["employment_contract"],
        ),
        (
            "non_compete_broad",
            [re.compile(r'non.?compete|not\s+to\s+work|compete\s+with|پابندی\s+روزگار', re.IGNORECASE)],
            "high",
            "روزگار پر پابندی — بہت وسیع شرط ہو سکتی ہے",
            ["employment_contract", "nda"],
        ),
        (
            "probation_without_benefits",
            [re.compile(r'probation(?:ary)?\s+period', re.IGNORECASE)],
            "medium",
            "پروبیشن کے دوران مراعات کا ذکر نہیں",
            ["employment_contract"],
        ),

        # ── Rent/Tenancy-specific ─────────────────────────────────────────────
        (
            "rent_increase_high",
            [re.compile(
                r'(?:rent|کرایہ)\s+(?:increase|بڑھ|زیادہ)\s+(?:[1-9]\d|[2-9])(?:\s*%|\s+percent)',
                re.IGNORECASE,
            )],
            "medium",
            "کرایہ بڑھانے کی شرح 10% سے زیادہ",
            ["rent_agreement"],
        ),
        (
            "evict_anytime",
            [re.compile(
                r'(?:landlord|مالک\s*مکان)\s+(?:may|can|shall|will)\s+(?:at\s+any\s+time\s+)?(?:evict|remove|ask\s+to\s+vacate|خالی\s+کرا)',
                re.IGNORECASE,
            )],
            "high",
            "مالک مکان کو کسی بھی وقت بے دخل کرنے کا حق",
            ["rent_agreement", "eviction_notice"],
        ),
        (
            "no_repair_responsibility",
            [re.compile(r'repair|maintenance|مرمت|صیانت', re.IGNORECASE)],
            "medium",
            "مرمت کی ذمہ داری کا ذکر نہیں",
            ["rent_agreement"],
        ),
        (
            "security_deposit_no_return",
            [re.compile(r'security\s+deposit|ضمانت\s+رقم|advance\s+rent', re.IGNORECASE)],
            "medium",
            "سیکورٹی ڈیپازٹ واپسی کی شرائط واضح نہیں",
            ["rent_agreement"],
        ),

        # ── Loan-specific ─────────────────────────────────────────────────────
        (
            "compound_interest",
            [re.compile(r'compound(?:ing)?\s+interest|سود\s+در\s+سود|interest\s+on\s+interest', re.IGNORECASE)],
            "high",
            "سود در سود — اسلامی اور قانونی مسئلہ",
            ["loan_agreement"],
        ),
        (
            "penalty_on_default",
            [re.compile(r'default|تاخیر\s+جرمانہ|penalty\s+interest|penal\s+rate', re.IGNORECASE)],
            "medium",
            "ادائیگی میں تاخیر پر جرمانے کی شرط",
            ["loan_agreement"],
        ),
        (
            "collateral_unclear",
            [re.compile(r'collateral|security|ضمانت|pledge|رہن', re.IGNORECASE)],
            "medium",
            "ضمانتی اثاثے کی تفصیل واضح نہیں",
            ["loan_agreement"],
        ),

        # ── Property deed-specific ────────────────────────────────────────────
        (
            "encumbrance_not_mentioned",
            [re.compile(r'encumbrance|mortgage|رہن|قرضہ\s+زمین|lien', re.IGNORECASE)],
            "high",
            "زمین پر رہن یا قرضہ ہو سکتا ہے — تصدیق کریں",
            ["property_deed"],
        ),
        (
            "no_possession_date",
            [re.compile(r'possession|قبضہ|handover|delivery\s+of\s+property', re.IGNORECASE)],
            "medium",
            "قبضہ منتقلی کی تاریخ درج نہیں",
            ["property_deed"],
        ),

        # ── Court notice-specific ─────────────────────────────────────────────
        (
            "short_response_deadline",
            [re.compile(
                r'(?:within|اندر)\s+(?:[3-9]|[1-9]\d?)\s+(?:days?|دن)',
                re.IGNORECASE,
            )],
            "high",
            "فوری جواب درکار — عدالتی نوٹس کا ردعمل ضروری ہے",
            ["court_notice", "eviction_notice"],
        ),
    ]

    def detect_risk_flags(
        self, text: str, doc_type: str
    ) -> tuple[list[RiskFlag], list[FavourableClause]]:
        """
        Applies rule-based risk detection tailored to the document type.

        For each rule:
          - If the trigger PATTERN IS NOT FOUND → risk flag raised
            (absence of expected clause = risk)
          - For "no_witness_signatures", "no_termination_clause",
            "no_repair_responsibility" etc — absence is the flag
          - For "evict_anytime", "compound_interest" etc — presence is the flag

        The design uses a consistent flag-if-absent approach for protective
        clauses and flag-if-present for dangerous clauses.

        Returns:
            (risk_flags, favourable_clauses)
        """
        lower = text.lower()
        risk_flags: list[RiskFlag] = []
        favourable: list[FavourableClause] = []

        # Which rules to apply for this doc type
        applicable = [
            rule for rule in self._RISK_RULES
            if rule[4] is None or doc_type in rule[4]
        ]

        # Clauses that are flagged if ABSENT (protective clauses)
        absence_flags = {
            "no_witness_signatures",
            "no_termination_clause",
            "governing_law_missing",
            "no_overtime_clause",
            "no_repair_responsibility",
            "security_deposit_no_return",
            "no_possession_date",
        }

        for flag_id, patterns, risk_level, urdu_label, _ in applicable:
            matched = any(p.search(text) for p in patterns)

            if flag_id in absence_flags:
                # Flag raised if the protective clause is MISSING
                if not matched:
                    risk_flags.append(RiskFlag(
                        clause_text=urdu_label,
                        clause_ref=None,
                        risk_level=risk_level,           # type: ignore[arg-type]
                        explanation=_build_flag_explanation(flag_id, doc_type),
                        recommendation=_build_recommendation(flag_id),
                    ))
                else:
                    # Clause IS present — this is favourable
                    favourable.append(FavourableClause(
                        clause_text=urdu_label,
                        explanation=f"✓ {urdu_label} موجود ہے — یہ آپ کے لیے فائدہ مند ہے۔",
                    ))
            else:
                # Flag raised if the DANGEROUS clause IS PRESENT
                if matched:
                    # Extract a short snippet around the match for context
                    snippet = ""
                    for p in patterns:
                        m = p.search(text)
                        if m:
                            start = max(0, m.start() - 40)
                            end   = min(len(text), m.end() + 80)
                            snippet = text[start:end].strip()
                            break

                    risk_flags.append(RiskFlag(
                        clause_text=snippet or urdu_label,
                        clause_ref=None,
                        risk_level=risk_level,           # type: ignore[arg-type]
                        explanation=_build_flag_explanation(flag_id, doc_type),
                        recommendation=_build_recommendation(flag_id),
                    ))

        logger.debug(
            f"[DocAnalyzer] Risk detection: {len(risk_flags)} flags, "
            f"{len(favourable)} favourable for {doc_type}"
        )
        return risk_flags, favourable

    # ─────────────────────────────────────────────────────────────────────────
    # METHOD 4: analyze_document
    # ─────────────────────────────────────────────────────────────────────────
    async def analyze_document(
        self,
        image_bytes: Optional[bytes] = None,
        text: Optional[str] = None,
        hint_doc_type: Optional[str] = None,
    ) -> DocumentAnalysisResponse:
        """
        Full document analysis pipeline.

        At least one of `image_bytes` or `text` must be provided.
        If both are provided, image_bytes takes priority and OCR text
        is used (the `text` argument is ignored).

        Steps:
          1. OCR (if image_bytes provided)
          2. Detect document type
          3. Extract entities (parties, dates, amounts, duration)
          4. Detect risk flags (rules) + identify favourable clauses
          5. Compute overall risk score (0–100)
          6. Generate plain-Urdu summary via Gemini Flash
          7. Assemble DocumentAnalysisResponse

        Args:
            image_bytes:   Raw image bytes (JPEG/PNG/TIFF) from camera
            text:          Pre-digitised document text
            hint_doc_type: Optional override for document type classification

        Returns:
            DocumentAnalysisResponse

        Raises:
            ValueError: if neither image_bytes nor text is provided
        """
        if image_bytes is None and (text is None or not text.strip()):
            raise ValueError(
                "Either image_bytes or text must be provided to analyze_document()."
            )

        start = time.perf_counter()

        # ── 1. OCR ────────────────────────────────────────────────────────────
        if image_bytes is not None:
            logger.info(f"[DocAnalyzer] OCR on {len(image_bytes):,} bytes")
            text = self._ocr.extract_text_from_image(image_bytes)
            logger.info(f"[DocAnalyzer] OCR yielded {len(text)} chars")

        assert text is not None  # guaranteed by guard above

        # ── 2. Document type ──────────────────────────────────────────────────
        doc_type = hint_doc_type or self.detect_document_type(text)
        type_info = DOCUMENT_TYPES.get(doc_type, DOCUMENT_TYPES["general_legal_document"])
        logger.info(f"[DocAnalyzer] Document type: {doc_type}")

        # ── 3. Entity extraction ──────────────────────────────────────────────
        entities = self.extract_entities(text)

        # ── 4. Risk flags ─────────────────────────────────────────────────────
        risk_flags, favourable_clauses = self.detect_risk_flags(text, doc_type)

        # ── 5. Risk score ─────────────────────────────────────────────────────
        risk_score = _compute_risk_score(risk_flags)

        # ── 6. Plain-Urdu summary via Gemini ──────────────────────────────────
        plain_explanation = await self._generate_summary(
            text=text,
            doc_type=doc_type,
            type_info=type_info,
            entities=entities,
            risk_flags=risk_flags,
        )

        # ── 7. Top-level recommendations ─────────────────────────────────────
        recommendations = _build_top_recommendations(doc_type, risk_flags, risk_score)

        elapsed = round((time.perf_counter() - start) * 1000)
        logger.info(
            f"[DocAnalyzer] Analysis complete in {elapsed}ms — "
            f"type={doc_type} flags={len(risk_flags)} score={risk_score}"
        )

        return DocumentAnalysisResponse(
            document_type=doc_type,
            risk_flags=risk_flags,
            favourable_clauses=favourable_clauses,
            plain_explanation=plain_explanation,
            overall_risk_score=risk_score,
            parties_identified=[
                {"party_type": "party", "name": name}
                for name in entities.get("parties", [])
            ],
            recommendations=recommendations,
        )

    # ─────────────────────────────────────────────────────────────────────────
    async def _generate_summary(
        self,
        text: str,
        doc_type: str,
        type_info: dict,
        entities: dict,
        risk_flags: list[RiskFlag],
    ) -> str:
        """
        Calls Gemini Flash to produce a 5–6 sentence plain-Urdu summary.

        The prompt instructs the model to follow a specific template:
          "یہ دستاویز [type] ہے۔ اس میں [parties] کے درمیان [topic] کا ذکر ہے۔
           اس میں [key terms]۔ [risk summary]۔ آپ کو [advice]۔"
        """
        doc_label_ur = type_info.get("label_ur", doc_type)
        parties_str  = "، ".join(entities.get("parties", [])) or "نامعلوم فریقین"
        amounts_str  = "، ".join(entities.get("amounts", [])) or "کوئی رقم نہیں"
        dates_str    = "، ".join(entities.get("dates", [])[:3]) or "تاریخ نہیں"
        flag_count   = len(risk_flags)
        high_flags   = [f for f in risk_flags if f.risk_level == "high"]

        risk_summary = (
            f"اس دستاویز میں {flag_count} خطرناک شرائط ملی ہیں"
            f"{f'، جن میں سے {len(high_flags)} بہت زیادہ خطرناک ہیں' if high_flags else ''}۔"
            if flag_count > 0
            else "کوئی واضح خطرناک شرط نہیں ملی۔"
        )

        prompt = f"""آپ پاکستانی قانون کے ماہر ہیں۔ نیچے ایک قانونی دستاویز کا متن دیا گیا ہے۔
براہ کرم اس دستاویز کی سادہ اردو میں 5 سے 6 جملوں میں وضاحت کریں۔

درج ذیل ڈھانچے پر عمل کریں:
1. "یہ دستاویز [قسم] ہے۔" — دستاویز کی قسم بتائیں۔
2. "اس میں [فریقین] کے درمیان [موضوع] کا ذکر ہے۔" — فریقین اور موضوع بتائیں۔
3. اہم مالی شرائط (رقم، کرایہ، قسط وغیرہ) بتائیں۔
4. مدت یا تاریخ کا ذکر کریں۔
5. {risk_summary}
6. "آپ کو دستخط کرنے سے پہلے وکیل سے مشورہ کرنا چاہیے۔"

معلومات:
- دستاویز کی قسم: {doc_label_ur}
- فریقین: {parties_str}
- رقم: {amounts_str}
- تاریخیں: {dates_str}
- خطرناک شرائط: {flag_count}

دستاویز متن (اوّل 1000 حروف):
{text[:1000]}

صرف اردو میں جواب دیں۔ قانونی اصطلاحات سے گریز کریں۔ عام پاکستانی شہری کے لیے لکھیں۔"""

        try:
            model = _get_gemini()
            response = model.generate_content(prompt)
            summary = response.text.strip()
            logger.info(f"[DocAnalyzer] Gemini summary: {len(summary)} chars")
            return summary

        except Exception as exc:
            logger.warning(f"[DocAnalyzer] Gemini unavailable — template fallback: {exc}")
            doc_label = type_info.get("label_ur", "قانونی دستاویز")
            return (
                f"یہ دستاویز {doc_label} ہے۔ "
                f"اس میں {parties_str} کے درمیان معاملات کا ذکر ہے۔ "
                f"دستاویز میں {amounts_str} کا ذکر ہے اور تاریخ {dates_str} ہے۔ "
                f"{risk_summary} "
                "دستخط کرنے سے پہلے کسی تجربہ کار وکیل سے مشورہ ضرور کریں۔"
            )


# ─────────────────────────────────────────────────────────────────────────────
# Module-level helpers
# ─────────────────────────────────────────────────────────────────────────────

def _compute_risk_score(risk_flags: list[RiskFlag]) -> int:
    """
    Converts risk flags to a 0–100 score.

    Weighting:
      high   → 25 points each (max contribution: 75)
      medium → 10 points each
      low    → 3 points each

    Capped at 100.
    """
    score = 0
    for flag in risk_flags:
        if flag.risk_level == "high":
            score += 25
        elif flag.risk_level == "medium":
            score += 10
        else:
            score += 3
    return min(score, 100)


def _build_flag_explanation(flag_id: str, doc_type: str) -> str:
    """Returns a plain-Urdu explanation for each flag type."""
    EXPLANATIONS: dict[str, str] = {
        "no_notice_termination":    "بغیر نوٹس کے معاہدہ ختم کیا جا سکتا ہے — یہ آپ کے حقوق کے لیے نقصاندہ ہے۔",
        "no_witness_signatures":    "گواہوں کے دستخط نہ ہونے سے دستاویز کی قانونی حیثیت کمزور ہو سکتی ہے۔",
        "unilateral_amendment":     "ایک فریق اکیلے شرائط تبدیل کر سکتا ہے — یہ غیر منصفانہ ہے۔",
        "no_termination_clause":    "معاہدہ ختم کرنے کا طریقہ واضح نہیں — مستقبل میں تنازعہ ہو سکتا ہے۔",
        "governing_law_missing":    "اگر تنازعہ ہو تو کس عدالت میں جائیں — یہ واضح نہیں۔",
        "excessive_penalty":        "3 ماہ سے زیادہ تنخواہ کٹوتی پاکستانی لیبر قانون کے خلاف ہو سکتی ہے۔",
        "no_overtime_clause":       "اضافی کام کا معاوضہ طے نہیں — یہ ملازم کے لیے نقصاندہ ہے۔",
        "non_compete_broad":        "ملازمت چھوڑنے کے بعد کام پر پابندی بہت وسیع ہو سکتی ہے۔",
        "probation_without_benefits": "پروبیشن کے دوران آپ کی مراعات کا تحفظ واضح نہیں۔",
        "rent_increase_high":       "سالانہ کرایہ بڑھانے کی شرح بہت زیادہ ہے — مذاکرات کریں۔",
        "evict_anytime":            "مالک مکان کسی بھی وقت بے دخل کر سکتا ہے — یہ کرایہ دار کے حقوق کے خلاف ہے۔",
        "no_repair_responsibility": "مرمت کی ذمہ داری طے نہیں — آپ کو مسائل میں پھنسنے کا خطرہ ہے۔",
        "security_deposit_no_return": "سیکورٹی ڈیپازٹ کی واپسی کی شرائط واضح نہیں — رقم واپس نہ ملنے کا خطرہ ہے۔",
        "compound_interest":        "سود در سود پاکستانی قانون اور اسلامی اصولوں کے خلاف ہے۔",
        "penalty_on_default":       "ادائیگی نہ ہونے پر جرمانے کی شرح بہت زیادہ ہو سکتی ہے۔",
        "collateral_unclear":       "ضمانتی اثاثے کی تفصیل واضح نہیں — آپ کی جائیداد خطرے میں ہو سکتی ہے۔",
        "encumbrance_not_mentioned": "زمین پر پہلے سے رہن یا قرضہ ہو سکتا ہے — محکمہ مال سے تصدیق کریں۔",
        "no_possession_date":       "جائیداد کا قبضہ کب ملے گا — یہ واضح نہیں۔",
        "short_response_deadline":  "آپ کو فوری جواب دینا ہے — دیر کی تو یکطرفہ فیصلہ ہو سکتا ہے۔",
    }
    return EXPLANATIONS.get(flag_id, "یہ شرط آپ کے لیے نقصاندہ ہو سکتی ہے۔ وکیل سے مشورہ کریں۔")


def _build_recommendation(flag_id: str) -> str:
    """Returns a concise Urdu action recommendation for each flag."""
    RECS: dict[str, str] = {
        "no_notice_termination":    "کم از کم 30 دن کا نوٹس شامل کروائیں۔",
        "no_witness_signatures":    "دو گواہوں کے دستخط لازمی کروائیں۔",
        "unilateral_amendment":     "دونوں فریقین کی رضامندی سے ترمیم کی شرط شامل کروائیں۔",
        "no_termination_clause":    "نوٹس پیریڈ اور فسخ کا طریقہ تحریر میں لکھوائیں۔",
        "governing_law_missing":    "لاہور/کراچی ہائی کورٹ کا دائرہ اختیار شامل کروائیں۔",
        "excessive_penalty":        "جرمانے کی شرط کم کروائیں یا ہٹوائیں — لیبر کورٹ میں چیلنج ہو سکتی ہے۔",
        "no_overtime_clause":       "اوور ٹائم ریٹ تحریر میں طے کروائیں۔",
        "non_compete_broad":        "پابندی کی مدت اور علاقہ واضح کروائیں — 6 ماہ سے زیادہ نہ ہو۔",
        "rent_increase_high":       "سالانہ کرایہ اضافہ 10% تک محدود کروائیں۔",
        "evict_anytime":            "مالک مکان صرف 30 دن نوٹس کے بعد بے دخل کر سکتا ہے — یہ شامل کروائیں۔",
        "security_deposit_no_return": "ڈیپازٹ واپسی کی تاریخ (جیسے خروج کے 7 دن اندر) تحریر کروائیں۔",
        "compound_interest":        "سود کی شرط ہٹوائیں یا بینک مارک اپ ریٹ تک محدود کروائیں۔",
        "encumbrance_not_mentioned": "فرد جمع بندی اور محکمہ مال سے تصدیق کریں — پھر دستخط کریں۔",
        "short_response_deadline":  "فوری وکیل سے رجوع کریں — عدالتی نوٹس نظر انداز نہ کریں۔",
    }
    return RECS.get(flag_id, "دستخط کرنے سے پہلے وکیل سے مشورہ کریں۔")


def _build_top_recommendations(
    doc_type: str,
    risk_flags: list[RiskFlag],
    risk_score: int,
) -> list[str]:
    """Generates top-level action recommendations based on overall risk."""
    recs: list[str] = []

    if risk_score >= 75:
        recs.append("⚠️ خطرے کی سطح بہت زیادہ — دستخط مت کریں، پہلے وکیل سے ملیں۔")
    elif risk_score >= 40:
        recs.append("⚠️ کچھ اہم مسائل ہیں — دستخط سے پہلے شرائط پر مذاکرات کریں۔")
    else:
        recs.append("✓ بنیادی شرائط ٹھیک نظر آتی ہیں، لیکن وکیل سے تصدیق مفید ہوگی۔")

    high_flags = [f for f in risk_flags if f.risk_level == "high"]
    if high_flags:
        recs.append(f"🔴 {len(high_flags)} خطرناک شرائط پر فوری توجہ دیں — ہر ایک کی وضاحت پڑھیں۔")

    # Document-type specific advice
    advice_map = {
        "rent_agreement":       "کرایہ نامہ رجسٹرڈ کروائیں — 3 صد روپے اسٹامپ پر ہو۔",
        "employment_contract":  "EOBI اور SESSI رجسٹریشن کنفرم کریں۔",
        "property_deed":        "خریداری سے پہلے فرد جمع بندی اور تسلیم نامہ ضرور لیں۔",
        "loan_agreement":       "SECP یا سٹیٹ بینک سے لون فنانسر کی رجسٹریشن تصدیق کریں۔",
        "court_notice":         "عدالتی نوٹس کا جواب آخری تاریخ سے پہلے دینا لازم ہے۔",
    }
    if doc_type in advice_map:
        recs.append(advice_map[doc_type])

    recs.append("یاد رہے: یہ تجزیہ AI کی مدد سے ہے — قانونی مشورہ نہیں ہے۔")
    return recs
