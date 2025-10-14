pip install -r requirements.txt
# OS Chatbot: No-Code RAG Bot
A simple, no-code Retrieval-Augmented Generation (RAG) chatbot for developers and non-developers.

## Developer Guide

### Prerequisites
- Python 3.8+
- Node.js 16+

### Backend Setup
1. Open a terminal and run:
  ```bash
  cd backend
  pip install -r requirements.txt
  ```

### Frontend Setup
1. Open a terminal and run:
  ```bash
  cd frontend
  npm install
  npm start
  ```

### Running Backend
```bash
cd backend
uvicorn app:app --reload
```

### Running Frontend
```bash
cd frontend
npm start
```

### Environment Variables
- Set up `.env` files in `backend/` and `frontend/` for API keys and service credentials.

### OCR Setup (Optional)
- Download tessdata from https://github.com/tesseract-ocr/tessdata
- Place `.traineddata` files in `backend/tessdata/`

### Testing
- Run backend tests:
  ```bash
  cd backend
  pytest
  ```

---
For more details, see code comments and folder-level README files.
#
# ---
#
# OS Chatbot Project Documentation
#
# This guide provides concise instructions for setting up, configuring, and using the OS Chatbot project. It covers environment variables, replacing Firebase/Vercel, setting up OCR (tessdata), and language/documentation tools used.
#
# ## 1. Project Setup
#
# ### Backend
# - Install Python 3.8+
# - Navigate to `backend/` and install dependencies:
#   ```powershell
#   cd backend
#   pip install -r requirements.txt
#   ```
#
# ### Frontend
# - Install Node.js (v16+ recommended)
# - Navigate to `frontend/` and install dependencies:
#   ```powershell
#   cd frontend
#   npm install
#   ```
#
# ## 2. Environment Variables
#
# - All environment variables are set in `.env` files in `backend/` and `frontend/`.
# - To replace Firebase or Vercel:
#   - Remove related keys from `.env` and config files.
#   - Add new service credentials to `.env` (e.g., for AWS, Azure, etc.).
#   - Update code to use new environment variables (search for `os.environ` or `process.env`).
#
# **Example:**
# ```env
# API_KEY=your_new_service_key
# DB_URL=your_new_database_url
# ```
#
# ## 3. Downloading tessdata for OCR
#
# - OCR uses Tesseract and language data files (`tessdata`).
# - Download tessdata from: https://github.com/tesseract-ocr/tessdata
# - Place downloaded `.traineddata` files in a folder (e.g., `backend/tessdata/`).
# - Set the path in your environment or code:
#   ```python
#   pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
#   # tessdata path: backend/tessdata/
#   ```
#
# ## 4. Language & Documentation Tools Used
#
# - **Docling**: Used for document inspection and language processing.
# - **OCR**: Tesseract via `pytesseract` for extracting text from images.
# - **Vector DB**: ChromaDB for storing embeddings.
# - **LLM Client**: Connects to language models (OpenAI, etc.).
#
# ## 5. Running the Project
#
# ### Backend
# ```powershell
# cd backend
# python main.py
# ```
# Or use Uvicorn for ASGI:
# ```powershell
# uvicorn app:app --reload
# ```
#
# ### Frontend
# ```powershell
# cd frontend
# npm run dev
# ```
#
# ## 6. Testing
# - Backend tests: `backend/tests/`
# - Run with:
#   ```powershell
#   pytest
#   ```
#
# ## 7. Additional Notes
# - Replace any service (Firebase, Vercel) by updating `.env` and config files, then refactor code to use new variables.
# - For OCR, ensure tessdata is downloaded and path is set correctly.
# - For language/documentation, see `backend/inspect_docling.py` and related files.
#
# ---
# For further details, see code comments and README files in each folder.
```

3. **Frontend Setup**
```bash
cd ../frontend
npm install
```

4. **Start Ollama** (in a separate terminal)
```bash
ollama serve
```

5. **Pull required models**
```bash
ollama pull qwen3:1.7b
ollama pull tinyllama:latest
# Optional: ollama pull mistral:7b-instruct-q4_K_M
```

6. **Download Tesseract language data** (required for OCR support)
```bash
# Create tessdata directory in backend folder
cd backend
mkdir tessdata

# Download language data files from tessdata repository
# Replace <lang> with language code (e.g., eng, hin, tel, tam, etc.)
curl -o tessdata/<lang>.traineddata https://github.com/tesseract-ocr/tessdata/raw/main/<lang>.traineddata

# Common Indian languages and their codes:
# eng - English
# hin - Hindi
# tel - Telugu
# tam - Tamil
# ben - Bengali
# guj - Gujarati
# kan - Kannada
# mal - Malayalam
# mar - Marathi
# pan - Punjabi
# ori - Odia

