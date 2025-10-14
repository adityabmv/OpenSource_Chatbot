# app.py
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from typing import List, Optional
from chunker import chunk_text, process_pdf_with_docling, extract_text_from_file, translate_if_needed
from embeddings import get_embeddings_model
from vectorstore import append_to_vectorstore, query_vectorstore, get_bot_vectorstore
from llm_client import LLMClient
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
from bot_manager import BotManager, BotConfig
from chat_history import ChatHistoryManager
from datetime import datetime

app = FastAPI(title="RAG Chatbot API with Bot Management")
DB_DIR = "vector_db"

# Initialize bot manager with absolute path
BOTS_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bots_config.json")
bot_manager = BotManager(storage_path=BOTS_CONFIG_PATH)

# Initialize chat history manager
chat_manager = ChatHistoryManager()

# Initialize LLM client
llm_client = LLMClient()

def load_vectorstore_if_needed():
    """Utility function to load vectorstore if it exists"""
    global vectorstore
    if not vectorstore:
        try:
            vectorstore = Chroma(persist_directory=DB_DIR, embedding_function=None)
        except Exception as e:
            print(f"Warning: Could not load vectorstore: {e}")
            vectorstore = None

# Load environment variables
import os
from dotenv import load_dotenv
load_dotenv()

# CORS setup - Updated for remote deployment support
base_origins = [
    "http://localhost:3000",      # Development
    "http://127.0.0.1:3000",     # Alternative localhost
    "http://localhost:3001",      # Alternative dev port
    "http://127.0.0.1:3001",     # Alternative localhost port
    "https://localhost:3000",     # HTTPS localhost
    "https://127.0.0.1:3000",    # HTTPS localhost
    "https://photosensitive-ollie-noncalculative.ngrok-free.dev"
]

# Add frontend URLs from environment variable
frontend_urls_env = os.getenv('FRONTEND_URLS', '')
if frontend_urls_env:
    frontend_urls = [url.strip() for url in frontend_urls_env.split(',') if url.strip()]
    base_origins.extend(frontend_urls)

# Allow all origins in development and add common remote deployment patterns
environment = os.getenv('ENVIRONMENT', 'development')
if environment == 'development':
    # In development, allow all origins for easier testing
    origins = ["*"]
else:
    # In production, use configured origins
    origins = base_origins
    # Add common remote deployment patterns
    origins.extend([
        "http://localhost:30000",     # Common remote frontend port
        "https://localhost:30000",    # HTTPS version
        "http://127.0.0.1:30000",    # Alternative
        "https://127.0.0.1:30000",   # HTTPS version
    ])

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,   # use the computed list, or ["*"] for dev
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,  # Change to True if you need to support cookies/auth (not recommended for public APIs
)

class QueryRequest(BaseModel):
    prompt: str
    top_k: int = 5
    llm_model: str
    bot_id: Optional[str] = None
    conversation_id: Optional[str] = None
    message_id: Optional[str] = None
    openrouter_api_key: Optional[str] = None

class BotCreateRequest(BaseModel):
    name: str
    description: str = ""
    # chunk_size and chunk_overlap removed for automatic chunking
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    ocr_lang: str = "eng"
    uid: str = ""

class BotUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    # chunk_size and chunk_overlap removed for automatic chunking
    embedding_model: Optional[str] = None
    ocr_lang: Optional[str] = None
    is_active: Optional[bool] = None

# =========================
# Bot Management Endpoints
# =========================

@app.post("/bots/")
async def create_bot(request: BotCreateRequest):
    """Create a new bot"""
    try:
        bot = bot_manager.create_bot(
            name=request.name,
            description=request.description,
            embedding_model=request.embedding_model,
            ocr_lang=request.ocr_lang,
            uid=request.uid
        )
        return {"bot": bot.dict(), "message": "Bot created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating bot: {str(e)}")

from fastapi import Request

@app.get("/bots/")
async def list_bots(request: Request):
    """List all bots for a user"""
    uid = request.headers.get("x-user-uid", "")
    bots = bot_manager.get_all_bots(uid=uid)
    return {"bots": [bot.dict() for bot in bots]}

