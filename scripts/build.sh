#!/bin/bash
# Build script for OpenRouter MCP Server

# Change to the project root directory
cd "$(dirname "$0")/.."

echo "Building OpenRouter MCP Server Docker image..."

# Build the Docker image
docker build -t openrouter:latest -f docker/Dockerfile .

if [ $? -eq 0 ]; then
    echo "✅ Docker image built successfully: openrouter:latest"
    echo ""
    echo "To run with docker-compose:"
    echo "  docker-compose -f docker/docker-compose.yml up -d"
    echo ""
    echo "To run with docker directly:"
    echo "  docker run -it --rm -e OPENROUTER_API_KEY='$OPENROUTER_API_KEY' -v $HOME:/host$HOME:ro openrouter:latest"
    echo ""
    echo "To run interactively for MCP:"
    echo "  docker run -i --rm -e OPENROUTER_API_KEY='$OPENROUTER_API_KEY' -v $HOME:/host$HOME:ro openrouter:latest"
else
    echo "❌ Docker build failed"
    exit 1
fi