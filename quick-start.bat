@echo off
echo 🚀 Quick RAG Setup - Let's get you running locally!
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

echo ✅ Python is available

REM Create and activate virtual environment
if not exist "venv" (
    echo 📦 Creating virtual environment...
    python -m venv venv
)

echo 🔧 Activating virtual environment...
call venv\Scripts\activate

echo 📚 Installing core dependencies...
pip install --upgrade pip

REM Install minimal dependencies for local development
pip install chainlit openai python-dotenv

echo.
echo 🔑 Setting up configuration...

REM Create .env if it doesn't exist
if not exist ".env" (
    echo Creating .env file...
    (
        echo # Local RAG Configuration
        echo ORGANIZATION_NAME=local-test
        echo ORGANIZATION_DISPLAY_NAME=Local Test
        echo OPENAI_API_KEY=your-openai-api-key-here
        echo.
        echo # Local Settings
        echo DATA_DIRECTORY=./data
        echo DEBUG=true
        echo LOG_LEVEL=DEBUG
        echo.
        echo # Feature Flags
        echo ENABLE_DOCUMENT_MANAGEMENT=true
        echo ENABLE_CHAT_HISTORY=true
        echo ENABLE_USER_MANAGEMENT=false
    ) > .env
)

REM Create data directory
if not exist "data" (
    mkdir data
    echo ✅ Created data directory
)

echo.
echo 📝 Please edit your .env file and add your OpenAI API key:
echo.
echo 1. Get your API key from: https://platform.openai.com/api-keys
echo 2. Open .env file in this directory
echo 3. Replace 'your-openai-api-key-here' with your actual API key
echo 4. Save the file
echo.

REM Check if API key is set
findstr /C:"your-openai-api-key-here" .env >nul
if %errorlevel%==0 (
    echo ⚠️  NEXT STEP: Edit .env file with your OpenAI API key
    echo Then run: chainlit run app.py
) else (
    echo ✅ API key appears to be set!
    echo.
    echo 🌟 Starting your RAG assistant...
    echo 🌐 Open http://localhost:8000 in your browser
    echo 🛑 Press Ctrl+C to stop
    echo.
    chainlit run app.py --host localhost --port 8000
)

pause