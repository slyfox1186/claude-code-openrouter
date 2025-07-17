#!/bin/bash
# Add OpenRouter MCP Docker server to Claude Code

# Load API key from .env file
export OPENROUTER_API_KEY=$(grep "^OPENROUTER_API_KEY=" .env | cut -d'=' -f2- | tr -d '"'"'")

# Add the MCP server to Claude Code
claude mcp add openrouter-docker -s user -- docker run -i --rm -e OPENROUTER_API_KEY="$OPENROUTER_API_KEY" -v $HOME:"/host$HOME":ro openrouter:latest python3 -m src.server