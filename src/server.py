#!/usr/bin/env python3
"""
OpenRouter MCP Server - Simple Synchronous Version
This version uses simple synchronous stdin to avoid Docker permission issues.
Enhanced with graceful shutdown protection for abrupt client disconnects.
"""
import json
import sys
import os
import logging
import signal
import threading
import time
from typing import Dict, Set, Optional
from dotenv import load_dotenv

# Set up paths for both direct execution and module import
try:
    from .conversation_manager import ConversationManager
    from .config import DEFAULT_MODEL, get_model_alias, OPENROUTER_API_KEY, DEFAULT_MAX_TOKENS
except ImportError:
    from conversation_manager import ConversationManager
    from config import DEFAULT_MODEL, get_model_alias, OPENROUTER_API_KEY, DEFAULT_MAX_TOKENS

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

# Global state for graceful shutdown protection
shutdown_requested = False
active_requests: Dict[str, Dict] = {}  # request_id -> request_info
active_requests_lock = threading.Lock()

logger.info("Simple OpenRouter MCP Server starting...")
logger.info(f"API Key configured: {bool(OPENROUTER_API_KEY)}")

class GracefulShutdownProtection:
    """Protects against abrupt client disconnects during active requests"""
    
    @staticmethod
    def register_request(request_id: str, request_type: str, continuation_id: Optional[str] = None):
        """Register an active request for tracking"""
        with active_requests_lock:
            active_requests[request_id] = {
                'type': request_type,
                'start_time': time.time(),
                'continuation_id': continuation_id,
                'status': 'active'
            }
        logger.info(f"PROTECTION: Registered active request {request_id} ({request_type})")
    
    @staticmethod
    def unregister_request(request_id: str):
        """Unregister a completed request"""
        with active_requests_lock:
            if request_id in active_requests:
                duration = time.time() - active_requests[request_id]['start_time']
                logger.info(f"PROTECTION: Completed request {request_id} in {duration:.2f}s")
                del active_requests[request_id]
    
    @staticmethod
    def get_active_requests() -> Dict[str, Dict]:
        """Get snapshot of active requests"""
        with active_requests_lock:
            return active_requests.copy()
    
    @staticmethod
    def handle_shutdown():
        """Handle graceful shutdown with active request protection"""
        global shutdown_requested
        shutdown_requested = True
        
        active = GracefulShutdownProtection.get_active_requests()
        if active:
            logger.warning(f"PROTECTION: Shutdown requested with {len(active)} active requests")
            for req_id, req_info in active.items():
                duration = time.time() - req_info['start_time']
                logger.warning(f"PROTECTION: Active request {req_id} ({req_info['type']}) running for {duration:.2f}s")
            
            # Give active requests time to complete
            max_wait = 30  # seconds
            wait_interval = 1
            waited = 0
            
            while waited < max_wait:
                active = GracefulShutdownProtection.get_active_requests()
                if not active:
                    logger.info("PROTECTION: All requests completed, proceeding with shutdown")
                    break
                
                logger.info(f"PROTECTION: Waiting for {len(active)} active requests to complete... ({waited}s/{max_wait}s)")
                time.sleep(wait_interval)
                waited += wait_interval
            
            # Force cleanup remaining requests
            active = GracefulShutdownProtection.get_active_requests()
            if active:
                logger.warning(f"PROTECTION: Force shutdown with {len(active)} requests still active")
                for req_id, req_info in active.items():
                    if req_info.get('continuation_id'):
                        logger.info(f"PROTECTION: Preserving conversation state for {req_info['continuation_id']}")
        else:
            logger.info("PROTECTION: Clean shutdown - no active requests")

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"PROTECTION: Received signal {signum}, initiating graceful shutdown...")
    GracefulShutdownProtection.handle_shutdown()
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def send_response(response_data):
    """Send JSON-RPC response to stdout with disconnect protection."""
    try:
        # Check if shutdown is requested
        if shutdown_requested:
            logger.debug("PROTECTION: Skipping response send due to shutdown")
            return
            
        response_str = json.dumps(response_data)
        logger.info(f"Sending response: {response_str}")
        print(response_str, flush=True)
        sys.stdout.flush()
    except BrokenPipeError:
        logger.warning("PROTECTION: Broken pipe while sending response, client disconnected")
        GracefulShutdownProtection.handle_shutdown()
    except OSError as e:
        if e.errno == 32:  # Broken pipe
            logger.warning("PROTECTION: Broken pipe (OSError 32) while sending response")
            GracefulShutdownProtection.handle_shutdown()
        else:
            logger.error(f"OSError sending response: {e}")
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
            "description": "Chat with OpenRouter AI models. ⚠️ CRITICAL INSTRUCTIONS: 1) You MUST include ALL related files and fully understand the problem by scanning the code yourself BEFORE you send ANY query to the LLMs or you risk it not having enough background information to return an optimal and correct response. Always attach relevant files, read documentation, and provide complete context. 2) You MUST ONLY use these exact model aliases: 'gemini', 'deepseek', 'kimi', 'grok', 'qwen', 'qwen3-coder' - NEVER use full OpenRouter model names like 'google/gemini-pro-2.5'! 3) ⚠️ CONVERSATION CONTINUITY - THIS IS CRITICAL: You MUST ALWAYS copy and paste the EXACT continuation_id from previous responses into ALL follow-up messages. Look for 'Conversation ID: [uuid]' in the response and copy that EXACT UUID string into the continuation_id parameter. NEVER ignore this! NEVER start fresh conversations when you have a continuation_id! This maintains conversation memory and context - failure to do this breaks the entire conversation flow! 4) ⚠️ VISUAL CONTENT: You MUST include images parameter when dealing with screenshots, diagrams, charts, UI elements, or any visual content - Gemini has vision capabilities that are wasted without images! Look for image files with extensions like .png, .jpg, .jpeg, .gif, .svg and ALWAYS include them in the images parameter!",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Message to send - MUST include full context and background information"},
                    "model": {"type": "string", "description": "⚠️ CRITICAL: You MUST use ONLY these exact aliases - DO NOT use full OpenRouter model names! Use: 'gemini' (for google/gemini-2.5-pro-preview), 'deepseek' (for deepseek/deepseek-r1-0528), 'kimi' (for moonshotai/kimi-k2), 'grok' (for x-ai/grok-4), 'qwen' (for qwen/qwen3-235b-a22b-2507), 'qwen3-coder' (for qwen/qwen3-coder), 'glm' (for z-ai/glm-4.5). NEVER use google/gemini-pro-2.5 or any other full model names!", "default": DEFAULT_MODEL},
                    "continuation_id": {"type": "string", "description": "⚠️ ABSOLUTELY MANDATORY FOR ALL FOLLOW-UPS: The EXACT UUID from 'Conversation ID: [uuid]' shown in previous responses - YOU MUST COPY AND PASTE THIS EXACT STRING! Example: if you see 'Conversation ID: 1b1d27c2-7abb-4f80-920e-34cec9909d60' then use continuation_id: '1b1d27c2-7abb-4f80-920e-34cec9909d60'. NEVER omit this! NEVER create new conversations when you have an existing ID! This maintains conversation memory and context - ignoring this BREAKS the entire conversation flow and wastes all previous context!"},
                    "files": {"type": "array", "items": {"type": "string"}, "description": "Files for context (absolute paths) - ALWAYS include all relevant files to maximize context window utilization. Look for files with extensions like .js, .ts, .tsx, .py, .md, .json, .css, etc."},
                    "images": {"type": "array", "items": {"type": "string"}, "description": "⚠️ ABSOLUTELY CRITICAL FOR VISUAL CONTENT: Images for visual analysis (absolute paths) - YOU MUST include this when dealing with screenshots, UI mockups, diagrams, charts, or any visual content! Look for files ending in .png, .jpg, .jpeg, .gif, .svg, .webp and ALWAYS include them! Gemini has powerful vision capabilities - use them or you're wasting a key feature!"},
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
    
    # Register this request for graceful shutdown protection
    continuation_id = arguments.get("continuation_id")
    GracefulShutdownProtection.register_request(req_id, "chat", continuation_id)
    
    try:
        prompt = arguments.get("prompt")
        model_alias = arguments.get("model", DEFAULT_MODEL)
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
        
        # Check for shutdown request before proceeding
        if shutdown_requested:
            logger.warning(f"PROTECTION: Rejecting new request {req_id} due to shutdown")
            send_response({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32000, "message": "Server shutting down, request rejected"}
            })
            return
        
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
        
        import httpx
        
        # Use the final_model (with :online suffix if web search enabled)
        logger.info(f"Calling OpenRouter with model: {final_model}")
        
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://claude.ai",
            "X-Title": "OpenRouter MCP Server"
        }
        
        # Model context windows (total available)
        model_context_windows = {
            "qwen/qwen3-235b-a22b-2507": 262144,
            "qwen/qwen3-coder": 262144,
            "deepseek/deepseek-r1-0528": 163840,
            "google/gemini-2.5-pro-preview": 500000,
            "moonshotai/kimi-k2": 131072,
            "x-ai/grok-4": 32000,
            "z-ai/glm-4.5": 131072
        }
        
        # Remove :online suffix for model lookup
        clean_model = final_model.replace(":online", "")
        
        # Calculate max_tokens dynamically based on input size
        # Estimate input tokens (rough approximation: 1 token per 4 characters)
        input_chars = sum(len(msg["content"]) for msg in messages)
        estimated_input_tokens = input_chars // 4
        
        # Get model's context window
        context_window = model_context_windows.get(clean_model, 32000)
        
        # Leave 10% buffer for safety, and subtract estimated input tokens
        safety_buffer = int(context_window * 0.1)
        max_tokens = context_window - estimated_input_tokens - safety_buffer
        
        # Ensure max_tokens is reasonable
        max_tokens = min(max_tokens, int(context_window * 0.8))  # Never use more than 80% for output
        max_tokens = max(max_tokens, 1000)  # Always allow at least 1000 tokens for output
        
        logger.info(f"Token calculation: context_window={context_window}, input_tokens={estimated_input_tokens}, max_tokens={max_tokens}")
        
        data = {
            "model": final_model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": max_tokens
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
        
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error in chat request: {e}")
        logger.error(f"Response status: {e.response.status_code}")
        logger.error(f"Response text: {e.response.text}")
        error_detail = e.response.text
        try:
            error_json = e.response.json()
            error_detail = error_json.get('error', {}).get('message', error_detail)
        except:
            pass
        send_response({
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32603, "message": f"OpenRouter API error: {str(e)} - Details: {error_detail}"}
        })
    except Exception as e:
        logger.error(f"Error calling OpenRouter: {e}")
        send_response({
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32603, "message": f"OpenRouter API error: {str(e)}"}
        })
    finally:
        # Always unregister the request when done
        GracefulShutdownProtection.unregister_request(req_id)

