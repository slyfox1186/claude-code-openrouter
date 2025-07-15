#!/usr/bin/env python3
"""
OpenRouter MCP Server - Clean Version
"""
import json
import sys
import os
import logging
from dotenv import load_dotenv
from conversation_manager import ConversationManager

# Configure detailed logging with both stdout and stderr
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)

# Add both stdout and stderr handlers to ensure logs are visible
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)

# Clear existing handlers
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)

# Add stderr handler
stderr_handler = logging.StreamHandler(sys.stderr)
stderr_handler.setLevel(logging.DEBUG)
stderr_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
stderr_handler.setFormatter(stderr_formatter)
root_logger.addHandler(stderr_handler)

# Add stdout handler for critical logs
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.INFO)
stdout_formatter = logging.Formatter('STDOUT: %(asctime)s - %(name)s - %(levelname)s - %(message)s')
stdout_handler.setFormatter(stdout_formatter)
root_logger.addHandler(stdout_handler)

# Add file handler for debugging
file_handler = logging.FileHandler('/tmp/openrouter_debug.log')
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
root_logger.addHandler(file_handler)
logger = logging.getLogger("openrouter")

# Load environment
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Initialize conversation manager
conversation_manager = ConversationManager()

logger.info("Starting OpenRouter MCP Server...")
logger.debug(f"API Key configured: {bool(OPENROUTER_API_KEY)}")
logger.debug(f"Python path: {sys.executable}")
logger.debug(f"Working directory: {os.getcwd()}")

def send_response(response):
    """Send JSON-RPC response"""
    logger.debug(f"Sending response: {json.dumps(response)[:200]}...")
    print(json.dumps(response), flush=True)

def handle_initialize(params, request_id):
    """Handle initialize request"""
    logger.info(f"Handling initialize request: {params}")
    result = {
        "protocolVersion": "2024-10-07",
        "capabilities": {"tools": {}},
        "serverInfo": {"name": "openrouter", "version": "1.0.0"}
    }
    logger.debug(f"Initialize response: {result}")
    return {"jsonrpc": "2.0", "id": request_id, "result": result}

def handle_tools_list(request_id):
    """Handle tools/list request"""
    logger.info("Handling tools/list request")
    from config import DEFAULT_MODEL
    tools = [
        {
            "name": "chat",
            "description": "Chat with OpenRouter AI models. Each response includes a continuation_id - use this ID in subsequent calls to maintain conversation history.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Message to send"},
                    "model": {
                        "type": "string", 
                        "default": DEFAULT_MODEL,
                        "description": "Model to use. Supports natural language like 'gemini', 'claude', 'kimi' or exact aliases like 'gemini-2.5-pro', 'claude-4-opus', 'claude-4-sonnet', 'kimi-k2'. Also accepts full OpenRouter model names."
                    },
                    "files": {
                        "type": "array", 
                        "description": "Optional files for context (absolute paths)",
                        "items": {"type": "string"}
                    },
                    "images": {
                        "type": "array",
                        "description": "Optional images for visual context (absolute paths)", 
                        "items": {"type": "string"}
                    },
                    "max_tokens": {
                        "type": "number",
                        "description": "Optional maximum tokens in response (no limit if not specified)",
                        "minimum": 1
                    },
                    "continuation_id": {
                        "type": "string",
                        "description": "UUID from previous chat response to continue conversation. Omit to start new conversation."
                    }
                },
                "required": ["prompt"]
            }
        },
        {
            "name": "list_conversations",
            "description": "List all stored conversations with their summaries",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "get_conversation",
            "description": "Get full conversation history by ID",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "continuation_id": {
                        "type": "string",
                        "description": "UUID of the conversation to retrieve"
                    }
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
                    "continuation_id": {
                        "type": "string",
                        "description": "UUID of the conversation to delete"
                    }
                },
                "required": ["continuation_id"]
            }
        }
    ]
    logger.debug(f"Returning {len(tools)} tools")
    return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": tools}}

