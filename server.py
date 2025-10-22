import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from retriever import HybridRetriever
from llm import LLM

# 🔧 гарантуємо наявність директорій (безпечніше для першого запуску)
os.makedirs("docs", exist_ok=True)
os.makedirs("store", exist_ok=True)

app = FastAPI(title="PromoDocs API")

# CORS (щоб Telegram-бот і браузер могли ходити до API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# 📂 публічна роздача PDF за /files
# ВАЖЛИВО: check_dir=False вимикає перевірку існування каталогу під час старту
app.mount("/files", StaticFiles(directory="docs", check_dir=False), name="files")

# ——— Моделі ———
class ChatRequest(BaseModel):
    question: str
    top_k: int = 6

# ——— Ініціалізація ———
retriever = None
llm = LLM()

def ensure_retriever():
    """Лінива ініціалізація ретривера, щоби не падати без індексу на старті."""
    global retriever
    if retriever is None:
        retriever = HybridRetriever()
    return retriever

# ——— Роути ———
@app.get("/health")
def health():
    return {"status": "ok"}

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
Контекст:
{context}
""".strip()
    ans = await llm.answer(prompt)
    sources = [
        {"doc_id": str(row.doc_id), "page": int(row.page), "source_path": str(row.source_path)}
        for _, row in r.iterrows()
    ]
    return {"answer": ans, "sources": sources}
