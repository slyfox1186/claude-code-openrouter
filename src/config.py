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
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "moonshotai/kimi-k2")
DEFAULT_TEMPERATURE = float(os.getenv("DEFAULT_TEMPERATURE", "0.7"))
DEFAULT_MAX_TOKENS = int(os.getenv("DEFAULT_MAX_TOKENS", "4096"))

# Tool configuration
ENABLE_WEB_SEARCH = os.getenv("ENABLE_WEB_SEARCH", "true").lower() == "true"
MAX_CONTEXT_TOKENS = int(os.getenv("MAX_CONTEXT_TOKENS", "100000"))
TOKEN_BUDGET_LIMIT = int(os.getenv("TOKEN_BUDGET_LIMIT", "50000"))

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "openrouter_mcp.log")

# Rate limiting
RATE_LIMIT_REQUESTS_PER_MINUTE = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "60"))
RATE_LIMIT_TOKENS_PER_MINUTE = int(os.getenv("RATE_LIMIT_TOKENS_PER_MINUTE", "100000"))

# MCP Transport limits
MAX_MESSAGE_SIZE = int(os.getenv("MAX_MESSAGE_SIZE", "10485760"))  # 10MB
MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "10"))

# OpenRouter-specific model configurations
PREFERRED_MODELS = {
    "gemini-2.5-pro": "google/gemini-2.5-pro",
    "gemini-pro": "google/gemini-2.5-pro",
    "deepseek-r1": "deepseek/deepseek-r1-0528",
    "deepseek": "deepseek/deepseek-r1-0528",
    "kimi-k2": "moonshotai/kimi-k2"
}

# Model capabilities configuration
MODEL_CAPABILITIES = {
    "vision": ["google/gemini-2.5-pro"],
    "function_calling": ["google/gemini-2.5-pro"],
    "large_context": ["moonshotai/kimi-k2", "google/gemini-2.5-pro"],
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
            "max_context_tokens": MAX_CONTEXT_TOKENS,
            "token_budget_limit": TOKEN_BUDGET_LIMIT,
        },
        "logging": {
            "level": LOG_LEVEL,
            "file": LOG_FILE,
        },
        "rate_limits": {
            "requests_per_minute": RATE_LIMIT_REQUESTS_PER_MINUTE,
            "tokens_per_minute": RATE_LIMIT_TOKENS_PER_MINUTE,
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
    # "gemini" or "google" -> gemini-2.5-pro
    if any(word in model_clean for word in ["gemini", "google"]):
        return PREFERRED_MODELS["gemini-2.5-pro"]
    
    # "deepseek" -> deepseek-r1-0528
    if any(word in model_clean for word in ["deepseek", "r1"]):
        return PREFERRED_MODELS["deepseek-r1"]
    
    # "kimi" or "moonshot" -> kimi-k2
    if any(word in model_clean for word in ["kimi", "moonshot", "k2"]):
        return PREFERRED_MODELS["kimi-k2"]
    
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
