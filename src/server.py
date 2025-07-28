#!/usr/bin/env python3
"""
OpenRouter MCP Server - Simple Synchronous Version
This version uses simple synchronous stdin to avoid Docker permission issues.
"""
import json
import sys
import os
import logging
from dotenv import load_dotenv

# Set up paths for both direct execution and module import
try:
    from .conversation_manager import ConversationManager
    from .config import DEFAULT_MODEL, get_model_alias, OPENROUTER_API_KEY
except ImportError:
    from conversation_manager import ConversationManager
    from config import DEFAULT_MODEL, get_model_alias, OPENROUTER_API_KEY

# Simple logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler('/tmp/openrouter_simple.log', mode='w')
    ]
)
logger = logging.getLogger("openrouter-simple")

# Load environment
load_dotenv()
conversation_manager = ConversationManager()

logger.info("Simple OpenRouter MCP Server starting...")
logger.info(f"API Key configured: {bool(OPENROUTER_API_KEY)}")

def send_response(response_data):
    """Send JSON-RPC response to stdout."""
    try:
        response_str = json.dumps(response_data)
        logger.info(f"Sending response: {response_str}")
        print(response_str, flush=True)
        sys.stdout.flush()
    except Exception as e:
        logger.error(f"Failed to send response: {e}")

def handle_initialize(req_id):
    """Handle initialize request."""
    logger.info("Handling initialize request")
    send_response({
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "protocolVersion": "2024-10-07",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "openrouter-simple", "version": "1.0.0"}
        }
    })

def handle_tools_list(req_id):
    """Handle tools/list request."""
    logger.info("Handling tools/list request")
    tools = [
        {
            "name": "chat",
            "description": "Chat with OpenRouter AI models. ⚠️ CRITICAL INSTRUCTIONS: 1) You MUST include ALL related files and fully understand the problem by scanning the code yourself BEFORE you send ANY query to the LLMs or you risk it not having enough background information to return an optimal and correct response. Always attach relevant files, read documentation, and provide complete context. 2) You MUST ONLY use these exact model aliases: 'gemini', 'deepseek', 'kimi', 'grok', 'qwen', 'qwen3-coder' - NEVER use full OpenRouter model names like 'google/gemini-pro-2.5'! 3) CRITICAL: You MUST use the continuation_id from previous responses in follow-up messages to maintain conversation context - this is REQUIRED for proper conversation flow!",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Message to send - MUST include full context and background information"},
                    "model": {"type": "string", "description": "⚠️ CRITICAL: You MUST use ONLY these exact aliases - DO NOT use full OpenRouter model names! Use: 'gemini' (for google/gemini-2.5-pro-preview), 'deepseek' (for deepseek/deepseek-r1-0528), 'kimi' (for moonshotai/kimi-k2), 'grok' (for x-ai/grok-4), 'qwen' (for qwen/qwen3-235b-a22b-2507), 'qwen3-coder' (for qwen/qwen3-coder). NEVER use google/gemini-pro-2.5 or any other full model names!", "default": DEFAULT_MODEL},
                    "continuation_id": {"type": "string", "description": "⚠️ REQUIRED for follow-up messages: Conversation ID from previous response - YOU MUST use this to maintain conversation context!"},
                    "files": {"type": "array", "items": {"type": "string"}, "description": "Optional files for context (absolute paths)"},
                    "images": {"type": "array", "items": {"type": "string"}, "description": "Optional images for visual context (absolute paths)"},
                    "force_internet_search": {"type": "boolean", "description": "Force internet-enabled models (like Gemini) to search the web for current information", "default": True}
                },
                "required": ["prompt"]
            }
        },
        {
            "name": "list_conversations",
            "description": "List all saved conversations",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "get_conversation",
            "description": "Get conversation history by ID",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "continuation_id": {"type": "string", "description": "Conversation ID to retrieve"}
                },
                "required": ["continuation_id"]
            }
        },
        {
            "name": "delete_conversation",
            "description": "Delete a conversation by ID",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "continuation_id": {"type": "string", "description": "Conversation ID to delete"}
                },
                "required": ["continuation_id"]
            }
        }
    ]
    send_response({
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {"tools": tools}
    })

