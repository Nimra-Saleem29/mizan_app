"""
Wakeel وکیل — RAG Service
Retrieval-Augmented Generation pipeline for Pakistani law Q&A.
Loads FAISS index + chunks, searches on query, calls Gemini with context.
"""

import json, time
from pathlib import Path
from typing import Optional
from loguru import logger

INDEX_DIR = Path(__file__).parent.parent / "rag" / "indices"
CHUNKS_PATH = INDEX_DIR / "wakeel_chunks.json"
FAISS_PATH  = INDEX_DIR / "wakeel_legal.faiss"

_faiss_index  = None
_chunks: list = []
_embed_model  = None
_gemini_model = None


def load_rag_pipeline():
    """Call once at startup to load FAISS index + embedding model."""
    global _faiss_index, _chunks, _embed_model

    if not FAISS_PATH.exists():
        logger.warning("FAISS index not found. Run: python rag/build_index.py")
        return False
    if not CHUNKS_PATH.exists():
        logger.warning("Chunks file not found. Run: python rag/build_index.py")
        return False

    try:
        import faiss
        from sentence_transformers import SentenceTransformer

        logger.info("Loading FAISS index...")
        _faiss_index = faiss.read_index(str(FAISS_PATH))

        logger.info("Loading chunks metadata...")
        with open(CHUNKS_PATH, encoding="utf-8") as f:
            _chunks = json.load(f)

        logger.info("Loading embedding model (multilingual)...")
        _embed_model = SentenceTransformer(
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )

        logger.info(f"✓ RAG pipeline ready — {_faiss_index.ntotal} vectors, {len(_chunks)} chunks")
        return True

    except Exception as exc:
        logger.error(f"RAG pipeline load failed: {exc}")
        return False


def _get_gemini():
    global _gemini_model
    if _gemini_model is None:
        import google.generativeai as genai
        from config import settings
        genai.configure(api_key=settings.GEMINI_API_KEY)
        _gemini_model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            generation_config=genai.GenerationConfig(
                temperature=settings.GEMINI_TEMPERATURE,
                max_output_tokens=settings.GEMINI_MAX_TOKENS,
            ),
        )
    return _gemini_model


def retrieve_relevant_chunks(query: str, top_k: int = 5) -> list[dict]:
    """Search FAISS index for chunks most relevant to the query."""
    if _faiss_index is None or _embed_model is None:
        return []

    import numpy as np
    query_vec = _embed_model.encode([query]).astype("float32")
    distances, indices = _faiss_index.search(query_vec, top_k)

    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx < len(_chunks):
            chunk = _chunks[idx].copy()
            chunk["relevance_score"] = float(1 / (1 + dist))
            results.append(chunk)

    results.sort(key=lambda x: x["relevance_score"], reverse=True)
    return results


