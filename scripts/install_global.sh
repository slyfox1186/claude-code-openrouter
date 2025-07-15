#!/usr/bin/env bash

# OpenRouter MCP Global Installation Script
# This script makes the setup script globally accessible

set -e

# Get the project directory
PROJECT_DIR="$(dirname "$(dirname "$(realpath "$0")")")"
SETUP_SCRIPT="$PROJECT_DIR/scripts/setup_claude_mcp.sh"

# Check if setup script exists
if [ ! -f "$SETUP_SCRIPT" ]; then
    echo "❌ Error: Setup script not found at $SETUP_SCRIPT"
    exit 1
fi

# Create global link
GLOBAL_LINK="/usr/local/bin/openrouter-mcp"

echo "🔧 Installing OpenRouter MCP global command..."
echo "📁 Project directory: $PROJECT_DIR"
echo "🔗 Creating global link: $GLOBAL_LINK"

# Create the global command
sudo tee "$GLOBAL_LINK" > /dev/null <<EOF
#!/usr/bin/env bash
# OpenRouter MCP Global Command
export OPENROUTER_DIR="$PROJECT_DIR"
exec "$SETUP_SCRIPT" "\$@"
EOF

# Make it executable
sudo chmod +x "$GLOBAL_LINK"

echo "✅ Installation complete!"
echo ""
echo "You can now use 'openrouter-mcp' from anywhere:"
echo "  openrouter-mcp build"
echo "  openrouter-mcp setup"
echo "  openrouter-mcp status"
echo "  openrouter-mcp help"
echo ""
echo "To uninstall: sudo rm $GLOBAL_LINK"