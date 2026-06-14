"""
Wakeel وکیل — FIR Analysis Router
====================================
Exposes the FIRAnalyzer service over HTTP.

Endpoints:
  POST /fir/analyze-image          — upload FIR photo/scan → full analysis
  POST /fir/analyze-text           — submit raw text       → full analysis
  GET  /fir/history/{user_id}      — user's past analyses  (RLS enforced)
  GET  /fir/{analysis_id}          — retrieve one analysis by ID
  DELETE /fir/{analysis_id}        — delete an analysis

Image pipeline:
  Expo camera → multipart upload → size/type validation
  → Tesseract OCR (urd+eng) → quality gate (≥20 chars)
  → FIRAnalyzer.analyze_fir() → persist to Supabase → FIRAnalysisResponse

Text pipeline (pre-digitised FIRs or reanalysis):
  JSON body → FIRAnalyzer.analyze_fir() → persist → FIRAnalysisResponse
"""

import time
from typing import Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from loguru import logger
from pydantic import BaseModel, Field
from supabase.client import AsyncClient

from database import get_supabase
from models.schemas import FIRAnalysisResponse, LanguageCode
from services.fir_analyzer import FIRAnalyzer

router = APIRouter()

# ── Module-level analyzer singleton ──────────────────────────────────────────
# Instantiated once at import time — reused across all requests.
# FIRAnalyzer holds no mutable state so this is safe.
_analyzer = FIRAnalyzer()

# ── Constants ─────────────────────────────────────────────────────────────────
ALLOWED_IMAGE_TYPES = frozenset({
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/tiff",
    "image/bmp",
    "image/webp",
    "application/pdf",
})

MAX_IMAGE_BYTES = 10 * 1024 * 1024   # 10 MB
MIN_OCR_CHARS   = 20                 # below this → image quality rejection


