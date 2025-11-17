# Multi-Tenant RAG System with OpenAI Agents SDK

A scalable, multi-organization RAG (Retrieval-Augmented Generation) system built with OpenAI's Agents SDK, Chainlit, and deployed on Google Cloud Platform with infrastructure as code.

## 🚀 Features

- **OpenAI Agents SDK**: Latest AI capabilities with built-in file search
- **Multi-Tenant**: Deploy separate instances for different organizations
- **Document Management**: Upload, view, and delete documents with web UI
- **Chat History**: SQLite-based persistence for conversations
- **Infrastructure as Code**: Terraform for reproducible deployments
- **Auto-Scaling**: Cloud Run with configurable scaling policies
- **Secure**: Secret Manager for API keys, IAM-based access control

## 🚀 Quick Start

### Prerequisites

1. **Google Cloud SDK**: `gcloud auth login`
2. **Docker**: Installed and running
3. **Terraform**: Version >= 1.0
4. **OpenAI API Key**: From your OpenAI account

### Deploy Your First Organization

**Linux/macOS**:
```bash
# Clone and enter directory
git clone <your-repo-url>
cd primo-chat

# Deploy for "acme-corp" organization
./scripts/deploy.sh acme-corp my-gcp-project-123 sk-your-openai-key us-central1
```

**Windows**:
```cmd
# Clone and enter directory
git clone <your-repo-url>
cd primo-chat

# Deploy for "acme-corp" organization
scripts\deploy.bat acme-corp my-gcp-project-123 sk-your-openai-key us-central1
```

### What Happens During Deployment

1. **Validation**: Checks tools and prerequisites
2. **API Enablement**: Enables required GCP services
3. **Image Build**: Creates and pushes Docker container
4. **Infrastructure**: Deploys with Terraform
5. **Testing**: Validates the deployment
6. **Configuration**: Creates environment files

## 💼 Multi-Organization Deployment

Deploy multiple isolated RAG systems:

```bash
# Organization 1 - US East
./scripts/deploy.sh acme-corp my-project sk-acme-key us-central1

# Organization 2 - EU
./scripts/deploy.sh euro-corp my-project sk-euro-key europe-west1

# Organization 3 - Asia
./scripts/deploy.sh asia-corp my-project sk-asia-key asia-southeast1
```

Each organization gets:
- ✅ Isolated Cloud Run service
- ✅ Separate SQLite database
- ✅ Individual OpenAI vector store
- ✅ Dedicated GCS bucket
- ✅ Own Secret Manager secrets

## 🔧 Configuration

### Environment Variables

```bash
# Core Configuration
ORGANIZATION_NAME=acme-corp
OPENAI_API_KEY=sk-your-key-here
GCP_PROJECT_ID=my-project-123

# Optional Configuration
MAX_FILE_SIZE_MB=20
ALLOWED_FILE_TYPES=pdf,txt,md,docx,doc,rtf,html,json,csv,xml
OPENAI_MODEL=gpt-4-turbo-preview
DEBUG=false
```

## 📊 Usage

### Upload Documents

1. Visit your service URL
2. Click "⬆️ Upload Documents"
3. Select PDFs, Word docs, text files, etc.
4. Documents are automatically processed and indexed

### Chat with Documents

1. Ask questions about your uploaded content
2. The AI searches through documents automatically
3. Responses include citations and sources
4. Chat history is saved automatically

### Manage Knowledge Base

- **📁 View Documents**: See all uploaded files
- **💬 Chat History**: Browse previous conversations  
- **📊 Stats**: View usage statistics
- **🗑️ Delete**: Remove unwanted documents

## 🧪 Local Development & Testing

### Quick Start (Windows)

```cmd
# 1. Get your OpenAI API key from https://platform.openai.com/api-keys

# 2. Run the setup script
start-local.bat

# 3. Edit .env file with your API key when prompted

# 4. The server will start automatically at http://localhost:8000
```

### Quick Start (Linux/macOS)

```bash
# 1. Get your OpenAI API key from https://platform.openai.com/api-keys

# 2. Make script executable and run
chmod +x start-local.sh
./start-local.sh

# 3. Edit .env file with your API key when prompted

# 4. The server will start automatically at http://localhost:8000
```

### Test Your Setup

```bash
# Run comprehensive tests
python test-local.py

# Manual testing
chainlit run app.py --host localhost --port 8000
```

### What You Get Locally

- ✅ **Full RAG System**: Upload docs, ask questions, get AI responses  
- ✅ **Document Management**: Web UI for file operations
- ✅ **Chat History**: Persistent conversations in SQLite
- ✅ **Debug Mode**: Detailed logging for development
- ✅ **Hot Reload**: Automatic restart on code changes

### Local vs Production

| Feature | Local Development | Production Deployment |
|---------|------------------|----------------------|
| **Database** | `./data/org.db` | GCS-mounted SQLite |
| **API Keys** | `.env` file | Google Secret Manager |
| **Scaling** | Single instance | Auto-scaling Cloud Run |
| **Security** | HTTP, local only | HTTPS, IAM controls |
| **Storage** | Local filesystem | Google Cloud Storage |

## 🛠️ Management Commands

### View Logs
```bash
gcloud logs tail --service=acme-corp-rag-agent --region=us-central1
```

### Update Service
```bash
./scripts/update.sh acme-corp my-project-123
```

### Scale Resources
```bash
gcloud run services update acme-corp-rag-agent \
  --max-instances=20 \
  --region=us-central1
```

### Monitor Performance
```bash
gcloud run services describe acme-corp-rag-agent --region=us-central1
```