# Example: Download English and Hindi
curl -o tessdata/eng.traineddata https://github.com/tesseract-ocr/tessdata/raw/main/eng.traineddata
curl -o tessdata/hin.traineddata https://github.com/tesseract-ocr/tessdata/raw/main/hin.traineddata
```

### Run the Application

1. **Start the Backend**
```bash
cd backend
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

2. **Start the Frontend** (in a new terminal)
```bash
cd frontend
npm run dev
```

3. **Open your browser**
   Navigate to `http://localhost:3000`

## 🌐 Remote Deployment

### Quick Remote Deployment Setup

If you're deploying to a remote server where the frontend and backend are on different ports or domains, follow these steps:

1. **Configure Backend Environment**
   ```bash
   cd backend
   cp .env.example .env
   # Edit .env file:
   # ENVIRONMENT=production
   # FRONTEND_URLS=http://your-frontend-domain.com:30000,https://your-frontend-domain.com:30000
   ```

2. **Configure Frontend Environment**
   ```bash
   cd ../frontend
   cp .env.example .env
   # Edit .env file:
   # VITE_API_BASE_URL=http://your-backend-domain.com:8000
   ```

3. **Start Backend on Remote Host**
   ```bash
   cd backend
   uvicorn app:app --host 0.0.0.0 --port 8000
   ```

4. **Start Frontend on Remote Host**
   ```bash
   cd frontend
   npm run dev -- --host 0.0.0.0 --port 30000
   ```

5. **Access Application**
   Navigate to `http://your-remote-host:30000`

### Configuration Options

#### Backend Configuration (.env)
```env
# Environment (development, production, etc.)
ENVIRONMENT=development

# Frontend URLs for CORS (comma-separated)
FRONTEND_URLS=http://localhost:3000,http://your-domain.com:30000

# Backend server settings
HOST=0.0.0.0
PORT=8000
```

#### Frontend Configuration (.env)
```env
# API Backend URL
VITE_API_BASE_URL=http://localhost:8000

# Frontend server settings
VITE_HOST=0.0.0.0
VITE_PORT=3000
```

### Troubleshooting Remote Deployment

**Problem**: Frontend can't connect to backend
- **Solution**: Check that `VITE_API_BASE_URL` in frontend `.env` matches your backend URL
- **Solution**: Ensure backend CORS allows your frontend domain in `FRONTEND_URLS`

**Problem**: CORS errors
- **Solution**: Add your frontend URL to `FRONTEND_URLS` in backend `.env`
- **Solution**: Set `ENVIRONMENT=development` in backend for permissive CORS during testing

**Problem**: Port conflicts
- **Solution**: Change ports in `.env` files for both frontend and backend
- **Solution**: Update corresponding URLs in both `.env` files

## 📋 Usage Guide

### Creating Your First Bot

1. **Access the Dashboard**
   - Open `http://localhost:3000`
   - Click **"+ Create Bot"**

2. **Configure Your Bot**
   - **Name**: Give your bot a descriptive name
   - **Description**: Explain what your bot specializes in
   - **Chunk Size**: Set text chunk size (default: 500)
   - **OCR Language**: Choose appropriate language for document processing

3. **Upload Files**
   - Click the bot card to select it
   - Click **"Upload Files & Build Database"**
   - Drag and drop your documents (PDF, CSV, DOCX, etc.)
   - Click **"Build Database & Preview"**

4. **Start Chatting**
   - Once the database is built, start asking questions!
   - Each bot maintains separate context and knowledge
   - **Chat History**: Click "History" to see all previous conversations
   - **Load Conversations**: Click any conversation to restore it and continue chatting
   - **New Conversations**: Click "New Conversation" to start fresh

### Managing Multiple Bots

- **Switch Between Bots**: Click different bot cards in the dashboard
- **Individual Settings**: Each bot has its own configuration and files
- **Database Status**: Monitor chunks, file count, and database size
- **Add More Files**: Upload additional documents to existing bots

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Multi-Bot AI System                  │
├─────────────────────────────────────────────────────────┤
│  Frontend (React/TypeScript)                            │
│  ├── BotDashboard - Bot management interface           │
│  ├── BotChat - Per-bot chat interface                  │
│  └── FileUpload - Drag & drop file processing         │
├─────────────────────────────────────────────────────────┤
│  Backend (FastAPI/Python)                               │
│  ├── BotManager - Bot lifecycle management             │
│  ├── VectorStore - ChromaDB integration               │
│  ├── FileProcessor - OCR & text extraction            │
│  └── ChatEngine - Ollama LLM integration              │
├─────────────────────────────────────────────────────────┤
│  Data Storage                                           │
│  ├── Bot Configs (JSON)                                │
│  ├── Vector Databases (ChromaDB)                       │
└─────────────────────────────────────────────────────────┘

