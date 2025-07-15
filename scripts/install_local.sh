#!/usr/bin/env bash

# OpenRouter MCP Local Installation Script
# This script makes the setup script accessible from user's local bin

set -e

# Get the project directory
PROJECT_DIR="$(dirname "$(dirname "$(realpath "$0")")")"
SETUP_SCRIPT="$PROJECT_DIR/scripts/setup_claude_mcp.sh"

# Check if setup script exists
if [ ! -f "$SETUP_SCRIPT" ]; then
    echo "❌ Error: Setup script not found at $SETUP_SCRIPT"
    exit 1
fi

# Create user's local bin directory if it doesn't exist
LOCAL_BIN="$HOME/.local/bin"
mkdir -p "$LOCAL_BIN"

# Create local link
LOCAL_LINK="$LOCAL_BIN/openrouter-mcp"

echo "🔧 Installing OpenRouter MCP local command..."
echo "📁 Project directory: $PROJECT_DIR"
echo "🔗 Creating local link: $LOCAL_LINK"

# Create the local command
cat > "$LOCAL_LINK" <<EOF
#!/usr/bin/env bash
# OpenRouter MCP Local Command
export OPENROUTER_DIR="$PROJECT_DIR"
exec "$SETUP_SCRIPT" "\$@"
EOF

# Make it executable
chmod +x "$LOCAL_LINK"

echo "✅ Installation complete!"
echo ""
echo "You can now use 'openrouter-mcp' from anywhere:"
echo "  openrouter-mcp build"
echo "  openrouter-mcp setup"
echo "  openrouter-mcp status"
echo "  openrouter-mcp help"
echo ""
echo "Note: Make sure $LOCAL_BIN is in your PATH"
echo "Add this to your ~/.bashrc or ~/.zshrc:"
echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
echo ""
echo "To uninstall: rm $LOCAL_LINK"