def handle_chat_tool(arguments, req_id):
    """Handle chat tool call."""
    logger.info(f"Handling chat tool: {arguments}")
    
    prompt = arguments.get("prompt")
    model_alias = arguments.get("model", DEFAULT_MODEL)
    continuation_id = arguments.get("continuation_id")
    files = arguments.get("files", [])
    images = arguments.get("images", [])
    force_internet_search = arguments.get("force_internet_search", True)
    
    if not prompt:
        send_response({
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32602, "message": "Missing required parameter: prompt"}
        })
        return
    
    # Create or get conversation
    if not continuation_id:
        continuation_id = conversation_manager.create_conversation()
    
    # Process files and images to add to prompt
    enhanced_prompt = prompt
    
    # Prepare model with internet search if needed
    from src.config import should_force_internet_search, get_model_alias
    actual_model = get_model_alias(model_alias)
    final_model = actual_model
    if force_internet_search and should_force_internet_search(actual_model):
        final_model = f"{actual_model}:online"
        logger.info(f"Enabling web search: {actual_model} -> {final_model}")
    
    if files:
        logger.info(f"Processing {len(files)} files")
        enhanced_prompt += "\n\n**Attached Files:**\n"
        for file_path in files:
            try:
                # Convert host path to container path
                # The volume is mounted as /host$HOME where $HOME is the host's home directory
                # We need to detect if this is under the host home and map it correctly
                if '/home/' in file_path:
                    # Extract the username from the path to construct the container path
                    path_parts = file_path.split('/')
                    if len(path_parts) >= 3 and path_parts[1] == 'home':
                        username = path_parts[2]
                        container_path = file_path.replace(f'/home/{username}', f'/host/home/{username}')
                    else:
                        container_path = file_path
                else:
                    container_path = file_path
                
                logger.info(f"Reading file: {file_path} -> {container_path}")
                with open(container_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    logger.info(f"File content length: {len(content)}")
                    logger.info(f"File content preview: {content[:100]}...")
                    enhanced_prompt += f"\n**{file_path}:**\n```\n{content}\n```\n"
                    logger.info(f"Enhanced prompt length after adding file: {len(enhanced_prompt)}")
            except Exception as e:
                logger.error(f"Error reading file {file_path} (tried {container_path}): {e}")
                enhanced_prompt += f"\n**{file_path}:** Error reading file: {e}\n"
    
    if images:
        logger.info(f"Processing {len(images)} images")
        enhanced_prompt += "\n\n**Attached Images:**\n"
        for image_path in images:
            enhanced_prompt += f"- {image_path}\n"
            # Note: For now just mention the image path, as OpenRouter vision support varies by model
    
    # Add user message with enhanced content
    conversation_manager.add_message(continuation_id, "user", enhanced_prompt)
    # Get conversation history without token limits
    messages = conversation_manager.get_conversation_history(continuation_id)
    
    # Debug: log what we're actually sending
    logger.info(f"Enhanced prompt length: {len(enhanced_prompt)}")
    logger.info(f"Number of messages being sent: {len(messages)}")
    total_chars = sum(len(msg["content"]) for msg in messages)
    estimated_tokens = total_chars // 4
    logger.info(f"Estimated conversation tokens: {estimated_tokens}")
    logger.info(f"Last message content preview: {enhanced_prompt[:200]}...")
    
    try:
        import httpx
        
        # Use the final_model (with :online suffix if web search enabled)
        logger.info(f"Calling OpenRouter with model: {final_model}")
        
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://claude.ai",
            "X-Title": "OpenRouter MCP Server"
        }
        
        data = {
            "model": final_model,
            "messages": messages,
            "temperature": 0.7
        }
        
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data
            )
            response.raise_for_status()
            result = response.json()
        
        ai_response = result["choices"][0]["message"]["content"]
        
        # Add AI response to conversation
        conversation_manager.add_message(continuation_id, "assistant", ai_response)
        
        # Send result
        send_response({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{
                    "type": "text",
                    "text": f"**{actual_model}**: {ai_response}\n\n*Conversation ID: {continuation_id}*"
                }],
                "continuation_id": continuation_id
            }
        })
        
    except Exception as e:
        logger.error(f"Error calling OpenRouter: {e}")
        send_response({
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32603, "message": f"OpenRouter API error: {str(e)}"}
        })