### Key Components

#### **ChatHistory** (`ChatHistory.tsx`)
- Displays conversation history with load/restore functionality
- Shows conversation previews with titles, dates, and message counts
- Provides intuitive dropdown interface for conversation management

#### **VectorStore** (`vectorstore.py`)
- ChromaDB integration for vector storage
- Individual vectorstores per bot (`vector_db_{bot_id}/`)
- Efficient similarity search and retrieval

#### **File Processor** (`app.py` - processing endpoints)
- Multi-format file parsing (PDF, CSV, DOCX, etc.)
- OCR integration for image text extraction
- Intelligent text chunking with configurable overlap

#### **ChatHistory** (`chat_history.py`)
- Manages conversation persistence and retrieval
- Handles conversation creation, message storage, and history loading
- Provides RESTful API endpoints for chat history operations

## 🔧 API Reference

### Bot Management Endpoints

#### Create Bot
```http
POST /bots/
Content-Type: application/json

{
  "name": "HR Assistant",
  "description": "Human Resources document assistant",
  "chunk_size": 500,
  "chunk_overlap": 50,
  "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
  "ocr_lang": "eng"
}
```

#### List Bots
```http
GET /bots/
```

#### Get Bot Status
```http
GET /bots/{bot_id}/status/
```

#### Update Bot
```http
PUT /bots/{bot_id}/
Content-Type: application/json

{
  "name": "Updated Bot Name",
  "description": "Updated description"
}
```

#### Delete Bot
```http
DELETE /bots/{bot_id}/
```

### File Processing Endpoints

#### Build Database with Preview
```http
POST /bots/{bot_id}/build_and_preview/
Content-Type: multipart/form-data

- files: Array of files to process
- chunk_size: Integer (default: bot's chunk_size)
- chunk_overlap: Integer (default: 50)
- embedding_model: String (default: bot's embedding_model)
- ocr_lang: String (default: bot's ocr_lang)
```

**Response:**
```json
{
  "status": "database built",
  "bot_id": "bot_123",
  "bot_name": "HR Assistant",
  "num_chunks": 150,
  "chunk_size": 500,
  "chunk_overlap": 50,
  "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
  "ocr_lang": "eng",
  "preview": ["--- From file: employee_handbook.pdf, page 1 ---", "Company policies and procedures...", "..."],
  "total_text_size": 75000,
  "files_processed": 3
  "prompt": "What are the vacation policies?",
  "llm_model": "qwen3:1.7b",
  "top_k": 5,
  "bot_id": "bot_123"
}
```

**Response:**
```json
{
  "answer": {
    "message": {
      "content": "According to the employee handbook:\n\n## Vacation Policy\n\n- **Annual Leave**: 20 days per year\n- **Carryover**: Maximum 5 days\n- **Approval**: Required 2 weeks in advance\n\n*Source: employee_handbook.pdf, page 15*",
      "role": "assistant"
    }
  }
}
```

### Chat History Endpoints

#### List Conversations
```http
GET /bots/{bot_id}/chat/conversations
```

**Response:**
```json
{
  "conversations": [
    {
      "id": "conv_123",
      "title": "What are the vacation policies?",
      "created_at": "2024-01-15T10:30:00Z",
      "message_count": 4
    }
  ]
}
```

#### Get Conversation
```http
GET /bots/{bot_id}/chat/conversations/{conversation_id}
```

**Response:**
```json
{
  "conversation": {
    "id": "conv_123",
    "title": "Vacation Policy Discussion",
    "created_at": "2024-01-15T10:30:00Z",
    "messages": [
      {
        "id": "msg_1",
        "role": "user",
        "content": "What are the vacation policies?",
        "timestamp": "2024-01-15T10:30:00Z"
      },
      {
        "id": "msg_2",
        "role": "assistant",
        "content": "According to the employee handbook...",
        "timestamp": "2024-01-15T10:30:05Z"
      }
    ]
  }
}
```

#### Create New Conversation
```http
POST /bots/{bot_id}/chat/conversations
```

**Response:**
```json
{
  "conversation_id": "conv_456",
  "message": "New conversation created"
}
```

#### Add Message to Conversation
```http
POST /bots/{bot_id}/chat/conversations/{conversation_id}/messages
Content-Type: application/json

{
  "role": "user",
  "content": "What are the vacation policies?"
}
```

**Response:**
```json
{
  "message_id": "msg_789",
  "message": "Message added to conversation"
}
```



### Testing

```bash
# Backend tests
cd backend
python -m pytest

# Frontend tests
cd frontend
npm test

# End-to-end tests
npm run test:e2e
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

