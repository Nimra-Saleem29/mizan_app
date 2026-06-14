"""
Wakeel وکیل — Voice / Whisper Router
=======================================
Accepts audio recordings from the Expo app's microphone and returns
Urdu/Roman Urdu/English transcriptions + optional legal answers.

Endpoints:
  POST /voice/transcribe        — audio → transcript + legal Q&A answer
  POST /voice/transcribe-only   — audio → transcript only (for user review)
  GET  /voice/status            — reports Whisper model readiness

Architecture:
  - Whisper model is loaded ONCE at startup (stored in app.state.whisper_model)
  - Each request retrieves it from app.state via the Request object
  - VoiceProcessor.set_model() injects it before transcription
  - Transcribed text is piped through the query router's RAG pipeline

Audio format support: WAV, MP3, M4A, WebM (from browser MediaRecorder API),
OGG, FLAC. Max size: 25 MB.
"""

import os
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from loguru import logger
from pydantic import BaseModel, Field
from supabase.client import AsyncClient

from database import get_supabase
from models.schemas import (
    Citation,
    QueryRequest,
    QueryResponse,
    VoiceTranscriptionResponse,
    LanguageCode,
)
from routers.query import ask_legal_question_endpoint as ask_legal_question
from services.voice_processor import SUPPORTED_MIME_TYPES, voice_processor

router = APIRouter()

# ── Constants ─────────────────────────────────────────────────────────────────
MAX_AUDIO_BYTES = 25 * 1024 * 1024   # 25 MB (Whisper's recommended max)
MIN_AUDIO_BYTES = 1024               # 1 KB minimum — smaller files are noise

# Map MIME type → file extension for temp file naming
_MIME_TO_EXT: dict[str, str] = {
    "audio/wav":        ".wav",
    "audio/x-wav":      ".wav",
    "audio/wave":       ".wav",
    "audio/mpeg":       ".mp3",
    "audio/mp3":        ".mp3",
    "audio/mp4":        ".m4a",
    "audio/x-m4a":      ".m4a",
    "audio/webm":       ".webm",
    "video/webm":       ".webm",
    "audio/ogg":        ".ogg",
    "audio/x-ogg":      ".ogg",
    "audio/flac":       ".flac",
}


# ─────────────────────────────────────────────────────────────────────────────
# Response model
# ─────────────────────────────────────────────────────────────────────────────
class VoiceAnswerResponse(BaseModel):
    """Full voice pipeline response: transcript + legal Q&A answer."""
    transcript:     str                      = Field(..., description="Whisper transcription")
    language:       str                      = Field(..., description="urdu | roman_urdu | english")
    whisper_lang:   str                      = Field(..., description="Raw Whisper language code")
    confidence:     float                    = Field(..., description="Transcription confidence 0–1")
    duration_sec:   float                    = Field(..., description="Audio clip duration in seconds")
    processing_ms:  int                      = Field(..., description="Whisper inference time in ms")
    legal_answer:   QueryResponse            = Field(..., description="RAG-powered legal answer")