def handle_list_conversations(req_id):
    """Handle list_conversations tool."""
    logger.info("Handling list_conversations tool")
    
    try:
        conversations = conversation_manager.list_conversations()
        if not conversations:
            result_text = "No conversations found."
        else:
            result_text = f"Found {len(conversations)} conversations:\n\n"
            for conv in conversations:
                result_text += f"• **ID**: `{conv['id']}`\n"
                result_text += f"  Messages: {conv['message_count']}\n"
                result_text += f"  Preview: {conv.get('first_message', 'No messages')[:100]}...\n\n"
        
        send_response({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"content": [{"type": "text", "text": result_text}]}
        })
        
    except Exception as e:
        logger.error(f"Error listing conversations: {e}")
        send_response({
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32603, "message": f"Error listing conversations: {str(e)}"}
        })

def handle_get_conversation(arguments, req_id):
    """Handle get_conversation tool."""
    logger.info(f"Handling get_conversation tool: {arguments}")
    
    continuation_id = arguments.get("continuation_id")
    if not continuation_id:
        send_response({
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32602, "message": "Missing required parameter: continuation_id"}
        })
        return
    
    try:
        history = conversation_manager.get_conversation_history(continuation_id)
        if not history:
            result_text = f"Conversation '{continuation_id}' not found."
        else:
            result_text = f"**Conversation ID**: `{continuation_id}`\n\n"
            for i, msg in enumerate(history, 1):
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                result_text += f"**{i}. {role.title()}**: {content}\n\n"
        
        send_response({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"content": [{"type": "text", "text": result_text}]}
        })
        
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        send_response({
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32603, "message": f"Error getting conversation: {str(e)}"}
        })

def handle_delete_conversation(arguments, req_id):
    """Handle delete_conversation tool."""
    logger.info(f"Handling delete_conversation tool: {arguments}")
    
    continuation_id = arguments.get("continuation_id")
    if not continuation_id:
        send_response({
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32602, "message": "Missing required parameter: continuation_id"}
        })
        return
    
    try:
        success = conversation_manager.delete_conversation(continuation_id)
        if success:
            result_text = f"✅ Conversation '{continuation_id}' deleted successfully."
        else:
            result_text = f"❌ Conversation '{continuation_id}' not found."
        
        send_response({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"content": [{"type": "text", "text": result_text}]}
        })
        
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        send_response({
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32603, "message": f"Error deleting conversation: {str(e)}"}
        })

def handle_tools_call(params, req_id):
    """Handle tools/call request."""
    tool_name = params.get("name")
    arguments = params.get("arguments", {})
    
    logger.info(f"Tool call: {tool_name} with args: {arguments}")
    
    if tool_name == "chat":
        handle_chat_tool(arguments, req_id)
    elif tool_name == "list_conversations":
        handle_list_conversations(req_id)
    elif tool_name == "get_conversation":
        handle_get_conversation(arguments, req_id)
    elif tool_name == "delete_conversation":
        handle_delete_conversation(arguments, req_id)
    else:
        send_response({
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}
        })

def main():
    """Main synchronous loop."""
    logger.info("Starting main loop, reading from stdin...")
    
    try:
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    logger.debug("EOF received, waiting for more input...")
                    import time
                    time.sleep(1.0)
                    continue
                
                line = line.strip()
                if not line:
                    continue
                
                logger.info(f"Received: {line}")
                
                try:
                    message = json.loads(line)
                    method = message.get("method")
                    params = message.get("params", {})
                    req_id = message.get("id")
                    
                    logger.info(f"Processing method: {method}, id: {req_id}")
                    
                    # Handle notifications (no response needed)
                    if req_id is None:
                        logger.info("Notification received, no response needed")
                        continue
                    
                    # Handle requests
                    if method == "initialize":
                        handle_initialize(req_id)
                    elif method == "tools/list":
                        handle_tools_list(req_id)
                    elif method == "tools/call":
                        handle_tools_call(params, req_id)
                    else:
                        send_response({
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "error": {"code": -32601, "message": f"Method not found: {method}"}
                        })
                        
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {e}")
                    
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")

if __name__ == "__main__":
    main()