#!/bin/bash

echo "Starting Local RAG Development Environment..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Creating .env file from example..."
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Edit .env file and add your OpenAI API key!"
    echo "   Open .env and replace 'your-openai-api-key-here' with your actual key"
    echo ""
    read -p "Press Enter after you've updated the .env file..."
fi

# Create data directory
if [ ! -d "data" ]; then
    echo "Creating data directory..."
    mkdir -p data
fi

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check if OpenAI API key is set
if grep -q "your-openai-api-key-here" .env; then
    echo ""
    echo "❌ Please edit .env file and add your OpenAI API key before running!"
    echo "   Replace 'your-openai-api-key-here' with your actual OpenAI API key"
    echo ""
    exit 1
fi

echo ""
echo "✅ Setup complete! Starting Chainlit server..."
echo ""
echo "🌐 Open your browser to: http://localhost:8000"
echo "🛑 Press Ctrl+C to stop the server"
echo ""

# Run the application
chainlit run app.py --host localhost --port 8000