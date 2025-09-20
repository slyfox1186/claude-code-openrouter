#!/bin/bash
# Add OpenRouter MCP Docker server to Claude Code

echo "🚀 Setting up OpenRouter MCP connection..."

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found. Please create one with your OPENROUTER_API_KEY."
    exit 1
fi

# Load API key from .env file
export OPENROUTER_API_KEY=$(grep "^OPENROUTER_API_KEY=" .env | cut -d'=' -f2- | tr -d '"'"'")

if [ -z "$OPENROUTER_API_KEY" ]; then
    echo "❌ Error: OPENROUTER_API_KEY not found in .env file"
    exit 1
fi

echo "✅ API key loaded successfully"

# Ensure the container is running via docker-compose
echo "🐳 Ensuring OpenRouter container is running..."
docker-compose -f docker/docker-compose.yml up -d

# Wait a moment for container to be ready
sleep 2

# Check if container is running
if ! docker ps | grep -q "openrouter"; then
    echo "❌ Error: OpenRouter container is not running"
    echo "Try: python3 tools/docker_manager.py start"
    exit 1
fi

echo "✅ Container is running"

# Add the MCP server to Claude Code
echo "🔗 Adding MCP server to Claude Code..."
claude mcp add openrouter-docker -s user -- docker exec -i openrouter python3 -m src.server

if [ $? -eq 0 ]; then
    echo "✅ MCP server added successfully!"
    echo "You can now use OpenRouter models in Claude Code"
else
    echo "❌ Error: Failed to add MCP server"
    exit 1
fi