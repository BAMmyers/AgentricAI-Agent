# AgentricAI

**Sovereign Intelligence Platform** - A local-first AI agent ecosystem for autonomous, privacy-respecting intelligence.

## Overview

AgentricAI is a self-contained AI platform that runs entirely on your local machine. It provides:

- **Local LLM Integration** - Connects to Ollama for fully local inference
- **Memory-Scoped Agents** - Agents with persistent, scoped memory
- **Tool Execution** - MCP-compatible tool system for extending capabilities
- **Modern UI** - Cursor-inspired dark theme chat interface
- **Full Privacy** - No data leaves your machine

## Quick Start

### Prerequisites

- **Ollama** installed with at least one model (e.g., `lacy:latest`)
- **Python 3.14+** or use the embedded runtime
- **Node.js 18+** (for UI development)

### Launch

## Development & Testing

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the test suite:

```bash
pytest tests/
```

Redis should be running locally for caching and Celery tasks; you can start it via Docker or `redis-server`.
Start a Celery worker in another terminal:

```bash
celery -A core.tasks.celery_app worker --loglevel=info
```


### Launch

```bash
# Using the launcher (recommended)
launch.bat

# Or with GPU acceleration
launch_gpu.bat
```

This starts:
- Ollama service (if not running)
- API server on http://127.0.0.1:3939
- UI on http://localhost:3000

## Architecture

```
AgentricAI/
├── core/                    # Core Python modules
│   ├── agents/              # Agent implementations
│   │   └── memory_scoped_agents.py
│   ├── memory/              # Memory management
│   ├── agent_loader.py      # Dynamic agent discovery
│   ├── tool_loader.py       # Tool loading and execution
│   ├── memory_router.py     # Memory routing and persistence
│   ├── conversation_engine.py
│   ├── config.py            # Configuration management
│   ├── schemas.py           # Pydantic validation schemas
│   ├── commands.py          # Command system
│   ├── hardware_bindings.py # Hardware detection
│   └── logging_config.py    # Structured logging
├── api/                     # FastAPI endpoints
│   └── gateway.py           # Main API gateway
├── UI/                      # Next.js frontend
│   ├── app/                 # App router pages
│   ├── components/          # React components
│   │   ├── chat/            # Chat components
│   │   └── layout/          # Layout components
│   └── lib/                 # Utilities
├── Tools/                   # MCP tools
│   ├── DataPreprocessor/
│   ├── GPUAccelerator/
│   └── MLModelTrainer/
├── tests/                   # Test suite
├── MCP_Catalog.json         # Tool definitions
├── runtime.json             # Runtime configuration
└── launch.bat               # Windows launcher
```

## Configuration

### New Features Added
- Redis caching layer & connection pooling
- Background task queue with Celery (Redis broker)
- Prometheus metrics at `/metrics`
- OpenTelemetry tracing with Jaeger (init via `core/tracing`)
- Kubernetes probes: `/healthz` and `/readyz`
- GZIP response compression
- Input sanitization and prompt injection detection
- Dockerfile and docker-compose support


### Environment Variables

```bash
AGENTRIC_HOST=127.0.0.1
AGENTRIC_API_PORT=3939
AGENTRIC_UI_PORT=3000
AGENTRIC_OLLAMA_URL=http://127.0.0.1:11434
AGENTRIC_DEFAULT_MODEL=lacy:latest
AGENTRIC_LOG_LEVEL=INFO
```

### runtime.json

The `runtime.json` file contains default configuration:

```json
{
  "runtime": {
    "host": "127.0.0.1",
    "api_port": 3939,
    "ollama_url": "http://127.0.0.1:11434",
    "default_model": "lacy:latest"
  }
}
```

## API Reference

### Chat

```http
POST /api/chat
Content-Type: application/json

{
  "text": "Hello, how are you?",
  "agent_id": "lacy",
  "resource": "default",
  "thread": "default",
  "stream": true
}
```

### Agents

```http
GET /api/agents
GET /api/agents/{agent_id}
POST /api/agents/create
DELETE /api/agents/{agent_id}
```

### Tools

```http
GET /api/tools
GET /api/tools/validation
POST /api/tools/execute
```

### Memory

```http
GET /api/memory/conversations/{resource}/{thread}
DELETE /api/memory/conversations/{resource}/{thread}
POST /api/memory/store
POST /api/memory/retrieve
POST /api/memory/search
```

### Health

```http
GET /health
GET /health/detailed
```

## Agents

### Built-in Agents

- **Lacy** (`lacy`) - Default assistant, warm and helpful
- **PersonalAssistantResource** (`personal-assistant-resource`) - Resource-scoped memory
- **PersonalAssistantThread** (`personal-assistant-thread`) - Thread-scoped memory

### Creating Custom Agents

```python
from core.agents.memory_scoped_agents import MemoryScopedAgent

class MyAgent(MemoryScopedAgent):
    id = "my-agent"
    name = "My Custom Agent"
    model = "lacy:latest"
    memory_config = {
        "scope": "resource",
        "template": "You are a helpful custom agent."
    }
```

## Tools

### Tool Structure

```
Tools/
└── MyTool/
    ├── my_tool.bat      # Windows launcher
    └── my_tool.py       # Python implementation
```

### Tool Catalog

Tools are defined in `MCP_Catalog.json`:

```json
{
  "id": "my-tool",
  "name": "MyTool",
  "category": "Utilities",
  "environment_bindings": {
    "relative_path": "Tools/MyTool",
    "binary": "my_tool.bat",
    "execution_mode": "CPU"
  }
}
```

## Development

### Setup

```bash
# Install Python dependencies
pip install fastapi uvicorn pydantic psutil

# Install UI dependencies
cd UI
npm install
```

### Running Tests

```bash
pytest tests/ -v
```

### Code Style

```bash
black core/ api/
isort core/ api/
flake8 core/ api/
```

## Memory System

AgentricAI uses SQLite for persistent memory:

- **Global scope** - Shared across all sessions
- **Resource scope** - Scoped to a resource (e.g., project)
- **Thread scope** - Scoped to a conversation thread

Memory is stored in `memory.db` with full conversation history.

## Troubleshooting

### Ollama Not Running

```bash
ollama serve
```

### Model Not Found

```bash
ollama pull lacy:latest
```

### Port Already in Use

Change ports in `runtime.json` or via environment variables.

### UI Not Loading

```bash
cd UI
npm install
npm run dev
```

## License

MIT License - See LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## Support

- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Discord**: discord.gg/letta
