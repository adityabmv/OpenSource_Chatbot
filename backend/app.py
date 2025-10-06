# app.py
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from typing import List
from chunker import chunk_text
from embeddings import get_embeddings_model
from vectorstore import build_vectorstore, query_vectorstore
import ollama
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from starlette.responses import FileResponse
import shutil
import tempfile
from convert_to_json import convert_to_json
import gc, time
from langchain_chroma import Chroma
from convert_to_json import ocr_lang_map

app = FastAPI(title="RAG Chatbot API")
DB_DIR = "vector_db"

# Global variable to store vectorstore
vectorstore = None

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    prompt: str
    top_k: int = 5
    llm_model: str

# =========================
# Helper: Load vectorstore if needed
# =========================
def load_vectorstore_if_needed(embedding_model_name="sentence-transformers/all-MiniLM-L6-v2"):
    global vectorstore
    if vectorstore is None and os.path.exists(DB_DIR):
        embeddings_model = get_embeddings_model(model_name=embedding_model_name)
        vectorstore = Chroma(
            collection_name="rag_db",
            embedding_function=embeddings_model,
            persist_directory=DB_DIR
        )

# =========================
# Endpoint 1: Download DB
# =========================
@app.get("/download_db/")
async def download_db():
    shutil.make_archive("vector_db_backup", "zip", "vector_db")
    return FileResponse("vector_db_backup.zip", filename="vector_db_backup.zip")

# =========================
# Endpoint 2: Build DB
# =========================
@app.post("/build_db/")
async def build_db(
    files: List[UploadFile] = File(...),
    chunk_size: int = Form(500),
    chunk_overlap: int = Form(50),
    embedding_model: str = Form("sentence-transformers/all-MiniLM-L6-v2"),
    ocr_lang: str = Form("eng"),
):
    global vectorstore
    temp_files = []

    try:
        all_texts = []
        preview_lines = []

        for f in files:
            if not f.filename:
                continue
            content = await f.read()
            if not content:
                continue

            temp_fd, temp_path = tempfile.mkstemp(suffix=os.path.splitext(f.filename)[1])
            temp_files.append(temp_path)

            try:
                with os.fdopen(temp_fd, "wb") as temp:
                    temp.write(content)
                # Pass through OCR language as received from frontend (Tesseract code like "tel", "hin", "eng")
                # The converter will normalize it internally.
                print(f"[DEBUG] OCR lang from frontend (passthrough): {ocr_lang}")
                json_data = convert_to_json(temp_path, ocr_lang=ocr_lang)
                for page in json_data["pages"]:
                    text = page.get("content_en") or page.get("content_original", "")
                    cleaned = text.replace("\n", " ").strip()
                    if cleaned:
                        all_texts.append(cleaned)
                        if len(preview_lines) < 10:
                            preview_lines.append(f"--- From file: {f.filename}, page {page['page_number']} ---")
                            preview_lines.append(cleaned[:500] + ("..." if len(cleaned) > 500 else ""))
                            preview_lines.append("")
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        if not all_texts:
            raise HTTPException(status_code=400, detail="No valid content found in uploaded files")

        combined_text = " ".join(all_texts)
        chunks = chunk_text(combined_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        embeddings_model = get_embeddings_model(model_name=embedding_model)

        if os.path.exists(DB_DIR):
            vectorstore = Chroma(
                collection_name="rag_db",
                embedding_function=embeddings_model,
                persist_directory=DB_DIR
            )
        else:
            os.makedirs(DB_DIR, exist_ok=True)
            vectorstore = build_vectorstore(
                chunks,
                embeddings_model,
                collection_name="rag_db",
                persist_directory=DB_DIR
            )

        # No explicit persist(); modern Chroma persists automatically when using a persistent directory

        return {
            "status": "database built",
            "num_chunks": len(chunks),
            "preview": preview_lines
        }

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"[ERROR] build_db failed: {e}\n{tb}")
        for p in temp_files:
            if os.path.exists(p):
                os.unlink(p)
        raise HTTPException(status_code=500, detail=f"Error building database: {str(e)}")

# =========================
# Endpoint 3: Query RAG
# =========================
@app.post("/query/")
async def query_rag(request: QueryRequest):
    global vectorstore
    load_vectorstore_if_needed()

    if not vectorstore:
        raise HTTPException(status_code=400, detail="Vector store not built yet. Please build database first.")

    try:
        retrieved_chunks = query_vectorstore(vectorstore, request.prompt, top_k=request.top_k)
        context = " ".join(retrieved_chunks)
        llm_prompt = f"Answer the question based on the context below:\n\n{context}\n\nQuestion: {request.prompt}"

        if "qwen" in request.llm_model.lower():
            response = ollama.chat(
                model=request.llm_model,
                messages=[
                    {"role": "system", "content": "Answer directly. Do not output reasoning steps."},
                    {"role": "user", "content": llm_prompt}
                ],
                
            )
        else:
            response = ollama.chat(
                model=request.llm_model,
                messages=[{"role": "user", "content": llm_prompt}]
            )

        return {
            "answer": response,
            "retrieved_chunks": retrieved_chunks
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error querying: {str(e)}")

# =========================
# Endpoint 4: Status
# =========================
@app.get("/status/")
async def status():
    global vectorstore
    if vectorstore:
        return {"vector_store_ready": True, "num_chunks": len(vectorstore._collection.get()["documents"])}
    else:
        return {"vector_store_ready": False, "num_chunks": 0}

# =========================
# Endpoint 5: Recommend Chunk Settings
# =========================
@app.post("/recommend_chunk_settings/")
async def recommend_chunk_settings(files: List[UploadFile] = File(...)):
    def get_recommendation(file_size_kb):
        if file_size_kb < 50:
            return {"chunk_size": 300, "chunk_overlap": 30}
        elif file_size_kb < 500:
            return {"chunk_size": 600, "chunk_overlap": 60}
        elif file_size_kb < 2000:
            return {"chunk_size": 1000, "chunk_overlap": 100}
        else:
            return {"chunk_size": 1500, "chunk_overlap": 150}

    total_size_kb = 0
    for f in files:
        content = await f.read()
        total_size_kb += len(content) / 1024

    recommendation = get_recommendation(total_size_kb)
    return {
        "recommended_chunk_size": recommendation["chunk_size"],
        "recommended_chunk_overlap": recommendation["chunk_overlap"],
        "total_file_size_kb": round(total_size_kb, 2)
    }

# =========================
# Run with:
# uvicorn app:app --reload
# =========================