#!/bin/bash
# Add OpenRouter MCP Docker server to Claude Code

set -euo pipefail

echo "🚀 Setting up OpenRouter MCP connection..."

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found. Please create one with your OPENROUTER_API_KEY."
    exit 1
fi

# Load API key and base URL from .env file
export OPENROUTER_API_KEY=$(grep "^OPENROUTER_API_KEY=" .env | head -n1 | cut -d'=' -f2- | tr -d '"')
OPENROUTER_BASE_URL=$(grep "^OPENROUTER_BASE_URL=" .env | head -n1 | cut -d'=' -f2- | tr -d '"') || true
if [ -z "${OPENROUTER_BASE_URL:-}" ]; then
    OPENROUTER_BASE_URL="https://openrouter.ai/api/v1"
fi
export OPENROUTER_BASE_URL

if [ -z "$OPENROUTER_API_KEY" ]; then
    echo "❌ Error: OPENROUTER_API_KEY not found in .env file"
    exit 1
fi

echo "✅ API key loaded successfully"

# Ensure the container is running via docker-compose
echo "🐳 Ensuring OpenRouter container is running..."
docker-compose -f docker/docker-compose.yml up -d

# Wait a moment for container to be ready
sleep 2

# Check if container is running
if ! docker ps | grep -q "openrouter"; then
    echo "❌ Error: OpenRouter container is not running"
    echo "Try: python3 tools/docker_manager.py start"
    exit 1
fi

echo "✅ Container is running"

# Update Claude configuration
CONFIG_PATH="${HOME}/.claude/settings.local.json"
echo "📝 Updating Claude configuration at ${CONFIG_PATH}..."
mkdir -p "$(dirname "${CONFIG_PATH}")"
export CONFIG_PATH

if [ ! -f "${CONFIG_PATH}" ]; then
    cat <<'EOF' > "${CONFIG_PATH}"
{
  "permissions": {
    "allow": [],
    "deny": [],
    "ask": []
  },
  "mcpServers": []
}
EOF
fi

python3 <<'PY'
import json
import os
from pathlib import Path

config_path = Path(os.environ["CONFIG_PATH"])
try:
    with config_path.open() as f:
        data = json.load(f)
except json.JSONDecodeError:
    data = {}

data.setdefault("permissions", {"allow": [], "deny": [], "ask": []})
servers = data.setdefault("mcpServers", [])

entry = {
    "id": "openrouter-docker",
    "transport": {
        "type": "command",
        "command": "docker",
        "args": [
            "exec",
            "-i",
            "openrouter",
            "python3",
            "-m",
            "src.server"
        ],
        "env": {
            "OPENROUTER_API_KEY": os.environ["OPENROUTER_API_KEY"],
            "OPENROUTER_BASE_URL": os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        }
    }
}

for idx, existing in enumerate(servers):
    if existing.get("id") == entry["id"]:
        servers[idx] = entry
        break
else:
    servers.append(entry)

with config_path.open("w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
PY

echo "✅ Claude configuration updated"

# Update DROID (.claude.json) configuration
CLAUDE_JSON_PATH="${HOME}/.claude.json"
echo "📝 Updating DROID configuration at ${CLAUDE_JSON_PATH}..."

python3 <<'PY'
import json
import os
from pathlib import Path

claude_path = Path(os.environ["HOME"]) / ".claude.json"
if not claude_path.exists():
    data = {}
else:
    try:
        with claude_path.open() as f:
            data = json.load(f)
    except json.JSONDecodeError:
        data = {}

projects = data.setdefault("projects", {})
project = projects.setdefault("/home/jman", {})
project.setdefault("allowedTools", [])
project.setdefault("history", [])
project["mcpContextUris"] = project.get("mcpContextUris", [])

mcp_servers = project.setdefault("mcpServers", {})

mcp_servers["supabase"] = {
    "type": "stdio",
    "command": "npx",
    "args": [
        "@supabase/mcp-server-supabase@latest",
        "--access-token",
        "sbp_b6d1bf056f1a16ffff65e350cdaec5d0456d6916",
        "--project-ref=jmksuwaovzjnczqfodde"
    ],
    "env": {}
}

mcp_servers["sequential-thinking"] = {
    "type": "stdio",
    "command": "npx",
    "args": [
        "@modelcontextprotocol/server-sequential-thinking"
    ],
    "env": {}
}

project.setdefault("enabledMcpjsonServers", [])
project.setdefault("disabledMcpjsonServers", [])
project["hasTrustDialogAccepted"] = project.get("hasTrustDialogAccepted", True)

with claude_path.open("w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
PY

echo "✅ DROID configuration updated"

# Add the MCP server to Claude Code
if command -v claude >/dev/null 2>&1; then
    echo "🔗 Registering MCP server via claude CLI..."
    if claude mcp add openrouter-docker -s user -- docker exec -i openrouter python3 -m src.server; then
        echo "✅ MCP server added successfully via claude CLI!"
    else
        echo "⚠️ Warning: claude CLI failed to add MCP server. Configuration file has been updated manually."
    fi
else
    echo "ℹ️ 'claude' CLI not found. Skipping CLI registration; configuration file has been updated."
fi

echo "✅ Setup complete. You can now use OpenRouter models in Claude Code."
