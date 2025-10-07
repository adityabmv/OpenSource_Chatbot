# 🤖 Multi-Bot AI Chatbot System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![React](https://img.shields.io/badge/React-18.0+-61dafb.svg)](https://reactjs.org/)

> **A powerful, scalable AI chatbot system that supports multiple specialized bots with individual knowledge bases, file processing, and intelligent conversations.**

## 🌟 Features

### 🤖 **Multi-Bot Architecture**
- **Individual Bot Management**: Create and manage multiple specialized AI bots
- **Isolated Knowledge Bases**: Each bot maintains its own vector database
- **Bot-Specific Configurations**: Custom chunk sizes, embedding models, and OCR settings per bot
- **Real-time Statistics**: Monitor each bot's database size, chunk count, and file processing status

### 📁 **Advanced File Processing**
- **Multi-format Support**: PDF, CSV, JSON, DOCX, PPTX, TXT files
- **Intelligent OCR**: Extract text from images and scanned documents with multi-language support
- **Smart Chunking**: Configurable text splitting with overlap for better context retention
- **One-Click Processing**: Combined preprocessing and database building in a single operation

### 💬 **Intelligent Chat System**
- **Per-Bot Conversations**: Each bot has its own chat interface and context
- **Multiple LLM Support**: Choose from various models (Qwen, TinyLlama, Mistral, Phi)
- **Custom Instructions**: Tailor bot behavior for specific use cases
- **Markdown Rendering**: Rich text responses with syntax highlighting

### 🎨 **Modern UI/UX**
- **Intuitive Dashboard**: Visual bot management with status indicators
- **Responsive Design**: Works seamlessly on desktop and mobile
- **Dark Theme**: Modern, eye-friendly interface
- **Real-time Updates**: Live status updates and progress indicators

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+**
- **Node.js 16+**
- **Ollama** (for local LLM inference)

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd os-chatbot
```

2. **Backend Setup**
```bash
cd backend
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
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
│  └── Individual bot directories                       │
└─────────────────────────────────────────────────────────┘
```

### Key Components

#### **BotManager** (`bot_manager.py`)
- Manages bot creation, updates, and deletion
- Handles bot configurations and metadata
- Provides bot statistics and status tracking

#### **VectorStore** (`vectorstore.py`)
- ChromaDB integration for vector storage
- Individual vectorstores per bot (`vector_db_{bot_id}/`)
- Efficient similarity search and retrieval

#### **File Processor** (`app.py` - processing endpoints)
- Multi-format file parsing (PDF, CSV, DOCX, etc.)
- OCR integration for image text extraction
- Intelligent text chunking with configurable overlap

#### **Chat Engine** (`app.py` - query endpoints)
- Ollama integration for LLM inference
- Context-aware query processing
- Markdown response formatting

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
}
```

### Chat Endpoints

