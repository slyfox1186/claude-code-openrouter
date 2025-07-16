#!/bin/bash
# MCP Server Wrapper Script
# This script ensures the MCP server stays connected properly

# Check if container is running
if ! docker ps | grep -q "openrouter"; then
    echo "ERROR: OpenRouter container is not running" >&2
    exit 1
fi

# Execute the server with proper stdin handling
exec docker exec -i openrouter python3 -m src.server