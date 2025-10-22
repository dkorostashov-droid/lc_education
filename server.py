from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from retriever import HybridRetriever
from llm import LLM


app = FastAPI()
retriever = HybridRetriever()
llm = LLM()


class ChatRequest(BaseModel):
question: str
top_k: int = 6


@app.get("/health")
def health():
return {"status":"ok"}


@app.post("/search")
def search(q: ChatRequest):
df = retriever.search(q.question, q.top_k)
return {"results": df.to_dict(orient="records")}


@app.post("/chat")
async def chat(q: ChatRequest):
df = retriever.search(q.question, q.top_k)
context = "\n\n".join([f"[p.{r['page']} {r['doc_id']}] {r['text']}" for _, r in df.iterrows()])
prompt = f"""
Відповідай на питання користувача українською, використовуючи лише наведений контекст.
Якщо відповідь відсутня у контексті — скажи це.
Додай посилання на джерела у форматі: doc_id p.page.


Користувач: {q.question}
Контекст:\n{context}
"""
ans = await llm.answer(prompt)
sources = [
{"doc_id": r.doc_id, "page": int(r.page), "source_path": r.source_path}
for _, r in df.iterrows()
]
return {"answer": ans, "sources": sources}