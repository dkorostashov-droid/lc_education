import os, json
from typing import List, Dict
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from retriever_lite import LiteIndex, ensure_index

os.makedirs("docs", exist_ok=True)
os.makedirs("store", exist_ok=True)

app = FastAPI(title="PromoDocs Lite API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], allow_credentials=True,
)

app.mount("/files", StaticFiles(directory="docs", check_dir=False), name="files")

class Query(BaseModel):
    question: str
    top_k: int = 6

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/files-list")
def files_list():
    files = []
    if os.path.isdir("docs"):
        for name in sorted(os.listdir("docs")):
            if name.lower().endswith(".pdf"):
                files.append({"name": name, "url": f"/files/{name}"})
    return {"files": files}

@app.post("/reindex")
def reindex():
    idx = ensure_index(rebuild=True)
    return {"status": "ok", "chunks": len(idx.corpus)}

@app.post("/search")
def search(q: Query):
    idx = ensure_index()
    results = idx.search(q.question, k=q.top_k)
    return {"results": results}

@app.post("/chat")
def chat(q: Query):
    idx = ensure_index()
    results = idx.search(q.question, k=q.top_k)
    answer = "\n\n".join([f"[{r['doc_id']} p.{r['page']}] {r['text']}" for r in results])
    return {"answer": answer or "Немає знайденого вмісту.", "sources": results}

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    path = os.path.join("docs", file.filename)
    with open(path, "wb") as f:
        f.write(await file.read())
    return {"message": f"{file.filename} uploaded. Запусти /reindex для оновлення індексу."}
