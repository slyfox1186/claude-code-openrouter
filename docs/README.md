# OpenRouter MCP Server

<div align="center">

[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://www.docker.com/)
[![OpenRouter](https://img.shields.io/badge/OpenRouter-400%2B%20Models-orange.svg)](https://openrouter.ai/)

**Use 400+ AI models (Claude, GPT-4, Gemini, etc.) directly in Claude Code**

</div>

## 🚀 Quick Start

**Get started in 3 commands:**

```bash
git clone https://github.com/slyfox1186/claude-code-openrouter.git
cd claude-code-openrouter
cp .env.example .env
```

**Add your OpenRouter API key to `.env`**, then run:

```bash
docker build -t openrouter:latest -f docker/Dockerfile .
docker run -d --name openrouter --env-file .env -v "$HOME:/host$HOME:ro" --restart unless-stopped openrouter:latest
claude mcp add openrouter-docker -s user -- docker exec -i openrouter python3 -m src.server
```

**Done!** Now you can use any OpenRouter model in Claude Code.

## 🔑 Get Your API Key

1. Go to [OpenRouter.ai](https://openrouter.ai/)
2. Sign up and get an API key
3. Add it to your `.env` file:
   ```
   OPENROUTER_API_KEY=your_key_here
   ```

## 🎯 What You Get

- **400+ AI Models**: Claude Opus, GPT-4, Gemini Pro, and hundreds more
- **File Attachments**: Send files to any model and get analysis
- **Conversation Memory**: Continue conversations across multiple requests
- **Model Switching**: Change models mid-conversation

## 💬 Usage Examples

**Chat with different models:**
```bash
# Use Gemini Pro
openrouter-docker - chat (model: "gemini", prompt: "Explain quantum computing")

# Switch to Claude Opus for creative tasks
openrouter-docker - chat (model: "claude-opus", prompt: "Write a short story")

# Continue previous conversation
openrouter-docker - chat (continuation_id: "uuid-from-previous", prompt: "Tell me more")
```

**Attach files for analysis:**
```bash
# Send code files to any model
openrouter-docker - chat (model: "gemini", files: ["/path/to/code.py"], prompt: "Review this code")
```

## 🤖 Available Models

Just use simple names:

- `gemini` → Google Gemini 2.5 Pro
- `claude` → Claude Sonnet 4
- `claude-opus` → Claude Opus 4  
- `gpt-4` → OpenAI GPT-4
- `kimi` → Moonshot Kimi K2

## 🛠️ Management Commands

**Check status:**
```bash
docker ps | grep openrouter
```

**View logs:**
```bash
docker logs openrouter
```

**Restart if needed:**
```bash
docker restart openrouter
```

**Remove and reinstall:**
```bash
claude mcp remove openrouter-docker
docker stop openrouter && docker rm openrouter
# Then run the setup commands again
```

## ⚠️ Troubleshooting

**Container not running?**
```bash
docker restart openrouter
```

**MCP connection issues?**
```bash
claude mcp remove openrouter-docker
claude mcp add openrouter-docker -s user -- docker exec -i openrouter python3 -m src.server
```

**Still having issues?**
- Check your API key in `.env`
- Make sure Docker is running
- [Open an issue](https://github.com/slyfox1186/claude-code-openrouter/issues)

## 📄 License

Apache 2.0 License - see [LICENSE](../LICENSE)

---

<div align="center">

**Made with ❤️ for Claude Code users**

[![GitHub stars](https://img.shields.io/github/stars/slyfox1186/claude-code-openrouter.svg?style=social)](https://github.com/slyfox1186/claude-code-openrouter/stargazers)

</div>