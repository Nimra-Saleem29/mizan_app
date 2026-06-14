"""
Wakeel — Document Analysis Router
====================================
Analyses legal documents: contracts, rent agreements, notices, etc.

Endpoints:
  POST /document/analyse         — upload document, get risk analysis
  GET  /document/history/{uid}   — list user's document analyses
"""

from uuid import UUID
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from supabase.client import AsyncClient

from database import get_supabase
from models.schemas import DocumentAnalysisResponse, LanguageCode

router = APIRouter()


@router.post("/analyse", response_model=DocumentAnalysisResponse, status_code=status.HTTP_200_OK,
             summary="Analyse a legal document for risks")
async def analyse_document(
    file: UploadFile = File(..., description="Contract / document image or PDF"),
    document_type: str = Form(default="other"),
    language: LanguageCode = Form(default="urdu"),
    user_id: str = Form(default=None),
    db: AsyncClient = Depends(get_supabase),
) -> DocumentAnalysisResponse:
    """
    Upload a legal document. Returns:
    - Risk flags with explanations
    - Favourable clauses
    - Plain-language summary
    - Overall risk score (0–100)

    > ⚠ Stub: document analysis pipeline coming in Step 8.
    """
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED,
                        detail="Document analysis pipeline coming in Step 8")


@router.get("/history/{user_id}", summary="List user's document analyses")
async def get_document_history(user_id: UUID, db: AsyncClient = Depends(get_supabase)):
    """Returns all document analyses for the given user, newest first."""
    result = await (
        db.table("document_analyses")
        .select("id, document_type, overall_risk_score, created_at")
        .eq("user_id", str(user_id))
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []
