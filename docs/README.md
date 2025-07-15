# OpenRouter MCP Server

<div align="center">

[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://www.docker.com/)
[![MCP](https://img.shields.io/badge/MCP-2024--10--07-purple.svg)](https://modelcontextprotocol.io/)
[![OpenRouter](https://img.shields.io/badge/OpenRouter-400%2B%20Models-orange.svg)](https://openrouter.ai/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](../LICENSE)

**A powerful Model Context Protocol (MCP) server providing unified access to 400+ AI models through OpenRouter's API**

</div>

## 🚀 Overview

OpenRouter MCP Server is a Python-based tool that bridges the gap between MCP clients (like Claude Code) and OpenRouter's extensive AI model ecosystem. It provides seamless access to models from OpenAI, Anthropic, Meta, Google, Mistral, and many other providers through a single, unified interface.

### ✨ Key Features

- **🤖 Multi-Model Access**: Connect to 400+ AI models from 30+ providers
- **🔄 Conversation Continuity**: Persistent chat history with UUID-based sessions
- **🎯 Smart Model Selection**: Natural language model aliases (`"gemini"` → `"google/gemini-2.5-pro"`)
- **📁 Multi-Modal Support**: Handle text, files, and images seamlessly
- **🐳 Docker Ready**: Containerized deployment with security best practices
- **⚡ Performance Optimized**: Intelligent caching and token management
- **🔧 Developer Friendly**: Comprehensive logging and debugging tools

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MCP Client    │───▶│  OpenRouter MCP │───▶│   OpenRouter    │
│  (Claude Code)  │    │     Server      │    │      API        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │  Conversation   │
                       │    Storage      │
                       └─────────────────┘
```

### Core Components

| Component | Description |
|-----------|-------------|
| **`src/server.py`** | Main MCP server with JSON-RPC protocol implementation |
| **`src/config.py`** | Configuration management and model alias resolution |
| **`src/conversation_manager.py`** | Persistent conversation storage with UUID sessions |
| **`tools/docker_manager.py`** | Docker container lifecycle management |

## 📦 Installation

### Prerequisites

- **Python 3.12+** (Required)
- **Docker & Docker Compose** (Recommended)
- **OpenRouter API Key** (Required)

### Method 1: Docker Deployment (Recommended)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/slyfox1186/claude-code-openrouter.git
   cd claude-code-openrouter
   ```

2. **Set up environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your OpenRouter API key
   nano .env
   ```

3. **Build and run:**
   ```bash
   ./scripts/build.sh
   ./scripts/run.sh
   ```

### Method 2: Direct Python Installation

1. **Clone and install dependencies:**
   ```bash
   git clone https://github.com/slyfox1186/claude-code-openrouter.git
   cd claude-code-openrouter
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Add your OpenRouter API key to .env
   ```

3. **Run the server:**
   ```bash
   python run_server.py
   ```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```env
# OpenRouter API Configuration
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# Default Model Settings
DEFAULT_MODEL=moonshotai/kimi-k2
DEFAULT_TEMPERATURE=0.7
DEFAULT_MAX_TOKENS=4096

# Tool Configuration
ENABLE_WEB_SEARCH=true
MAX_CONTEXT_TOKENS=100000
TOKEN_BUDGET_LIMIT=50000

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=openrouter_mcp.log

# Optional: Rate limiting
RATE_LIMIT_REQUESTS_PER_MINUTE=60
RATE_LIMIT_TOKENS_PER_MINUTE=100000

# Docker Compose Bake delegation for better build performance
COMPOSE_BAKE=true
```

### 🔑 Getting Your OpenRouter API Key

1. Visit [OpenRouter.ai](https://openrouter.ai/)
2. Sign up for an account
3. Navigate to the API Keys section
4. Generate a new API key
5. Add it to your `.env` file as `OPENROUTER_API_KEY`

## 🎯 Usage

### MCP Tools Available

The server exposes these MCP tools for client interaction:

| Tool | Description |
|------|-------------|
| **`chat`** | Main chat interface with model selection and conversation continuation |
| **`list_conversations`** | View all stored conversation summaries |
| **`get_conversation`** | Retrieve full conversation history by ID |
| **`delete_conversation`** | Remove a conversation from storage |

### Model Selection

The server supports intelligent model aliases:

```json
{
  "model": "gemini"          // → google/gemini-2.5-pro
  "model": "claude"          // → anthropic/claude-4-sonnet
  "model": "claude opus"     // → anthropic/claude-4-opus
  "model": "kimi"            // → moonshotai/kimi-k2
  "model": "gpt-4"           // → openai/gpt-4
}
```

### Conversation Continuity

Each chat session returns a `continuation_id` that can be used to maintain context:

```json
{
  "prompt": "Follow up question...",
  "continuation_id": "uuid-from-previous-response"
}
```

### Multi-Modal Input

Support for various input types:

```json
{
  "prompt": "Analyze this code",
  "files": ["/path/to/file.py"],
  "images": ["/path/to/screenshot.png"],
  "model": "gemini"
}
```

## 🐳 Docker Management

Use the included Docker manager for easy container operations:

```bash
# Build image
python tools/docker_manager.py build

# Start container
python tools/docker_manager.py start

# View logs
python tools/docker_manager.py logs

# Interactive shell
python tools/docker_manager.py shell

# Stop container
python tools/docker_manager.py stop

# Full restart
python tools/docker_manager.py restart

# Check status
python tools/docker_manager.py status
```

## 🔧 Development

### Project Structure

```
openrouter-connect/
├── src/                   # Source code
│   ├── server.py          # Main MCP server implementation
│   ├── config.py          # Configuration and model management
│   └── conversation_manager.py # Conversation persistence
├── tools/                 # Development tools
│   └── docker_manager.py  # Docker operations and management
├── scripts/               # Build and deployment scripts
│   ├── build.sh           # Docker build script
│   └── run.sh            # Docker run script
├── docker/               # Docker configuration
│   ├── Dockerfile        # Container definition
│   └── docker-compose.yml # Service orchestration
├── docs/                 # Documentation
│   └── README.md         # This file
├── examples/             # Usage examples
│   └── example_usage.py  # Basic usage examples
├── requirements.txt      # Python dependencies
├── run_server.py         # Main server launcher
├── .env.example          # Environment template
├── .gitignore            # Git ignore patterns
├── CLAUDE.md             # Claude Code instructions
└── LICENSE               # Apache 2.0 license
```

### Logging and Debugging

- **Server logs**: `/tmp/openrouter_debug.log`
- **Application logs**: `openrouter_mcp.log`
- **Container logs**: `docker logs openrouter`

### Model Capabilities

The server automatically detects model capabilities:

- **Vision Models**: Handle image inputs (Gemini Pro, GPT-4V)
- **Large Context**: Support extended conversations (Kimi K2, Gemini)
- **Function Calling**: Tool use capabilities (Gemini Pro, GPT-4)

## 🚨 Security & Best Practices

### Environment Security

- ✅ **Never commit `.env` files** (protected by `.gitignore`)
- ✅ **Use `.env.example` for templates**
- ✅ **Run containers as non-root user**
- ✅ **Read-only volume mounts**

### API Key Management

- 🔐 Store API keys in `.env` only
- 🔐 Use environment variables in production
- 🔐 Rotate keys regularly
- 🔐 Monitor usage and billing

## 📊 Monitoring & Performance

### Token Management

- Automatic conversation truncation to prevent API limits
- Token usage tracking and reporting
- Configurable token budgets per request

### Performance Features

- In-memory conversation caching
- Efficient JSON-RPC protocol
- Streaming response support
- Request rate limiting

## 🔄 Supported Models

### Popular Model Aliases

| Alias | Full Model Name | Provider |
|-------|-----------------|----------|
| `gemini` | `google/gemini-2.5-pro` | Google |
| `claude` | `anthropic/claude-4-sonnet` | Anthropic |
| `claude-opus` | `anthropic/claude-4-opus` | Anthropic |
| `kimi` | `moonshotai/kimi-k2` | Moonshot |
| `gpt-4` | `openai/gpt-4` | OpenAI |
| `llama` | `meta-llama/llama-3.1-8b-instruct` | Meta |

### Model Categories

- **💬 Chat Models**: General conversation and reasoning
- **👁️ Vision Models**: Image understanding and analysis
- **🔧 Function Models**: Tool use and function calling
- **📚 Long Context**: Extended conversation memory
- **⚡ Fast Models**: Quick responses and low latency

## 🛠️ Troubleshooting

### Common Issues

**Server won't start:**
```bash
# Check environment configuration
python -c "from src.config import validate_config; print(validate_config())"

# Verify API key
echo $OPENROUTER_API_KEY
```

**Container issues:**
```bash
# Check container status
python tools/docker_manager.py status

# View detailed logs
python tools/docker_manager.py logs

# Restart everything
python tools/docker_manager.py restart
```

**Model selection problems:**
```bash
# Test model alias resolution
python -c "from src.config import get_model_alias; print(get_model_alias('gemini'))"
```

### Debug Mode

Enable detailed logging:
```bash
export LOG_LEVEL=DEBUG
python run_server.py
```

## 📄 License

This project is licensed under the Apache 2.0 License - see the [LICENSE](../LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Development Setup

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 🙏 Acknowledgments

- [OpenRouter](https://openrouter.ai/) for providing unified AI model access
- [Model Context Protocol](https://modelcontextprotocol.io/) for the standard
- [Anthropic](https://anthropic.com/) for Claude and MCP development

## 📞 Support

- **GitHub Issues**: [Report bugs or request features](https://github.com/slyfox1186/claude-code-openrouter/issues)
- **OpenRouter Documentation**: [OpenRouter API Docs](https://openrouter.ai/docs)
- **MCP Specification**: [Model Context Protocol](https://modelcontextprotocol.io/)

---

<div align="center">

**Made with ❤️ for the AI development community**

[![GitHub stars](https://img.shields.io/github/stars/slyfox1186/claude-code-openrouter.svg?style=social)](https://github.com/slyfox1186/claude-code-openrouter/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/slyfox1186/claude-code-openrouter.svg?style=social)](https://github.com/slyfox1186/claude-code-openrouter/network)

</div>