async def handle_tools_call(params, request_id):
    """Handle tools/call request"""
    logger.info(f"Handling tools/call request: {params}")
    tool_name = params.get("name")
    arguments = params.get("arguments", {})
    logger.debug(f"Tool: {tool_name}, Arguments: {arguments}")
    
    if tool_name == "chat":
        prompt = arguments.get("prompt", "")
        from config import DEFAULT_MODEL
        model = arguments.get("model", DEFAULT_MODEL)
        # Map model alias to actual model name
        from config import get_model_alias
        original_model = model
        model = get_model_alias(model)
        logger.info(f"MODEL MAPPING: '{original_model}' -> '{model}'")
        files = arguments.get("files", [])
        images = arguments.get("images", [])
        max_tokens = arguments.get("max_tokens")
        continuation_id = arguments.get("continuation_id")
        
        # Debug: Log all arguments received
        logger.info(f"ARGS: Received arguments: {arguments}")
        logger.info(f"ARGS: continuation_id = {continuation_id}")
        logger.info(f"ARGS: prompt = {prompt[:50]}...")
        logger.info(f"ARGS: model = {model}")
        logger.info(f"ARGS: files = {files}")
        logger.info(f"ARGS: images = {images}")
        logger.info(f"ARGS: max_tokens = {max_tokens}")
        
        # Handle conversation continuation (following Zen MCP pattern)
        if continuation_id:
            logger.info(f"CONTINUATION: Attempting to continue conversation: {continuation_id}")
            conversation_history = conversation_manager.get_conversation_history(continuation_id)
            if not conversation_history:
                logger.warning(f"CONTINUATION: Conversation {continuation_id} not found, starting new conversation")
                continuation_id = conversation_manager.create_conversation()
                conversation_history = []
                logger.info(f"CONTINUATION: Created new conversation: {continuation_id}")
            else:
                logger.info(f"CONTINUATION: Loaded {len(conversation_history)} messages from conversation {continuation_id}")
        else:
            logger.info("CONTINUATION: No continuation_id provided, starting new conversation")
            continuation_id = conversation_manager.create_conversation()
            conversation_history = []
            logger.info(f"CONTINUATION: Created new conversation: {continuation_id}")
        
        logger.info(f"Chat request - Model: {model}, Files: {len(files)}, Images: {len(images)}, Continuation: {continuation_id}")
        logger.debug(f"Conversation history: {len(conversation_history)} messages")
        
        # Build context from files
        context_parts = []
        
        # Add file contents
        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    context_parts.append(f"File: {file_path}\n```\n{content}\n```")
            except Exception as e:
                context_parts.append(f"Error reading {file_path}: {str(e)}")
        
        # Add image references (for vision models)
        for image_path in images:
            if os.path.exists(image_path):
                context_parts.append(f"Image: {image_path}")
            else:
                context_parts.append(f"Image not found: {image_path}")
        
        # Add current user message to conversation history
        current_user_message = prompt
        if context_parts:
            current_user_message = f"{prompt}\n\nContext:\n" + "\n\n".join(context_parts)
        
        # Add user message to conversation history
        logger.info(f"STORAGE: Adding user message to conversation {continuation_id}")
        logger.debug(f"STORAGE: User message content: {current_user_message[:100]}...")
        success = conversation_manager.add_message(
            continuation_id, 
            "user", 
            current_user_message,
            metadata={
                "model": model,
                "files": files,
                "images": images,
                "file_count": len(files),
                "image_count": len(images)
            }
        )
        
        if success:
            logger.info(f"STORAGE: Successfully added user message to conversation {continuation_id}")
        else:
            logger.error(f"STORAGE: Failed to add user message to conversation {continuation_id}")
        
        # Get updated conversation history
        conversation_history = conversation_manager.get_conversation_history(continuation_id)
        logger.info(f"STORAGE: Retrieved {len(conversation_history)} messages after adding user message")
        
        # Make actual OpenRouter API call
        if not OPENROUTER_API_KEY:
            logger.error("OpenRouter API key not configured")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32603, "message": "OpenRouter API key not configured"}
            }
        
        logger.debug("Attempting to import openai library...")
        try:
            from openai import AsyncOpenAI
            logger.debug("Successfully imported openai library")
            
            # Initialize OpenRouter client
            logger.debug("Initializing OpenRouter client...")
            logger.debug(f"API Key length: {len(OPENROUTER_API_KEY) if OPENROUTER_API_KEY else 0}")
            logger.debug(f"API Key starts with: {OPENROUTER_API_KEY[:10] if OPENROUTER_API_KEY else 'None'}...")
            client = AsyncOpenAI(
                api_key=OPENROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1",
                default_headers={
                    "HTTP-Referer": "https://claude.ai",
                    "X-Title": "OpenRouter MCP"
                }
            )
            logger.debug("OpenRouter client initialized successfully")
            
            # Use conversation history for messages
            messages = conversation_history
            logger.info(f"API_CALL: Prepared {len(messages)} messages for OpenRouter API")
            logger.debug(f"API_CALL: Messages being sent to API:")
            for i, msg in enumerate(messages):
                logger.debug(f"API_CALL: Message {i+1}: {msg['role']} - {msg['content'][:100]}...")
            
            # Prepare API call parameters
            api_params = {
                "model": model,
                "messages": messages,
                "temperature": 0.7,
                "timeout": 60.0
            }
            
            # Only add max_tokens if specified
            if max_tokens:
                api_params["max_tokens"] = int(max_tokens)
                logger.debug(f"Max tokens set to: {max_tokens}")
            
            logger.info(f"Making API call to OpenRouter with model: {model}")
            # Make API call
            response = await client.chat.completions.create(**api_params)
            logger.info("API call successful!")
            
            content = response.choices[0].message.content
            usage = {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            }
            
            # Add assistant response to conversation history
            logger.info(f"STORAGE: Adding assistant response to conversation {continuation_id}")
            logger.debug(f"STORAGE: Assistant response content: {content[:100]}...")
            assistant_success = conversation_manager.add_message(
                continuation_id,
                "assistant",
                content,
                metadata={
                    "model": model,
                    "usage": usage,
                    "file_count": len(files),
                    "image_count": len(images)
                }
            )
            
            if assistant_success:
                logger.info(f"STORAGE: Successfully added assistant response to conversation {continuation_id}")
            else:
                logger.error(f"STORAGE: Failed to add assistant response to conversation {continuation_id}")
            
            # Format response with conversation continuation info (CRITICAL: Make it very visible)
            result_text = f"🔄 **CONTINUATION ID**: `{continuation_id}`\n"
            result_text += f"📋 **CONTINUATION_ID**: {continuation_id}\n"  
            result_text += f"📋 **To continue this conversation, use**: `continuation_id: \"{continuation_id}\"`\n"
            result_text += f"📋 **COPY THIS FOR NEXT CALL**: `\"continuation_id\": \"{continuation_id}\"`\n\n"
            result_text += f"**Model**: {model}\n"
            
            if files:
                result_text += f"**Files analyzed**: {len(files)} files\n"
            
            if images:
                result_text += f"**Images analyzed**: {len(images)} images\n"
            
            # Show conversation context
            conversation_turns = len(conversation_history) // 2
            result_text += f"**Conversation turns**: {conversation_turns}\n"
            
            result_text += f"\n**Response**:\n{content}\n\n"
            result_text += f"**Usage**: {usage['total_tokens']} tokens ({usage['prompt_tokens']} + {usage['completion_tokens']})\n\n"
            result_text += f"💡 **Next steps**: To continue this conversation, include `continuation_id: \"{continuation_id}\"` in your next mcp__openrouter-docker__chat call.\n\n"
            result_text += f"CONTINUATION_ID: {continuation_id}"
            
        except Exception as e:
            logger.error(f"Error calling OpenRouter API: {str(e)}", exc_info=True)
            result_text = f"**Error calling OpenRouter API**: {str(e)}\n\n**Model**: {model}\n**Continuation ID**: {continuation_id}\n**Files**: {len(files)} files\n**Images**: {len(images)} images"
        
        # Following proper MCP pattern - return continuation_id as a separate field
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [{"type": "text", "text": result_text}],
                "continuation_id": continuation_id,
                "metadata": {
                    "continuation_id": continuation_id,
                    "conversation_turns": len(conversation_history) // 2
                }
            }
        }
    
    elif tool_name == "list_conversations":
        logger.info("Listing conversations")
        conversations = conversation_manager.list_conversations()
        
        if not conversations:
            result_text = "**No conversations found**\n\nNo conversation history is currently stored."
        else:
            result_text = f"**Stored Conversations** ({len(conversations)} total)\n\n"
            for i, conv in enumerate(conversations, 1):
                result_text += f"**{i}. {conv['id'][:8]}...{conv['id'][-8:]}**\n"
                result_text += f"   - Messages: {conv['message_count']}\n"
                result_text += f"   - Created: {conv.get('created_at', 'Unknown')}\n"
                result_text += f"   - Updated: {conv.get('updated_at', 'Unknown')}\n"
                if conv.get('last_message'):
                    last_msg = conv['last_message']
                    preview = last_msg['content'][:100] + "..." if len(last_msg['content']) > 100 else last_msg['content']
                    result_text += f"   - Last ({last_msg['role']}): {preview}\n"
                result_text += "\n"
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"content": [{"type": "text", "text": result_text}]}
        }
    
    elif tool_name == "get_conversation":
        continuation_id = arguments.get("continuation_id")
        if not continuation_id:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32602, "message": "continuation_id is required"}
            }
        
        logger.info(f"Getting conversation: {continuation_id}")
        conversation_data = conversation_manager.load_conversation(continuation_id)
        
        if not conversation_data:
            result_text = f"**Conversation not found**: {continuation_id}"
        else:
            messages = conversation_data.get("messages", [])
            result_text = f"**Conversation**: {continuation_id}\n"
            result_text += f"**Created**: {conversation_data.get('created_at', 'Unknown')}\n"
            result_text += f"**Messages**: {len(messages)}\n\n"
            
            if messages:
                result_text += "**Conversation History**:\n\n"
                for i, msg in enumerate(messages, 1):
                    role_label = "🧑 User" if msg['role'] == 'user' else "🤖 Assistant"
                    result_text += f"**{i}. {role_label}** ({msg.get('timestamp', 'Unknown')})\n"
                    result_text += f"{msg['content']}\n\n"
                    
                    if msg.get('metadata'):
                        meta = msg['metadata']
                        if meta.get('model'):
                            result_text += f"   *Model: {meta['model']}*\n"
                        if meta.get('usage'):
                            usage = meta['usage']
                            result_text += f"   *Tokens: {usage.get('total_tokens', 0)}*\n"
                        result_text += "\n"
            else:
                result_text += "No messages in conversation.\n"
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"content": [{"type": "text", "text": result_text}]}
        }
    
    elif tool_name == "delete_conversation":
        continuation_id = arguments.get("continuation_id")
        if not continuation_id:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32602, "message": "continuation_id is required"}
            }
        
        logger.info(f"Deleting conversation: {continuation_id}")
        success = conversation_manager.delete_conversation(continuation_id)
        
        if success:
            result_text = f"**Conversation deleted**: {continuation_id}\n\nThe conversation has been permanently removed from storage."
        else:
            result_text = f"**Error deleting conversation**: {continuation_id}\n\nThe conversation may not exist or there was an error during deletion."
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"content": [{"type": "text", "text": result_text}]}
        }
    
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}
    }

