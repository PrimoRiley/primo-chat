@echo off
echo Starting Local RAG Development Environment...

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate

REM Check if .env exists
if not exist ".env" (
    echo Creating .env file from example...
    copy .env.example .env
    echo.
    echo ⚠️  IMPORTANT: Edit .env file and add your OpenAI API key!
    echo    Open .env and replace 'your-openai-api-key-here' with your actual key
    echo.
    pause
)

REM Create data directory
if not exist "data" (
    echo Creating data directory...
    mkdir data
)

REM Install dependencies
echo Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt

REM Check if OpenAI API key is set
findstr /C:"your-openai-api-key-here" .env >nul
if %errorlevel%==0 (
    echo.
    echo ❌ Please edit .env file and add your OpenAI API key before running!
    echo    Replace 'your-openai-api-key-here' with your actual OpenAI API key
    echo.
    pause
    exit /b 1
)

echo.
echo ✅ Setup complete! Starting Chainlit server...
echo.
echo 🌐 Open your browser to: http://localhost:8000
echo 🛑 Press Ctrl+C to stop the server
echo.

REM Run the application
chainlit run app.py --host localhost --port 8000