# ─────────────────────────────────────────────────────────────────────────────
# Request models
# ─────────────────────────────────────────────────────────────────────────────
class FIRTextRequest(BaseModel):
    """Request body for POST /fir/analyze-text"""
    text: str = Field(
        ...,
        min_length=MIN_OCR_CHARS,
        max_length=50_000,
        description="Raw FIR text — Urdu, English, or mixed",
        examples=["FIR No. 45/2024 تھانہ ماڈل ٹاؤن لاہور دفعہ 302/34 PPC..."],
    )
    language: LanguageCode = Field(default="urdu")
    user_id: Optional[UUID] = Field(
        default=None,
        description="Authenticated user UUID — omit for anonymous analysis",
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /fir/analyze-image
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/analyze-image",
    response_model=FIRAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload a FIR image and receive a full legal analysis",
    responses={
        200: {"description": "FIR analysis with PPC sections, flags, and plain-Urdu explanation"},
        413: {"description": "File exceeds 10 MB size limit"},
        415: {"description": "Unsupported file type — use JPEG, PNG, TIFF, WebP, or PDF"},
        422: {"description": "Image quality too low for text extraction"},
        500: {"description": "OCR engine or AI pipeline error"},
    },
)
async def analyze_fir_image(
    image: UploadFile = File(
        ...,
        description="FIR document photo or scan (JPEG, PNG, TIFF, WebP, or PDF)",
    ),
    language: LanguageCode = Form(
        default="urdu",
        description="Preferred language for the plain explanation",
    ),
    user_id: Optional[str] = Form(
        default=None,
        description="Authenticated user UUID (optional — omit for anonymous)",
    ),
    db: AsyncClient = Depends(get_supabase),
) -> FIRAnalysisResponse:
    """
    **FIR Image Analysis** — the primary endpoint for the Wakeel app's camera feature.

    **Full pipeline:**
    1. Validates MIME type (JPEG / PNG / TIFF / WebP / PDF only)
    2. Enforces 10 MB file size limit
    3. Pre-processes image: grayscale → contrast ×2 → sharpen → upscale if needed
    4. Runs Tesseract OCR with `urd+eng` language packs
    5. Quality gate: rejects images yielding fewer than 20 characters
    6. Identifies PPC / CrPC / PECA section numbers via regex
    7. Looks up punishment, bailability, cognizability from knowledge base
    8. Checks procedural flags: signature, date, station seal, FIR number
    9. Calls Gemini Flash for a 3–4 sentence plain-Urdu summary
    10. Persists to Supabase `fir_analyses` (if user_id provided)

    **Photography tips for best OCR accuracy:**
    - Photograph in bright, even lighting — avoid shadows
    - Keep the FIR flat; unfold any creases
    - Aim for ≥ 300 DPI or ≥ 1200px wide
    - Ensure all four corners of the document are visible
    """
    request_start = time.perf_counter()
    logger.info(
        f"[POST /fir/analyze-image] "
        f"file={image.filename!r} "
        f"content_type={image.content_type!r} "
        f"user={'anon' if not user_id else user_id[:8]}"
    )

    # ── Validate MIME type ────────────────────────────────────────────────────
    content_type = (image.content_type or "").lower().split(";")[0].strip()
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"File type '{content_type}' is not supported. "
                "Please upload a JPEG, PNG, TIFF, WebP, or PDF file.\n"
                "فائل کی قسم قابلِ قبول نہیں — JPEG، PNG، یا PDF فائل اپلوڈ کریں۔"
            ),
        )

    # ── Read bytes ────────────────────────────────────────────────────────────
    image_bytes = await image.read()

    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file is empty. فائل خالی ہے۔",
        )

    if len(image_bytes) > MAX_IMAGE_BYTES:
        size_mb = len(image_bytes) / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"File size {size_mb:.1f} MB exceeds the 10 MB limit. "
                "Please compress the image and try again.\n"
                f"فائل کا سائز {size_mb:.1f} MB حد سے زیادہ ہے — تصویر چھوٹی کریں۔"
            ),
        )

    # ── OCR ───────────────────────────────────────────────────────────────────
    logger.info(f"[/fir/analyze-image] OCR starting on {len(image_bytes):,} bytes")
    try:
        extracted_text = _analyzer.extract_text_from_image(image_bytes)
    except ValueError as exc:
        # Pillow could not decode the image data
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Could not decode image: {exc}\n"
                "تصویر پڑھی نہ جا سکی — براہ کرم دوسری فائل اپلوڈ کریں۔"
            ),
        ) from exc
    except RuntimeError as exc:
        # Tesseract binary not found or crashed
        logger.error(f"[/fir/analyze-image] Tesseract error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "OCR engine error. Ensure Tesseract is installed with "
                "the Urdu language pack: sudo apt install tesseract-ocr-urd"
            ),
        ) from exc

    # ── Quality gate ──────────────────────────────────────────────────────────
    ocr_chars = len(extracted_text.strip())
    logger.info(f"[/fir/analyze-image] OCR yielded {ocr_chars} chars")

    if ocr_chars < MIN_OCR_CHARS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Image quality too low for text extraction. "
                "Please retake the photo.\n\n"
                "تصویر کا معیار بہت کم ہے — براہ کرم روشنی میں دوبارہ تصویر لیں۔\n"
                f"(Extracted only {ocr_chars} characters; minimum required: {MIN_OCR_CHARS})"
            ),
        )

    # ── Analysis + persistence ────────────────────────────────────────────────
    result = await _run_analysis(
        text=extracted_text,
        user_id=user_id,
        db=db,
        source="image",
    )

    total_ms = round((time.perf_counter() - request_start) * 1000)
    logger.info(f"[/fir/analyze-image] ✓ completed in {total_ms}ms")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# POST /fir/analyze-text
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/analyze-text",
    response_model=FIRAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyse a FIR from plain text — no OCR step",
    responses={
        200: {"description": "FIR analysis with PPC sections, flags, and plain-Urdu explanation"},
        422: {"description": "Text too short (< 20 characters)"},
        500: {"description": "AI pipeline error"},
    },
)
async def analyze_fir_text(
    payload: FIRTextRequest,
    db: AsyncClient = Depends(get_supabase),
) -> FIRAnalysisResponse:
    """
    **FIR Text Analysis** — for digitally-available FIR text.

    Use this when:
    - The FIR was received as a digital document (Word, PDF text layer, etc.)
    - You have already run OCR externally
    - Running automated tests against the analysis pipeline

    Runs the identical `FIRAnalyzer.analyze_fir()` pipeline as the image
    endpoint but skips OCR entirely — jumping straight to section extraction,
    procedural checks, and Gemini explanation.

    Accepts mixed Urdu (Nastaliq script), English, and Roman Urdu text.
    """
    request_start = time.perf_counter()
    logger.info(
        f"[POST /fir/analyze-text] "
        f"chars={len(payload.text)} "
        f"lang={payload.language} "
        f"user={'anon' if not payload.user_id else str(payload.user_id)[:8]}"
    )

    result = await _run_analysis(
        text=payload.text,
        user_id=str(payload.user_id) if payload.user_id else None,
        db=db,
        source="text",
    )

    total_ms = round((time.perf_counter() - request_start) * 1000)
    logger.info(f"[/fir/analyze-text] ✓ completed in {total_ms}ms")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# GET /fir/history/{user_id}
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/history/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="List a user's FIR analyses, newest first",
)
async def get_fir_history(
    user_id: UUID,
    limit: int = Query(default=20, ge=1, le=100, description="Results per page"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
    db: AsyncClient = Depends(get_supabase),
) -> list[dict]:
    """
    Returns a summary list of the user's FIR analyses (no raw text or full sections).
    For the full detail of a specific analysis, use `GET /fir/{analysis_id}`.

    Supabase RLS ensures users only see their own rows — even if they guess
    another user's UUID, they receive an empty array.
    """
    logger.info(
        f"[GET /fir/history] user={str(user_id)[:8]} "
        f"limit={limit} offset={offset}"
    )
    try:
        result = await (
            db.table("fir_analyses")
            .select(
                "id, fir_number, fir_date, police_station, district, "
                "has_non_bailable, has_capital_charge, created_at"
            )
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return result.data or []

    except Exception as exc:
        logger.error(f"[/fir/history] DB error for user {str(user_id)[:8]}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve FIR analysis history.",
        ) from exc


# ─────────────────────────────────────────────────────────────────────────────
# GET /fir/{analysis_id}
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/{analysis_id}",
    status_code=status.HTTP_200_OK,
    summary="Retrieve a specific FIR analysis",
)
async def get_fir_analysis(
    analysis_id: UUID,
    db: AsyncClient = Depends(get_supabase),
) -> dict:
    """
    Returns the full stored analysis: all sections, flags, plain explanation,
    extracted metadata, and your rights. RLS enforces ownership.
    """
    try:
        result = await (
            db.table("fir_analyses")
            .select("*")
            .eq("id", str(analysis_id))
            .single()
            .execute()
        )
    except Exception as exc:
        logger.error(f"[/fir/{analysis_id}] DB error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analysis.",
        ) from exc

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"FIR analysis '{analysis_id}' not found.",
        )
    return result.data


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /fir/{analysis_id}
# ─────────────────────────────────────────────────────────────────────────────
@router.delete(
    "/{analysis_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a FIR analysis from history",
)
async def delete_fir_analysis(
    analysis_id: UUID,
    db: AsyncClient = Depends(get_supabase),
) -> None:
    """
    Permanently deletes the analysis. RLS enforces that users can only
    delete their own rows — a user cannot delete another user's analysis.
    """
    try:
        await (
            db.table("fir_analyses")
            .delete()
            .eq("id", str(analysis_id))
            .execute()
        )
    except Exception as exc:
        logger.error(f"[DELETE /fir/{analysis_id}] DB error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete analysis.",
        ) from exc


