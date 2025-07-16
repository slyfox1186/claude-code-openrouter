#!/usr/bin/env python3
"""
OpenRouter MCP Server - Official SDK Implementation
"""
import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Sequence

import httpx
from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolResult,
    TextContent,
    Tool,
    INTERNAL_ERROR,
    INVALID_PARAMS,
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("openrouter-mcp")

# Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "moonshotai/kimi-k2")

# Model aliases
PREFERRED_MODELS = {
    "gemini-2.5-pro": "google/gemini-2.5-pro",
    "gemini-pro": "google/gemini-2.5-pro",
    "claude-4-opus": "anthropic/claude-opus-4",
    "claude-opus-4": "anthropic/claude-opus-4",
    "claude-4-sonnet": "anthropic/claude-sonnet-4",
    "claude-sonnet-4": "anthropic/claude-sonnet-4",
    "kimi-k2": "moonshotai/kimi-k2"
}

# Conversation storage
conversations: Dict[str, List[Dict[str, Any]]] = {}

def get_model_alias(model_name: str) -> str:
    """Get the actual OpenRouter model name for an alias"""
    if not model_name:
        return DEFAULT_MODEL
    
    # Clean and normalize the input
    model_clean = model_name.lower().strip()
    
    # Direct alias match
    if model_name in PREFERRED_MODELS:
        return PREFERRED_MODELS[model_name]
    
    # Case-insensitive direct match
    for alias, actual_model in PREFERRED_MODELS.items():
        if alias.lower() == model_clean:
            return actual_model
    
    # Fuzzy matching for natural language requests
    if any(word in model_clean for word in ["gemini", "google"]):
        return PREFERRED_MODELS["gemini-2.5-pro"]
    
    if any(word in model_clean for word in ["claude", "anthropic"]):
        if "opus" in model_clean:
            return PREFERRED_MODELS["claude-opus-4"]
        else:
            return PREFERRED_MODELS["claude-sonnet-4"]
    
    if any(word in model_clean for word in ["kimi", "moonshot", "k2"]):
        return PREFERRED_MODELS["kimi-k2"]
    
    # If no alias found, assume it's already a full model name
    return model_name

async def call_openrouter_api(
    messages: List[Dict[str, Any]], 
    model: str = DEFAULT_MODEL,
    max_tokens: int = 4096,
    temperature: float = 0.7
) -> Dict[str, Any]:
    """Call OpenRouter API with messages"""
    if not OPENROUTER_API_KEY:
        raise ValueError("OpenRouter API key not configured")
    
    # Resolve model alias
    actual_model = get_model_alias(model)
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://claude.ai",
        "X-Title": "OpenRouter MCP Server"
    }
    
    data = {
        "model": actual_model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers=headers,
            json=data
        )
        response.raise_for_status()
        return response.json()

# Create MCP server
server = Server("openrouter-mcp")

