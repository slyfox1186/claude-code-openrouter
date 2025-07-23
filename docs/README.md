# OpenRouter MCP Server

<div align="center">

[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://www.docker.com/)
[![OpenRouter](https://img.shields.io/badge/OpenRouter-400%2B%20Models-orange.svg)](https://openrouter.ai/)

**Use 400+ AI models (Claude, GPT-4, Gemini, etc.) directly in Claude Code**

</div>

## 🚀 Quick Start

**Get started in 4 simple steps:**

### Step 1: Clone and Setup
```bash
git clone https://github.com/slyfox1186/claude-code-openrouter.git
cd claude-code-openrouter
```

### Step 2: Configure API Key
Create a `.env` file with your OpenRouter API key:
```bash
# Create .env file
cat > .env << EOF
# OpenRouter API Configuration
OPENROUTER_API_KEY=sk-or-v1-your_actual_api_key_here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# Default Model Settings
DEFAULT_MODEL=deepseek/deepseek-r1-0528
DEFAULT_TEMPERATURE=0.7
DEFAULT_MAX_TOKENS=1000000

# Tool Configuration
ENABLE_WEB_SEARCH=true

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=openrouter_mcp.log

# Optional: Rate limiting
RATE_LIMIT_REQUESTS_PER_MINUTE=60

# Docker Compose Bake delegation for better build performance
COMPOSE_BAKE=true
EOF
```

**Replace `sk-or-v1-your_actual_api_key_here` with your actual OpenRouter API key!**

### Step 3: Build and Start Container
```bash
# Make scripts executable
chmod +x tools/docker_manager.py add_mcp.sh

# Build and start the container
python3 tools/docker_manager.py build
python3 tools/docker_manager.py start
```

### Step 4: Connect to Claude Code
```bash
# Add MCP server to Claude Code
./add_mcp.sh
```

**Done!** Now you can use any OpenRouter model in Claude Code with large file support.

## 🔑 Get Your API Key

1. Go to [OpenRouter.ai](https://openrouter.ai/)
2. Sign up and get an API key
3. Add it to your `.env` file:
   ```
   OPENROUTER_API_KEY=your_key_here
   ```

## 🎯 What You Get

- **400+ AI Models**: DeepSeek R1, GPT-4, Gemini Pro, and hundreds more
- **Large File Support**: Send multiple large files (1M token limit) without errors
- **Conversation Memory**: Continue conversations across multiple requests with full context
- **Model Switching**: Change models mid-conversation seamlessly
- **Easy Management**: Interactive Docker manager for build/start/logs/shell
- **No Duplicates**: Single persistent container (no more container proliferation)

## 💬 Usage Examples

**Chat with different models:**
```bash
# Use DeepSeek R1 (default)
openrouter-docker - chat (prompt: "Explain quantum computing")

# Use Gemini Pro for complex analysis
openrouter-docker - chat (model: "gemini", prompt: "Analyze this algorithm")

# Continue previous conversation
openrouter-docker - chat (continuation_id: "uuid-from-previous", prompt: "Tell me more")
```

**Attach files for analysis:**
```bash
# Send multiple code files to any model (supports large files now!)
openrouter-docker - chat (model: "gemini", files: ["/path/to/code.py", "/path/to/config.json"], prompt: "Review this codebase")

# Analyze documentation
openrouter-docker - chat (model: "deepseek", files: ["/path/to/README.md"], prompt: "Summarize this project")
```

## 🤖 Available Models

Just use simple names:

- `gemini` → Google Gemini 2.5 Pro Preview
- `gpt-4` → OpenAI GPT-4
- `deepseek` → DeepSeek R1
- `qwen` → Qwen3 Coder

## 🛠️ Management Commands

**Check status:**
```bash
python3 tools/docker_manager.py status
```

**View logs:**
```bash
python3 tools/docker_manager.py logs
```

**Restart container:**
```bash
python3 tools/docker_manager.py restart
```

**Interactive shell:**
```bash
python3 tools/docker_manager.py shell
```

**Manual Docker commands:**
```bash
# Check container status
docker ps | grep openrouter

# View logs directly
docker logs openrouter

# Manual restart
docker restart openrouter
```

## ⚠️ Troubleshooting

**Container not running?**
```bash
python3 tools/docker_manager.py restart
```

**MCP connection issues?**
```bash
claude mcp remove openrouter-docker
./add_mcp.sh
```

**Build issues?**
```bash
python3 tools/docker_manager.py stop
python3 tools/docker_manager.py build
python3 tools/docker_manager.py start
```

**Large file attachment errors (400 Bad Request)?**
- This should be fixed with 1M token limit
- Check logs: `python3 tools/docker_manager.py logs`
- Verify container is running: `python3 tools/docker_manager.py status`

**Still having issues?**
- Check your API key in `.env` file
- Make sure Docker is running and accessible
- Run interactive mode: `python3 tools/docker_manager.py`
- [Open an issue](https://github.com/slyfox1186/claude-code-openrouter/issues)

## 📄 License

Apache 2.0 License - see [LICENSE](../LICENSE)

---

<div align="center">

**Made with ❤️ for Claude Code users**

[![GitHub stars](https://img.shields.io/github/stars/slyfox1186/claude-code-openrouter.svg?style=social)](https://github.com/slyfox1186/claude-code-openrouter/stargazers)

</div>