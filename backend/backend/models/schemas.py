"""
Wakeel وکیل — Pydantic Schemas
================================
All request bodies, response models, and shared data types.

Naming convention:
  - *Request  → incoming request body
  - *Response → outgoing response body
  - Everything else is a shared sub-model (e.g. Citation, FIRSection)

All models use `model_config = ConfigDict(from_attributes=True)` so they
can be instantiated directly from ORM / Supabase response dicts.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ─────────────────────────────────────────────────────────────────────────────
# Enums-as-literals (avoids importing Python enum for simple string choices)
# ─────────────────────────────────────────────────────────────────────────────
from typing import Literal

LanguageCode   = Literal["urdu", "english", "roman_urdu"]
InputType      = Literal["text", "voice"]
RiskLevel      = Literal["high", "medium", "low"]
LegalDomain    = Literal[
    "criminal", "family", "property", "labour",
    "consumer", "cyber", "land", "constitutional",
    "civil", "tax", "corporate", "general"
]
OffenceSeverity = Literal["bailable", "non_bailable", "capital", "civil"]


# ═════════════════════════════════════════════════════════════════════════════
# SHARED SUB-MODELS
# ═════════════════════════════════════════════════════════════════════════════

class Citation(BaseModel):
    """A legal citation returned alongside an AI answer."""
    model_config = ConfigDict(from_attributes=True)

    case_name:   str            = Field(..., description="Name of the case or statute")
    court:       str            = Field(..., description="Court name, e.g. 'Supreme Court of Pakistan'")
    year:        str            = Field(..., description="Year of judgment or enactment, e.g. '2019'")
    section:     Optional[str]  = Field(None, description="Section number, e.g. 'Section 302 PPC'")
    url:         Optional[str]  = Field(None, description="Link to full judgment if available")

    @field_validator("year")
    @classmethod
    def validate_year(cls, v: str) -> str:
        if not v.isdigit() or not (1800 <= int(v) <= 2100):
            raise ValueError(f"Invalid year: {v}")
        return v


class FIRSection(BaseModel):
    """One penal section identified within an FIR document."""
    model_config = ConfigDict(from_attributes=True)

    section_number:  str  = Field(..., description="e.g. '302', '324', '34'")
    act:             str  = Field(default="PPC", description="e.g. 'PPC', 'CrPC', 'PECA'")
    title:           str  = Field(..., description="Official title of the offence")
    min_punishment:  str  = Field(..., description="Minimum punishment, e.g. '7 years'")
    max_punishment:  str  = Field(..., description="Maximum punishment, e.g. 'Death'")
    bailable:        bool = Field(..., description="True if the offence is bailable")
    cognizable:      bool = Field(default=True, description="True if police can arrest without warrant")
    explanation:     str  = Field(..., description="Plain-language explanation in user's language")


class RiskFlag(BaseModel):
    """A risky or unfair clause found in a scanned legal document."""
    model_config = ConfigDict(from_attributes=True)

    clause_text:  str       = Field(..., description="The problematic clause text")
    clause_ref:   Optional[str] = Field(None, description="Clause/section number if identifiable")
    risk_level:   RiskLevel = Field(..., description="high | medium | low")
    explanation:  str       = Field(..., description="Why this clause is risky")
    recommendation: Optional[str] = Field(None, description="What the user should do / negotiate")


class FavourableClause(BaseModel):
    """A clause in a document that protects or benefits the user."""
    model_config = ConfigDict(from_attributes=True)

    clause_text:  str = Field(..., description="The beneficial clause text")
    explanation:  str = Field(..., description="Why this clause is favourable")


class ActionStep(BaseModel):
    """A concrete action step in a scenario session outcome."""
    model_config = ConfigDict(from_attributes=True)

    step_number:   int          = Field(..., ge=1)
    action:        str          = Field(..., description="What the user should do")
    urgency:       Literal["immediate", "within_24h", "within_week", "when_possible"]
    relevant_law:  Optional[str] = Field(None)
    helpline:      Optional[str] = Field(None, description="e.g. 'Legal Aid: 0800-12345'")


class ErrorResponse(BaseModel):
    """Standard error response body."""
    error:      str = Field(..., description="Error type name")
    detail:     str = Field(..., description="Human-readable explanation")
    request_id: Optional[str] = None


# ═════════════════════════════════════════════════════════════════════════════
# LEGAL Q&A
# ═════════════════════════════════════════════════════════════════════════════

class QueryRequest(BaseModel):
    """Request body for POST /query/ask"""
    model_config = ConfigDict(from_attributes=True)

    query_text:       str          = Field(
        ...,
        min_length=3,
        max_length=4000,
        description="The legal question in any language",
        examples=["میرے کرایہ دار نے کرایہ دینا بند کر دیا، کیا کروں؟"],
    )
    language:         LanguageCode = Field(
        default="urdu",
        description="Language the user wrote in",
    )
    response_language: Optional[LanguageCode] = Field(
        default=None,
        description="Language for the AI response. Defaults to same as input.",
    )
    input_type:       InputType    = Field(default="text")
    user_id:          Optional[UUID] = Field(
        default=None,
        description="Authenticated user's UUID. Omit for anonymous queries.",
    )
    legal_domain_hint: Optional[LegalDomain] = Field(
        default=None,
        description="Optional hint to improve retrieval accuracy",
    )


class QueryResponse(BaseModel):
    """Response body for POST /query/ask"""
    model_config = ConfigDict(from_attributes=True)

    query_id:          Optional[UUID] = None
    answer:            str            = Field(..., description="AI-generated legal explanation")
    citations:         List[Citation] = Field(default_factory=list)
    legal_domain:      LegalDomain    = Field(default="general")
    language_detected: LanguageCode   = Field(
        ...,
        description="Language the AI detected in the query",
    )
    response_language: LanguageCode
    disclaimer:        str = Field(
        default=(
            "یہ معلومات قانونی مشورے کا متبادل نہیں ہے۔ "
            "اہم معاملات کے لیے کسی وکیل سے ملیں۔\n"
            "This is not legal advice. Consult a qualified lawyer for your specific situation."
        ),
        description="Mandatory disclaimer in Urdu + English",
    )
    processing_time_ms: Optional[int] = None
    model_used:         Optional[str] = None


class QueryHistoryItem(BaseModel):
    """A single query record from the history endpoint."""
    model_config = ConfigDict(from_attributes=True)

    id:               UUID
    query_text:       str
    query_language:   LanguageCode
    response_text:    Optional[str]
    legal_domain:     Optional[str]
    input_type:       InputType
    processing_time_ms: Optional[int]
    created_at:       datetime


# ═════════════════════════════════════════════════════════════════════════════
# FIR ANALYSIS
# ═════════════════════════════════════════════════════════════════════════════

class FIRAnalysisResponse(BaseModel):
    """Response body for POST /fir/analyse"""
    model_config = ConfigDict(from_attributes=True)

    analysis_id:       Optional[UUID]     = None
    sections:          List[FIRSection]   = Field(..., description="Penal sections found in the FIR")
    plain_explanation: str                = Field(..., description="Plain-language summary")
    flags:             List[str]          = Field(
        default_factory=list,
        description="List of procedural or rights violations detected",
    )
    is_bailable:       bool               = Field(
        ...,
        description="True only if ALL sections are bailable",
    )
    has_capital_charge: bool              = Field(default=False)
    fir_metadata:      Optional[Dict[str, Any]] = Field(
        default=None,
        description="Extracted FIR number, date, police station, district",
    )
    your_rights:       List[str]          = Field(
        default_factory=list,
        description="Immediate rights the accused has under this FIR",
    )
    disclaimer:        str = Field(
        default=(
            "یہ تجزیہ AI کی مدد سے ہے اور قانونی مشورہ نہیں۔ "
            "فوری طور پر کسی وکیل سے رابطہ کریں۔"
        ),
    )


# ═════════════════════════════════════════════════════════════════════════════
# DOCUMENT ANALYSIS
# ═════════════════════════════════════════════════════════════════════════════

class DocumentAnalysisResponse(BaseModel):
    """Response body for POST /document/analyse"""
    model_config = ConfigDict(from_attributes=True)

    analysis_id:        Optional[UUID]          = None
    document_type:      str                     = Field(..., description="Detected or provided document type")
    risk_flags:         List[RiskFlag]           = Field(default_factory=list)
    favourable_clauses: List[FavourableClause]  = Field(default_factory=list)
    plain_explanation:  str                     = Field(..., description="Plain-language summary")
    overall_risk_score: Optional[int]           = Field(
        None,
        ge=0,
        le=100,
        description="0 = very low risk, 100 = extremely high risk",
    )
    parties_identified: List[Dict[str, str]]    = Field(
        default_factory=list,
        description="e.g. [{'party_type': 'landlord', 'name': 'Mr. Ahmed'}]",
    )
    recommendations:    List[str]               = Field(
        default_factory=list,
        description="Top-level actions the user should take",
    )
    disclaimer:         str = Field(
        default=(
            "دستاویز کا یہ تجزیہ مکمل قانونی جائزے کا متبادل نہیں۔ "
            "دستخط کرنے سے پہلے وکیل سے مشورہ کریں۔"
        ),
    )


# ═════════════════════════════════════════════════════════════════════════════
# VOICE
# ═════════════════════════════════════════════════════════════════════════════

class VoiceTranscriptionResponse(BaseModel):
    """Response body for POST /voice/transcribe"""
    model_config = ConfigDict(from_attributes=True)

    transcription:     str          = Field(..., description="Whisper transcription of the audio")
    detected_language: str          = Field(..., description="ISO 639-1 language code detected")
    confidence:        Optional[float] = Field(None, ge=0.0, le=1.0)
    duration_seconds:  Optional[float] = None


# ═════════════════════════════════════════════════════════════════════════════
# SCENARIO / KNOW YOUR RIGHTS
# ═════════════════════════════════════════════════════════════════════════════

class ScenarioStartRequest(BaseModel):
    """Request body for POST /scenario/start"""
    scenario_type: str         = Field(..., description="e.g. 'arrested', 'eviction'")
    language:      LanguageCode = Field(default="urdu")
    user_id:       Optional[UUID] = None


class ScenarioAnswerRequest(BaseModel):
    """Request body for POST /scenario/{session_id}/answer"""
    step_id:    str                          = Field(..., description="Current step identifier")
    answer:     Literal["yes", "no", "unsure"]
    user_id:    Optional[UUID] = None


class ScenarioStepResponse(BaseModel):
    """A single step in the guided scenario flowchart."""
    model_config = ConfigDict(from_attributes=True)

    session_id:   UUID
    step_id:      str
    question:     str                                = Field(..., description="The yes/no question in user's language")
    context:      Optional[str]                      = Field(None, description="Explanatory context for this step")
    is_terminal:  bool                               = Field(default=False, description="True if this is the final step")
    guidance:     Optional[str]                      = Field(None, description="Final guidance (only when is_terminal=True)")
    action_steps: Optional[List[ActionStep]]         = None
    progress_pct: int                                = Field(default=0, ge=0, le=100)


# ═════════════════════════════════════════════════════════════════════════════
# AUTH
# ═════════════════════════════════════════════════════════════════════════════

class SignUpRequest(BaseModel):
    email:              str          = Field(..., description="User's email address")
    password:           str          = Field(..., min_length=8)
    full_name:          str          = Field(..., min_length=2)
    phone:              Optional[str] = Field(None, pattern=r"^\+92[0-9]{10}$")
    preferred_language: LanguageCode = Field(default="urdu")


class LoginRequest(BaseModel):
    email:    str = Field(...)
    password: str = Field(...)


class AuthResponse(BaseModel):
    access_token:  str
    token_type:    str  = "bearer"
    user_id:       UUID
    full_name:     str
    preferred_language: LanguageCode


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                 UUID
    full_name:          str
    phone:              Optional[str]
    preferred_language: LanguageCode
    city:               Optional[str]
    province:           Optional[str]
    created_at:         datetime
