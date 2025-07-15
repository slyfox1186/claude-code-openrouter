#!/bin/bash
# Run script for OpenRouter MCP Server

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please create it with your OPENROUTER_API_KEY"
    exit 1
fi

# Source environment variables
source .env

if [ -z "$OPENROUTER_API_KEY" ]; then
    echo "❌ OPENROUTER_API_KEY not set in .env file"
    exit 1
fi

echo "Starting OpenRouter MCP Server with Docker..."

# Run with docker-compose
docker-compose -f docker/docker-compose.yml up

echo "OpenRouter MCP Server stopped."