#!/bin/bash

# ChatServer Development Server Startup Script
# Uses uv for dependency management

set -e

echo "🚀 Starting ChatServer development server with uv..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "📝 Please edit .env file with your API keys before running again."
        echo "   Especially set GOOGLE_CLOUD_API_KEY for Gemini API functionality."
        echo "   Also set OPENAI_API_KEY for OpenAI functionality."
        exit 1
    else
        echo "❌ .env.example file not found. Please create .env file manually."
        exit 1
    fi
fi

# Check if API keys are set
if ! grep -q "GOOGLE_CLOUD_API_KEY=your_google_cloud_api_key_here" .env; then
    echo "✅ Google Cloud API key appears to be configured."
else
    echo "⚠️  Please set your GOOGLE_CLOUD_API_KEY in .env file."
    echo "   Current value appears to be the default placeholder."
fi

if ! grep -q "OPENAI_API_KEY=your_openai_api_key_here" .env; then
    echo "✅ OpenAI API key appears to be configured."
else
    echo "⚠️  Please set your OPENAI_API_KEY in .env file."
    echo "   Current value appears to be the default placeholder."
fi

# Create virtual environment and install dependencies using uv
echo "📦 Installing dependencies with uv..."
uv sync

# Check for port conflicts and use alternative port if needed
PORT=${PORT:-8000}

# Check if port is already in use
if ss -tlnp | grep -q ":$PORT "; then
    echo "⚠️  Port $PORT is already in use. Trying port 8001..."
    PORT=8001
    if ss -tlnp | grep -q ":$PORT "; then
        echo "⚠️  Port $PORT is also in use. Trying port 8002..."
        PORT=8002
    fi
fi

# Start the development server
echo "🌐 Starting FastAPI server on http://localhost:$PORT"
echo "📖 API documentation will be available at http://localhost:$PORT/docs"
echo "🔍 Health check endpoint: http://localhost:$PORT/health"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Run the server using uv
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port $PORT