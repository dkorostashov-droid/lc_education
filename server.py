import os
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

# Гарантуємо каталоги
os.makedirs("docs", exist_ok=True)
os.makedirs("store", exist_ok=True)

app = FastAPI(title="PromoDocs API (Lite)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], allow_credentials=True
)

# Роздача PDF
app.mount("/files", StaticFiles(directory="docs", check_dir=False), name="files")

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

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    try:
        path = os.path.join("docs", file.filename)
        with open(path, "wb") as f:
            f.write(await file.read())
        return {"message": f"{file.filename} uploaded"}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
