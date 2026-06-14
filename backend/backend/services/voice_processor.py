"""
Wakeel وکیل — Voice Processor Service
========================================
Handles speech-to-text transcription for Urdu, Roman Urdu, and English
audio queries using OpenAI Whisper (local inference).

Design decisions:
  - Whisper "medium" model: best balance of accuracy vs speed for Urdu.
    "large-v3" is more accurate but requires ~10GB RAM. "small" misses
    Urdu phonemes. "medium" (1.5GB VRAM / ~3GB RAM) is the sweet spot.
  - Model is loaded ONCE at app startup and stored in app.state.
    Loading takes ~15–30s; reloading on every request would be unusable.
  - language=None → Whisper auto-detects. This handles code-switching
    (mixing Urdu + English in the same sentence — very common in Pakistan).
  - Temp files are used because Whisper's Python API expects a file path,
    not bytes. We clean up immediately after transcription.
  - fp16=False → required for CPU. GPU deployments can enable fp16.

Usage (from router):
    from services.voice_processor import VoiceProcessor
    processor = VoiceProcessor()
    result = await processor.transcribe_audio(audio_bytes, file_ext=".wav")
"""

import asyncio
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Any, Optional

from loguru import logger


# ─────────────────────────────────────────────────────────────────────────────
# Supported audio formats
# ─────────────────────────────────────────────────────────────────────────────
SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({
    ".wav", ".mp3", ".m4a", ".webm", ".ogg", ".flac", ".mp4",
})

SUPPORTED_MIME_TYPES: frozenset[str] = frozenset({
    "audio/wav",  "audio/x-wav", "audio/wave",
    "audio/mpeg", "audio/mp3",
    "audio/mp4",  "audio/x-m4a",
    "audio/webm", "video/webm",   # WebM from browser MediaRecorder API
    "audio/ogg",  "audio/x-ogg",
    "audio/flac",
})

# Whisper's detected language code → our LanguageCode enum
_WHISPER_LANG_MAP: dict[str, str] = {
    "ur":  "urdu",
    "hi":  "roman_urdu",   # Hindi is often misidentified Roman Urdu
    "en":  "english",
    "pa":  "roman_urdu",   # Punjabi → treat as Roman Urdu
    "ar":  "urdu",         # Arabic script → map to Urdu
}

# Urdu/Arabic Unicode block range
_URDU_UNICODE_RANGE = re.compile(r'[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]')

# Common romanised Urdu words (a non-exhaustive signal set)
_ROMAN_URDU_SIGNALS = frozenset({
    "hai", "hain", "nahi", "nahin", "kya", "karo", "karna", "mera",
    "meri", "tera", "uska", "unka", "aur", "lekin", "kyunke", "phir",
    "abhi", "yahan", "wahan", "theek", "shukriya", "meherbani",
    "jan", "bhai", "apa", "sahib", "jee", "zaroor", "bilkul",
    "adalat", "vakeel", "wakeel", "qanun", "fir", "darkhwast",
    "talaq", "kiraya", "naukri", "tankhwah", "bail",
})


