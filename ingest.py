import os, glob, pandas as pd
import fitz  # PyMuPDF
from sentence_transformers import SentenceTransformer
import faiss
from pathlib import Path

MODEL = os.getenv("EMB_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "900"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))

def chunk_text(txt: str, size: int, overlap: int):
    txt = (txt or "").strip()
    if not txt:
        return []
    res = []
    i = 0
    step = max(1, size - overlap)
    while i < len(txt):
        res.append(txt[i:i+size])
        i += step
    return res

def pdf_to_chunks(path: str):
    doc = fitz.open(path)
    for p in range(len(doc)):
        text = doc[p].get_text("text")
        for piece in chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP):
            yield {
                "doc_id": Path(path).stem,
                "page": p + 1,
                "text": piece,
                "source_path": path,
            }

if __name__ == "__main__":
    os.makedirs("store", exist_ok=True)
    files = glob.glob("docs/**/*.pdf", recursive=True) + glob.glob("docs/*.pdf", recursive=False)
    rows = []
    for f in files:
        try:
            rows.extend(list(pdf_to_chunks(f)))
        except Exception as e:
            print(f"[WARN] failed to parse {f}: {e}")

    if not rows:
        print("[INFO] No PDF chunks found in docs/. Put PDF files first.")
        exit(0)

    df = pd.DataFrame(rows)
    df.to_parquet("store/chunks.parquet")

    model = SentenceTransformer(MODEL)
    X = model.encode(df["text"].tolist(), normalize_embeddings=True)
    import numpy as np
    X = np.asarray(X, dtype="float32")
    index = faiss.IndexFlatIP(X.shape[1])
    index.add(X)
    faiss.write_index(index, "store/faiss.index")
    print(f"[OK] Indexed {len(df)} chunks from {len(files)} PDFs.")
