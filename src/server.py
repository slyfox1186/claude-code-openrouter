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
    from .config import DEFAULT_MODEL, get_model_alias, OPENROUTER_API_KEY, DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE, should_force_internet_search
except ImportError:
    from conversation_manager import ConversationManager
    from config import DEFAULT_MODEL, get_model_alias, OPENROUTER_API_KEY, DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE, should_force_internet_search

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

def process_files_and_images(prompt: str, files: list, images: list) -> str:
    """Process files and images to enhance the prompt with context."""
    enhanced_prompt = prompt
    host_home = os.environ.get('HOST_HOME')

    if files:
        logger.info(f"Processing {len(files)} files")
        enhanced_prompt += "\n\n**Attached Files:**\n"
        for file_path in files:
            try:
                container_path = file_path
                # Only attempt translation if the file is under the home directory and we have HOST_HOME
                if host_home and file_path.startswith(host_home):
                    container_path = file_path.replace(host_home, f"/host{host_home}", 1)
                elif file_path.startswith('/home/') and not host_home:
                    logger.warning("HOST_HOME not set but file is under /home/. Path translation may fail.")

                logger.info(f"Reading file: {file_path} -> {container_path}")
                with open(container_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    enhanced_prompt += f"\n**{os.path.basename(file_path)}:**\n```\n{content}\n```\n"
            except Exception as e:
                logger.error(f"Error reading file {file_path} (tried {container_path}): {e}")
                enhanced_prompt += f"\n**{os.path.basename(file_path)}:** Error reading file: {e}\n"

    if images:
        logger.info(f"Processing {len(images)} images")
        enhanced_prompt += "\n\n**Attached Images:**\n"
        for image_path in images:
            enhanced_prompt += f"- {os.path.basename(image_path)}\n"

    return enhanced_prompt

def add_reasoning_config(data: dict, model: str, thinking_effort: str) -> dict:
    """Add reasoning configuration to request data based on model capabilities."""
    reasoning_models = ["thinking", "claude", "gemini", "glm", "deepseek", "grok", "qwen"]
    clean_model = model.replace(":online", "")
    has_reasoning = any(keyword in clean_model.lower() for keyword in reasoning_models)

    if has_reasoning and thinking_effort in ["high", "medium", "low"]:
        from .config import DEFAULT_MAX_REASONING_TOKENS
        effort_ratios = {"high": 0.8, "medium": 0.5, "low": 0.2}
        reasoning_budget = int(DEFAULT_MAX_REASONING_TOKENS * effort_ratios[thinking_effort])
        reasoning_budget = min(reasoning_budget, 32000 if "claude" in clean_model.lower() else DEFAULT_MAX_REASONING_TOKENS)

        if "anthropic" in clean_model.lower() or "claude" in clean_model.lower():
            data["thinking"] = {"budget_tokens": reasoning_budget}
        else:
            data["reasoning"] = {"effort": thinking_effort, "max_thinking_tokens": reasoning_budget, "exclude": False}

        logger.info(f"Enabled reasoning for model {clean_model} with effort: {thinking_effort}, reasoning_budget: {reasoning_budget}")

    return data

def _execute_chat_completion(req_id: str, arguments: dict, is_custom_model: bool = False):
    """Unified handler for all chat completions."""
    continuation_id = arguments.get("continuation_id")
    GracefulShutdownProtection.register_request(req_id, "chat", continuation_id)

    try:
        prompt = arguments.get("prompt")
        if not prompt:
            send_response({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32602, "message": "Missing required parameter: prompt"}
            })
            return

        # Resolve model
        if is_custom_model:
            model_name = arguments.get("custom_model")
            if not model_name:
                send_response({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32602, "message": "Missing required parameter: custom_model"}
                })
                return
            actual_model = model_name
        else:
            model_alias = arguments.get("model", DEFAULT_MODEL)
            actual_model = get_model_alias(model_alias, prompt)

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
        enhanced_prompt = process_files_and_images(
            prompt,
            arguments.get("files", []),
            arguments.get("images", [])
        )

        # Prepare model with internet search if needed
        final_model = actual_model
        force_internet_search = arguments.get("force_internet_search", True)
        if force_internet_search and not is_custom_model and should_force_internet_search(actual_model):
            final_model = f"{actual_model}:online"
            logger.info(f"Enabling web search: {actual_model} -> {final_model}")

        # Add user message with enhanced content
        conversation_manager.add_message(continuation_id, "user", enhanced_prompt)
        messages = conversation_manager.get_conversation_history(continuation_id)

        # Debug logging
        logger.info(f"Enhanced prompt length: {len(enhanced_prompt)}")
        logger.info(f"Number of messages being sent: {len(messages)}")

        import httpx

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
            "temperature": arguments.get("temperature", DEFAULT_TEMPERATURE)
        }

        # Add max_tokens if specified
        max_tokens = arguments.get("max_tokens")
        if max_tokens:
            data["max_tokens"] = max_tokens

        # Add reasoning configuration
        thinking_effort = arguments.get("thinking_effort", "high")
        data = add_reasoning_config(data, final_model, thinking_effort)

        # Set timeout based on model capabilities
        timeout = 180.0 if any(keyword in final_model.lower() for keyword in ["thinking", "claude", "gemini", "glm", "deepseek", "grok", "qwen"]) else 60.0

        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data
            )
            response.raise_for_status()

            # Parse JSON response with error handling
            try:
                response_text = response.text
                logger.info(f"Response size: {len(response_text)} characters")

                if len(response_text) > 1048576:  # 1MB
                    logger.warning(f"Very large response ({len(response_text)} chars), may cause parsing issues")

                result = response.json()

            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                send_response({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32603, "message": f"Failed to parse OpenRouter response: {e}"}
                })
                return

        # Extract response, handling both regular content and reasoning tokens
        message = result["choices"][0]["message"]
        ai_response = message.get("content", "")

        # Check if model returned reasoning tokens
        reasoning = message.get("reasoning", "")
        if reasoning:
            ai_response = f"{reasoning}\n\n---\n\n{ai_response}" if ai_response else reasoning
            logger.info(f"Model returned reasoning tokens: {len(reasoning)} chars")

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
            "description": "**PRIMARY TOOL** - Chat with OpenRouter AI models using intelligent model aliases. This is the DEFAULT tool for all standard model requests. Uses smart model resolution with aliases like 'gemini', 'deepseek', 'kimi', 'grok', 'qwen-max', 'qwen-coder', 'glm' that automatically map to the best available models. For best results: include relevant files using the 'files' parameter to provide context, maintain conversation history with continuation_id, and include images when working with visual content.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "User message with necessary context and background information"},
                    "model": {"type": "string", "description": "Model alias to use. PREFERRED ALIASES: 'gemini' (Google Gemini 2.5 Pro), 'deepseek' (DeepSeek R1), 'deepseek-v3.1' (DeepSeek Chat v3.1), 'kimi' (Kimi K2), 'grok' (Grok 4), 'qwen-max' (Qwen3 Max), 'qwen-coder' (Qwen3 Coder Plus), 'glm' (GLM 4.5), 'gpt-5' (OpenAI GPT-5). These aliases automatically resolve to the correct OpenRouter model codes.", "default": DEFAULT_MODEL},
                    "continuation_id": {"type": "string", "description": "UUID of an existing conversation to continue. Copy the exact UUID from previous responses to maintain conversation memory and context."},
                    "files": {"type": "array", "items": {"type": "string"}, "description": "Absolute paths to files providing context. Essential for accurate responses, especially for code-related queries. Include all relevant source files, config files, documentation, etc."},
                    "images": {"type": "array", "items": {"type": "string"}, "description": "Absolute paths to images for visual analysis. Required when working with screenshots, diagrams, charts, or any visual content. Supports .png, .jpg, .jpeg, .gif, .svg, .webp formats."},
                    "force_internet_search": {"type": "boolean", "description": "Enable web search for models that support it (like Gemini) to get current information.", "default": True},
                    "thinking_effort": {"type": "string", "enum": ["high", "medium", "low"], "description": "Controls reasoning depth for capable models. Use 'high' for complex problems, 'medium' for standard queries, 'low' for simple tasks.", "default": "high"}
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
        },
        {
            "name": "chat_with_custom_model",
            "description": "**ADVANCED TOOL - USE ONLY WHEN NEEDED** - Chat with OpenRouter models using exact model codes. WARNING: Only use this tool when you need a specific model code that is NOT available in the standard aliases (gemini, deepseek, kimi, grok, qwen-max, qwen-coder, glm, gpt-5). For 99% of requests, use the 'chat' tool instead. This tool bypasses intelligent model resolution and requires exact OpenRouter model codes like 'anthropic/claude-3-opus' or 'meta-llama/llama-3.3-70b-instruct'.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "User message with full context and background information"},
                    "custom_model": {"type": "string", "description": "The exact OpenRouter model code (e.g., 'anthropic/claude-3-opus', 'meta-llama/llama-3.3-70b-instruct'). MUST be the full model identifier as used by OpenRouter. Do NOT use aliases like 'gemini' here - use the 'chat' tool for aliases."},
                    "continuation_id": {"type": "string", "description": "Optional UUID of existing conversation to continue. If not provided, a new conversation will be started."},
                    "files": {"type": "array", "items": {"type": "string"}, "description": "Absolute paths to files providing context. Essential for accurate responses, especially for code-related queries."},
                    "images": {"type": "array", "items": {"type": "string"}, "description": "Absolute paths to images for visual analysis"},
                    "max_tokens": {"type": "integer", "description": "Optional maximum tokens for the response. If not specified, will use model's default."},
                    "temperature": {"type": "number", "description": "Optional temperature for response generation (0.0-2.0). Default is 0.7.", "minimum": 0.0, "maximum": 2.0},
                    "thinking_effort": {"type": "string", "enum": ["high", "medium", "low"], "description": "Controls reasoning depth for capable models. Use 'high' for complex problems, 'medium' for standard queries, 'low' for simple tasks.", "default": "high"}
                },
                "required": ["prompt", "custom_model"]
            }
        }
    ]
    send_response({
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {"tools": tools}
    })

def handle_chat_tool(arguments, req_id):
    """Handle chat tool call by deferring to the unified chat handler."""
    logger.info(f"Handling chat tool: {arguments}")
    _execute_chat_completion(req_id, arguments, is_custom_model=False)

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

def handle_chat_with_custom_model(arguments, req_id):
    """Handle chat_with_custom_model tool call by deferring to the unified chat handler."""
    logger.info(f"Handling chat_with_custom_model tool: {arguments}")
    _execute_chat_completion(req_id, arguments, is_custom_model=True)

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
    elif tool_name == "chat_with_custom_model":
        handle_chat_with_custom_model(arguments, req_id)
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