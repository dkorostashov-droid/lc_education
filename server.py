from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from retriever import HybridRetriever
from llm import LLM

app = FastAPI(title="PromoDocs API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# static files: /files -> docs/
app.mount("/files", StaticFiles(directory="docs"), name="files")

retriever = None
llm = LLM()

class ChatRequest(BaseModel):
    question: str
    top_k: int = 6

@app.get("/health")
def health():
    return {"status":"ok"}

def ensure_retriever():
    global retriever
    if retriever is None:
        retriever = HybridRetriever()
    return retriever

@app.post("/search")
def search(q: ChatRequest):
    r = ensure_retriever().search(q.question, q.top_k)
    return {"results": r.to_dict(orient="records")}

@app.post("/chat")
async def chat(q: ChatRequest):
    r = ensure_retriever().search(q.question, q.top_k)
    context = "\n\n".join([f"[p.{int(row.page)} {row.doc_id}] {row.text}" for _, row in r.iterrows()])
    prompt = f"""
Відповідай на питання користувача українською, використовуючи лише наведений контекст.
Якщо відповіді немає у контексті — скажи про це.
Додай посилання на джерела у форматі: doc_id p.page.

Користувач: {q.question}
Контекст:\n{context}
"""
    ans = await llm.answer(prompt)
    sources = [
        {"doc_id": str(row.doc_id), "page": int(row.page), "source_path": str(row.source_path)}
        for _, row in r.iterrows()
    ]
    return {"answer": ans, "sources": sources}
