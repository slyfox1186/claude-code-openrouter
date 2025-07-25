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
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "deepseek/deepseek-r1-0528")
DEFAULT_TEMPERATURE = float(os.getenv("DEFAULT_TEMPERATURE", "0.7"))
DEFAULT_MAX_TOKENS = int(os.getenv("DEFAULT_MAX_TOKENS", "1048576"))

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
    "qwen3": "qwen/qwen3-coder",
    "qwen": "qwen/qwen3-coder",
    "kimi-k2": "moonshotai/kimi-k2",
    "kimi": "moonshotai/kimi-k2",
    "grok-4": "x-ai/grok-4",
    "grok": "x-ai/grok-4"
}

# Model capabilities configuration
MODEL_CAPABILITIES = {
    "vision": ["google/gemini-2.5-pro-preview"],
    "function_calling": ["google/gemini-2.5-pro-preview"],
    "large_context": ["deepseek/deepseek-r1-0528", "google/gemini-2.5-pro-preview", "qwen/qwen3-coder", "moonshotai/kimi-k2", "x-ai/grok-4"],
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

def get_model_alias(model_name: str) -> str:
    """Get the actual OpenRouter model name for an alias with smart matching"""
    if not model_name:
        return DEFAULT_MODEL
    
    # Clean and normalize the input
    model_clean = model_name.lower().strip()
    
    # Remove common words that don't help with matching
    words_to_remove = ["model", "the", "use", "with", "ai", "assistant"]
    for word in words_to_remove:
        model_clean = model_clean.replace(word, "").strip()
    
    # Direct alias match
    if model_name in PREFERRED_MODELS:
        return PREFERRED_MODELS[model_name]
    
    # Case-insensitive direct match
    for alias, actual_model in PREFERRED_MODELS.items():
        if alias.lower() == model_clean:
            return actual_model
    
    # Fuzzy matching for natural language requests
    # "gemini" or "google" -> gemini-2.5-pro-preview
    if any(word in model_clean for word in ["gemini", "google"]):
        return PREFERRED_MODELS["gemini-2.5-pro"]
    
    # "deepseek" -> deepseek-r1-0528
    if any(word in model_clean for word in ["deepseek", "r1"]):
        return PREFERRED_MODELS["deepseek-r1"]
    
    # "qwen" -> qwen3-coder
    if any(word in model_clean for word in ["qwen", "qwen3", "coder"]):
        return PREFERRED_MODELS["qwen3"]
    
    # "kimi" or "moonshot" -> moonshotai/kimi-k2
    if any(word in model_clean for word in ["kimi", "moonshot", "k2"]):
        return PREFERRED_MODELS["kimi-k2"]
    
    # "grok" or "x-ai" -> x-ai/grok-4
    if any(word in model_clean for word in ["grok", "x-ai", "xai"]):
        return PREFERRED_MODELS["grok-4"]
    
    # Partial match (e.g., "gemini-pro" matches "gemini-2.5-pro")
    for alias, actual_model in PREFERRED_MODELS.items():
        if model_clean in alias.lower() or alias.lower() in model_clean:
            return actual_model
    
    # If no alias found, assume it's already a full model name
    return model_name

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
