#!/bin/bash

# Add this function to your ~/.bashrc or ~/.zshrc file

# Function to quickly setup OpenRouter MCP and start Claude Code
claude_mcp() {
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
    
    # Change to openrouter directory temporarily
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
    
    # Remove existing MCP connection (ignore errors)
    # echo "🗑️  Removing existing MCP connection..."
    # claude mcp remove openrouter-docker 2>/dev/null || true
    
    # Add new MCP connection
    echo "🔗 Adding new MCP connection..."
    claude mcp add openrouter-docker -s user -- docker run -i --rm -e OPENROUTER_API_KEY="$OPENROUTER_API_KEY" -v $HOME:"/host$HOME":ro openrouter:latest
    
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
    echo "🚀 Starting Claude Code..."
    claude
}

# Usage examples:
# claude_mcp                    # Setup MCP and start Claude in current directory
# claude_mcp /path/to/project   # Setup MCP and start Claude in specified directory
