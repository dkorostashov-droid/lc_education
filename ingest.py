import os, pickle
from pathlib import Path
from tqdm import tqdm
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS  # можна залишити FAISS для сумісності
from langchain_community.embeddings import FakeEmbeddings  # щоб не вантажити реальну модель

DATA_PATH = Path("docs")
INDEX_PATH = Path("store")

def load_docs():
    docs = []
    for pdf_path in DATA_PATH.glob("*.pdf"):
        loader = PyPDFLoader(str(pdf_path))
        docs.extend(loader.load())
    return docs

def ingest():
    print("🧩 Завантажую PDF...")
    docs = load_docs()
    print(f"✅ Документів: {len(docs)}")

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    texts = text_splitter.split_documents(docs)
    print(f"✂️ Розбито на {len(texts)} частин")

    # FakeEmbeddings просто повертає хеш тексту — RAM ≈ 100 MB
    embeddings = FakeEmbeddings(size=384)
    vectorstore = FAISS.from_documents(texts, embeddings)
    vectorstore.save_local(str(INDEX_PATH))
    print("💾 Індекс створено та збережено!")

if __name__ == "__main__":
    ingest()
