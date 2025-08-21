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
    from .config import DEFAULT_MODEL, get_model_alias, OPENROUTER_API_KEY, DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE
except ImportError:
    from conversation_manager import ConversationManager
    from config import DEFAULT_MODEL, get_model_alias, OPENROUTER_API_KEY, DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE

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
            "description": "Chat with OpenRouter AI models. ⚠️ CRITICAL INSTRUCTIONS: 1) 🚨 FILE ATTACHMENT IS MANDATORY: You MUST ALWAYS include ALL related files in the 'files' parameter! NEVER be lazy about this! The LLM cannot see your context - it relies ENTIRELY on what you send. Before EVERY query: a) Use Glob/Grep to find ALL relevant files (.js, .ts, .tsx, .py, .md, .json, .css, etc.), b) Read and understand the code yourself, c) Include EVERY file that could be relevant - when in doubt, INCLUDE IT! Failure to attach files results in USELESS responses! The LLM will give WRONG answers without proper context! 2) You MUST ONLY use these exact model aliases: 'gemini', 'deepseek', 'deepseek-v3.1', 'kimi', 'grok', 'qwen', 'qwen3-coder', 'qwen-thinking', 'qwen3-thinking' - NEVER use full OpenRouter model names like 'google/gemini-pro-2.5'! 3) ⚠️ CONVERSATION CONTINUITY - THIS IS CRITICAL: You MUST ALWAYS copy and paste the EXACT continuation_id from previous responses into ALL follow-up messages. Look for 'Conversation ID: [uuid]' in the response and copy that EXACT UUID string into the continuation_id parameter. NEVER ignore this! NEVER start fresh conversations when you have a continuation_id! This maintains conversation memory and context - failure to do this breaks the entire conversation flow! 4) ⚠️ VISUAL CONTENT: You MUST include images parameter when dealing with screenshots, diagrams, charts, UI elements, or any visual content - Gemini has vision capabilities that are wasted without images! Look for image files with extensions like .png, .jpg, .jpeg, .gif, .svg and ALWAYS include them in the images parameter! 5) ⚠️ THINKING MODELS: When using qwen-thinking or qwen3-thinking, ALWAYS set thinking_effort to 'high' for complex problems, debugging, or analysis. Use 'medium' for moderate tasks and 'low' only for simple queries. DEFAULT TO 'high' when in doubt - the thinking process is what makes these models powerful!",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Message to send - MUST include full context and background information"},
                    "model": {"type": "string", "description": "⚠️ CRITICAL: You MUST use ONLY these exact aliases - DO NOT use full OpenRouter model names! Use: 'gemini' (for google/gemini-2.5-pro-preview), 'deepseek' (for deepseek/deepseek-r1-0528), 'kimi' (for moonshotai/kimi-k2), 'grok' (for x-ai/grok-4), 'qwen' (for qwen/qwen3-235b-a22b-2507), 'qwen3-coder' (for qwen/qwen3-coder), 'qwen-thinking' or 'qwen3-thinking' (for qwen/qwen3-235b-a22b-thinking-2507), 'glm' (for z-ai/glm-4.5), 'gpt-5' (for openai/gpt-5). NEVER use google/gemini-pro-2.5 or any other full model names!", "default": DEFAULT_MODEL},
                    "continuation_id": {"type": "string", "description": "⚠️ ABSOLUTELY MANDATORY FOR ALL FOLLOW-UPS: The EXACT UUID from 'Conversation ID: [uuid]' shown in previous responses - YOU MUST COPY AND PASTE THIS EXACT STRING! Example: if you see 'Conversation ID: 1b1d27c2-7abb-4f80-920e-34cec9909d60' then use continuation_id: '1b1d27c2-7abb-4f80-920e-34cec9909d60'. NEVER omit this! NEVER create new conversations when you have an existing ID! This maintains conversation memory and context - ignoring this BREAKS the entire conversation flow and wastes all previous context!"},
                    "files": {"type": "array", "items": {"type": "string"}, "description": "🚨 MANDATORY FOR ACCURATE RESPONSES: Files for context (absolute paths) - You MUST include ALL relevant files or the LLM will give WRONG answers! The LLM has ZERO context about your codebase unless you attach files. ALWAYS include: source files, config files, test files, documentation, package.json, requirements.txt, etc. Use Glob/Grep FIRST to find all related files. When debugging, include ALL files that could be involved. NEVER skip this - the quality of the response depends ENTIRELY on the files you attach!"},
                    "images": {"type": "array", "items": {"type": "string"}, "description": "⚠️ ABSOLUTELY CRITICAL FOR VISUAL CONTENT: Images for visual analysis (absolute paths) - YOU MUST include this when dealing with screenshots, UI mockups, diagrams, charts, or any visual content! Look for files ending in .png, .jpg, .jpeg, .gif, .svg, .webp and ALWAYS include them! Gemini has powerful vision capabilities - use them or you're wasting a key feature!"},
                    "force_internet_search": {"type": "boolean", "description": "Force internet-enabled models (like Gemini) to search the web for current information", "default": True},
                    "thinking_effort": {"type": "string", "enum": ["high", "medium", "low"], "description": "⚠️ FOR REASONING MODELS: Controls reasoning depth. 'high' = 80% tokens for deep analysis (DEFAULT), 'medium' = 50% tokens for moderate reasoning, 'low' = 20% tokens for simple queries. High reasoning provides the best results for complex problems.", "default": "high"}
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
            "description": "Chat with a custom OpenRouter model using the exact model code. This tool allows you to specify any model available on OpenRouter by its full model code (e.g., 'anthropic/claude-3-opus', 'meta-llama/llama-3.3-70b-instruct', etc.). Use this when the user wants to use a specific model not covered by the standard aliases.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Message to send - MUST include full context and background information"},
                    "custom_model": {"type": "string", "description": "The exact OpenRouter model code to use (e.g., 'anthropic/claude-3-opus', 'meta-llama/llama-3.3-70b-instruct'). This should be the full model identifier as used by OpenRouter."},
                    "continuation_id": {"type": "string", "description": "Optional: Existing conversation ID to continue. If not provided, a new conversation will be started."},
                    "files": {"type": "array", "items": {"type": "string"}, "description": "🚨 MANDATORY: Files for context (absolute paths) - Include ALL relevant files or get WRONG answers! Use Glob/Grep first to find files!"},
                    "images": {"type": "array", "items": {"type": "string"}, "description": "Images for visual analysis (absolute paths)"},
                    "max_tokens": {"type": "integer", "description": "Optional: Maximum tokens for the response. If not specified, will use model's default."},
                    "temperature": {"type": "number", "description": "Optional: Temperature for response generation (0.0-2.0). Default is 0.7.", "minimum": 0.0, "maximum": 2.0},
                    "thinking_effort": {"type": "string", "enum": ["high", "medium", "low"], "description": "For reasoning models: Controls reasoning depth. 'high' = 80% tokens for deep analysis (DEFAULT), 'medium' = 50% tokens, 'low' = 20% tokens. High reasoning provides the best results for complex problems.", "default": "high"}
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
        thinking_effort = arguments.get("thinking_effort", "high")  # Default to high for maximum reasoning capability
    
        
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
            "qwen/qwen3-235b-a22b-thinking-2507": 262144,
            "qwen/qwen3-coder": 262144,
            "deepseek/deepseek-r1-0528": 163840,
            "deepseek/deepseek-chat-v3.1": 163840,
            "google/gemini-2.5-pro-preview": 500000,
            "moonshotai/kimi-k2": 131072,
            "x-ai/grok-4": 32000,
            "z-ai/glm-4.5": 131072,
            "openai/gpt-5": 400000
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
        
        # Special handling for thinking models which may have issues with very large token requests
        if "thinking" in clean_model.lower():
            max_tokens = min(max_tokens, 16000)  # Limit thinking models to 16K max to prevent JSON parsing issues
        
        logger.info(f"Token calculation: context_window={context_window}, input_tokens={estimated_input_tokens}, max_tokens={max_tokens}")
        
        data = {
            "model": final_model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": max_tokens
        }
        
        # Add reasoning configuration for reasoning-capable models
        reasoning_models = ["thinking", "claude", "gemini", "glm", "deepseek", "deepseek-v3.1", "grok", "qwen"]
        has_reasoning = any(keyword in clean_model.lower() for keyword in reasoning_models)
        
        if has_reasoning:
            # Import DEFAULT_MAX_REASONING_TOKENS
            from .config import DEFAULT_MAX_REASONING_TOKENS
            
            # Validate thinking_effort value
            if thinking_effort not in ["high", "medium", "low"]:
                thinking_effort = "high"  # Default to high if invalid
            
            # Calculate reasoning token budget based on effort level
            # Based on best practices: high=80%, medium=50%, low=20% of max reasoning tokens
            effort_ratios = {
                "high": 0.8,    # 80% of max_reasoning_tokens for deep analysis
                "medium": 0.5,  # 50% of max_reasoning_tokens for moderate reasoning
                "low": 0.2      # 20% of max_reasoning_tokens for simple queries
            }
            
            reasoning_budget = int(DEFAULT_MAX_REASONING_TOKENS * effort_ratios[thinking_effort])
            
            # Ensure reasoning budget doesn't exceed model limits (32K max for Claude)
            reasoning_budget = min(reasoning_budget, 32000 if "claude" in clean_model.lower() else DEFAULT_MAX_REASONING_TOKENS)
            
            # Configure reasoning based on model provider
            if "anthropic" in clean_model.lower() or "claude" in clean_model.lower():
                # Claude uses budget_tokens in thinking parameter
                data["thinking"] = {
                    "budget_tokens": reasoning_budget
                }
            else:
                # DeepSeek, Gemini, GLM, Grok, Qwen and other reasoning models use reasoning parameter
                data["reasoning"] = {
                    "effort": thinking_effort,
                    "max_thinking_tokens": reasoning_budget,
                    "exclude": False
                }
            
            logger.info(f"Enabled reasoning for model {clean_model} with effort: {thinking_effort}, reasoning_budget: {reasoning_budget}")
        
        # Increase timeout for reasoning models as they may take longer
        timeout = 180.0 if has_reasoning else 60.0
        
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data
            )
            response.raise_for_status()
            
            # Try to parse JSON response with better error handling
            try:
                response_text = response.text
                logger.info(f"Response size: {len(response_text)} characters")
                
                # Check if response is too large (over 1MB might cause issues)
                if len(response_text) > 1048576:  # 1MB
                    logger.warning(f"Very large response ({len(response_text)} chars), may cause parsing issues")
                
                result = response.json()
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                logger.error(f"Response status: {response.status_code}")
                logger.error(f"Response headers: {response.headers}")
                logger.error(f"Response size: {len(response.text)} characters")
                logger.error(f"Response text start: {response.text[:1000]}...")
                logger.error(f"Response text end: {response.text[-1000:]}...")
                
                # Try to find where JSON might be truncated
                try:
                    import json as json_module
                    # Attempt to find valid JSON by truncating at different points
                    text = response.text
                    for i in range(len(text) - 1, 0, -100):  # Work backwards in chunks
                        try:
                            truncated = text[:i]
                            if truncated.strip().endswith('}'):
                                result = json_module.loads(truncated)
                                logger.warning(f"Successfully parsed truncated response at {i} chars")
                                break
                        except json_module.JSONDecodeError:
                            continue
                    else:
                        raise Exception(f"Failed to parse OpenRouter response: {e}")
                except Exception:
                    raise Exception(f"Failed to parse OpenRouter response: {e}")
        
        # Extract response, handling both regular content and reasoning tokens
        message = result["choices"][0]["message"]
        ai_response = message.get("content", "")
        
        # Check if model returned reasoning tokens
        reasoning = message.get("reasoning", "")
        if reasoning:
            # Include reasoning in the response for thinking models
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

