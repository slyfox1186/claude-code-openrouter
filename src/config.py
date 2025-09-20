"""
Configuration management for OpenRouter MCP Server
"""
import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Version and metadata
VERSION = "1.0.0"
MCP_VERSION = "1.0"

# OpenRouter API Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

# Default model settings
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "z-ai/glm-4.5")
DEFAULT_TEMPERATURE = float(os.getenv("DEFAULT_TEMPERATURE", "0.7"))
DEFAULT_MAX_TOKENS = int(os.getenv("DEFAULT_MAX_TOKENS", "8192"))
DEFAULT_MAX_REASONING_TOKENS = int(os.getenv("DEFAULT_MAX_REASONING_TOKENS", "16384"))  # Max thinking/reasoning tokens

# Tool configuration
ENABLE_WEB_SEARCH = os.getenv("ENABLE_WEB_SEARCH", "true").lower() == "true"
FORCE_INTERNET_SEARCH = os.getenv("FORCE_INTERNET_SEARCH", "true").lower() == "true"

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "openrouter_mcp.log")

# Rate limiting
RATE_LIMIT_REQUESTS_PER_MINUTE = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "60"))

# MCP Transport limits
MAX_MESSAGE_SIZE = int(os.getenv("MAX_MESSAGE_SIZE", "10485760"))  # 10MB
MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "10"))

# OpenRouter-specific model configurations
PREFERRED_MODELS = {
    "gemini-2.5-pro": "google/gemini-2.5-pro-preview",
    "gemini-pro": "google/gemini-2.5-pro-preview",
    "deepseek-r1": "deepseek/deepseek-r1-0528",
    "deepseek": "deepseek/deepseek-r1-0528",
    "deepseek-v3.1": "deepseek/deepseek-chat-v3.1",
    "deepseek-chat-v3": "deepseek/deepseek-chat-v3.1",
    "kimi-k2": "moonshotai/kimi-k2",
    "kimi": "moonshotai/kimi-k2",
    "grok-4": "x-ai/grok-4",
    "grok": "x-ai/grok-4",
    "qwen3-max": "qwen/qwen3-max",
    "qwen-max": "qwen/qwen3-max",
    "qwen3-coder-plus": "qwen/qwen3-coder-plus",
    "qwen3-coder": "qwen/qwen3-coder-plus",
    "qwen-coder": "qwen/qwen3-coder-plus",
    "glm-4.5": "z-ai/glm-4.5",
    "glm": "z-ai/glm-4.5",
    "gpt-5": "openai/gpt-5",
    "openai-gpt-5": "openai/gpt-5"
}

# Model capabilities configuration
MODEL_CAPABILITIES = {
    "vision": ["google/gemini-2.5-pro-preview", "openai/gpt-5"],
    "function_calling": ["google/gemini-2.5-pro-preview", "openai/gpt-5"],
    "large_context": ["deepseek/deepseek-r1-0528", "deepseek/deepseek-chat-v3.1", "google/gemini-2.5-pro-preview", "moonshotai/kimi-k2", "x-ai/grok-4", "qwen/qwen3-max", "qwen/qwen3-coder-plus", "z-ai/glm-4.5", "openai/gpt-5"],
    "internet_access": ["google/gemini-2.5-pro-preview"],
}

def get_config() -> Dict[str, Any]:
    """Get current configuration as dictionary"""
    return {
        "version": VERSION,
        "mcp_version": MCP_VERSION,
        "openrouter": {
            "api_key": bool(OPENROUTER_API_KEY),  # Don't expose actual key
            "base_url": OPENROUTER_BASE_URL,
        },
        "defaults": {
            "model": DEFAULT_MODEL,
            "temperature": DEFAULT_TEMPERATURE,
            "max_tokens": DEFAULT_MAX_TOKENS,
            "max_reasoning_tokens": DEFAULT_MAX_REASONING_TOKENS,
        },
        "tools": {
            "web_search": ENABLE_WEB_SEARCH,
            "force_internet_search": FORCE_INTERNET_SEARCH,
        },
        "logging": {
            "level": LOG_LEVEL,
            "file": LOG_FILE,
        },
        "rate_limits": {
            "requests_per_minute": RATE_LIMIT_REQUESTS_PER_MINUTE,
        },
        "transport": {
            "max_message_size": MAX_MESSAGE_SIZE,
            "max_concurrent_requests": MAX_CONCURRENT_REQUESTS,
        },
    }

def validate_config() -> bool:
    """Validate configuration and return True if valid"""
    if not OPENROUTER_API_KEY:
        print("ERROR: OPENROUTER_API_KEY is required")
        return False
    
    if DEFAULT_TEMPERATURE < 0 or DEFAULT_TEMPERATURE > 2:
        print("ERROR: DEFAULT_TEMPERATURE must be between 0 and 2")
        return False
    
    if DEFAULT_MAX_TOKENS < 1:
        print("ERROR: DEFAULT_MAX_TOKENS must be positive")
        return False
    
    return True

