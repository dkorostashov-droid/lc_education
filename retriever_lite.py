import os, pickle
from typing import List, Dict
from dataclasses import dataclass
import fitz  # PyMuPDF
from rank_bm25 import BM25Okapi

INDEX_PATH = "store/lite_index.pkl"

def pdf_to_pages(path: str):
    doc = fitz.open(path)
    for p in range(len(doc)):
        text = doc[p].get_text("text") or ""
        yield p+1, text

def tokenize(text: str):
    return [t for t in (text or "").lower().split() if t.isalnum()]

@dataclass
class LiteIndex:
    corpus: list
    meta: list
    bm25: BM25Okapi

    def search(self, query: str, k: int = 6):
        if not query or not self.corpus:
            return []
        scores = self.bm25.get_scores(tokenize(query))
        top = sorted(range(len(scores)), key=lambda i: -scores[i])[:k]
        res = []
        for i in top:
            m = self.meta[i].copy()
            m["text"] = self.corpus[i][:400].replace("\n"," ")
            m["score"] = float(scores[i])
            res.append(m)
        return res

def build_index() -> LiteIndex:
    texts, metas, tokenized = [], [], []
    docs = [f for f in os.listdir("docs") if f.lower().endswith(".pdf")]
    for name in docs:
        path = os.path.join("docs", name)
        try:
            for page, txt in pdf_to_pages(path):
                toks = tokenize(txt)
                if not toks: continue
                texts.append(txt)
                tokenized.append(toks)
                metas.append({"doc_id": os.path.splitext(name)[0], "page": page, "source_path": path})
        except Exception as e:
            print(f"[warn] failed {name}: {e}")
    bm25 = BM25Okapi(tokenized if tokenized else [[]])
    idx = LiteIndex(texts, metas, bm25)
    os.makedirs("store", exist_ok=True)
    with open(INDEX_PATH, "wb") as f:
        pickle.dump(idx, f)
    return idx

_cached = None
def ensure_index(rebuild: bool = False) -> LiteIndex:
    global _cached
    if rebuild or _cached is None:
        if rebuild or not os.path.exists(INDEX_PATH):
            _cached = build_index()
        else:
            with open(INDEX_PATH, "rb") as f:
                _cached = pickle.load(f)
    return _cached