# ─────────────────────────────────────────────────────────────────────────────
# Internal: shared analysis + persistence pipeline
# ─────────────────────────────────────────────────────────────────────────────
async def _run_analysis(
    text: str,
    user_id: Optional[str],
    db: AsyncClient,
    *,
    source: str,
) -> FIRAnalysisResponse:
    """
    Runs FIRAnalyzer.analyze_fir() and persists the result to Supabase.

    Persistence is non-fatal — if the DB write fails, the user still receives
    their complete analysis. The analysis_id on the response will be None.
    """
    try:
        result: FIRAnalysisResponse = await _analyzer.analyze_fir(text)
    except Exception as exc:
        logger.error(f"[FIR/_run_analysis] analyze_fir failed ({source}): {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "FIR analysis failed due to an internal error. "
                "داخلی خرابی — دوبارہ کوشش کریں۔"
            ),
        ) from exc

    # Persist (non-fatal)
    analysis_id = await _persist_fir_analysis(
        db=db,
        text=text,
        result=result,
        user_id=user_id,
        source=source,
    )
    result.analysis_id = analysis_id
    return result


async def _persist_fir_analysis(
    *,
    db: AsyncClient,
    text: str,
    result: FIRAnalysisResponse,
    user_id: Optional[str],
    source: str,
) -> Optional[UUID]:
    """
    Inserts the FIR analysis into the `fir_analyses` Supabase table.
    Returns the new row UUID on success, or None on failure / anonymous.
    """
    if not user_id:
        return None   # anonymous — no persistence

    try:
        row = {
            "user_id":            user_id,
            "raw_text":           text[:10_000],    # cap at 10k chars
            "sections_identified": [
                {
                    "section":    s.section_number,
                    "act":        s.act,
                    "title":      s.title,
                    "punishment": s.max_punishment,
                    "bailable":   s.bailable,
                    "cognizable": s.cognizable,
                }
                for s in result.sections
            ],
            "plain_explanation":  result.plain_explanation,
            "flags": [
                {"flag_type": "procedural", "description": f, "severity": "medium"}
                for f in result.flags
            ],
            "has_non_bailable":   not result.is_bailable,
            "has_capital_charge": result.has_capital_charge,
            "fir_number":     result.fir_metadata.get("fir_number")     if result.fir_metadata else None,
            "police_station": result.fir_metadata.get("police_station") if result.fir_metadata else None,
            "district":       result.fir_metadata.get("district")       if result.fir_metadata else None,
        }

        insert_result = await db.table("fir_analyses").insert(row).execute()
        if insert_result.data:
            row_id = UUID(insert_result.data[0]["id"])
            logger.info(
                f"[FIR] Persisted analysis {str(row_id)[:8]} "
                f"for user {user_id[:8]} (source={source})"
            )
            return row_id

    except Exception as exc:
        logger.warning(f"[FIR] Non-fatal: could not persist analysis: {exc}")

    return None
