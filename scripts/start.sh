#!/bin/bash

# ChatServer Production Server Startup Script
# Uses uv for dependency management

set -e

echo "🚀 Starting ChatServer production server with uv..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please create it with your configuration."
    exit 1
fi

# Install dependencies using uv
echo "📦 Installing dependencies with uv..."
uv sync --frozen

# Start the production server
echo "🌐 Starting FastAPI server on http://localhost:8000"
echo "📖 API documentation will be available at http://localhost:8000/docs"
echo ""

# Run the server using uv with production settings
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4