@app.get("/bots/active/")
async def list_active_bots(request: Request):
    """List all active bots for a user"""
    uid = request.headers.get("x-user-uid", "")
    bots = bot_manager.get_active_bots(uid=uid)
    return {"bots": [bot.dict() for bot in bots]}

@app.get("/bots/{bot_id}")
async def get_bot(bot_id: str):
    """Get a specific bot"""
    bot = bot_manager.get_bot(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    return {"bot": bot.dict()}

@app.put("/bots/{bot_id}")
async def update_bot(bot_id: str, request: BotUpdateRequest):
    """Update a bot"""
    bot = bot_manager.update_bot(bot_id, **request.dict(exclude_unset=True))
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    return {"bot": bot.dict(), "message": "Bot updated successfully"}

@app.delete("/bots/{bot_id}")
async def delete_bot(bot_id: str):
    """Delete a bot"""
    try:
        success = bot_manager.delete_bot(bot_id)
        if not success:
            raise HTTPException(status_code=404, detail="Bot not found")
        return {"message": "Bot deleted successfully"}
    except Exception as e:
        # Log the error but return success if the bot was removed from config
        print(f"Warning: Error during bot deletion: {e}")
        if bot_id not in bot_manager.bots:
            return {"message": "Bot configuration deleted successfully", "warning": "Some files may need manual cleanup"}
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/bots/{bot_id}/stats")
async def get_bot_stats(bot_id: str):
    """Get statistics for a bot"""
    stats = bot_manager.get_bot_stats(bot_id)
    if stats is None:
        raise HTTPException(status_code=404, detail="Bot not found")
    return {"stats": stats}

@app.get("/bots/{bot_id}/files")
async def get_bot_files(bot_id: str):
    """Get list of uploaded files for a bot"""
    bot = bot_manager.get_bot(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    files = bot_manager.get_uploaded_files(bot_id)
    return {"files": files, "total_files": len(files)}

@app.post("/bots/{bot_id}/rebuild")
async def rebuild_bot_database(bot_id: str):
    """Clear all uploaded files and reset database for a bot"""
    bot = bot_manager.get_bot(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    try:
        # Clear uploaded files list
        bot_manager.clear_uploaded_files(bot_id)
        
        # Delete vectorstore directory
        vectorstore_path = bot.vectorstore_path
        if os.path.exists(vectorstore_path):
            shutil.rmtree(vectorstore_path)
            print(f"Deleted vectorstore at {vectorstore_path}")
        
        return {
            "status": "success",
            "message": "Bot database cleared successfully. Upload new files to rebuild.",
            "bot_id": bot_id
        }
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"[ERROR] rebuild_bot_database failed: {e}\n{tb}")
        raise HTTPException(status_code=500, detail=f"Error rebuilding database: {str(e)}")

# =========================
# Updated Endpoints for Bot Support
# =========================

@app.post("/bots/{bot_id}/build_and_preview/")
async def build_bot_with_preview(
    bot_id: str,
    files: List[UploadFile] = File(...),
):
    """Process files and build database using bot's configured settings"""
    # Get bot configuration
    bot = bot_manager.get_bot(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")

    temp_files = []
    all_texts = []
    preview_lines = []

    try:
        # Process files and extract text
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

                # Unified pipeline for all file types
                file_extension = os.path.splitext(f.filename)[1][1:].lower()  # Get extension without dot
                raw_text = extract_text_from_file(temp_path, file_extension, bot.ocr_lang)

                if raw_text.strip():
                    # Translate if needed (Indic languages)
                    processed_text = translate_if_needed(raw_text, bot.ocr_lang)

                    # Create chunks (automatic chunking)
                    file_chunks = chunk_text(
                        text=processed_text,
                        metadata={
                            "file_name": f.filename,
                            "language": bot.ocr_lang or "eng",
                            "source_type": "document",
                            "processor": "unified"
                        }
                    )
                    all_texts.extend(file_chunks)

                    # Add preview for first chunk
                    if len(preview_lines) < 5:
                        processor_name = "Docling" if file_extension == 'pdf' else "Unified"
                        preview_lines.append(f"--- From file: {f.filename} ({processor_name} processed) ---")
                        preview_lines.append(file_chunks[0]["text"][:300] + "...")
                        preview_lines.append("")
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        if not all_texts:
            raise HTTPException(status_code=400, detail="No valid content found in uploaded files")

        # all_texts now contains chunks with metadata
        chunks = all_texts  # Each chunk already has its text and metadata
        embeddings_model = get_embeddings_model()

        # Calculate chunk_size for logging (average chunk length)
        if chunks:
            avg_chunk_size = int(sum(len(chunk["text"]) for chunk in chunks) / len(chunks))
        else:
            avg_chunk_size = 0

        vectorstore = append_to_vectorstore(
            chunks,
            embeddings_model,
            collection_name="rag_db",
            persist_directory=bot.vectorstore_path
        )

        # Track uploaded files
        files_info = []
        for f in files:
            if f.filename:
                files_info.append({
                    "name": f.filename,
                    "size": f.size if hasattr(f, 'size') else 0,
                    "uploaded_at": datetime.now().isoformat()
                })

        # Add files to bot's uploaded files list
        bot_manager.add_uploaded_files(bot_id, files_info)

        return {
            "status": "database built",
            "bot_id": bot_id,
            "bot_name": bot.name,
            "num_chunks": len(chunks),
            "settings": {
                "embedding_model": "default",
                "ocr_lang": bot.ocr_lang,
                "chunk_size": avg_chunk_size  # For log/info only
            },
            "preview": preview_lines,
            "total_text_size": sum(len(chunk["text"]) for chunk in chunks),
            "files_processed": len(files_info),
            "source_files": [f["name"] for f in files_info],
            "uploaded_files": files_info
        }

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"[ERROR] build_bot_with_preview failed: {e}\n{tb}")
        for p in temp_files:
            if os.path.exists(p):
                os.unlink(p)
        raise HTTPException(status_code=500, detail=f"Error building database: {str(e)}")

@app.post("/bots/{bot_id}/query/")
async def query_bot_rag(bot_id: str, request: QueryRequest):
    """Query a specific bot"""
    try:
        # Validate request data
        if not request.prompt or not request.prompt.strip():
            raise HTTPException(status_code=400, detail="Prompt cannot be empty")
        
        if request.top_k < 1 or request.top_k > 20:
            raise HTTPException(status_code=400, detail="top_k must be between 1 and 20")
        
        # No model validation: allow any model name, let LLM provider handle errors
        
        # Get bot configuration
        bot = bot_manager.get_bot(bot_id)
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")

        # Initialize embeddings and vectorstore
        try:
            embeddings_model = get_embeddings_model(model_name=bot.embedding_model)
        except Exception as e:
            print(f"Error initializing embeddings for bot {bot_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Error initializing embeddings: {str(e)}")

        try:
            vectorstore = get_bot_vectorstore(bot, embeddings_model)
        except Exception as e:
            print(f"Error loading vectorstore for bot {bot_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Error loading vectorstore: {str(e)}")

        if not vectorstore:
            raise HTTPException(status_code=400, detail="Bot vectorstore not found. Please build the database first.")

        # Query vectorstore
        try:
            chunk_results = query_vectorstore(vectorstore, request.prompt, top_k=request.top_k)
        except Exception as e:
            print(f"Vectorstore query error for bot {bot_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Error querying vectorstore: {str(e)}")

        # Build context and prompt
        context = " ".join(chunk['content'] for chunk in chunk_results)
        llm_prompt = f"Answer the question based on the context below:\n\n{context}\n\nQuestion: {request.prompt}"

        messages = [
            {"role": "system", "content": "Answer directly based on the given context. Be concise and accurate."},
            {"role": "user", "content": llm_prompt}
        ]

        # Get LLM response
        try:
            # Use API key from request if provided
            api_key = request.openrouter_api_key
            response = await llm_client.chat(messages, model=request.llm_model, api_key_override=api_key)
        except Exception as e:
            print(f"LLM chat error for bot {bot_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Error getting LLM response: {str(e)}")

        return {
            "answer": {
                "message": {
                    "content": response
                }
            },
            "retrieved_chunks": chunk_results,
            "bot_id": bot_id,
            "bot_name": bot.name
        }

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        print(f"Unexpected error in query_bot_rag for bot {bot_id}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@app.get("/bots/{bot_id}/status/")
async def bot_status(bot_id: str):
    """Get status for a specific bot"""
    bot = bot_manager.get_bot(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")

    stats = bot_manager.get_bot_stats(bot_id)
    return {
        "bot_id": bot_id,
        "bot_name": bot.name,
        "is_active": bot.is_active,
        "source_files": stats["num_files"],  # Renamed to be clearer
        "chunks": stats["num_chunks"],
        "db_size_mb": round(stats["vectorstore_size_mb"], 2),
        "status": "Ready" if stats["vectorstore_exists"] else "Not Built"
    }

# =========================
# Model Management Endpoints
# =========================

@app.get("/models/available")
async def get_available_models():
    """Get list of available LLM models (for reference only; any model name can be used)"""
    return {"models": llm_client.get_available_models(), "note": "Any model name can be used; this list is for reference only."}

# =========================
# Chat History Endpoints
# =========================

@app.post("/bots/{bot_id}/chat/conversations")
async def create_conversation(bot_id: str, request: Request):
    """Create a new conversation for a user"""
    try:
        uid = request.headers.get("x-user-uid", "")
        conversation_id = chat_manager.create_conversation(bot_id, uid=uid)
        return {"conversation_id": conversation_id, "message": "Conversation created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating conversation: {str(e)}")

@app.get("/bots/{bot_id}/chat/conversations")
@app.get("/bots/{bot_id}/chat/conversations")
async def get_conversations(bot_id: str, request: Request):
    """Get all conversations for a bot and user"""
    try:
        uid = request.headers.get("x-user-uid", "")
        conversations = chat_manager.get_conversations(bot_id, uid=uid)
        return {"conversations": conversations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting conversations: {str(e)}")

@app.get("/bots/{bot_id}/chat/conversations/{conversation_id}")
@app.get("/bots/{bot_id}/chat/conversations/{conversation_id}")
async def get_conversation(bot_id: str, conversation_id: str, request: Request):
    """Get a specific conversation for a user"""
    try:
        uid = request.headers.get("x-user-uid", "")
        conversation = chat_manager.get_conversation(bot_id, conversation_id, uid=uid)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return {"conversation": conversation}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting conversation: {str(e)}")

@app.delete("/bots/{bot_id}/chat/conversations/{conversation_id}")
@app.delete("/bots/{bot_id}/chat/conversations/{conversation_id}")
async def delete_conversation(bot_id: str, conversation_id: str, request: Request):
    """Delete a conversation for a user"""
    try:
        uid = request.headers.get("x-user-uid", "")
        success = chat_manager.delete_conversation(bot_id, conversation_id, uid=uid)
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return {"message": "Conversation deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting conversation: {str(e)}")

@app.post("/bots/{bot_id}/chat/conversations/{conversation_id}/messages")
async def save_message(bot_id: str, conversation_id: str, message: dict):
    """Save a message to conversation"""
    try:
        required_fields = ["role", "content"]
        for field in required_fields:
            if field not in message:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

        chat_manager.save_message(bot_id, conversation_id, message["role"], message["content"])
        return {"message": "Message saved successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving message: {str(e)}")

@app.put("/bots/{bot_id}/chat/conversations/{conversation_id}/title")
async def update_conversation_title(bot_id: str, conversation_id: str, title: dict):
    """Update a conversation's title"""
    try:
        if "title" not in title:
            raise HTTPException(status_code=400, detail="Missing title field")

        chat_manager.update_conversation_title(bot_id, conversation_id, title["title"])
        return {"message": "Conversation title updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating title: {str(e)}")

# =========================
# Run with:
# uvicorn app:app --reload
# =========================