def get_model_alias(model_name: str, user_prompt: str = "") -> str:
    """Get the actual OpenRouter model name using intelligent LLM-based selection"""
    if not model_name:
        return DEFAULT_MODEL

    # Direct alias match first
    if model_name in PREFERRED_MODELS:
        return PREFERRED_MODELS[model_name]

    # If it's already a full OpenRouter model name, return as-is
    if "/" in model_name and model_name not in PREFERRED_MODELS:
        return model_name

    # Use LLM intelligence to determine the best model based on user query
    return _intelligent_model_selection(model_name, user_prompt)

def _intelligent_model_selection(model_request: str, user_prompt: str = "") -> str:
    """Use LLM intelligence to select the best model based on context"""

    # Model capabilities for intelligent selection
    model_info = {
        "gemini-2.5-pro": {
            "model": "google/gemini-2.5-pro-preview",
            "strengths": "vision, web search, general reasoning, large context (1M+ tokens)",
            "best_for": "image analysis, current information, research, general tasks"
        },
        "deepseek-r1": {
            "model": "deepseek/deepseek-r1-0528",
            "strengths": "advanced reasoning, logical analysis, problem solving",
            "best_for": "complex reasoning, mathematical problems, logical analysis"
        },
        "deepseek-v3.1": {
            "model": "deepseek/deepseek-chat-v3.1",
            "strengths": "latest version with 163K context, advanced chat capabilities",
            "best_for": "general chat, latest features, large context tasks"
        },
        "kimi-k2": {
            "model": "moonshotai/kimi-k2",
            "strengths": "advanced reasoning, programming, large context",
            "best_for": "programming tasks, code analysis, advanced reasoning"
        },
        "grok-4": {
            "model": "x-ai/grok-4",
            "strengths": "creative thinking, analytical tasks, general intelligence",
            "best_for": "creative solutions, brainstorming, analytical tasks"
        },
        "qwen3-max": {
            "model": "qwen/qwen3-max",
            "strengths": "large context (128K), general reasoning, multilingual",
            "best_for": "large document analysis, general tasks, multilingual content"
        },
        "qwen3-coder-plus": {
            "model": "qwen/qwen3-coder-plus",
            "strengths": "coding, programming, technical tasks (32K context)",
            "best_for": "code generation, debugging, programming assistance"
        },
        "glm-4.5": {
            "model": "z-ai/glm-4.5",
            "strengths": "balanced performance, general tasks, good default choice",
            "best_for": "general purpose tasks, balanced performance"
        },
        "gpt-5": {
            "model": "openai/gpt-5",
            "strengths": "flagship model with 400K context, latest capabilities",
            "best_for": "cutting-edge performance, large context tasks, latest features"
        }
    }

    # Simple intelligent matching based on request context
    request_lower = model_request.lower().strip()
    prompt_lower = user_prompt.lower() if user_prompt else ""

    # Direct name matching with intelligence
    if "gemini" in request_lower or "google" in request_lower:
        return model_info["gemini-2.5-pro"]["model"]
    elif "deepseek" in request_lower:
        # Check for version preference
        if any(word in request_lower for word in ["v3.1", "v3", "chat", "latest"]):
            return model_info["deepseek-v3.1"]["model"]
        else:
            return model_info["deepseek-r1"]["model"]
    elif "kimi" in request_lower or "moonshot" in request_lower:
        return model_info["kimi-k2"]["model"]
    elif "grok" in request_lower or "x-ai" in request_lower or "xai" in request_lower:
        return model_info["grok-4"]["model"]
    elif "glm" in request_lower or "z-ai" in request_lower:
        return model_info["glm-4.5"]["model"]
    elif "gpt-5" in request_lower or "gpt5" in request_lower or "openai" in request_lower:
        return model_info["gpt-5"]["model"]

    # For qwen, use context to determine which variant
    elif "qwen" in request_lower:
        # Analyze user prompt to determine best qwen variant
        if any(word in prompt_lower for word in ["code", "programming", "debug", "function", "script", "development"]):
            return model_info["qwen3-coder-plus"]["model"]
        else:
            return model_info["qwen3-max"]["model"]

    # If no match found, return the request as-is (assume it's a full model name)
    return model_request

def list_available_aliases() -> dict:
    """List all available model aliases and their mappings"""
    return PREFERRED_MODELS.copy()

def suggest_model_alias(partial_name: str) -> list:
    """Suggest model aliases based on partial input"""
    if not partial_name:
        return []
    
    partial_lower = partial_name.lower()
    suggestions = []
    
    for alias in PREFERRED_MODELS.keys():
        if partial_lower in alias.lower():
            suggestions.append(alias)
    
    return sorted(suggestions)

def has_capability(model_name: str, capability: str) -> bool:
    """Check if a model has a specific capability"""
    actual_model = get_model_alias(model_name)
    return actual_model in MODEL_CAPABILITIES.get(capability, [])

def should_force_internet_search(model_name: str) -> bool:
    """Check if we should force internet search for this model"""
    if not FORCE_INTERNET_SEARCH:
        return False
    return has_capability(model_name, "internet_access")
