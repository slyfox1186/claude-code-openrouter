# OpenRouter MCP Server

<div align="center">

[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://www.docker.com/)
[![OpenRouter](https://img.shields.io/badge/OpenRouter-400%2B%20Models-orange.svg)](https://openrouter.ai/)

**Use 400+ AI models (Claude, GPT-4, Gemini, etc.) directly in Claude Code**

*Intelligent model selection • 1M+ token support • Multi-model collaboration*

</div>

## 🚀 Complete Setup Guide

**Follow these steps exactly to get up and running in 5 minutes:**

### Prerequisites
- **Docker** installed and running ([Get Docker](https://docs.docker.com/get-docker/))
- **Python 3.8+** installed ([Get Python](https://www.python.org/downloads/))
- **Claude Code** desktop app ([Get Claude Code](https://claude.ai/code))
- **OpenRouter API key** ([Get API Key](https://openrouter.ai/))

### Step 1: Clone Repository
```bash
git clone https://github.com/slyfox1186/claude-code-openrouter.git
cd claude-code-openrouter
```

### Step 2: Get Your OpenRouter API Key
1. Go to [OpenRouter.ai](https://openrouter.ai/)
2. Sign up or log in to your account
3. Navigate to "Keys" in your dashboard
4. Create a new API key
5. Copy the key (starts with `sk-or-v1-`)

### Step 3: Configure Environment
Create your `.env` file with your API key:
```bash
cat > .env << 'EOF'
# Required: Your OpenRouter API Key
OPENROUTER_API_KEY=sk-or-v1-your_actual_api_key_here

# OpenRouter API Configuration
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# Default Model Settings
DEFAULT_MODEL=z-ai/glm-4.5
DEFAULT_TEMPERATURE=0.7
DEFAULT_MAX_TOKENS=1048576
DEFAULT_MAX_REASONING_TOKENS=16384

# Tool Configuration
ENABLE_WEB_SEARCH=true
FORCE_INTERNET_SEARCH=true

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=openrouter_mcp.log

# Rate Limiting
RATE_LIMIT_REQUESTS_PER_MINUTE=60

# MCP Transport
MAX_MESSAGE_SIZE=10485760
MAX_CONCURRENT_REQUESTS=10
EOF
```

**⚠️ IMPORTANT:** Replace `sk-or-v1-your_actual_api_key_here` with your actual OpenRouter API key!

### Step 4: Build and Start
```bash
# Make scripts executable
chmod +x tools/docker_manager.py add_mcp.sh

# Build and start the container in one command
python3 tools/docker_manager.py build && python3 tools/docker_manager.py start
```

### Step 5: Connect to Claude Code
```bash
# Add MCP server to Claude Code
./add_mcp.sh
```

### Step 6: Verify Setup
Test that everything is working:
```bash
# Check container status
python3 tools/docker_manager.py status

# View logs (should show "Simple OpenRouter MCP Server starting...")
python3 tools/docker_manager.py logs
```

**🎉 Success!** You can now use any OpenRouter model in Claude Code.

## ✨ Key Features

### 🧠 Intelligent Model Selection
- **Context-Aware**: Automatically chooses the best model based on your request
- **Smart Qwen Handling**: `model: "qwen"` intelligently selects between qwen3-max (general) or qwen3-coder-plus (coding)
- **No More Errors**: Eliminates fuzzy matching failures with LLM-powered decisions

### 🔧 Advanced Capabilities
- **400+ AI Models**: Access to all OpenRouter models including GPT-4, Claude, Gemini, DeepSeek, etc.
- **1M+ Token Support**: Send massive files without errors (1,048,576 token limit)
- **Web Search Integration**: Gemini automatically searches for current information
- **Conversation Memory**: Continue conversations with full context preservation
- **Multi-Model Collaboration**: Use `/call-openrouter` command for structured workflows

### 🛡️ Production Ready
- **Graceful Shutdown Protection**: Survives Claude Code disconnects without breaking
- **Rate Limiting**: Built-in protection against API limits
- **Error Handling**: Comprehensive error recovery and logging
- **Docker Containerized**: Isolated, reproducible environment

## 🎯 Quick Test

Try these commands in Claude Code to verify everything works:

```bash
# Test basic functionality
openrouter-docker - chat (prompt: "Hello! Can you confirm you're working?")

# Test intelligent model selection
openrouter-docker - chat (model: "qwen", prompt: "Write a Python function to reverse a string")
# ^ Should automatically choose qwen3-coder-plus due to coding context

openrouter-docker - chat (model: "qwen", prompt: "Explain quantum computing")
# ^ Should automatically choose qwen3-max for general explanation

# Test with file attachment
openrouter-docker - chat (model: "gemini", files: ["/path/to/file.py"], prompt: "Review this code")
```

### Step 7: Install Claude Code Command (Optional)
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

- **400+ AI Models**: DeepSeek R1, GPT-4, Gemini Pro Preview, Kimi K2, Grok 4, and hundreds more
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

# Use DeepSeek Chat v3.1 (deepseek/deepseek-chat-v3.1) - latest version with 163K context
openrouter-docker - chat (model: "deepseek-v3.1", prompt: "Solve this complex problem step by step")

# Use Gemini 2.5 Pro Preview with automatic web search for current info
openrouter-docker - chat (model: "gemini", prompt: "What are the latest AI developments in 2025?")

# Use Kimi K2 for advanced reasoning and programming tasks
openrouter-docker - chat (model: "kimi", prompt: "Write a Python function to sort a dictionary by values")

# Use Kimi K2 by Moonshot AI for advanced reasoning
openrouter-docker - chat (model: "kimi", prompt: "Analyze this complex system architecture")

# Use Grok 4 by X.AI for creative and analytical tasks
openrouter-docker - chat (model: "grok", prompt: "Help me brainstorm innovative solutions")

# Use GPT-5 for latest flagship performance with 400K context window
openrouter-docker - chat (model: "gpt-5", prompt: "Analyze this complex business strategy")

# Continue previous conversation with context
openrouter-docker - chat (continuation_id: "uuid-from-previous", prompt: "Can you elaborate on that?")
```

**Attach files for analysis:**
```bash
# Send multiple large code files to any model (1M+ tokens supported!)
openrouter-docker - chat (model: "gemini", files: ["/path/to/main.py", "/path/to/config.json"], prompt: "Review this codebase for security vulnerabilities")

# Analyze documentation with web search for current best practices
openrouter-docker - chat (model: "gemini", files: ["/path/to/README.md"], prompt: "Summarize this project and compare with 2025 industry standards")

# Programming help with Kimi K2
openrouter-docker - chat (model: "kimi", files: ["/path/to/broken_script.py"], prompt: "Debug this code and suggest improvements")

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
# 3. Kimi K2 provides tie-breaking if needed
# 4. Automatic implementation of the agreed solution
```

## 🤖 Available Models

Just use simple names:

- `gemini` → Google Gemini 2.5 Pro Preview (with web search)
- `deepseek` → DeepSeek R1 (reasoning & analysis)
- `deepseek-v3.1` → DeepSeek Chat v3.1 (latest version with 163K context)
- `kimi` → Moonshot Kimi K2 (advanced reasoning)
- `grok` → X.AI Grok Code Fast 1 (fast code generation & programming)
- `gpt-5` → OpenAI GPT-5 (latest flagship model with 400K context)
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

## 🆘 Troubleshooting Guide

### Common Issues & Solutions

#### 🔧 **Setup Issues**

**"No such file or directory" when running scripts:**
```bash
# Make sure you're in the right directory
cd claude-code-openrouter

# Make scripts executable
chmod +x tools/docker_manager.py add_mcp.sh
```

**Docker not found or permission denied:**
```bash
# On Linux, add your user to docker group
sudo usermod -aG docker $USER
# Then log out and back in

# Or run with sudo (not recommended)
sudo python3 tools/docker_manager.py build
```

**Python command not found:**
```bash
# Try different Python commands
python tools/docker_manager.py build  # On some systems
py tools/docker_manager.py build      # On Windows
```

#### 🔌 **Connection Issues**

**MCP server not connecting to Claude Code:**
```bash
# Remove and re-add the MCP connection
claude mcp remove openrouter-docker
./add_mcp.sh

# Check if container is running
python3 tools/docker_manager.py status

# Restart Claude Code app completely
```

**Container won't start:**
```bash
# Full restart sequence
python3 tools/docker_manager.py stop
python3 tools/docker_manager.py build
python3 tools/docker_manager.py start

# Check for errors in logs
python3 tools/docker_manager.py logs
```

#### 🚫 **API Issues**

**OpenRouter API errors (401 Unauthorized):**
```bash
# Check your .env file has the correct API key
cat .env | grep OPENROUTER_API_KEY

# Verify your API key is valid at openrouter.ai
# Make sure it starts with 'sk-or-v1-'
```

**Rate limiting errors (429 Too Many Requests):**
```bash
# Edit .env file to reduce rate limit
echo "RATE_LIMIT_REQUESTS_PER_MINUTE=30" >> .env

# Restart container
python3 tools/docker_manager.py restart
```

**Large file errors (413 Request Too Large):**
- ✅ This is fixed in the latest version with 1M+ token support
- Update to latest: `git pull && python3 tools/docker_manager.py build && python3 tools/docker_manager.py restart`

#### 🐛 **Model Selection Issues**

**"Model not found" errors:**
```bash
# Use simple aliases instead of full model names
# ✅ Good: model: "gemini"
# ❌ Bad: model: "google/gemini-2.5-pro-preview"

# Test intelligent model selection
openrouter-docker - chat (model: "qwen", prompt: "test")
```

### 🔍 **Diagnostic Commands**

**Full system check:**
```bash
# Check all components
echo "=== Docker Status ===" && docker --version
echo "=== Container Status ===" && python3 tools/docker_manager.py status
echo "=== MCP Status ===" && claude mcp list
echo "=== Logs ===" && python3 tools/docker_manager.py logs --tail 5
```

**Reset everything:**
```bash
# Nuclear option - rebuild from scratch
python3 tools/docker_manager.py stop
docker system prune -f
python3 tools/docker_manager.py build
python3 tools/docker_manager.py start
claude mcp remove openrouter-docker
./add_mcp.sh
```

### 🆘 **Still Need Help?**

1. **Check logs first:** `python3 tools/docker_manager.py logs`
2. **Verify your .env file** has a valid OpenRouter API key
3. **Make sure Docker is running** and accessible
4. **Try the diagnostic commands** above
5. **[Open an issue](https://github.com/slyfox1186/claude-code-openrouter/issues)** with:
   - Your operating system
   - Error messages from logs
   - Steps you've already tried

## 📄 License

Apache 2.0 License - see [LICENSE](../LICENSE)

---

<div align="center">

**Made with ❤️ for Claude Code users**

[![GitHub stars](https://img.shields.io/github/stars/slyfox1186/claude-code-openrouter.svg?style=social)](https://github.com/slyfox1186/claude-code-openrouter/stargazers)

</div>
