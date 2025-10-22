import os
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from retriever import HybridRetriever
from llm import LLM

# 🔧 гарантуємо існування директорій перед підключенням StaticFiles
os.makedirs("docs", exist_ok=True)
os.makedirs("store", exist_ok=True)

app = FastAPI(title="PromoDocs API")

# Дозволяємо CORS (щоб бот і веб могли звертатися)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 📂 публікуємо PDF через /files/
app.mount("/files", StaticFiles(directory="docs"), name="files")

# Ініціалізація компонентів
retriever = HybridRetriever(store_dir="store")
llm = LLM(provider=os.getenv("LLM_PROVIDER", "openai"), api_key=os.getenv("LLM_API_KEY", ""))

# ---- MODELS ----
class AskRequest(BaseModel):
    question: str

# ---- ROUTES ----
@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    """Приймає PDF, зберігає і додає до індексу."""
    try:
        filename = file.filename
        path = os.path.join("docs", filename)
        with open(path, "wb") as f:
            f.write(await file.read())
        retriever.add_document(path)
        return {"message": f"{filename} uploaded and indexed"}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/ask")
async def ask(request: AskRequest):
    """Питання до бази документів."""
    try:
        docs = retriever.search(request.question)
        answer = llm.answer(request.question, docs)
        return {"answer": answer, "sources": [d["source"] for d in docs]}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/reindex")
async def reindex():
    """Повне переіндексування."""
    retriever.reindex("docs")
    return {"message": "Reindex complete"}

@app.get("/")
def root():
    return {"message": "PromoDocs API is running"}

# ---- DEBUG RUN ----
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
