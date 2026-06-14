"""
Wakeel وکیل — FAISS Index Builder
Run ONCE after collect_laws.py:
    python rag/build_index.py
Output: rag/indices/wakeel_legal.faiss + rag/indices/wakeel_chunks.json
"""

import json, time
from pathlib import Path

RAW_DIR     = Path(__file__).parent / "raw_laws"
INDEX_DIR   = Path(__file__).parent / "indices"
INDEX_DIR.mkdir(exist_ok=True)

CHUNK_SIZE    = 400   # characters per chunk
CHUNK_OVERLAP = 80    # overlap between chunks to preserve context


def load_law_files() -> list[dict]:
    """Load all .txt files from raw_laws/ directory."""
    docs = []
    for filepath in sorted(RAW_DIR.glob("*.txt")):
        text = filepath.read_text(encoding="utf-8").strip()
        docs.append({"source": filepath.name, "text": text})
        print(f"  Loaded: {filepath.name} ({len(text):,} chars)")
    return docs


def split_into_chunks(docs: list[dict]) -> list[dict]:
    """Split documents into overlapping chunks for better retrieval."""
    chunks = []
    for doc in docs:
        text   = doc["text"]
        source = doc["source"]
        # Split on section boundaries first
        sections = text.split("\n\nSECTION ")
        for i, section in enumerate(sections):
            if i > 0:
                section = "SECTION " + section
            # Further split large sections by character limit
            for start in range(0, len(section), CHUNK_SIZE - CHUNK_OVERLAP):
                chunk_text = section[start:start + CHUNK_SIZE].strip()
                if len(chunk_text) > 80:  # skip tiny fragments
                    chunks.append({
                        "id":     len(chunks),
                        "source": source,
                        "text":   chunk_text,
                    })
    return chunks


def build_faiss_index(chunks: list[dict]):
    """Embed chunks and build FAISS index."""
    print(f"\nEmbedding {len(chunks)} chunks...")
    print("(This may take 5-10 minutes on first run — downloads ~90MB model)")

    try:
        import faiss
        import numpy as np
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        print(f"\nERROR: Missing package: {e}")
        print("Run: pip install faiss-cpu sentence-transformers")
        return

    # Load multilingual model — handles Urdu + English + Roman Urdu
    print("Loading multilingual embedding model...")
    model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

    texts = [c["text"] for c in chunks]

    # Embed in batches to show progress
    batch_size = 32
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        embeddings = model.encode(batch, show_progress_bar=False)
        all_embeddings.append(embeddings)
        print(f"  Embedded {min(i+batch_size, len(texts))}/{len(texts)} chunks...")

    import numpy as np
    embeddings_np = np.vstack(all_embeddings).astype("float32")

    # Build FAISS index
    dimension = embeddings_np.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings_np)

    # Save index
    index_path = INDEX_DIR / "wakeel_legal.faiss"
    faiss.write_index(index, str(index_path))
    print(f"\n  ✓ FAISS index saved: {index_path}")
    print(f"    Vectors: {index.ntotal}, Dimension: {dimension}")

    # Save chunks metadata
    chunks_path = INDEX_DIR / "wakeel_chunks.json"
    with open(chunks_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    print(f"  ✓ Chunks metadata saved: {chunks_path}")

    return index, embeddings_np


if __name__ == "__main__":
    start = time.perf_counter()
    print("=" * 55)
    print("Wakeel — FAISS Index Builder")
    print("=" * 55)

    if not RAW_DIR.exists() or not list(RAW_DIR.glob("*.txt")):
        print("ERROR: No law files found. Run collect_laws.py first.")
        exit(1)

    docs   = load_law_files()
    chunks = split_into_chunks(docs)
    print(f"\n✓ Created {len(chunks)} chunks from {len(docs)} documents")

    build_faiss_index(chunks)

    elapsed = round(time.perf_counter() - start, 1)
    print(f"\n✅ Index built in {elapsed}s")
    print("Next step: Restart uvicorn — RAG pipeline will auto-load the index.")
