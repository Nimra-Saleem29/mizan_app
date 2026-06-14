"""
Wakeel وکیل — Legal Q&A Router (RAG-powered)
"""

import time
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from supabase.client import AsyncClient

from database import get_supabase
from models.schemas import Citation, LegalDomain, QueryHistoryItem, QueryRequest, QueryResponse
from services.rag_service import answer_legal_question, retrieve_relevant_chunks

router = APIRouter()

# Domain detection keywords
_DOMAIN_KEYWORDS = {
    "criminal":       ["fir", "arrest", "police", "bail", "murder", "theft", "302", "جیل", "گرفتار", "ایف آئی آر"],
    "family":         ["divorce", "talaq", "nikah", "custody", "marriage", "طلاق", "نکاح", "کفالت", "مہر"],
    "property":       ["rent", "eviction", "property", "deed", "registry", "کرایہ", "بے دخلی", "جائیداد", "زمین"],
    "labour":         ["salary", "job", "employer", "fired", "termination", "تنخواہ", "نوکری", "ملازمت", "برطرفی"],
    "consumer":       ["fraud", "cheating", "product", "refund", "دھوکہ", "واپسی", "خراب مال"],
    "cyber":          ["online", "internet", "social media", "hacking", "harassment", "آن لائن", "ہراسانی"],
    "constitutional": ["rights", "fundamental", "constitution", "آئین", "بنیادی حقوق", "حق"],
}


def _detect_domain(text: str) -> LegalDomain:
    lower = text.lower()
    for domain, keywords in _DOMAIN_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return domain  # type: ignore
    return "general"


@router.post(
    "/ask",
    response_model=QueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask a legal question — powered by Pakistani law RAG",
)
async def ask_legal_question_endpoint(
    payload: QueryRequest,
    db: AsyncClient = Depends(get_supabase),
) -> QueryResponse:
    """
    Submit a legal question in Urdu, Roman Urdu, or English.
    Answers are grounded in actual Pakistani law via RAG (FAISS + Gemini).
    """
    start_time = time.perf_counter()
    logger.info(f"[/query/ask] lang={payload.language} user={str(payload.user_id)[:8] if payload.user_id else 'anon'}")

    detected_language   = payload.language
    response_language   = payload.response_language or payload.language
    legal_domain        = payload.legal_domain_hint or _detect_domain(payload.query_text)

    # ── RAG pipeline ──────────────────────────────────────────────────────────
    try:
        rag_result = await answer_legal_question(
            query_text=payload.query_text,
            language=response_language,
            top_k=5,
        )
        answer     = rag_result["answer"]
        citations  = [Citation(**c) for c in rag_result["citations"]]
        model_used = "gemini-rag" if rag_result["rag_active"] else "gemini-direct"
    except Exception as exc:
        logger.error(f"[/query/ask] RAG pipeline error: {exc}")
        answer     = "معاف کریں، جواب تیار کرنے میں مسئلہ ہوا۔ دوبارہ کوشش کریں۔"
        citations  = []
        model_used = "error"

    elapsed_ms = round((time.perf_counter() - start_time) * 1000)

    # ── Persist to Supabase ───────────────────────────────────────────────────
    query_id: Optional[UUID] = None
    if payload.user_id:
        try:
            row = {
                "user_id":            str(payload.user_id),
                "query_text":         payload.query_text,
                "query_language":     payload.language,
                "input_type":         payload.input_type,
                "response_text":      answer,
                "response_language":  response_language,
                "legal_domain":       legal_domain,
                "citations":          [c.model_dump() for c in citations],
                "processing_time_ms": elapsed_ms,
                "model_used":         model_used,
            }
            result = await db.table("queries").insert(row).execute()
            if result.data:
                query_id = UUID(result.data[0]["id"])
        except Exception as exc:
            logger.warning(f"[/query/ask] DB persist failed (non-fatal): {exc}")

    logger.info(f"[/query/ask] ✓ {elapsed_ms}ms domain={legal_domain} model={model_used}")

    return QueryResponse(
        query_id=query_id,
        answer=answer,
        citations=citations,
        legal_domain=legal_domain,
        language_detected=detected_language,
        response_language=response_language,
        processing_time_ms=elapsed_ms,
        model_used=model_used,
    )


@router.get(
    "/history/{user_id}",
    response_model=List[QueryHistoryItem],
    status_code=status.HTTP_200_OK,
    summary="Get query history for a user",
)
async def get_query_history(
    user_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    domain: Optional[LegalDomain] = Query(default=None),
    db: AsyncClient = Depends(get_supabase),
) -> List[QueryHistoryItem]:
    try:
        builder = (
            db.table("queries")
            .select("id, query_text, query_language, response_text, legal_domain, input_type, processing_time_ms, created_at")
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
        )
        if domain:
            builder = builder.eq("legal_domain", domain)
        result = await builder.execute()
        return [QueryHistoryItem(**row) for row in (result.data or [])]
    except Exception as exc:
        logger.error(f"[/query/history] DB error: {exc}")
        raise HTTPException(status_code=500, detail="Failed to retrieve history.")


@router.delete("/{query_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_query(query_id: UUID, db: AsyncClient = Depends(get_supabase)):
    await db.table("queries").delete().eq("id", str(query_id)).execute()


@router.patch("/{query_id}/feedback", status_code=status.HTTP_200_OK)
async def submit_feedback(query_id: UUID, rating: int = Query(..., ge=1, le=5), db: AsyncClient = Depends(get_supabase)):
    await db.table("queries").update({"feedback_rating": rating}).eq("id", str(query_id)).execute()
    return {"message": "شکریہ! Feedback recorded."}