async def main():
    """Main server loop"""
    logger.info("Starting main server loop...")
    while True:
        try:
            logger.debug("Waiting for input on stdin...")
            line = await asyncio.to_thread(sys.stdin.readline)
            if not line:
                logger.info("EOF received, shutting down")
                break
            
            line = line.strip()
            if not line:
                continue
            
            logger.info(f"RAW_MESSAGE: Received message: {line}")
            print(f"CONSOLE: RAW_MESSAGE: {line}", flush=True)
            
            # Write to debug file
            with open('/tmp/openrouter_debug.log', 'a') as f:
                f.write(f"RAW_MESSAGE: {line}\n")
                f.flush()
            
            try:
                message = json.loads(line)
                logger.info(f"PARSED_MESSAGE: {message}")
                print(f"CONSOLE: PARSED_MESSAGE: {message}", flush=True)
                
                # Write to debug file
                with open('/tmp/openrouter_debug.log', 'a') as f:
                    f.write(f"PARSED_MESSAGE: {message}\n")
                    f.flush()
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON: {e}")
                print(f"CONSOLE: JSON ERROR: {e}", flush=True)
                continue
            
            if "id" not in message:
                logger.debug("Notification received (no response needed)")
                continue
            
            method = message.get("method")
            params = message.get("params", {})
            req_id = message.get("id")
            
            logger.info(f"REQUEST: Processing request: {method} (id: {req_id})")
            logger.info(f"REQUEST: Parameters: {params}")
            print(f"CONSOLE: REQUEST: {method} (id: {req_id})", flush=True)
            print(f"CONSOLE: PARAMS: {params}", flush=True)
            
            if method == "initialize":
                response = handle_initialize(params, req_id)
            elif method == "tools/list":
                response = handle_tools_list(req_id)
            elif method == "tools/call":
                print(f"CONSOLE: CALLING TOOL: {params.get('name')}", flush=True)
                response = await handle_tools_call(params, req_id)
            else:
                logger.warning(f"Unknown method: {method}")
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"}
                }
            
            logger.info(f"RESPONSE: Sending response: {str(response)[:200]}...")
            print(f"CONSOLE: RESPONSE: {str(response)[:200]}...", flush=True)
            send_response(response)
            
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)
            break

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())