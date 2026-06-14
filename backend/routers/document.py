"""
Wakeel وکیل — Document Analysis Router
=========================================
Connects the DocumentAnalyzer service to HTTP endpoints.

Endpoints:
  POST /document/analyze        — upload image/text, get risk analysis
  GET  /document/types          — list all supported document types
  GET  /document/history/{uid}  — user's past analyses
  GET  /document/{analysis_id}  — retrieve one analysis
  DELETE /document/{analysis_id}— delete an analysis
"""

import time
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from loguru import logger
from pydantic import BaseModel, Field
from supabase.client import AsyncClient

from database import get_supabase
from models.schemas import DocumentAnalysisResponse, LanguageCode
from services.document_analyzer import DOCUMENT_TYPES, DocumentAnalyzer

router = APIRouter()

_analyzer = DocumentAnalyzer()

ALLOWED_IMAGE_TYPES = frozenset({
    "image/jpeg", "image/jpg", "image/png",
    "image/tiff", "image/webp", "application/pdf",
})
MAX_BYTES = 10 * 1024 * 1024   # 10 MB
MIN_OCR_CHARS = 20


class DocumentTextRequest(BaseModel):
    text: str = Field(..., min_length=MIN_OCR_CHARS, max_length=50_000)
    document_type: Optional[str] = None
    language: LanguageCode = "urdu"
    user_id: Optional[UUID] = None


# ─── GET /document/types ──────────────────────────────────────────────────────
@router.get("/types", summary="List all supported document types")
async def list_document_types() -> dict:
    """Returns every document type Wakeel can analyse, with Urdu labels and icons."""
    return {
        "document_types": [
            {"id": k, **v} for k, v in DOCUMENT_TYPES.items()
        ]
    }