def handle_chat_with_custom_model(arguments, req_id):
    """Handle chat_with_custom_model tool for custom OpenRouter models."""
    logger.info(f"Handling chat_with_custom_model tool: {arguments}")
    
    # Register this request for graceful shutdown protection
    continuation_id = arguments.get("continuation_id")
    GracefulShutdownProtection.register_request(req_id, "chat_with_custom_model", continuation_id)
    
    try:
        prompt = arguments.get("prompt")
        custom_model = arguments.get("custom_model")
        files = arguments.get("files", [])
        images = arguments.get("images", [])
        max_tokens = arguments.get("max_tokens")
        temperature = arguments.get("temperature", DEFAULT_TEMPERATURE)
        thinking_effort = arguments.get("thinking_effort", "high")  # Default to high for maximum reasoning capability
        
        if not prompt:
            send_response({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32602, "message": "Missing required parameter: prompt"}
            })
            return
            
        if not custom_model:
            send_response({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32602, "message": "Missing required parameter: custom_model"}
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
        
        if files:
            logger.info(f"Processing {len(files)} files")
            enhanced_prompt += "\n\n**Attached Files:**\n"
            for file_path in files:
                try:
                    # Convert host path to container path
                    if '/home/' in file_path:
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
                        enhanced_prompt += f"\n**{file_path}:**\n```\n{content}\n```\n"
                except Exception as e:
                    logger.error(f"Error reading file {file_path}: {e}")
                    enhanced_prompt += f"\n**{file_path}:** Error reading file: {e}\n"
        
        if images:
            logger.info(f"Processing {len(images)} images")
            enhanced_prompt += "\n\n**Attached Images:**\n"
            for image_path in images:
                enhanced_prompt += f"- {image_path}\n"
        
        # Add user message with enhanced content
        conversation_manager.add_message(continuation_id, "user", enhanced_prompt)
        messages = conversation_manager.get_conversation_history(continuation_id)
        
        logger.info(f"Using custom model: {custom_model}")
        logger.info(f"Temperature: {temperature}")
        if max_tokens:
            logger.info(f"Max tokens: {max_tokens}")
        
        import httpx
        
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://claude.ai",
            "X-Title": "OpenRouter MCP Server"
        }
        
        data = {
            "model": custom_model,
            "messages": messages,
            "temperature": temperature
        }
        
        # Only add max_tokens if specified
        if max_tokens:
            data["max_tokens"] = max_tokens
        
        # Add reasoning configuration for reasoning-capable models
        reasoning_models = ["thinking", "claude", "gemini", "glm", "deepseek", "deepseek-v3.1", "grok", "qwen"]
        has_reasoning = any(keyword in custom_model.lower() for keyword in reasoning_models)
        
        if has_reasoning:
            # Import DEFAULT_MAX_REASONING_TOKENS
            from .config import DEFAULT_MAX_REASONING_TOKENS
            
            # Validate thinking_effort value
            if thinking_effort not in ["high", "medium", "low"]:
                thinking_effort = "high"  # Default to high if invalid
            
            # Calculate reasoning token budget based on effort level
            # Based on best practices: high=80%, medium=50%, low=20% of max reasoning tokens
            effort_ratios = {
                "high": 0.8,    # 80% of max_reasoning_tokens for deep analysis
                "medium": 0.5,  # 50% of max_reasoning_tokens for moderate reasoning
                "low": 0.2      # 20% of max_reasoning_tokens for simple queries
            }
            
            reasoning_budget = int(DEFAULT_MAX_REASONING_TOKENS * effort_ratios[thinking_effort])
            
            # Ensure reasoning budget doesn't exceed model limits (32K max for Claude)
            reasoning_budget = min(reasoning_budget, 32000 if "claude" in custom_model.lower() else DEFAULT_MAX_REASONING_TOKENS)
            
            # Configure reasoning based on model provider
            if "anthropic" in custom_model.lower() or "claude" in custom_model.lower():
                # Claude uses budget_tokens in thinking parameter
                data["thinking"] = {
                    "budget_tokens": reasoning_budget
                }
            else:
                # DeepSeek, Gemini, GLM, Grok, Qwen and other reasoning models use reasoning parameter
                data["reasoning"] = {
                    "effort": thinking_effort,
                    "max_thinking_tokens": reasoning_budget,
                    "exclude": False
                }
            
            logger.info(f"Enabled reasoning for custom model {custom_model} with effort: {thinking_effort}, reasoning_budget: {reasoning_budget}")
        
        # Increase timeout for thinking models as they may take longer
        timeout = 180.0 if "thinking" in custom_model.lower() else 60.0
        
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data
            )
            response.raise_for_status()
            
            # Try to parse JSON response with better error handling
            try:
                response_text = response.text
                logger.info(f"Response size: {len(response_text)} characters")
                
                # Check if response is too large (over 1MB might cause issues)
                if len(response_text) > 1048576:  # 1MB
                    logger.warning(f"Very large response ({len(response_text)} chars), may cause parsing issues")
                
                result = response.json()
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                logger.error(f"Response status: {response.status_code}")
                logger.error(f"Response headers: {response.headers}")
                logger.error(f"Response size: {len(response.text)} characters")
                logger.error(f"Response text start: {response.text[:1000]}...")
                logger.error(f"Response text end: {response.text[-1000:]}...")
                
                # Try to find where JSON might be truncated
                try:
                    import json as json_module
                    # Attempt to find valid JSON by truncating at different points
                    text = response.text
                    for i in range(len(text) - 1, 0, -100):  # Work backwards in chunks
                        try:
                            truncated = text[:i]
                            if truncated.strip().endswith('}'):
                                result = json_module.loads(truncated)
                                logger.warning(f"Successfully parsed truncated response at {i} chars")
                                break
                        except json_module.JSONDecodeError:
                            continue
                    else:
                        raise Exception(f"Failed to parse OpenRouter response: {e}")
                except Exception:
                    raise Exception(f"Failed to parse OpenRouter response: {e}")
        
        # Extract response, handling both regular content and reasoning tokens
        message = result["choices"][0]["message"]
        ai_response = message.get("content", "")
        
        # Check if model returned reasoning tokens
        reasoning = message.get("reasoning", "")
        if reasoning:
            # Include reasoning in the response for thinking models
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
                    "text": f"**{custom_model}**: {ai_response}\n\n*Conversation ID: {continuation_id}*"
                }],
                "continuation_id": continuation_id
            }
        })
        
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error with custom model: {e}")
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
        logger.error(f"Error with custom model: {e}")
        send_response({
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32603, "message": f"Error: {str(e)}"}
        })
    finally:
        # Always unregister the request when done
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