@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available tools"""
    return [
        Tool(
            name="chat",
            description="Chat with AI models through OpenRouter",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The message to send to the AI model"
                    },
                    "model": {
                        "type": "string",
                        "description": "Model to use (e.g., 'gemini', 'claude', 'kimi')",
                        "default": DEFAULT_MODEL
                    },
                    "continuation_id": {
                        "type": "string",
                        "description": "ID to continue previous conversation",
                        "default": None
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Maximum tokens in response",
                        "default": 4096
                    },
                    "temperature": {
                        "type": "number",
                        "description": "Response randomness (0-1)",
                        "default": 0.7
                    }
                },
                "required": ["prompt"]
            }
        ),
        Tool(
            name="list_conversations",
            description="List all stored conversations",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_conversation",
            description="Get conversation history by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "continuation_id": {
                        "type": "string",
                        "description": "Conversation ID to retrieve"
                    }
                },
                "required": ["continuation_id"]
            }
        ),
        Tool(
            name="delete_conversation",
            description="Delete a conversation by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "continuation_id": {
                        "type": "string",
                        "description": "Conversation ID to delete"
                    }
                },
                "required": ["continuation_id"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
    """Handle tool calls"""
    try:
        if name == "chat":
            return await handle_chat(arguments)
        elif name == "list_conversations":
            return await handle_list_conversations()
        elif name == "get_conversation":
            return await handle_get_conversation(arguments)
        elif name == "delete_conversation":
            return await handle_delete_conversation(arguments)
        else:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unknown tool: {name}")],
                isError=True
            )
    except Exception as e:
        logger.error(f"Error in tool {name}: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True
        )

async def handle_chat(arguments: Dict[str, Any]) -> CallToolResult:
    """Handle chat tool"""
    prompt = arguments.get("prompt")
    model = arguments.get("model", DEFAULT_MODEL)
    continuation_id = arguments.get("continuation_id")
    max_tokens = arguments.get("max_tokens", 4096)
    temperature = arguments.get("temperature", 0.7)
    
    if not prompt:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: prompt is required")],
            isError=True
        )
    
    # Get or create conversation
    if continuation_id and continuation_id in conversations:
        messages = conversations[continuation_id]
    else:
        messages = []
        continuation_id = f"conv_{len(conversations) + 1}"
        conversations[continuation_id] = messages
    
    # Add user message
    messages.append({"role": "user", "content": prompt})
    
    try:
        # Call OpenRouter API
        response = await call_openrouter_api(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        # Extract response content
        ai_response = response["choices"][0]["message"]["content"]
        
        # Add AI response to conversation
        messages.append({"role": "assistant", "content": ai_response})
        
        # Return result
        return CallToolResult(
            content=[TextContent(
                type="text", 
                text=json.dumps({
                    "response": ai_response,
                    "continuation_id": continuation_id,
                    "model": get_model_alias(model)
                })
            )]
        )
    
    except Exception as e:
        logger.error(f"Error calling OpenRouter API: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True
        )

async def handle_list_conversations() -> CallToolResult:
    """Handle list conversations tool"""
    conversation_list = []
    for conv_id, messages in conversations.items():
        if messages:
            first_message = messages[0]["content"][:100] + "..." if len(messages[0]["content"]) > 100 else messages[0]["content"]
            conversation_list.append({
                "id": conv_id,
                "message_count": len(messages),
                "first_message": first_message
            })
    
    return CallToolResult(
        content=[TextContent(
            type="text",
            text=json.dumps(conversation_list)
        )]
    )

async def handle_get_conversation(arguments: Dict[str, Any]) -> CallToolResult:
    """Handle get conversation tool"""
    continuation_id = arguments.get("continuation_id")
    
    if not continuation_id:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: continuation_id is required")],
            isError=True
        )
    
    if continuation_id not in conversations:
        return CallToolResult(
            content=[TextContent(type="text", text="Conversation not found")],
            isError=True
        )
    
    return CallToolResult(
        content=[TextContent(
            type="text",
            text=json.dumps(conversations[continuation_id])
        )]
    )

async def handle_delete_conversation(arguments: Dict[str, Any]) -> CallToolResult:
    """Handle delete conversation tool"""
    continuation_id = arguments.get("continuation_id")
    
    if not continuation_id:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: continuation_id is required")],
            isError=True
        )
    
    if continuation_id in conversations:
        del conversations[continuation_id]
        return CallToolResult(
            content=[TextContent(type="text", text="Conversation deleted")]
        )
    else:
        return CallToolResult(
            content=[TextContent(type="text", text="Conversation not found")],
            isError=True
        )

async def main():
    """Main server function"""
    logger.info("Starting OpenRouter MCP Server...")
    
    if not OPENROUTER_API_KEY:
        logger.error("OPENROUTER_API_KEY environment variable is required")
        sys.exit(1)
    
    # Run server using official MCP SDK
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream=read_stream,
            write_stream=write_stream,
            initialization_options={}
        )

if __name__ == "__main__":
    asyncio.run(main())