#!/bin/bash

# Install script for claude_mcp function

echo "🛠️  Installing claude_mcp function..."

# Detect shell
if [ -n "$ZSH_VERSION" ]; then
    SHELL_RC="$HOME/.zshrc"
    SHELL_NAME="zsh"
elif [ -n "$BASH_VERSION" ]; then
    SHELL_RC="$HOME/.bashrc"
    SHELL_NAME="bash"
else
    echo "❌ Unsupported shell. Please manually add the function to your shell profile."
    exit 1
fi

echo "📝 Detected shell: $SHELL_NAME"
echo "📁 Adding function to: $SHELL_RC"

# Check if function already exists
if grep -q "claude_mcp()" "$SHELL_RC" 2>/dev/null; then
    echo "⚠️  Function already exists in $SHELL_RC"
    read -p "Do you want to replace it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Installation cancelled"
        exit 1
    fi
    
    # Remove existing function
    sed -i '/# Function to quickly setup OpenRouter MCP and start Claude Code/,/^}/d' "$SHELL_RC"
    sed -i '/^claude_mcp() {/,/^}/d' "$SHELL_RC"
fi

# Add function to shell profile
echo "" >> "$SHELL_RC"
echo "# OpenRouter MCP Claude Code Function" >> "$SHELL_RC"
cat examples/claude_mcp_function.sh >> "$SHELL_RC"

echo "✅ Function installed successfully!"
echo ""
echo "To use the function, either:"
echo "1. Restart your terminal, or"
echo "2. Run: source $SHELL_RC"
echo ""
echo "Usage:"
echo "  claude_mcp                    # Setup MCP and start Claude in current directory"
echo "  claude_mcp /path/to/project   # Setup MCP and start Claude in specified directory"
echo ""
echo "Example:"
echo "  claude_mcp ~/my-project"