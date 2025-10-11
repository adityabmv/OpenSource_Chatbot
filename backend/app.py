# app.py
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from typing import List, Optional
from chunker import chunk_text
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
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
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
    chunk_size: int = 500
    chunk_overlap: int = 50
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    ocr_lang: str = "eng"

class BotUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
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
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
            embedding_model=request.embedding_model,
            ocr_lang=request.ocr_lang
        )
        return {"bot": bot.dict(), "message": "Bot created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating bot: {str(e)}")

@app.get("/bots/")
async def list_bots():
    """List all bots"""
    bots = bot_manager.get_all_bots()
    return {"bots": [bot.dict() for bot in bots]}

@app.get("/bots/active/")
async def list_active_bots():
    """List all active bots"""
    bots = bot_manager.get_active_bots()
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
                json_data = convert_to_json(temp_path, ocr_lang=bot.ocr_lang)
                # Process each page and create structured chunks with metadata
                for page in json_data["pages"]:
                    text = page.get("content_en") or page.get("content_original", "")
                    if text.strip():
                        # Create chunks with page-level metadata
                        page_chunks = chunk_text(
                            text=text,
                            chunk_size=300,
                            chunk_overlap=30,
                            metadata={
                                "file_name": f.filename,
                                "page_number": page["page_number"],
                                "language": page.get("language", "unknown"),
                                "source_type": "document"
                            }
                        )
                        all_texts.extend(page_chunks)
                        
                        # Add preview for first few chunks
                        if len(preview_lines) < 5:
                            preview_lines.append(f"--- From file: {f.filename}, page {page['page_number']} ---")
                            preview_lines.append(page_chunks[0]["text"][:300] + "...")
                            preview_lines.append("")
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        if not all_texts:
            raise HTTPException(status_code=400, detail="No valid content found in uploaded files")

        # all_texts now contains chunks with metadata
        chunks = all_texts  # Each chunk already has its text and metadata
        embeddings_model = get_embeddings_model()

        vectorstore = append_to_vectorstore(
            chunks,
            embeddings_model,
            collection_name="rag_db",
            persist_directory=bot.vectorstore_path
        )

        return {
            "status": "database built",
            "bot_id": bot_id,
            "bot_name": bot.name,
            "num_chunks": len(chunks),
            "settings": {
                "chunk_size": 300,
                "chunk_overlap": 30,
                "embedding_model": "default",
                "ocr_lang": bot.ocr_lang
            },
            "preview": preview_lines,
            "total_text_size": sum(len(chunk["text"]) for chunk in chunks),
            "files_processed": 1,  # Only count the actual source file
            "source_files": [f.filename for f in files]  # List of original file names
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
        
        # Validate model
        available_models = llm_client.get_available_models()
        if request.llm_model not in available_models:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid model '{request.llm_model}'. Available models: {', '.join(available_models)}"
            )
        
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
    """Get list of available LLM models"""
    return {"models": llm_client.get_available_models()}

# =========================
# Chat History Endpoints
# =========================

@app.post("/bots/{bot_id}/chat/conversations")
async def create_conversation(bot_id: str):
    """Create a new conversation"""
    try:
        conversation_id = chat_manager.create_conversation(bot_id)
        return {"conversation_id": conversation_id, "message": "Conversation created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating conversation: {str(e)}")