# ─────────────────────────────────────────────────────────────────────────────
# GET /voice/status
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/status",
    status_code=status.HTTP_200_OK,
    summary="Check Whisper model readiness",
)
async def voice_status(request: Request) -> dict:
    """
    Reports whether the Whisper model has been successfully loaded.
    The frontend can call this on app launch to decide whether to show
    the voice input button.
    """
    whisper_model = getattr(request.app.state, "whisper_model", None)
    is_ready = whisper_model is not None

    return {
        "whisper_ready": is_ready,
        **voice_processor.get_model_info(),
        "message": (
            "Voice input is available. آواز سے سوال کریں!"
            if is_ready
            else "Voice model loading — please try again in a moment."
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# POST /voice/transcribe-only
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/transcribe-only",
    response_model=VoiceTranscriptionResponse,
    status_code=status.HTTP_200_OK,
    summary="Transcribe audio to text — no Q&A, user reviews first",
    responses={
        200: {"description": "Transcription result with detected language"},
        400: {"description": "Empty audio file"},
        413: {"description": "File exceeds 25 MB limit"},
        415: {"description": "Unsupported audio format"},
        503: {"description": "Whisper model not loaded"},
    },
)
async def transcribe_only(
    request: Request,
    audio: UploadFile = File(
        ...,
        description="Audio file (WAV, MP3, M4A, WebM, OGG, FLAC)",
    ),
    language_hint: Optional[str] = Form(
        default=None,
        description="Optional ISO 639-1 language hint for Whisper (e.g. 'ur'). "
                    "Leave empty for auto-detection.",
    ),
    db: AsyncClient = Depends(get_supabase),
) -> VoiceTranscriptionResponse:
    """
    **Step 1 of the two-step voice flow.**

    Transcribes the audio and returns the transcript for the user to
    review in the app UI. The user can edit the transcript before
    submitting it to `POST /query/ask`.

    This is preferred over the single-shot `/voice/transcribe` endpoint
    when Whisper confidence is low, or for short queries where OCR
    mistakes matter (names of people, section numbers, etc.).

    Supports all common mobile audio formats including WebM from the
    Expo `expo-av` MediaRecorder API.
    """
    logger.info(
        f"[POST /voice/transcribe-only] "
        f"file={audio.filename!r} "
        f"content_type={audio.content_type!r}"
    )

    # Inject the pre-loaded Whisper model
    _inject_model(request)

    # Read, validate, transcribe
    audio_bytes, file_ext = await _read_and_validate_audio(audio)
    result = await voice_processor.transcribe_audio(
        audio_bytes=audio_bytes,
        file_ext=file_ext,
        language_hint=language_hint or None,
    )

    logger.info(
        f"[/voice/transcribe-only] ✓ "
        f"lang={result['detected_language']} "
        f"chars={len(result['transcript'])} "
        f"conf={result['confidence']:.2f}"
    )

    return VoiceTranscriptionResponse(
        transcription=result["transcript"],
        detected_language=result["detected_language"],
        confidence=result["confidence"],
        duration_seconds=result["duration_seconds"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /voice/transcribe
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/transcribe",
    response_model=VoiceAnswerResponse,
    status_code=status.HTTP_200_OK,
    summary="Transcribe audio AND get a legal answer in one shot",
    responses={
        200: {"description": "Transcript + AI legal answer"},
        400: {"description": "Empty or too-short audio"},
        413: {"description": "File exceeds 25 MB limit"},
        415: {"description": "Unsupported audio format"},
        503: {"description": "Whisper model not loaded"},
    },
)
async def transcribe_and_answer(
    request: Request,
    audio: UploadFile = File(
        ...,
        description="Audio file (WAV, MP3, M4A, WebM, OGG, FLAC)",
    ),
    language_hint: Optional[str] = Form(
        default=None,
        description="Optional ISO 639-1 language hint for Whisper (e.g. 'ur')",
    ),
    response_language: Optional[LanguageCode] = Form(
        default=None,
        description="Language for the legal answer. Defaults to detected language.",
    ),
    user_id: Optional[str] = Form(
        default=None,
        description="Authenticated user UUID — omit for anonymous",
    ),
    db: AsyncClient = Depends(get_supabase),
) -> VoiceAnswerResponse:
    """
    **Single-shot voice-to-legal-answer pipeline.**

    Full flow:
    1. Validate audio format (MIME type + file size)
    2. Transcribe audio via Whisper (auto language detection)
    3. Classify transcript language (Urdu / Roman Urdu / English)
    4. Pipe transcript through the RAG legal Q&A pipeline
       (same as `POST /query/ask` — FAISS retrieval + Gemini Flash)
    5. Return transcript + full legal answer in one response

    **When to use this vs `/voice/transcribe-only`:**
    - Use this when the user expects an immediate answer (low-latency UX)
    - Use `/transcribe-only` when the user wants to review/correct the
      transcript before submitting (better for complex legal questions)

    The `legal_answer.disclaimer` field always contains the mandatory
    Urdu + English disclaimer reminding the user this is not legal advice.
    """
    logger.info(
        f"[POST /voice/transcribe] "
        f"file={audio.filename!r} "
        f"content_type={audio.content_type!r} "
        f"user={user_id[:8] if user_id else 'anon'}"
    )

    # ── 1. Inject model ───────────────────────────────────────────────────────
    _inject_model(request)

    # ── 2. Read + validate audio ──────────────────────────────────────────────
    audio_bytes, file_ext = await _read_and_validate_audio(audio)

    # ── 3. Transcribe ─────────────────────────────────────────────────────────
    try:
        transcription_result = await voice_processor.transcribe_audio(
            audio_bytes=audio_bytes,
            file_ext=file_ext,
            language_hint=language_hint or None,
        )
    except Exception as exc:
        logger.error(f"[/voice/transcribe] Whisper error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Transcription failed due to an internal error. "
                "ترجمہ میں خرابی — دوبارہ کوشش کریں۔"
            ),
        ) from exc

    transcript        = transcription_result["transcript"]
    detected_language = transcription_result["detected_language"]

    if not transcript.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Could not transcribe any speech from the audio. "
                "آواز سمجھ نہیں آئی — واضح آواز میں دوبارہ کوشش کریں۔"
            ),
        )

    logger.info(
        f"[/voice/transcribe] Transcript ({len(transcript)} chars, "
        f"lang={detected_language}, "
        f"conf={transcription_result['confidence']:.2f}): "
        f"{transcript[:80]!r}"
    )

    # ── 4. Pipe through RAG Q&A pipeline ─────────────────────────────────────
    query_payload = QueryRequest(
        query_text=transcript,
        language=detected_language,                         # type: ignore[arg-type]
        response_language=response_language or detected_language,  # type: ignore[arg-type]
        input_type="voice",
        user_id=UUID(user_id) if user_id else None,
    )

    try:
        legal_answer: QueryResponse = await ask_legal_question(
            payload=query_payload,
            db=db,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[/voice/transcribe] RAG pipeline error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Legal analysis failed after transcription.",
        ) from exc

    logger.info(
        f"[/voice/transcribe] ✓ Complete — "
        f"transcript={len(transcript)} chars, "
        f"answer={len(legal_answer.answer)} chars"
    )

    return VoiceAnswerResponse(
        transcript=transcript,
        language=detected_language,
        whisper_lang=transcription_result["whisper_language"],
        confidence=transcription_result["confidence"],
        duration_sec=transcription_result["duration_seconds"],
        processing_ms=transcription_result["processing_ms"],
        legal_answer=legal_answer,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _inject_model(request: Request) -> None:
    """
    Retrieves the Whisper model from app.state and injects it into the
    module-level voice_processor singleton.

    Raises HTTP 503 if the model failed to load at startup.
    """
    whisper_model = getattr(request.app.state, "whisper_model", None)
    if whisper_model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Voice transcription is temporarily unavailable. "
                "The Whisper model failed to load at startup — "
                "check server logs for details.\n"
                "آواز کی سہولت ابھی دستیاب نہیں — بعد میں کوشش کریں۔"
            ),
        )
    voice_processor.set_model(whisper_model)


