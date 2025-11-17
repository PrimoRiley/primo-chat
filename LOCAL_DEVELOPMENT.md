# Local Development Setup

## Quick Local Testing

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Set Environment Variables

Create a `.env` file in the project root:

```bash
# Core Configuration
ORGANIZATION_NAME=local-test
ORGANIZATION_DISPLAY_NAME=Local Test
OPENAI_API_KEY=sk-your-openai-api-key-here

# Local Development Settings
DATA_DIRECTORY=./data
DEBUG=true
LOG_LEVEL=DEBUG

# Optional Configuration
MAX_FILE_SIZE_MB=20
ALLOWED_FILE_TYPES=pdf,txt,md,docx,doc,rtf,html,json,csv,xml
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_ASSISTANT_MODEL=gpt-4-turbo-preview

# Feature Flags
ENABLE_DOCUMENT_MANAGEMENT=true
ENABLE_CHAT_HISTORY=true
ENABLE_USER_MANAGEMENT=false

# Chainlit Configuration
CHAINLIT_HOST=localhost
CHAINLIT_PORT=8000
```

### 3. Create Local Data Directory

```bash
# Windows
mkdir data

# Linux/macOS
# mkdir -p data
```

### 4. Run the Application

```bash
# Load environment variables and run
chainlit run app.py --host localhost --port 8000
```

### 5. Open in Browser

Visit: http://localhost:8000

## Local Development Features

- ✅ **SQLite Database**: Stored in `./data/local-test.db`
- ✅ **Document Upload**: Works with local file system
- ✅ **Chat History**: Persisted locally
- ✅ **Debug Logging**: Detailed console output
- ✅ **Hot Reload**: Chainlit auto-reloads on code changes

## Testing Different Organizations

You can test multiple organizations locally by changing the environment:

```bash
# Organization 1
set ORGANIZATION_NAME=org1
chainlit run app.py --port 8001

# Organization 2 (new terminal)
set ORGANIZATION_NAME=org2
chainlit run app.py --port 8002
```

Each will have its own SQLite database and isolated data.

## Troubleshooting

### Common Issues

1. **OpenAI API Key Missing**
   ```
   Error: OPENAI_API_KEY is required
   ```
   **Solution**: Add your OpenAI API key to `.env` file

2. **Port Already in Use**
   ```
   Error: [Errno 48] Address already in use
   ```
   **Solution**: Use a different port: `chainlit run app.py --port 8001`

3. **Module Not Found**
   ```
   ModuleNotFoundError: No module named 'openai'
   ```
   **Solution**: Activate virtual environment and install dependencies

4. **Permission Denied on Data Directory**
   ```
   PermissionError: [Errno 13] Permission denied
   ```
   **Solution**: Create data directory manually or run with appropriate permissions

### Debug Mode

Enable detailed logging by setting `DEBUG=true` in your `.env` file. This will show:
- Database operations
- OpenAI API calls
- File upload details
- Error stack traces

## Local vs Production Differences

| Feature | Local | Production |
|---------|--------|------------|
| Database | `./data/org.db` | GCS-mounted volume |
| API Keys | `.env` file | Secret Manager |
| Scaling | Single instance | Auto-scaling |
| HTTPS | HTTP only | HTTPS with certificates |
| Monitoring | Console logs | Cloud Logging |

## Next Steps

Once you've tested locally:

1. **Validate Core Features**: Upload docs, ask questions, check chat history
2. **Test Edge Cases**: Large files, multiple uploads, long conversations
3. **Performance Testing**: Upload multiple documents, stress test queries
4. **Deploy to GCP**: Use the deployment scripts when ready

Your local environment mimics production behavior while being easy to debug and iterate on!