# ChatServer

FastAPI backend for ChatLLM application with Google Gemini AI integration.

## Features

- **FastAPI Framework**: Modern, fast web framework for building APIs
- **Google Gemini Integration**: Real-time AI chat responses with streaming support
- **Multiple Communication Protocols**: REST API, Server-Sent Events, WebSocket
- **Type Safety**: Full TypeScript-compatible API schemas with Pydantic
- **Environment Management**: Clean dependency management with `uv`

## Requirements

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager
- Google Cloud API key for Gemini API

## Quick Start

### 1. Clone and Setup

```bash
cd ChatServer
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your API keys
# Especially set GOOGLE_CLOUD_API_KEY for Gemini functionality
nano .env
```

### 3. Start Development Server

```bash
# Using the provided script (recommended)
./scripts/dev.sh

# Or manually with uv
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Access the Application

- **API Server**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## API Endpoints

### Chat Endpoints

- `POST /api/chat/send` - Send message and get complete response
- `POST /api/chat/stream` - Send message and get streaming response (SSE)

### Model Endpoints

- `GET /api/models/` - Get list of available AI models
- `GET /api/models/{model_id}` - Get specific model information

### WebSocket

- `WS /ws/chat/{client_id}` - WebSocket connection for real-time chat

## Project Structure

```
ChatServer/
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── chat.py          # Chat API endpoints
│   │   │   └── models.py        # Model information endpoints
│   │   └── websockets/
│   │       └── chat.py          # WebSocket handlers
│   ├── core/
│   │   └── config.py           # Application configuration
│   ├── models/
│   │   └── schemas.py          # Pydantic schemas
│   ├── services/
│   │   └── gemini_service.py   # Google Gemini API integration
│   └── main.py                 # FastAPI application entry point
├── scripts/
│   ├── dev.sh                  # Development server script
│   └── start.sh                # Production server script
├── tests/                      # Test files
├── .env.example               # Environment variables template
├── pyproject.toml             # Project configuration and dependencies
└── README.md                  # This file
```

## Development

### Using uv for Development

```bash
# Install development dependencies
uv sync --dev

# Run tests
uv run pytest

# Code formatting
uv run black app/
uv run isort app/

# Type checking
uv run mypy app/

# Linting
uv run flake8 app/
```

### Environment Variables

Create a `.env` file based on `.env.example`:

```env
# Required for Gemini AI functionality
GOOGLE_CLOUD_API_KEY=your_google_cloud_api_key_here

# Optional
DEBUG=false
APP_NAME=ChatLLM API
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

## Production Deployment

```bash
# Start production server
./scripts/start.sh

# Or manually
uv sync --frozen
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Integration with Frontend

This backend is designed to work with the ChatLLMApp React Native frontend. The frontend automatically:

- Detects API connection status
- Falls back to dummy responses when backend is unavailable
- Supports real-time streaming for Google Gemini models
- Provides seamless model switching

## Supported AI Models

- **Google Gemini 1.5 Pro** - High-performance multimodal model
- **Google Gemini 1.5 Flash** - Fast response optimized model
- **OpenAI GPT-4o** - (Future implementation)
- **Anthropic Claude** - (Future implementation)

Currently, only Google Gemini models have full backend integration. Other models return structured dummy responses.

## License

This project is part of the ChatLLM application suite.