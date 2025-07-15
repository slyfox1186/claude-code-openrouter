# OpenRouter MCP Docker Manager

A comprehensive Python-based Docker management tool for the OpenRouter MCP Server with enhanced performance through Docker Compose Bake delegation.

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose installed
- Python 3.6+ (for the management script)
- OpenRouter API key

### Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd openrouter-connect
```

2. **Configure environment**
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your OpenRouter API key
nano .env  # or use your preferred editor
```

Edit the `.env` file and replace the placeholder with your actual OpenRouter API key:
```bash
# OpenRouter API Configuration
OPENROUTER_API_KEY=sk-or-v1-your_actual_api_key_here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
# ... rest of the configuration
```

3. **Make the script executable**
```bash
chmod +x docker_manager.py
```

4. **Get your OpenRouter API Key**
   - Visit [OpenRouter.ai](https://openrouter.ai)
   - Sign up or log in to your account  
   - Go to your API Keys section
   - Create a new API key
   - Copy the key that starts with `sk-or-v1-...`

## 🎯 Usage

### Interactive Mode (Recommended)
```bash
./docker_manager.py
```

This launches a beautiful, color-coded interactive menu with the following options:

```
==================================================
    OpenRouter MCP Docker Manager
==================================================

1) Status      - Check container status
2) Start       - Start container
3) Stop        - Stop and remove container
4) Restart     - Full restart (stop + rebuild + start)
5) Build       - Build/rebuild image only
6) Logs        - View container logs (Ctrl+C to exit)
7) Shell       - Interactive shell in container
8) Quit        - Exit script

==================================================
```

### Command Line Mode
For automation and scripting:

```bash
# Check status
./docker_manager.py status

# Start container
./docker_manager.py start

# Stop container
./docker_manager.py stop

# Full restart (recommended for updates)
./docker_manager.py restart

# Build image only
./docker_manager.py build

# View logs (Ctrl+C to exit)
./docker_manager.py logs

# Interactive shell
./docker_manager.py shell
```

## 🔧 Features

### ✅ **Fixed Issues from Shell Version**
- **Exit from logs**: Press `Ctrl+C` to exit log viewer
- **Better formatting**: Clean, spaced output with visual separators
- **Enhanced colors**: Rich color scheme for better readability

### 🎨 **Visual Enhancements**
- **Color-coded messages**: 
  - 🟢 **INFO** (Green): General information
  - 🟡 **WARN** (Yellow): Warnings
  - 🔴 **ERROR** (Red): Errors
  - 🔵 **SUCCESS** (Cyan): Success messages
  - 🔷 **DOCKER** (Blue): Docker operations
- **Visual separators**: Clean lines between operations
- **Status indicators**: Clear container and image status display

### 🛡️ **Enhanced Capabilities**
- **Robust error handling**: Comprehensive error checking and user feedback
- **Dependency checking**: Automatically detects missing Docker/Docker Compose
- **Interrupt handling**: Graceful handling of Ctrl+C throughout
- **Type safety**: Proper Python typing and data structures
- **Performance**: Docker Compose Bake delegation for faster builds

### ⚡ **Docker Compose Bake Delegation**
This tool uses `COMPOSE_BAKE=true` for enhanced build performance:
- **Parallel building**: Build multiple images simultaneously
- **Deduplicated context transfers**: Avoid redundant file transfers
- **Advanced caching**: Faster build times through better caching
- **Multi-platform support**: Build for multiple architectures

## 📊 Container Status Information

The status command shows detailed information:
- Container existence and running state
- Container status and uptime
- Port mappings
- Image availability
- Build timestamp information

## 🔒 Security

- **API Key Protection**: Your OpenRouter API key is securely stored in `.env` file
- **Git Ignore**: `.env` files are automatically excluded from version control
- **Template Available**: Use `.env.example` as a template for new setups

## 🐳 Docker Architecture

The system uses:
- **Base Image**: `python:3.12-slim`
- **Non-root User**: Runs as `mcpuser` for security
- **Volume Mounts**: 
  - `/home/jman:/host/home/jman:ro` (read-only home directory access)
  - `/tmp:/host/tmp:ro` (read-only tmp access)
- **Environment Variables**: Configured via `.env` file
- **Compose Bake**: Enhanced build performance

## 🔗 Connecting to Claude Code

### Step 1: Build the Docker Image

First, make sure your Docker image is built:

```bash
./docker_manager.py build
```

### Step 2: Add MCP Server to Claude Code

#### Method 1: Using Environment Variable (Recommended)

```bash
# Navigate to the project directory
cd /path/to/openrouter-connect

# Method A: Source the .env file directly
source .env
claude mcp add openrouter-docker -s user -- docker run -i --rm -e OPENROUTER_API_KEY="$OPENROUTER_API_KEY" -v $HOME:"/host$HOME":ro openrouter:latest
```

**Alternative if sourcing doesn't work:**
```bash
# Method B: Manual extraction (more reliable)
export OPENROUTER_API_KEY=$(grep "^OPENROUTER_API_KEY=" .env | cut -d'=' -f2- | tr -d '"'"'")
echo "API Key: $OPENROUTER_API_KEY"  # Verify it's not empty
claude mcp add openrouter-docker -s user -- docker run -i --rm -e OPENROUTER_API_KEY="$OPENROUTER_API_KEY" -v $HOME:"/host$HOME":ro openrouter:latest
```

#### Method 2: Direct API Key (Replace with your actual key)

```bash
claude mcp add openrouter-docker -s user -- docker run -i --rm -e OPENROUTER_API_KEY='sk-or-v1-YOUR_ACTUAL_API_KEY_HERE' -v $HOME:"/host$HOME":ro openrouter:latest
```

**Important**: 
- Replace `sk-or-v1-YOUR_ACTUAL_API_KEY_HERE` with your actual OpenRouter API key
- Make sure to use your actual API key from your `.env` file
- The `$HOME` variable will automatically use your home directory path

### Step 3: Verify Connection

Test that the MCP server is properly connected:

```bash
# Check if the server is listed
claude mcp list

# Test the connection
claude mcp status openrouter-docker
```

### Complete Example for GitHub Users

Here's a complete step-by-step example for someone downloading this project from GitHub:

```bash
# 1. Clone and setup
git clone https://github.com/your-username/openrouter-connect.git
cd openrouter-connect

# 2. Configure your API key
cp .env.example .env
nano .env  # Add your OpenRouter API key

# 3. Make script executable and build
chmod +x docker_manager.py
./docker_manager.py build

# 4. Test the setup
./docker_manager.py start
./docker_manager.py status

# 5. Connect to Claude Code
export OPENROUTER_API_KEY=$(grep "^OPENROUTER_API_KEY=" .env | cut -d'=' -f2- | tr -d '"'"'")
claude mcp add openrouter-docker -s user -- docker run -i --rm -e OPENROUTER_API_KEY="$OPENROUTER_API_KEY" -v $HOME:"/host$HOME":ro openrouter:latest

# 6. Verify connection
claude mcp list
claude mcp status openrouter-docker
```

### Important Notes for GitHub Users

- **No hardcoded paths**: All commands use relative paths or standard environment variables
- **Automatic home directory**: Uses `$HOME` variable that works on any system
- **Secure API key**: Your API key stays in your local `.env` file (never committed to git)
- **Cross-platform**: Works on Linux, macOS, and Windows (with WSL)

### Configuration in Claude Code

After adding the MCP server, you can use it in Claude Code by referencing the OpenRouter tools:

```python
# The MCP server provides these tools:
# - chat: Send messages to OpenRouter models
# - file context: Include file contents in chat
# - image context: Include images in chat (for vision models)
```

## 📝 Example Usage Workflow

1. **Initial Setup**:
```bash
./docker_manager.py build    # Build the image
./docker_manager.py start    # Start the container
./docker_manager.py status   # Verify it's running
```

2. **Development Workflow**:
```bash
./docker_manager.py restart  # After making changes
./docker_manager.py logs     # Monitor output
./docker_manager.py shell    # Debug if needed
```

3. **Maintenance**:
```bash
./docker_manager.py stop     # Stop when done
./docker_manager.py status   # Check status
```

## 🛠️ Troubleshooting

### Common Issues

1. **Container won't start**:
   - Check `.env` file exists and has valid API key
   - Verify Docker is running
   - Check logs: `./docker_manager.py logs`

2. **Build fails**:
   - Ensure Docker Compose is installed
   - Check internet connection for package downloads
   - Try: `./docker_manager.py stop` then `./docker_manager.py build`

3. **Permission errors**:
   - Ensure script is executable: `chmod +x docker_manager.py`
   - Check Docker permissions for your user

4. **API key errors**:
   - Verify `.env` file format: `OPENROUTER_API_KEY=your_key_here`
   - No spaces around the `=` sign
   - No quotes around the key

### Debug Mode

For detailed debugging:
```bash
# View container logs
./docker_manager.py logs

# Interactive shell access
./docker_manager.py shell

# Check detailed status
./docker_manager.py status
```

## 🤝 Contributing

When contributing:
1. Never commit `.env` files
2. Update `.env.example` for new configuration options
3. Test both interactive and command-line modes
4. Ensure Docker Compose Bake compatibility

## 📄 License

[Your License Here]

---

**Note**: This tool automatically enables Docker Compose Bake delegation (`COMPOSE_BAKE=true`) for improved build performance. This requires Docker Compose version 2.10 or higher.