async def _read_and_validate_audio(
    audio: UploadFile,
) -> tuple[bytes, str]:
    """
    Reads the uploaded audio file and validates:
      - MIME type is in the supported set
      - File size is within 1 KB – 25 MB bounds
      - Derives the correct file extension for temp file creation

    Returns:
        (audio_bytes, file_ext) where file_ext includes the dot, e.g. ".wav"

    Raises:
        HTTP 415 for unsupported MIME types
        HTTP 413 for files exceeding the limit
        HTTP 400 for empty files
    """
    # ── MIME type check ───────────────────────────────────────────────────────
    content_type = (audio.content_type or "").lower().split(";")[0].strip()
    if content_type not in SUPPORTED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Audio format '{content_type}' is not supported. "
                f"Please use WAV, MP3, M4A, WebM, OGG, or FLAC.\n"
                "آڈیو فارمیٹ قابلِ قبول نہیں — WAV، MP3 یا M4A فائل بھیجیں۔"
            ),
        )

    # ── Read bytes ────────────────────────────────────────────────────────────
    audio_bytes = await audio.read()
    size = len(audio_bytes)

    if size < MIN_AUDIO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Audio file is too small ({size} bytes). "
                "Please record at least 1 second of audio.\n"
                "آڈیو فائل بہت چھوٹی ہے — کم از کم 1 سیکنڈ ریکارڈ کریں۔"
            ),
        )

    if size > MAX_AUDIO_BYTES:
        size_mb = size / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"Audio file {size_mb:.1f} MB exceeds the 25 MB limit. "
                "Please shorten the recording.\n"
                f"آڈیو فائل {size_mb:.1f} MB — حد سے زیادہ، ریکارڈنگ چھوٹی کریں۔"
            ),
        )

    # ── Derive extension ──────────────────────────────────────────────────────
    # Prefer explicit extension from filename, fall back to MIME map
    file_ext = ""
    if audio.filename:
        _, file_ext = os.path.splitext(audio.filename)
        file_ext = file_ext.lower()

    if not file_ext:
        file_ext = _MIME_TO_EXT.get(content_type, ".wav")

    logger.debug(
        f"[_read_and_validate_audio] "
        f"size={size:,}B ext={file_ext} mime={content_type}"
    )
    return audio_bytes, file_ext
