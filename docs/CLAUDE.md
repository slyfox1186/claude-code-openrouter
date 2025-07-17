# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build/Development Commands

- **Install dependencies**: `pip install -r requirements.txt`
- **Run server directly**: `python server.py`
- **Build Docker image**: `./build.sh` or `python docker_manager.py build`
- **Start Docker container**: `./run.sh` or `python docker_manager.py start`
- **View logs**: `python docker_manager.py logs`
- **Interactive Docker shell**: `python docker_manager.py shell`

## Project Architecture

### Overview
This is a **Python-based Model Context Protocol (MCP) Server** that provides unified access to 400+ AI models through OpenRouter's API. The server acts as a bridge between MCP clients (like Claude Code) and various AI providers.

### Core Components

#### 1. Server Architecture (`server.py`)
- **JSON-RPC Protocol**: Implements MCP specification for tool communication
- **Conversation Management**: Maintains chat history with UUID-based continuation
- **Model Selection**: Smart model alias resolution (e.g., "gemini" → "google/gemini-2.5-pro")
- **Multi-modal Support**: Handles both text and image inputs for vision models

#### 2. Configuration System (`config.py`)
- **Environment Variables**: Manages API keys, model defaults, and runtime settings
- **Model Aliases**: Maps natural language names to OpenRouter model identifiers
- **Capabilities Detection**: Tracks model features (vision, function calling, large context)
- **Rate Limiting**: Configurable request and token limits

#### 3. Conversation Management (`conversation_manager.py`)
- **Persistent Storage**: JSON-based conversation history in `/tmp/openrouter_conversations`
- **Memory Cache**: In-memory caching for active conversations
- **OpenAI Format**: Converts messages to OpenAI-compatible format
- **Token Optimization**: Truncates conversation history to stay within token limits

#### 4. Docker Management (`docker_manager.py`)
- **Container Lifecycle**: Build, start, stop, restart operations
- **Interactive Features**: Log viewing, shell access, status monitoring
- **Environment Integration**: Automatic `.env` file loading and validation
- **Multi-container Support**: Handles multiple openrouter container instances

### Key Features

#### Model Access & Selection
- **400+ Models**: Access to OpenAI, Anthropic, Meta, Google, Mistral, and more
- **Smart Aliases**: Natural language model selection ("claude" → "anthropic/claude-4-sonnet")
- **Fallback Logic**: Automatic model selection based on capabilities
- **Cost Optimization**: Intelligent model routing for cost-effective operations

#### Conversation Continuity
- **UUID-based Sessions**: Each conversation gets a unique identifier
- **Persistent History**: Conversations survive server restarts
- **Context Preservation**: Maintains full conversation context across tool calls
- **Memory Management**: Automatic cleanup of old conversations

#### Development Tools
- **Multi-modal Input**: Support for text, files, and images
- **Debug Logging**: Comprehensive logging to `/tmp/openrouter_debug.log`
- **Error Handling**: Robust error recovery and reporting
- **Performance Monitoring**: Token usage tracking and optimization

### MCP Tool Interface

The server exposes these MCP tools:

1. **`chat`**: Main chat interface with conversation continuation
2. **`list_conversations`**: View all stored conversation summaries
3. **`get_conversation`**: Retrieve full conversation history
4. **`delete_conversation`**: Remove conversation from storage

### Environment Configuration

Required environment variables in `.env`:
- `OPENROUTER_API_KEY`: Your OpenRouter API key
- `DEFAULT_MODEL`: Default model (default: "deepseek/deepseek-r1-0528")
- `DEFAULT_TEMPERATURE`: Response randomness (default: 0.7)
- `LOG_LEVEL`: Logging verbosity (default: "INFO")

### Docker Deployment

- **Base Image**: Python 3.12-slim with git support
- **Security**: Runs as non-root user (mcpuser)
- **Volume Mounts**: Read-only access to host filesystem (`$HOME`, `/tmp`)
- **Interactive Mode**: Supports both daemon and interactive execution

### File Structure

```
├── server.py              # Main MCP server implementation
├── config.py              # Configuration and model management
├── conversation_manager.py # Conversation persistence
├── docker_manager.py      # Docker operations and management
├── requirements.txt       # Python dependencies
├── Dockerfile             # Container definition
├── docker-compose.yml     # Service orchestration
├── build.sh               # Build script
└── run.sh                 # Runtime script
```

### Development Workflow

1. **Setup**: Create `.env` with `OPENROUTER_API_KEY`
2. **Development**: Run `python server.py` for direct testing
3. **Containerization**: Use `./build.sh` and `./run.sh` for Docker deployment
4. **Debugging**: Monitor logs via `python docker_manager.py logs`
5. **Testing**: Use MCP clients to interact with the server

### Model Capabilities

The server automatically detects and routes based on model capabilities:
- **Vision Models**: Handle image inputs (Gemini Pro, GPT-4V)
- **Large Context**: Support extended conversations (DeepSeek R1, Gemini)
- **Function Calling**: Tool use capabilities (Gemini Pro, GPT-4)

### Performance Considerations

- **Token Management**: Automatic conversation truncation to prevent API limits
- **Caching**: In-memory conversation cache for performance
- **Logging**: Structured logging for debugging and monitoring
- **Resource Limits**: Configurable rate limiting and message size limits