import os, glob, pandas as pd, fitz
from sentence_transformers import SentenceTransformer
import faiss
from pathlib import Path


MODEL = os.getenv("EMB_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
CHUNK_SIZE, CHUNK_OVERLAP = 900, 150


def pdf_to_chunks(path: str):
doc = fitz.open(path)
for page_num in range(len(doc)):
text = doc[page_num].get_text("text").strip()
# простий чанкінг
for i in range(0, len(text), CHUNK_SIZE - CHUNK_OVERLAP):
yield {
"doc_id": Path(path).stem,
"page": page_num + 1,
"text": text[i:i+CHUNK_SIZE],
"source_path": path,
}


if __name__ == "__main__":
files = glob.glob("docs/**/*.pdf", recursive=True)
rows = []
for f in files:
rows.extend(list(pdf_to_chunks(f)))
df = pd.DataFrame(rows)
df.to_parquet("store/chunks.parquet")


model = SentenceTransformer(MODEL)
X = model.encode(df["text"].tolist(), normalize_embeddings=True)
index = faiss.IndexFlatIP(X.shape[1])
index.add(X.astype('float32'))
faiss.write_index(index, "store/faiss.index")