@app.get("/bots/{bot_id}/chat/conversations")
async def get_conversations(bot_id: str):
    """Get all conversations for a bot"""
    try:
        conversations = chat_manager.get_conversations(bot_id)
        return {"conversations": conversations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting conversations: {str(e)}")

@app.get("/bots/{bot_id}/chat/conversations/{conversation_id}")
async def get_conversation(bot_id: str, conversation_id: str):
    """Get a specific conversation"""
    try:
        conversation = chat_manager.get_conversation(bot_id, conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return {"conversation": conversation}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting conversation: {str(e)}")

@app.delete("/bots/{bot_id}/chat/conversations/{conversation_id}")
async def delete_conversation(bot_id: str, conversation_id: str):
    """Delete a conversation"""
    try:
        success = chat_manager.delete_conversation(bot_id, conversation_id)
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

# Keep legacy endpoints for backward compatibility (using default bot or first available)
@app.post("/build_db/")
async def build_db(
    files: List[UploadFile] = File(...),
    chunk_size: int = Form(500),
    chunk_overlap: int = Form(50),
    embedding_model: str = Form("sentence-transformers/all-MiniLM-L6-v2"),
    ocr_lang: str = Form("eng"),
    use_cached: bool = Form(False),
):
    """Legacy endpoint - creates a default bot if none exists"""
    # Get or create default bot
    bots = bot_manager.get_active_bots()
    if not bots:
        default_bot = bot_manager.create_bot(
            name="Default Bot",
            description="Default bot created for backward compatibility"
        )
        bot_id = default_bot.id
    else:
        bot_id = bots[0].id

    # Use the new bot-specific endpoint
    return await build_bot_with_preview(bot_id, files)

@app.post("/query/")
async def query_rag(request: QueryRequest):
    """Legacy endpoint - uses first available bot"""
    bots = bot_manager.get_active_bots()
    if not bots:
        raise HTTPException(status_code=400, detail="No bots available. Please create a bot first.")

    bot_id = bots[0].id
    return await query_bot_rag(bot_id, request)

@app.get("/status/")
async def status():
    """Legacy endpoint - returns status of all bots"""
    bots = bot_manager.get_active_bots()
    bot_statuses = []

    for bot in bots:
        stats = bot_manager.get_bot_stats(bot.id)
        bot_statuses.append({
            "bot_id": bot.id,
            "bot_name": bot.name,
            **stats
        })

    return {"bots": bot_statuses}

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
    use_cached: bool = Form(False),  # New parameter to use cached data
):
    global vectorstore, processed_data_cache
    temp_files = []

    try:
        # Check if we should use cached processed data
        if use_cached and processed_data_cache and (time.time() - processed_data_cache.get("timestamp", 0)) < 300:  # 5 min cache
            print("[INFO] Using cached processed data")
            all_texts = processed_data_cache["all_texts"]
            preview_lines = processed_data_cache["preview_lines"]
        else:
            print("[INFO] Processing files fresh (no cache or cache expired)")
            all_texts = []
            preview_lines = []

            for f in files:
                if not f.filename:
                    continue
                content = await f.read()
                if not content:
                    continue

                # Create metadata for the file
                file_metadata = {
                    "source": f.filename,
                    "file_type": os.path.splitext(f.filename)[1],
                    "uploaded_at": datetime.now().isoformat()
                }

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
        # Use default chunk parameters since they've been removed from bot config
        chunks = chunk_text(combined_text)
        embeddings_model = get_embeddings_model()

        vectorstore = append_to_vectorstore(
                                                chunks,
                                                embeddings_model,
                                                collection_name="rag_db",
                                                persist_directory=DB_DIR
                                            )


        # No explicit persist(); modern Chroma persists automatically when using a persistent directory

        return {
            "status": "database built",
            "num_chunks": len(chunks),
            "preview": preview_lines,
            "used_cache": use_cached and processed_data_cache and (time.time() - processed_data_cache.get("timestamp", 0)) < 300
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

    # If this is a historical message and we have conversation_id, return the stored response
    if request.conversation_id and request.message_id:
        try:
            stored_messages = chat_manager.get_conversation_messages(request.bot_id, request.conversation_id)
            for msg in stored_messages:
                if msg["id"] == request.message_id and msg["role"] == "assistant":
                    return {
                        "answer": msg["content"],
                        "retrieved_chunks": [],
                        "from_history": True
                    }
        except Exception as e:
            print(f"Warning: Could not retrieve history: {str(e)}")
            # Continue with normal query if history retrieval fails

        # Generate new response
    try:
        # Check if vectorstore is initialized
        if not vectorstore:
            raise HTTPException(status_code=500, detail="Vector store not initialized")

        # Query vectorstore with error handling
        try:
            retrieved_chunks = query_vectorstore(vectorstore, request.prompt, top_k=request.top_k)
            if not retrieved_chunks:
                print("Warning: No relevant chunks found for the query")
                retrieved_chunks = []
        except Exception as e:
            print(f"Vector store query error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Vector store query failed: {str(e)}")

        context = " ".join(retrieved_chunks) if retrieved_chunks else ""
        llm_prompt = f"Answer the question based on the context below:\n\n{context}\n\nQuestion: {request.prompt}"

        messages = [
            {"role": "system", "content": "Answer directly based on the given context. Be concise and accurate."},
            {"role": "user", "content": llm_prompt}
        ]

        try:
            response = await llm_client.chat(messages, model=request.llm_model)
        except Exception as e:
            print(f"LLM query error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"LLM query failed: {str(e)}")

        # Save to history if conversation tracking is enabled
        if request.conversation_id and request.bot_id:
            try:
                chat_manager.save_message(request.bot_id, request.conversation_id, "user", request.prompt)
                chat_manager.save_message(request.bot_id, request.conversation_id, "assistant", response)
            except Exception as e:
                print(f"Warning: Could not save to history: {str(e)}")

        # Get bot name safely
        bot_name = None
        if request.bot_id:
            try:
                bot = bot_manager.get_bot_by_id(request.bot_id)
                bot_name = bot.name if bot else None
            except Exception as e:
                print(f"Warning: Could not get bot name: {str(e)}")

        return {
            "answer": {
                "message": {
                    "content": response
                }
            },
            "retrieved_chunks": retrieved_chunks,
            "bot_id": request.bot_id,
            "bot_name": bot_name
        }

    except HTTPException as e:
        raise e  # Re-raise HTTP exceptions as is
    except Exception as e:
        print(f"Unexpected error in query endpoint: {str(e)}")
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
# Endpoint 5: Process & Recommend (New combined endpoint)
# =========================
@app.post("/process_and_recommend/")
async def process_and_recommend(
    files: List[UploadFile] = File(...),
    ocr_lang: str = Form("eng"),
):
    global processed_data_cache
    
    def get_recommendation(text_size_kb):
        if text_size_kb < 50:
            return {"chunk_size": 300, "chunk_overlap": 30}
        elif text_size_kb < 500:
            return {"chunk_size": 600, "chunk_overlap": 60}
        elif text_size_kb < 2000:
            return {"chunk_size": 1000, "chunk_overlap": 100}
        else:
            return {"chunk_size": 1500, "chunk_overlap": 150}

    # Process files to get actual text content and recommendations
    all_texts = []
    preview_lines = []
    total_text_length = 0
    total_file_size_kb = 0
    temp_files = []
    
    try:
        for f in files:
            if not f.filename:
                continue
            content = await f.read()
            if not content:
                continue

            total_file_size_kb += len(content) / 1024
            temp_fd, temp_path = tempfile.mkstemp(suffix=os.path.splitext(f.filename)[1])
            temp_files.append(temp_path)

            try:
                with os.fdopen(temp_fd, "wb") as temp:
                    temp.write(content)
                
                # Process to JSON and measure actual text content
                print(f"[DEBUG] Processing file {f.filename} with OCR lang: {ocr_lang}")
                json_data = convert_to_json(temp_path, ocr_lang=ocr_lang)
                
                for page in json_data["pages"]:
                    text = page.get("content_en") or page.get("content_original", "")
                    cleaned = text.replace("\n", " ").strip()
                    if cleaned:
                        all_texts.append(cleaned)
                        total_text_length += len(text)
                        if len(preview_lines) < 10:
                            preview_lines.append(f"--- From file: {f.filename}, page {page['page_number']} ---")
                            preview_lines.append(cleaned[:500] + ("..." if len(cleaned) > 500 else ""))
                            preview_lines.append("")
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
    finally:
        # Clean up any remaining temp files
        for p in temp_files:
            if os.path.exists(p):
                os.unlink(p)

    if not all_texts:
        raise HTTPException(status_code=400, detail="No valid content found in uploaded files")

    # Convert text length to KB for recommendation
    total_text_kb = total_text_length / 1024
    recommendation = get_recommendation(total_text_kb)
    
    # Cache processed data for build_db to reuse
    processed_data_cache = {
        "all_texts": all_texts,
        "preview_lines": preview_lines,
        "ocr_lang": ocr_lang,
        "timestamp": time.time()
    }
    
    return {
        "recommended_chunk_size": recommendation["chunk_size"],
        "recommended_chunk_overlap": recommendation["chunk_overlap"],
        "total_text_size_kb": round(total_text_kb, 2),
        "total_file_size_kb": round(total_file_size_kb, 2),
        "preview": preview_lines,
        "num_pages": len([line for line in preview_lines if "page" in line])
    }

# =========================
# Endpoint 6: Legacy Recommend Chunk Settings (kept for compatibility)
# =========================
@app.post("/recommend_chunk_settings/")
async def recommend_chunk_settings(files: List[UploadFile] = File(...)):
    def get_recommendation(text_size_kb):
        if text_size_kb < 50:
            return {"chunk_size": 300, "chunk_overlap": 30}
        elif text_size_kb < 500:
            return {"chunk_size": 600, "chunk_overlap": 60}
        elif text_size_kb < 2000:
            return {"chunk_size": 1000, "chunk_overlap": 100}
        else:
            return {"chunk_size": 1500, "chunk_overlap": 150}

    # Process files to get actual text content size (not raw file size)
    total_text_length = 0
    total_file_size_kb = 0
    temp_files = []
    
    try:
        for f in files:
            if not f.filename:
                continue
            content = await f.read()
            if not content:
                continue

            total_file_size_kb += len(content) / 1024
            temp_fd, temp_path = tempfile.mkstemp(suffix=os.path.splitext(f.filename)[1])
            temp_files.append(temp_path)

            try:
                with os.fdopen(temp_fd, "wb") as temp:
                    temp.write(content)
                
                # Process to JSON and measure actual text content
                json_data = convert_to_json(temp_path, ocr_lang="eng")  # Default to English for recommendation
                for page in json_data["pages"]:
                    text = page.get("content_en") or page.get("content_original", "")
                    total_text_length += len(text)
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
    finally:
        # Clean up any remaining temp files
        for p in temp_files:
            if os.path.exists(p):
                os.unlink(p)

    # Convert text length to KB for recommendation
    total_text_kb = total_text_length / 1024

    recommendation = get_recommendation(total_text_kb)
    return {
        "recommended_chunk_size": recommendation["chunk_size"],
        "recommended_chunk_overlap": recommendation["chunk_overlap"],
        "total_text_size_kb": round(total_text_kb, 2),
        "total_file_size_kb": round(total_file_size_kb, 2)
    }

# =========================
# Run with:
# uvicorn app:app --reload
# =========================