def handle_list_conversations(req_id):
    """Handle list_conversations tool."""
    logger.info("Handling list_conversations tool")
    
    GracefulShutdownProtection.register_request(req_id, "list_conversations")
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
    finally:
        GracefulShutdownProtection.unregister_request(req_id)

def handle_get_conversation(arguments, req_id):
    """Handle get_conversation tool."""
    logger.info(f"Handling get_conversation tool: {arguments}")
    
    continuation_id = arguments.get("continuation_id")
    GracefulShutdownProtection.register_request(req_id, "get_conversation", continuation_id)
    
    try:
        if not continuation_id:
            send_response({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32602, "message": "Missing required parameter: continuation_id"}
            })
            return
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
    finally:
        GracefulShutdownProtection.unregister_request(req_id)

def handle_delete_conversation(arguments, req_id):
    """Handle delete_conversation tool."""
    logger.info(f"Handling delete_conversation tool: {arguments}")
    
    continuation_id = arguments.get("continuation_id")
    GracefulShutdownProtection.register_request(req_id, "delete_conversation", continuation_id)
    
    try:
        if not continuation_id:
            send_response({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32602, "message": "Missing required parameter: continuation_id"}
            })
            return
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
    finally:
        GracefulShutdownProtection.unregister_request(req_id)

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
    """Main synchronous loop with graceful shutdown protection."""
    logger.info("Starting main loop, reading from stdin...")
    
    # Track consecutive EOF reads to detect client disconnect
    eof_count = 0
    max_eof_retries = 5
    
    try:
        while not shutdown_requested:
            try:
                # Check if stdin is closed (client disconnected)
                if sys.stdin.closed:
                    logger.warning("PROTECTION: stdin closed, client disconnected")
                    GracefulShutdownProtection.handle_shutdown()
                    break
                
                line = sys.stdin.readline()
                if not line:
                    eof_count += 1
                    if eof_count >= max_eof_retries:
                        logger.warning(f"PROTECTION: Received {eof_count} consecutive EOFs, client likely disconnected")
                        GracefulShutdownProtection.handle_shutdown()
                        break
                    else:
                        logger.debug(f"EOF received ({eof_count}/{max_eof_retries}), waiting for more input...")
                        time.sleep(1.0)
                        continue
                
                # Reset EOF counter on successful read
                eof_count = 0
                
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
                    
            except BrokenPipeError:
                logger.warning("PROTECTION: Broken pipe detected, client disconnected")
                GracefulShutdownProtection.handle_shutdown()
                break
            except OSError as e:
                if e.errno == 32:  # Broken pipe
                    logger.warning("PROTECTION: Broken pipe (OSError 32), client disconnected")
                    GracefulShutdownProtection.handle_shutdown()
                    break
                else:
                    logger.error(f"OSError in main loop: {e}")
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                
    except KeyboardInterrupt:
        logger.info("PROTECTION: KeyboardInterrupt received")
        GracefulShutdownProtection.handle_shutdown()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        GracefulShutdownProtection.handle_shutdown()
    
    logger.info("PROTECTION: Main loop exited, server shutdown complete")

if __name__ == "__main__":
    main()