async def answer_legal_question(
    query_text: str,
    language: str = "urdu",
    top_k: int = 5,
) -> dict:
    """
    Full RAG pipeline:
    1. Retrieve relevant Pakistani law chunks via FAISS
    2. Pass query + context to Gemini Flash
    3. Return structured answer with citations
    """
    start = time.perf_counter()

    # Retrieve relevant law chunks
    relevant_chunks = retrieve_relevant_chunks(query_text, top_k=top_k)

    if not relevant_chunks:
        # Fallback — no index loaded, use Gemini with general knowledge
        logger.warning("RAG: No chunks retrieved — using Gemini general knowledge")
        context_text = "پاکستانی قانون کے عمومی اصولوں کی بنیاد پر جواب دیں۔"
        sources = []
    else:
        context_text = "\n\n---\n\n".join(
            f"[{c['source']}]\n{c['text']}" for c in relevant_chunks
        )
        sources = list({c["source"] for c in relevant_chunks})

    # Language-specific prompt
    if language == "urdu":
        prompt = f"""آپ پاکستانی قانون کے ماہر وکیل ہیں۔ نیچے پاکستانی قانون کے متعلقہ حصے دیے گئے ہیں۔
انہی کی بنیاد پر سوال کا جواب سادہ اردو میں دیں۔

قانونی متن:
{context_text}

سوال: {query_text}

ہدایات:
- صرف فراہم کردہ قانونی متن کی بنیاد پر جواب دیں
- سادہ اردو میں جواب دیں جو عام شہری سمجھ سکے
- متعلقہ دفعات (PPC، آئین وغیرہ) کا حوالہ دیں
- عملی مشورہ دیں کہ کیا کرنا چاہیے
- آخر میں لکھیں: "یاد رہے: یہ قانونی معلومات ہیں، باقاعدہ قانونی مشورے کے لیے وکیل سے ملیں۔"
"""
    elif language == "roman_urdu":
        prompt = f"""Aap Pakistani qanoon ke mahir wakeel hain. Neeche Pakistani qanoon ke mutalliqah hissay diye gaye hain.
Inhein ki bunyaad par sawal ka jawab simple Roman Urdu mein dein.

Qanooni Matn:
{context_text}

Sawal: {query_text}

Hidayaat:
- Sirf diye gaye qanooni matn ki bunyaad par jawab dein
- Simple Roman Urdu mein likhein
- Mutalliqah dafaat (PPC, Constitution etc.) ka hawala dein
- Akhir mein likhein: "Yaad rahay: professional legal advice ke liye wakeel se milein."
"""
    else:
        prompt = f"""You are an expert Pakistani lawyer. Using the Pakistani law text provided below,
answer the question in clear, simple English that any ordinary citizen can understand.

Legal Context:
{context_text}

Question: {query_text}

Instructions:
- Base your answer ONLY on the provided legal text
- Use simple language, avoid complex legal jargon
- Reference specific sections (PPC, Constitution, CrPC etc.) where relevant
- Give practical advice on what the person should do
- End with: "Note: This is legal information, not professional legal advice. Consult a qualified lawyer for your specific situation."
"""

    try:
        model = _get_gemini()
        response = model.generate_content(prompt)
        answer = response.text.strip()
    except Exception as exc:
        logger.error(f"Gemini error: {exc}")
        answer = (
            "معاف کریں، اس وقت جواب دینے میں مسئلہ ہے۔ براہ کرم دوبارہ کوشش کریں۔"
            if language == "urdu"
            else "Sorry, unable to generate answer right now. Please try again."
        )

    elapsed_ms = round((time.perf_counter() - start) * 1000)

    # Build citations from sources
    source_map = {
    "ppc_core.txt":          ("Pakistan Penal Code 1860",                  "Legislature", "1860"),
    "constitution_core.txt": ("Constitution of Pakistan 1973",             "Legislature", "1973"),
    "crpc_core.txt":         ("Code of Criminal Procedure 1898",           "Legislature", "1898"),
    "bail_guide.txt":        ("CrPC — Bail Provisions",                    "Legislature", "1898"),
    "family_law.txt":        ("Muslim Family Laws Ordinance 1961",         "Legislature", "1961"),
    "labour_law.txt":        ("Industrial & Commercial Employment Ord.",   "Legislature", "1968"),
    "rent_laws.txt":         ("Punjab Rented Premises Act 2009",           "Legislature", "2009"),
    "consumer_rights.txt":   ("Consumer Protection Act 2005",              "Legislature", "2005"),
    "cyber_law.txt":         ("Prevention of Electronic Crimes Act 2016",  "Legislature", "2016"),
    "legal_aid.txt":         ("Legal Aid Resources Pakistan",              "Government",  "2024"),
}

    citations = []
    for src in sources:
        if src in source_map:
            name, court, year = source_map[src]
            citations.append({
                "case_name": name,
                "court":     court,
                "year":      year,
                "section":   None,
                "url":       None,
            })

    return {
        "answer":             answer,
        "citations":          citations,
        "sources_searched":   sources,
        "chunks_retrieved":   len(relevant_chunks),
        "processing_ms":      elapsed_ms,
        "rag_active":         len(relevant_chunks) > 0,
    }
