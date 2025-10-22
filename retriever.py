import pandas as pd, numpy as np
from rank_bm25 import BM25Okapi
import faiss
from sentence_transformers import SentenceTransformer


class HybridRetriever:
def __init__(self, df_path="store/chunks.parquet", index_path="store/faiss.index", model_name="sentence-transformers/all-MiniLM-L6-v2"):
self.df = pd.read_parquet(df_path)
self.model = SentenceTransformer(model_name)
self.index = faiss.read_index(index_path)
self.tokens = [t.split() for t in self.df.text.tolist()]
self.bm25 = BM25Okapi(self.tokens)


def search(self, query, k=8):
# BM25
bm_scores = self.bm25.get_scores(query.split())
# Векторний
q = self.model.encode([query], normalize_embeddings=True).astype('float32')
D, I = self.index.search(q, k*5)
vec_scores = np.zeros(len(self.df))
vec_scores[I[0]] = D[0]
# Злиття
alpha = 0.5
scores = alpha*bm_scores + (1-alpha)*vec_scores
top = np.argsort(-scores)[:k]
return self.df.iloc[top][["doc_id","page","text","source_path"]].assign(score=scores[top])