class VoiceProcessor:
    """
    Manages Whisper model lifecycle and provides async-safe transcription.

    The model is NOT loaded at instantiation — call `load_model()` once
    during FastAPI lifespan and pass the result to `set_model()`.

    Thread safety: Whisper inference is CPU-bound. We run it in a
    ThreadPoolExecutor via asyncio.get_event_loop().run_in_executor()
    to avoid blocking the async event loop.
    """

    def __init__(self) -> None:
        self._model: Any = None           # whisper.WhisperModel instance
        self._model_name: str = "medium"
        self._model_loaded: bool = False

    # ─────────────────────────────────────────────────────────────────────────
    # Model lifecycle
    # ─────────────────────────────────────────────────────────────────────────
    def load_model(self, model_size: str = "medium") -> Any:
        """
        Loads the Whisper model synchronously.
        Call this from FastAPI lifespan — NOT from a request handler.

        Args:
            model_size: "tiny" | "base" | "small" | "medium" | "large-v3"
                        "medium" is recommended for Urdu accuracy on CPU.

        Returns:
            The loaded whisper model (also stored internally).

        Raises:
            ImportError: if openai-whisper is not installed
            RuntimeError: if model download fails
        """
        try:
            import whisper
        except ImportError as exc:
            raise ImportError(
                "openai-whisper is not installed. "
                "Run: pip install openai-whisper"
            ) from exc

        self._model_name = model_size
        start = time.perf_counter()

        logger.info(f"  ⏳  Loading Whisper '{model_size}' model...")
        logger.info("      This may take 30–60s on first run (downloads ~1.5GB)")

        try:
            self._model = whisper.load_model(model_size)
            self._model_loaded = True
        except Exception as exc:
            logger.error(f"  ✗  Whisper model load failed: {exc}")
            raise RuntimeError(f"Failed to load Whisper model '{model_size}': {exc}") from exc

        elapsed = round(time.perf_counter() - start, 1)
        logger.info(f"  ✓  Whisper '{model_size}' loaded in {elapsed}s")
        return self._model

    def set_model(self, model: Any) -> None:
        """
        Injects a pre-loaded model (e.g. stored in app.state.whisper_model).
        Called by the router before processing requests.
        """
        self._model = model
        self._model_loaded = model is not None

    @property
    def is_ready(self) -> bool:
        return self._model_loaded and self._model is not None

    # ─────────────────────────────────────────────────────────────────────────
    # METHOD 1: transcribe_audio
    # ─────────────────────────────────────────────────────────────────────────
    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        file_ext: str,
        *,
        language_hint: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Transcribes audio bytes to text using Whisper.

        Steps:
          1. Validate the model is loaded
          2. Write bytes to a named temp file (Whisper needs a file path)
          3. Run Whisper inference in a thread (non-blocking)
          4. Classify the output language via detect_input_language()
          5. Clean up temp file
          6. Return structured result

        Args:
            audio_bytes:   Raw audio bytes from the uploaded file
            file_ext:      File extension including dot, e.g. ".wav", ".m4a"
            language_hint: Optional ISO 639-1 code to guide Whisper, e.g. "ur".
                           Pass None for full auto-detection (recommended).

        Returns:
            {
                "transcript":        str,   # transcribed text
                "detected_language": str,   # "urdu" | "roman_urdu" | "english"
                "whisper_language":  str,   # raw Whisper language code, e.g. "ur"
                "confidence":        float, # avg log-prob converted to 0–1
                "duration_seconds":  float, # audio duration
                "processing_ms":     int,   # wall-clock time for inference
                "model":             str,   # model size used
            }

        Raises:
            RuntimeError: if the model is not loaded
            ValueError:   if audio_bytes is empty or ext is unsupported
        """
        if not self.is_ready:
            raise RuntimeError(
                "Whisper model is not loaded. "
                "Ensure load_model() was called during app startup."
            )

        if not audio_bytes:
            raise ValueError("audio_bytes is empty — nothing to transcribe.")

        ext = file_ext.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported audio format '{ext}'. "
                f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            )

        logger.info(
            f"[Voice] Transcribing {len(audio_bytes):,} bytes "
            f"(ext={ext}, lang_hint={language_hint or 'auto'})"
        )

        # Write to temp file — Whisper needs a filesystem path
        tmp_path: Optional[Path] = None
        try:
            tmp_path = _write_temp_audio(audio_bytes, ext)
            result = await _run_whisper_inference(
                model=self._model,
                audio_path=str(tmp_path),
                language_hint=language_hint,
            )
        finally:
            if tmp_path and tmp_path.exists():
                try:
                    tmp_path.unlink()
                    logger.debug(f"[Voice] Cleaned up temp file: {tmp_path}")
                except OSError:
                    pass  # non-fatal

        transcript: str      = result.get("text", "").strip()
        whisper_lang: str    = result.get("language", "unknown")
        avg_log_prob: float  = result.get("avg_logprob", -1.0)
        duration: float      = result.get("duration", 0.0)
        processing_ms: int   = result.get("_processing_ms", 0)

        # Convert log-probability to a 0–1 confidence score
        # avg_logprob is typically in range [-2, 0]; 0 = perfect confidence
        confidence = max(0.0, min(1.0, 1.0 + (avg_log_prob / 2.0)))

        # Classify final language from script analysis
        detected_language = self.detect_input_language(transcript, whisper_lang)

        logger.info(
            f"[Voice] ✓ Transcribed {len(transcript)} chars "
            f"in {processing_ms}ms "
            f"| lang={detected_language} (whisper={whisper_lang}) "
            f"| conf={confidence:.2f} "
            f"| duration={duration:.1f}s"
        )

        return {
            "transcript":        transcript,
            "detected_language": detected_language,
            "whisper_language":  whisper_lang,
            "confidence":        round(confidence, 3),
            "duration_seconds":  round(duration, 2),
            "processing_ms":     processing_ms,
            "model":             self._model_name,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # METHOD 2: detect_input_language
    # ─────────────────────────────────────────────────────────────────────────
    def detect_input_language(
        self,
        text: str,
        whisper_lang_code: Optional[str] = None,
    ) -> str:
        """
        Classifies the script/language of the transcribed text.

        Detection order (highest confidence first):
          1. Whisper's own language detection (most reliable signal)
          2. Unicode script analysis — Urdu/Arabic block presence
          3. Roman Urdu keyword matching — common words in romanised form
          4. Fallback → "english"

        Args:
            text:             The transcribed text string
            whisper_lang_code: ISO 639-1 code from Whisper, e.g. "ur", "en"

        Returns:
            "urdu" | "roman_urdu" | "english"
        """
        # ── 1. Trust Whisper's language detection first ───────────────────────
        if whisper_lang_code and whisper_lang_code in _WHISPER_LANG_MAP:
            mapped = _WHISPER_LANG_MAP[whisper_lang_code]
            # But override with script analysis if Whisper said "hi" (Hindi)
            # and the text contains Urdu Unicode — Whisper confuses them
            if mapped != "roman_urdu":
                logger.debug(f"[Voice] Language via Whisper map: {mapped}")
                return mapped

        if not text:
            return "english"

        # ── 2. Unicode script analysis ────────────────────────────────────────
        urdu_chars = len(_URDU_UNICODE_RANGE.findall(text))
        total_chars = len(text.replace(" ", "").replace("\n", ""))

        if total_chars > 0:
            urdu_ratio = urdu_chars / total_chars
            if urdu_ratio > 0.15:   # >15% Urdu/Arabic script → Urdu
                logger.debug(f"[Voice] Language via script analysis: urdu ({urdu_ratio:.0%} Urdu chars)")
                return "urdu"

        # ── 3. Roman Urdu keyword detection ──────────────────────────────────
        words = set(text.lower().split())
        signal_hits = len(words & _ROMAN_URDU_SIGNALS)
        # If ≥2 Roman Urdu signal words appear → Roman Urdu
        if signal_hits >= 2:
            logger.debug(f"[Voice] Language via keyword signals: roman_urdu ({signal_hits} hits)")
            return "roman_urdu"

        # ── 4. Fallback ───────────────────────────────────────────────────────
        logger.debug("[Voice] Language fallback: english")
        return "english"

    # ─────────────────────────────────────────────────────────────────────────
    # Utility
    # ─────────────────────────────────────────────────────────────────────────
    def get_model_info(self) -> dict[str, Any]:
        """Returns metadata about the currently loaded model."""
        return {
            "loaded":     self.is_ready,
            "model_size": self._model_name if self.is_ready else None,
            "supported_formats": sorted(SUPPORTED_EXTENSIONS),
            "supported_languages": ["urdu", "roman_urdu", "english"],
        }


# ─────────────────────────────────────────────────────────────────────────────
# Module-level helpers
# ─────────────────────────────────────────────────────────────────────────────

def _write_temp_audio(audio_bytes: bytes, ext: str) -> Path:
    """
    Writes audio bytes to a named temporary file.

    Uses delete=False so the file persists after closing (needed on Windows
    and for Whisper which re-opens by path). Caller is responsible for
    calling unlink() after use.

    Returns the Path to the temp file.
    """
    suffix = ext if ext.startswith(".") else f".{ext}"
    tmp = tempfile.NamedTemporaryFile(
        suffix=suffix,
        prefix="wakeel_audio_",
        delete=False,
    )
    try:
        tmp.write(audio_bytes)
        tmp.flush()
        return Path(tmp.name)
    finally:
        tmp.close()


async def _run_whisper_inference(
    model: Any,
    audio_path: str,
    language_hint: Optional[str],
) -> dict[str, Any]:
    """
    Runs Whisper transcription in a ThreadPoolExecutor to avoid
    blocking the FastAPI async event loop.

    Whisper is CPU-bound and can take 5–60s for medium model.
    Running it in a thread allows other requests to be served concurrently.

    Returns the raw Whisper result dict (text, language, segments, etc.)
    with an added _processing_ms key.
    """
    loop = asyncio.get_event_loop()

    def _inference() -> dict[str, Any]:
        start = time.perf_counter()

        transcribe_kwargs: dict[str, Any] = {
            "task":         "transcribe",
            "fp16":         False,           # CPU compatibility
            "verbose":      False,
            "word_timestamps": False,        # faster without word-level timing
            "condition_on_previous_text": True,  # improves Urdu coherence
        }

        # Only pass language if explicitly hinted — None = auto-detect
        if language_hint:
            transcribe_kwargs["language"] = language_hint

        result: dict[str, Any] = model.transcribe(audio_path, **transcribe_kwargs)

        elapsed_ms = round((time.perf_counter() - start) * 1000)
        result["_processing_ms"] = elapsed_ms
        return result

    return await loop.run_in_executor(None, _inference)


# ─────────────────────────────────────────────────────────────────────────────
# Module-level singleton (shared across routers)
# ─────────────────────────────────────────────────────────────────────────────
# The router imports this and calls .set_model(app.state.whisper_model)
# at request time. The model itself lives in app.state.
voice_processor = VoiceProcessor()
