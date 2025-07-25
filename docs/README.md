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
cat > .env << 'EOF'
# OpenRouter API Configuration
OPENROUTER_API_KEY=sk-or-v1-your_actual_api_key_here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# Default Model Settings
DEFAULT_MODEL=deepseek/deepseek-r1-0528
DEFAULT_TEMPERATURE=0.7
DEFAULT_MAX_TOKENS=1048576

# Tool Configuration
ENABLE_WEB_SEARCH=true
FORCE_INTERNET_SEARCH=true

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

### Step 5: Install Claude Code Command (Optional)
For enhanced multi-model collaboration, copy the command script:
```bash
# Create Claude commands directory if it doesn't exist
mkdir -p ~/.claude/commands

# Copy the multi-model protocol command
cp examples/call-openrouter.md ~/.claude/commands/

# Now you can use '/call-openrouter' in Claude Code for collaborative workflows
```

## 🔑 Get Your API Key

1. Go to [OpenRouter.ai](https://openrouter.ai/)
2. Sign up and get an API key
3. Add it to your `.env` file:
   ```
   OPENROUTER_API_KEY=your_key_here
   ```

## 🎯 What You Get

- **400+ AI Models**: DeepSeek R1, GPT-4, Gemini Pro Preview, Qwen3 Coder, Kimi K2, Grok 4, and hundreds more
- **Large File Support**: Send multiple large files (1,048,576 token limit) without errors
- **Web Search Integration**: Gemini automatically searches the internet for current information
- **Conversation Memory**: Continue conversations across multiple requests with full context
- **Model Switching**: Change models mid-conversation seamlessly
- **Multi-Model Collaboration**: Use `/call-openrouter` command for structured model collaboration workflows
- **Easy Management**: Interactive Docker manager for build/start/logs/shell
- **No Duplicates**: Single persistent container (no more container proliferation)

## 💬 Usage Examples

**Chat with different models:**
```bash
# Use DeepSeek R1 (default) - great for reasoning and analysis
openrouter-docker - chat (prompt: "Explain quantum computing concepts")

# Use Gemini 2.5 Pro Preview with automatic web search for current info
openrouter-docker - chat (model: "gemini", prompt: "What are the latest AI developments in 2025?")

# Use Qwen3 Coder for programming tasks and code generation
openrouter-docker - chat (model: "qwen", prompt: "Write a Python function to sort a dictionary by values")

# Use Kimi K2 by Moonshot AI for advanced reasoning
openrouter-docker - chat (model: "kimi", prompt: "Analyze this complex system architecture")

# Use Grok 4 by X.AI for creative and analytical tasks
openrouter-docker - chat (model: "grok", prompt: "Help me brainstorm innovative solutions")

# Continue previous conversation with context
openrouter-docker - chat (continuation_id: "uuid-from-previous", prompt: "Can you elaborate on that?")
```

**Attach files for analysis:**
```bash
# Send multiple large code files to any model (1M+ tokens supported!)
openrouter-docker - chat (model: "gemini", files: ["/path/to/main.py", "/path/to/config.json"], prompt: "Review this codebase for security vulnerabilities")

# Analyze documentation with web search for current best practices
openrouter-docker - chat (model: "gemini", files: ["/path/to/README.md"], prompt: "Summarize this project and compare with 2025 industry standards")

# Programming help with Qwen3 Coder
openrouter-docker - chat (model: "qwen", files: ["/path/to/broken_script.py"], prompt: "Debug this code and suggest improvements")

# Control web search behavior manually when needed
openrouter-docker - chat (model: "gemini", force_internet_search: false, prompt: "Explain basic programming concepts without external references")
```

**Multi-Model Collaboration:**
```bash
# Use the collaborative workflow command in Claude Code
/call-openrouter

# This initiates a structured workflow:
# 1. Gemini Pro 2.5 creates initial proposal
# 2. DeepSeek R1 refines and improves the plan
# 3. Qwen3 Coder provides tie-breaking if needed
# 4. Automatic implementation of the agreed solution
```

## 🤖 Available Models

Just use simple names:

- `gemini` → Google Gemini 2.5 Pro Preview (with web search)
- `deepseek` → DeepSeek R1 (reasoning & analysis)
- `qwen` → Qwen3 Coder (programming tasks)
- `kimi` → Moonshot Kimi K2 (advanced reasoning)
- `grok` → X.AI Grok 4 (creative & analytical)
- Plus 400+ other models available by full name

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
- Fixed with 1,048,576 token limit (1M+ tokens supported)
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
