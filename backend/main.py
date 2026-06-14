"""
Wakeel وکیل — FastAPI Application Entry Point (updated with RAG)
"""

import time, uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from config import settings
from database import init_supabase
from routers import auth, query, fir, document, voice, scenario
from services.voice_processor import voice_processor
from services import rag_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("━" * 55)
    logger.info("  🟢  Wakeel وکیل backend starting")
    logger.info(f"      Environment : {settings.ENVIRONMENT}")
    logger.info("━" * 55)

    # Supabase
    await init_supabase()
    logger.info("  ✓  Supabase client ready")

    # Whisper
    try:
        whisper_model = voice_processor.load_model(model_size=settings.WHISPER_MODEL_SIZE)
        app.state.whisper_model = whisper_model
        logger.info(f"  ✓  Whisper '{settings.WHISPER_MODEL_SIZE}' model ready")
    except (ImportError, RuntimeError) as exc:
        logger.warning(f"  ⚠  Whisper NOT loaded: {exc}")
        app.state.whisper_model = None

    # RAG pipeline
    rag_loaded = rag_service.load_rag_pipeline()
    if rag_loaded:
        logger.info("  ✓  RAG pipeline ready (FAISS index loaded)")
    else:
        logger.warning("  ⚠  RAG pipeline NOT loaded — run: python rag/build_index.py")

    logger.info("  ✓  Startup complete — ready to serve")
    yield
    logger.info("  🔴  Wakeel backend shutting down")


app = FastAPI(
    title="Wakeel وکیل API",
    description="AI-Powered Legal Assistant for Pakistan. Grounded in Pakistani law.",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time"],
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{elapsed_ms}ms"
    logger.info(f"{request.method} {request.url.path} → {response.status_code} [{elapsed_ms}ms]")
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception(f"Unhandled exception [{request_id[:8]}]: {exc}")
    detail = str(exc) if settings.DEBUG else "An internal error occurred."
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": type(exc).__name__, "detail": detail, "request_id": request_id},
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": "InvalidInput", "detail": str(exc),
                 "request_id": getattr(request.state, "request_id", "unknown")},
    )


app.include_router(auth.router,     prefix="/auth",     tags=["Authentication"])
app.include_router(query.router,    prefix="/query",    tags=["Legal Q&A"])
app.include_router(fir.router,      prefix="/fir",      tags=["FIR Analysis"])
app.include_router(document.router, prefix="/document", tags=["Document Analysis"])
app.include_router(voice.router,    prefix="/voice",    tags=["Voice / Whisper"])
app.include_router(scenario.router, prefix="/scenario", tags=["Know Your Rights"])


@app.get("/health", tags=["System"])
async def health_check():
    from services.rag_service import _faiss_index
    return {
        "status": "ok",
        "app": "Wakeel", "app_urdu": "وکیل", "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "rag_index_loaded": _faiss_index is not None,
        "whisper_loaded": getattr(app.state, "whisper_model", None) is not None,
    }


@app.get("/", tags=["System"], include_in_schema=False)
async def root():
    return {"message": "Wakeel وکیل API", "docs": "/docs", "health": "/health"}