#### Query Bot
```http
POST /bots/{bot_id}/query/
Content-Type: application/json

{
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

## 🎯 Use Cases

### **HR Assistant Bot**
- Upload employee handbooks, policies, and HR documents
- Answer questions about company policies, benefits, procedures
- Assist with employee onboarding and training

### **Legal Document Bot**
- Process contracts, legal agreements, and case files
- Provide insights on legal requirements and compliance
- Help with document review and analysis

### **Technical Documentation Bot**
- Upload API documentation, user manuals, and technical guides
- Answer questions about product features and troubleshooting
- Assist developers with codebase understanding

### **Research Assistant Bot**
- Process academic papers, research documents, and reports
- Summarize key findings and methodologies
- Help with literature review and citation management

## 🔒 Security & Privacy

- **Local Processing**: All data processing happens locally
- **No External APIs**: LLM inference via local Ollama instance
- **Isolated Databases**: Each bot's data is completely separate
- **Configurable Privacy**: Choose what data to include in each bot

## 🚀 Performance & Scalability

### **Efficient Vector Storage**
- ChromaDB for fast similarity search
- Optimized chunk sizes and overlap for context preservation
- Incremental updates without full database rebuilds

### **Memory Management**
- Configurable LLM models based on available resources
- Streaming responses for large document processing
- Efficient caching of embeddings and processed content

### **Scalability Features**
- Individual vectorstores prevent database bloat
- Horizontal scaling potential with multiple backend instances
- Configurable processing parameters for different hardware

## 🛠️ Development

### Project Structure

```
os-chatbot/
├── backend/
│   ├── app.py              # Main FastAPI application
│   ├── bot_manager.py      # Bot lifecycle management
│   ├── vectorstore.py      # ChromaDB integration
│   ├── requirements.txt    # Python dependencies
│   └── bots_config.json    # Bot configurations storage
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── BotDashboard.tsx    # Bot management UI
│   │   │   ├── BotChat.tsx        # Chat interface
│   │   │   └── MainApp.tsx        # Main application
│   │   ├── App.tsx                # React app entry point
│   │   └── index.tsx              # React DOM entry point
│   ├── package.json               # Node.js dependencies
│   └── tailwind.config.js         # Styling configuration
└── README.md                      # This file
```

### Contributing

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes**
4. **Test thoroughly**
5. **Submit a pull request**

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

## 🙏 Acknowledgments

- **LangChain** for the powerful RAG framework
- **ChromaDB** for efficient vector storage
- **Ollama** for local LLM inference
- **React & TypeScript** for the modern frontend
- **Tailwind CSS** for beautiful styling

## 🚀 For future Production Deployment

### Deployment Options

#### **Docker Deployment** (Recommended)
```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY backend/ ./backend/
COPY frontend/build ./frontend/build

WORKDIR /app/backend
EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# Build and run
docker build -t chatbot-system .
docker run -p 8000:8000 -v ollama_data:/ollama chatbot-system
```

#### **Cloud Deployment**

**AWS (ECS Fargate)**
```bash
# Build and push to ECR
aws ecr create-repository --repository-name chatbot-system
docker build -t chatbot-system .
docker tag chatbot-system:latest <account-id>.dkr.ecr.<region>.amazonaws.com/chatbot-system:latest
aws ecr get-login-password | docker login --username AWS --password-stdin <account-id>.dkr.ecr.<region>.amazonaws.com
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/chatbot-system:latest

# Deploy to ECS
aws ecs create-cluster --cluster-name chatbot-cluster
aws ecs create-service --cluster chatbot-cluster --service-name chatbot-service --task-definition chatbot-task
```

**Google Cloud Run**
```bash
gcloud builds submit --tag gcr.io/PROJECT-ID/chatbot-system
gcloud run deploy --image gcr.io/PROJECT-ID/chatbot-system --platform managed --region us-central1
```

**Azure Container Instances**
```bash
az container create --resource-group chatbot-rg --name chatbot-container --image chatbot-registry.azurecr.io/chatbot-system:latest --dns-name-label chatbot-dns --ports 8000
```

### Scaling Strategies

#### **Horizontal Scaling**
- **Load Balancer Setup**: Distribute requests across multiple backend instances
- **Database Sharding**: Split bot data across multiple ChromaDB instances
- **Stateless Design**: Each request can be handled by any backend instance

#### **Vertical Scaling**
- **Resource Optimization**: Configure chunk sizes based on available memory
- **Model Selection**: Choose appropriate LLM models for hardware capabilities
- **Batch Processing**: Process multiple files concurrently

### Performance Optimization

#### **Database Optimization**
- **Vectorstore Tuning**: Optimize ChromaDB settings for query performance
- **Embedding Caching**: Cache frequently used embeddings in Redis
- **Connection Pooling**: Reuse database connections for better performance

#### **Frontend Optimization**
- **Code Splitting**: Lazy load components for faster initial load
- **Service Workers**: Cache static assets for offline functionality
- **CDN Integration**: Serve static files from content delivery networks

### Monitoring & Observability

#### **Application Monitoring**
```bash
# Health check endpoint
GET /health