# ─── POST /document/analyze ───────────────────────────────────────────────────
@router.post(
    "/analyze",
    response_model=DocumentAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyse a legal document (image upload or raw text)",
    responses={
        200: {"description": "Risk flags, favourable clauses, plain-Urdu summary"},
        413: {"description": "File exceeds 10 MB"},
        415: {"description": "Unsupported file type"},
        422: {"description": "Image quality too low / text too short"},
    },
)
async def analyze_document(
    image: Optional[UploadFile] = File(default=None, description="Document image or PDF (optional)"),
    text: Optional[str] = Form(default=None, description="Raw document text (optional)"),
    document_type: Optional[str] = Form(default=None, description="Hint for document type"),
    language: LanguageCode = Form(default="urdu"),
    user_id: Optional[str] = Form(default=None),
    db: AsyncClient = Depends(get_supabase),
) -> DocumentAnalysisResponse:
    """
    Analyses a Pakistani legal document for risk flags and plain-Urdu explanation.
    Provide at least one of image or text.
    """
    start = time.perf_counter()
    logger.info(
        f"[POST /document/analyze] "
        f"has_image={image is not None} "
        f"has_text={bool(text)} "
        f"user={user_id or 'anon'}"
    )

    if image is None and not text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide either an image file or text. دستاویز کی تصویر یا متن فراہم کریں۔",
        )

    image_bytes: Optional[bytes] = None

    if image is not None:
        content_type = (image.content_type or "").lower().split(";")[0].strip()
        if content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"File type '{content_type}' not supported. Use JPEG, PNG, or PDF.",
            )
        image_bytes = await image.read()
        if not image_bytes:
            raise HTTPException(status_code=422, detail="Uploaded file is empty.")
        if len(image_bytes) > MAX_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File {len(image_bytes)/(1024*1024):.1f} MB exceeds 10 MB limit.",
            )

    try:
        result: DocumentAnalysisResponse = await _analyzer.analyze_document(
            image_bytes=image_bytes,
            text=text or None,
            hint_doc_type=document_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.error(f"[/document/analyze] pipeline error: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Document analysis failed. دوبارہ کوشش کریں۔",
        )

    # Persist to Supabase
    analysis_id = await _persist_document_analysis(
        db=db,
        result=result,
        raw_text=(text or "")[:10_000],
        user_id=user_id,
    )
    result.analysis_id = analysis_id

    elapsed = round((time.perf_counter() - start) * 1000)
    logger.info(
        f"[/document/analyze] ✓ {elapsed}ms "
        f"type={result.document_type} "
        f"score={result.overall_risk_score}"
    )
    return result


# ─── Also support /analyse (British spelling) for backward compat ─────────────
@router.post(
    "/analyse",
    response_model=DocumentAnalysisResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,  # hidden from docs — just an alias
)
async def analyse_document_alias(
    image: Optional[UploadFile] = File(default=None),
    text: Optional[str] = Form(default=None),
    document_type: Optional[str] = Form(default=None),
    language: LanguageCode = Form(default="urdu"),
    user_id: Optional[str] = Form(default=None),
    db: AsyncClient = Depends(get_supabase),
) -> DocumentAnalysisResponse:
    """Alias for /analyze (British spelling)."""
    return await analyze_document(image, text, document_type, language, user_id, db)


# ─── GET /document/history/{user_id} ─────────────────────────────────────────
@router.get("/history/{user_id}", summary="List a user's document analyses")
async def get_document_history(
    user_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncClient = Depends(get_supabase),
) -> list:
    try:
        result = await (
            db.table("document_analyses")
            .select("id, document_type, overall_risk_score, created_at")
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return result.data or []
    except Exception as exc:
        logger.error(f"[/document/history] DB error: {exc}")
        raise HTTPException(status_code=500, detail="Failed to retrieve history.")


# ─── GET /document/{analysis_id} ─────────────────────────────────────────────
@router.get("/{analysis_id}", summary="Get a specific document analysis")
async def get_document_analysis(
    analysis_id: UUID,
    db: AsyncClient = Depends(get_supabase),
):
    try:
        result = await (
            db.table("document_analyses")
            .select("*")
            .eq("id", str(analysis_id))
            .single()
            .execute()
        )
    except Exception as exc:
        logger.error(f"[/document/{analysis_id}] DB error: {exc}")
        raise HTTPException(status_code=500, detail="Failed to retrieve analysis.")

    if not result.data:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return result.data


# ─── DELETE /document/{analysis_id} ──────────────────────────────────────────
@router.delete("/{analysis_id}", status_code=204, summary="Delete a document analysis")
async def delete_document_analysis(
    analysis_id: UUID,
    db: AsyncClient = Depends(get_supabase),
):
    try:
        await (
            db.table("document_analyses")
            .delete()
            .eq("id", str(analysis_id))
            .execute()
        )
    except Exception as exc:
        logger.error(f"[DELETE /document/{analysis_id}] DB error: {exc}")
        raise HTTPException(status_code=500, detail="Failed to delete analysis.")


# ─── Internal persistence ─────────────────────────────────────────────────────
async def _persist_document_analysis(
    *,
    db: AsyncClient,
    result: DocumentAnalysisResponse,
    raw_text: str,
    user_id: Optional[str],
) -> Optional[UUID]:
    if not user_id:
        return None
    try:
        row = {
            "user_id":             user_id,
            "document_type":       result.document_type,
            "raw_text":            raw_text,
            "risk_flags":          [f.model_dump() for f in result.risk_flags],
            "favourable_clauses":  [c.model_dump() for c in result.favourable_clauses],
            "plain_explanation":   result.plain_explanation,
            "overall_risk_score":  result.overall_risk_score,
            "parties_identified":  result.parties_identified,
        }
        inserted = await db.table("document_analyses").insert(row).execute()
        if inserted.data:
            return UUID(inserted.data[0]["id"])
    except Exception as exc:
        logger.warning(f"[document] Non-fatal: persist failed: {exc}")
    return None
