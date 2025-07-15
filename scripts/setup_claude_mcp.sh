#!/usr/bin/env bash

# OpenRouter MCP Setup Script
# This script sets up the OpenRouter MCP connection for Claude Code

set -e  # Exit on any error

# Function to show usage
show_usage() {
    echo "Usage: $0 [COMMAND] [TARGET_DIR]"
    echo ""
    echo "Commands:"
    echo "  setup     Set up MCP connection (default)"
    echo "  stop      Stop the OpenRouter container"
    echo "  build     Build the OpenRouter Docker image"
    echo "  start     Start the OpenRouter container"
    echo "  restart   Restart the OpenRouter container"
    echo "  status    Check container status"
    echo "  logs      View container logs"
    echo ""
    echo "Examples:"
    echo "  $0                    # Setup MCP connection"
    echo "  $0 setup              # Setup MCP connection"
    echo "  $0 stop               # Stop container"
    echo "  $0 build              # Build Docker image"
    echo "  $0 start              # Start container"
    echo "  $0 setup /path/to/dir # Setup and cd to directory"
}

# Function to get project directory
get_project_dir() {
    echo "${OPENROUTER_DIR:-$(dirname "$(dirname "$(realpath "$0")")")}"
}

# Function to manage Docker container
docker_command() {
    local cmd="$1"
    local project_dir=$(get_project_dir)
    
    cd "$project_dir"
    
    case "$cmd" in
        "stop")
            echo "🛑 Stopping OpenRouter container..."
            python tools/docker_manager.py stop
            ;;
        "build")
            echo "🏗️ Building OpenRouter Docker image..."
            python tools/docker_manager.py build
            ;;
        "start")
            echo "🚀 Starting OpenRouter container..."
            python tools/docker_manager.py start
            ;;
        "restart")
            echo "🔄 Restarting OpenRouter container..."
            python tools/docker_manager.py restart
            ;;
        "status")
            echo "📊 Checking OpenRouter container status..."
            python tools/docker_manager.py status
            ;;
        "logs")
            echo "📋 Viewing OpenRouter container logs..."
            python tools/docker_manager.py logs
            ;;
        *)
            echo "❌ Unknown command: $cmd"
            show_usage
            return 1
            ;;
    esac
}

# Function to setup OpenRouter MCP and start Claude Code
setup_claude_mcp() {
    local target_dir="${1:-$(pwd)}"
    local openrouter_dir=$(get_project_dir)
    
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
        claude mcp add openrouter-docker -s user -- docker exec -i "$CONTAINER_NAME" python3 -m src.server
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
    
    # Change to target directory only if it exists and is a directory
    if [ -d "$target_dir" ]; then
        echo "📁 Changing to target directory: $target_dir"
        cd "$target_dir"
    else
        echo "📁 Staying in current directory: $(pwd)"
    fi
    
    # Start Claude Code
    echo
    echo "🚀 Claude has been setup successfully!"
}

# Main script logic
main() {
    local command="${1:-setup}"
    local target_dir="$2"
    
    case "$command" in
        "setup"|"")
            setup_claude_mcp "$target_dir"
            ;;
        "stop"|"build"|"start"|"restart"|"status"|"logs")
            docker_command "$command"
            ;;
        "help"|"-h"|"--help")
            show_usage
            ;;
        *)
            # If the first argument looks like a directory path, treat it as setup with target directory
            if [ -d "$command" ] || [[ "$command" == /* ]] || [[ "$command" == ~* ]]; then
                setup_claude_mcp "$command"
            else
                echo "❌ Unknown command: $command"
                show_usage
                return 1
            fi
            ;;
    esac
}

# If script is run directly (not sourced)
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    main "$@"
fi