#!/usr/bin/env bash

# OpenRouter MCP Setup Script
# This script sets up the OpenRouter MCP connection for Claude Code

set -e  # Exit on any error

# Function to setup OpenRouter MCP and start Claude Code
setup_claude_mcp() {
    local target_dir="${1:-$(pwd)}"
    local openrouter_dir="$HOME/tmp/openrouter-connect-improved"
    
    echo "🔧 Setting up OpenRouter MCP connection..."
    
    # Check if openrouter directory exists
    if [ ! -d "$openrouter_dir" ]; then
        echo "❌ Error: OpenRouter directory not found at $openrouter_dir"
        return 1
    fi
    
    # Check if .env file exists
    if [ ! -f "$openrouter_dir/.env" ]; then
        echo "❌ Error: .env file not found at $openrouter_dir/.env"
        return 1
    fi
    
    # Store current directory
    local original_dir=$(pwd)
    
    # Change to openrouter directory
    cd "$openrouter_dir"
    
    # Extract API key from .env file
    echo "🔑 Extracting API key from .env file..."
    export OPENROUTER_API_KEY=$(grep "^OPENROUTER_API_KEY=" .env | cut -d'=' -f2- | tr -d '"'"'")
    
    if [ -z "$OPENROUTER_API_KEY" ]; then
        echo "❌ Error: OPENROUTER_API_KEY not found in .env file"
        cd "$original_dir"
        return 1
    fi
    
    echo "✅ API key extracted successfully"

    # Check if MCP connection already exists
    if claude mcp list | grep -q "openrouter-docker"; then
        echo "🔄 MCP connection 'openrouter-docker' already exists, removing old one..."
        claude mcp remove openrouter-docker
    fi
    
    # Check if container already exists
    CONTAINER_NAME="openrouter"
    
    if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        echo "🔄 Container '${CONTAINER_NAME}' already exists, reusing..."
        
        # Check if it's running
        if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
            echo "✅ Container '${CONTAINER_NAME}' is already running"
        else
            echo "🚀 Starting existing container '${CONTAINER_NAME}'..."
            docker start "$CONTAINER_NAME"
        fi
        
        # Use existing container for MCP
        echo "🔗 Adding MCP connection to existing container..."
        claude mcp add openrouter-docker -s user -- docker exec -i "$CONTAINER_NAME" python3 server.py
    else
        echo "🔗 Creating new MCP connection with new container..."
        claude mcp add openrouter-docker -s user -- docker run -i --name "$CONTAINER_NAME" -e OPENROUTER_API_KEY="$OPENROUTER_API_KEY" -v $HOME:"/host$HOME":ro openrouter:latest
    fi
    
    if [ $? -eq 0 ]; then
        echo "✅ MCP connection added successfully"
    else
        echo "❌ Error: Failed to add MCP connection"
        cd "$original_dir"
        return 1
    fi
    
    # Change to target directory
    echo "📁 Changing to target directory: $target_dir"
    cd "$target_dir"
    
    # Start Claude Code
    echo
    echo "🚀 Claude has been setup successfully!"
}

# If script is run directly (not sourced)
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    setup_claude_mcp "$@"
fi