# Metrics endpoint
GET /metrics
```

#### **Logging Strategy**
- **Structured Logging**: JSON format for easy parsing and analysis
- **Log Aggregation**: Send logs to Elasticsearch or similar service
- **Error Tracking**: Monitor and alert on critical errors

#### **Performance Monitoring**
- **Response Times**: Track API endpoint performance
- **Resource Usage**: Monitor CPU, memory, and disk utilization
- **User Analytics**: Track bot usage patterns and popular queries

### Security Considerations

#### **Production Security**
- **HTTPS Only**: Enforce SSL/TLS encryption for all communications
- **API Authentication**: Implement JWT tokens for API access
- **Input Validation**: Sanitize all user inputs and file uploads
- **Rate Limiting**: Prevent abuse with request rate limiting

#### **Data Protection**
- **Encryption at Rest**: Encrypt vector databases and configuration files
- **Access Controls**: Implement role-based access for different users
- **Audit Logging**: Track all data access and modifications
- **GDPR Compliance**: Handle personal data according to regulations

### DevOps & CI/CD

#### **Continuous Integration**
```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline

on:
  push:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          cd backend && pip install -r requirements.txt
      - name: Run tests
        run: |
          cd backend && python -m pytest
```

#### **Continuous Deployment**
```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  release:
    types: [published]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Build and push Docker image
        run: |
          docker build -t chatbot-system:${{ github.event.release.tag_name }} .
          docker push myregistry/chatbot-system:${{ github.event.release.tag_name }}
      - name: Deploy to Kubernetes
        run: |
          kubectl set image deployment/chatbot-deployment chatbot=myregistry/chatbot-system:${{ github.event.release.tag_name }}
```

### High Availability Setup

#### **Multi-Region Deployment**
- **Global Load Balancer**: Route users to nearest region
- **Data Replication**: Sync bot configurations across regions
- **Failover Strategy**: Automatic failover for backend services

#### **Backup & Recovery**
- **Automated Backups**: Daily backups of vectorstores and configurations
- **Disaster Recovery**: Geographic redundancy for critical data
- **Point-in-Time Recovery**: Restore system to any previous state

### Cost Optimization

#### **Infrastructure Costs**
- **Right-Sizing**: Choose appropriate instance types for workload
- **Auto-Scaling**: Scale resources based on demand
- **Spot Instances**: Use discounted compute for non-critical workloads

#### **Operational Efficiency**
- **Resource Monitoring**: Identify and eliminate waste
- **Automated Cleanup**: Remove unused bot data and temporary files
- **Efficient Storage**: Compress and deduplicate stored content

## 🔮 Advanced Features Roadmap

### **Phase 1: Enhanced Intelligence** (v2.0)
- **Multi-Modal Processing**: Support for images, audio, and video files
- **Advanced RAG**: Hybrid search combining semantic and keyword matching
- **Conversation Memory**: Persistent chat history and context retention
- **Custom Embeddings**: Fine-tuned embedding models for specific domains

### **Phase 2: Enterprise Integration** (v2.5)
- **LDAP/SSO Integration**: Enterprise authentication systems
- **API Rate Limiting**: Advanced quota management for API users
- **Audit Compliance**: Detailed logging for regulatory requirements
- **Multi-Tenant Architecture**: Support for multiple organizations

### **Phase 3: Advanced Analytics** (v3.0)
- **Usage Analytics**: Detailed insights into bot performance and usage
- **Query Optimization**: Automatic improvement of bot responses
- **A/B Testing**: Compare different bot configurations and models
- **Predictive Insights**: Anticipate user needs based on usage patterns

### **Phase 4: Ecosystem Expansion** (v3.5)
- **Plugin System**: Extensible architecture for custom integrations
- **Marketplace**: Share and discover pre-trained bots and datasets
- **Mobile Apps**: Native iOS and Android applications
- **Voice Integration**: Conversational voice interfaces

## 📞 Production Support

For production deployments and enterprise support:

- **Email**: enterprise@yourcompany.com
- **Slack Community**: [Join our workspace](https://chatbot-community.slack.com)
- **Documentation**: [Enterprise Docs](https://docs.yourcompany.com)
- **Support Portal**: [Get Help](https://support.yourcompany.com)

---

*Ready to take your chatbot system to production? This roadmap provides a clear path from development to enterprise-scale deployment with all the tools and strategies you'll need for success! 🚀*
