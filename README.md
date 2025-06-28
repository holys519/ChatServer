# ChatServer

FastAPI backend for ChatLLM application with Google Gemini AI integration.

## Features

- **FastAPI Framework**: Modern, fast web framework for building APIs
- **Google Gemini Integration**: Real-time AI chat responses with streaming support
- **Multiple Communication Protocols**: REST API, Server-Sent Events, WebSocket
- **Type Safety**: Full TypeScript-compatible API schemas with Pydantic
- **Environment Management**: Clean dependency management with `uv`
- **🔬 Enhanced Research Agents**: Advanced multi-agent system for academic paper search and analysis
- **🤖 Multi-Agent Architecture**: Sequential workflow with specialized agents for quality assurance
- **📊 Research Quality Assurance**: Comprehensive validation, criticism, and enhancement of research results

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

### Research Agent Commands (via Chat)

- `@paper-scout-auditor <query>` - Enhanced paper search with multi-agent validation
- `@paper-scout <query>` - Basic paper search and analysis
- `@review-creation` - Literature review generation with selected papers

### Task Management Endpoints

- `POST /api/tasks/execute` - Execute background tasks with progress tracking
- `GET /api/tasks/status/{task_id}` - Get task progress and status
- `POST /api/tasks/stream/{task_id}` - Stream task progress in real-time

### Model Endpoints

- `GET /api/models/` - Get list of available AI models
- `GET /api/models/{model_id}` - Get specific model information

### WebSocket

- `WS /ws/chat/{client_id}` - WebSocket connection for real-time chat

## Project Structure

```
ChatServer/
├── app/
│   ├── agents/                          # 🤖 Multi-Agent System
│   │   ├── paper_scout_agent.py         # Basic paper search and analysis
│   │   ├── paper_critic_agent.py        # Paper validation and quality assessment
│   │   ├── paper_reviser_agent.py       # Result enhancement and gap filling
│   │   ├── paper_search_auditor.py      # Advanced multi-agent coordinator
│   │   └── review_creation_agent.py     # Literature review generation
│   ├── api/
│   │   ├── routes/
│   │   │   ├── chat.py                  # Chat API with agent command integration
│   │   │   ├── models.py                # Model information endpoints
│   │   │   ├── tasks.py                 # Task management and progress tracking
│   │   │   └── sessions.py              # Session management
│   │   └── websockets/
│   │       └── chat.py                  # WebSocket handlers
│   ├── core/
│   │   └── config.py                   # Application configuration
│   ├── models/
│   │   └── schemas.py                  # Pydantic schemas for agents and tasks
│   ├── services/
│   │   ├── agent_base.py               # 🏗️ Agent base class and orchestrator
│   │   ├── gemini_service.py           # Google Gemini API integration
│   │   ├── pubmed_service.py           # PubMed API integration for research
│   │   ├── translation_service.py      # Multi-language support
│   │   ├── task_service.py             # Background task execution
│   │   ├── session_service.py          # Session persistence
│   │   └── firebase_service.py         # Firebase integration
│   └── main.py                         # FastAPI application entry point
├── scripts/
│   ├── dev.sh                          # Development server script
│   └── start.sh                        # Production server script
├── tests/                              # Test files including agent tests
├── .env.example                        # Environment variables template
├── pyproject.toml                      # Project configuration and dependencies
└── README.md                          # This file
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

## 🤖 Enhanced Research Agent System

### Multi-Agent Architecture

The ChatServer features an advanced multi-agent system designed for high-quality academic research:

#### **PaperCriticAgent** - Research Validation & Quality Assessment
- **Multi-dimensional Quality Scoring**: Relevance, quality, credibility, methodology, and impact assessment
- **Statistical Validity Analysis**: Bias detection and methodology evaluation
- **Citation Impact Analysis**: H-index and journal ranking verification
- **Comprehensive Validation**: Structured scoring with detailed justifications

#### **PaperReviserAgent** - Result Enhancement & Gap Filling
- **Research Gap Analysis**: Systematic identification of missing research areas
- **Quality Optimization**: Intelligent filtering and improvement strategies
- **Diversity Enhancement**: Methodological, geographic, and temporal balancing
- **Strategic Supplementation**: Targeted searches to fill identified gaps

#### **PaperSearchAuditor** - Advanced Multi-Agent Coordinator
- **Sequential Workflow**: Orchestrates critic and reviser agents for optimal results
- **Comprehensive Quality Assurance**: End-to-end validation with confidence scoring
- **Audit Trail**: Complete documentation of all agent actions and decisions
- **Final Validation**: Risk assessment and reliability verification

### Usage Examples

#### Basic Research Query
```
@paper-scout-auditor machine learning in healthcare diagnosis
```

#### Advanced Research with Specific Focus
```
@paper-scout-auditor COVID-19 vaccine efficacy against variants
```

### Research Quality Metrics

The system provides comprehensive quality assessment:
- **Quality Grades**: A+ to D rating system
- **Confidence Scores**: 0.0 to 1.0 reliability assessment
- **Coverage Analysis**: Gap identification and mitigation
- **Bias Detection**: Systematic bias identification and correction

### Supported Research Features

- **Multi-language Support**: Japanese and English query translation
- **Advanced Query Optimization**: PubMed syntax enhancement with MeSH terms
- **Temporal Analysis**: Publication date distribution and recency scoring
- **Geographic Diversity**: International research perspective inclusion
- **Methodology Balancing**: Systematic reviews, RCTs, observational studies

## Supported AI Models

- **Google Gemini 2.0 Flash** - Latest multimodal model with advanced reasoning
- **Google Gemini 2.0 Flash Lite** - Cost-optimized version
- **Google Gemini 2.5 Pro** - Advanced reasoning capabilities (preview)
- **Google Gemini 2.5 Flash** - Thinking model with enhanced analysis (preview)
- **Google Gemini 1.5 Pro** - High-performance multimodal model
- **Google Gemini 1.5 Flash** - Fast response optimized model
- **OpenAI GPT-4o** - (Future implementation)
- **Anthropic Claude** - (Future implementation)

Currently, Google Gemini models have full backend integration with research agents. Other models return structured dummy responses.

## License

This project is part of the ChatLLM application suite.