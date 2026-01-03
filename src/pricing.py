"""
OpenRouter Pricing Module

Automatically fetches and caches model pricing from the OpenRouter API.
Pricing is refreshed periodically to stay up-to-date.
"""

import json
import os
import time
import threading
import logging
from typing import Dict, Optional, Any
from pathlib import Path

logger = logging.getLogger("openrouter-pricing")

# Cache configuration
CACHE_DIR = Path(os.getenv("PRICING_CACHE_DIR", "/tmp/openrouter_cache"))
CACHE_FILE = CACHE_DIR / "model_pricing.json"
CACHE_TTL_SECONDS = int(os.getenv("PRICING_CACHE_TTL", "3600"))  # 1 hour default
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"

# Thread-safe pricing cache
_pricing_cache: Dict[str, Dict[str, float]] = {}
_cache_lock = threading.Lock()
_last_fetch_time: float = 0
_fetch_in_progress = False


def _ensure_cache_dir():
    """Ensure cache directory exists."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _load_cached_pricing() -> Optional[Dict[str, Any]]:
    """Load pricing from disk cache if valid."""
    try:
        if CACHE_FILE.exists():
            with open(CACHE_FILE, "r") as f:
                data = json.load(f)
                cache_time = data.get("timestamp", 0)
                if time.time() - cache_time < CACHE_TTL_SECONDS:
                    logger.debug(f"Loaded pricing from cache (age: {time.time() - cache_time:.0f}s)")
                    return data
                else:
                    logger.debug("Cache expired, will refresh")
    except Exception as e:
        logger.warning(f"Failed to load pricing cache: {e}")
    return None


def _save_pricing_cache(pricing: Dict[str, Dict[str, float]]):
    """Save pricing to disk cache."""
    try:
        _ensure_cache_dir()
        data = {
            "timestamp": time.time(),
            "pricing": pricing,
        }
        with open(CACHE_FILE, "w") as f:
            json.dump(data, f, indent=2)
        logger.debug(f"Saved pricing cache with {len(pricing)} models")
    except Exception as e:
        logger.warning(f"Failed to save pricing cache: {e}")


def _fetch_pricing_from_api() -> Dict[str, Dict[str, float]]:
    """Fetch current pricing from OpenRouter API."""
    import httpx

    try:
        # Get API key from environment
        api_key = os.getenv("OPENROUTER_API_KEY")
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        logger.info("Fetching model pricing from OpenRouter API...")

        with httpx.Client(timeout=30.0) as client:
            response = client.get(OPENROUTER_MODELS_URL, headers=headers)
            response.raise_for_status()
            data = response.json()

        pricing = {}
        models = data.get("data", [])

        for model in models:
            model_id = model.get("id", "")
            model_pricing = model.get("pricing", {})

            # OpenRouter returns pricing as strings like "0.0000015" per token
            # Convert to per-million-tokens pricing
            try:
                # prompt = input tokens, completion = output tokens
                input_per_token = float(model_pricing.get("prompt", "0"))
                output_per_token = float(model_pricing.get("completion", "0"))

                # Convert per-token to per-million-tokens
                pricing[model_id] = {
                    "input": input_per_token * 1_000_000,
                    "output": output_per_token * 1_000_000,
                }
            except (ValueError, TypeError) as e:
                logger.debug(f"Could not parse pricing for {model_id}: {e}")
                continue

        logger.info(f"Fetched pricing for {len(pricing)} models")
        return pricing

    except Exception as e:
        logger.error(f"Failed to fetch pricing from API: {e}")
        return {}


def refresh_pricing(force: bool = False) -> bool:
    """
    Refresh pricing data from OpenRouter API.

    Args:
        force: If True, refresh even if cache is valid

    Returns:
        True if pricing was refreshed, False otherwise
    """
    global _pricing_cache, _last_fetch_time, _fetch_in_progress

    with _cache_lock:
        # Check if refresh is needed
        if not force and _pricing_cache and (time.time() - _last_fetch_time < CACHE_TTL_SECONDS):
            return False

        # Prevent concurrent fetches
        if _fetch_in_progress:
            return False
        _fetch_in_progress = True

    try:
        # Try disk cache first (if not forcing refresh)
        if not force:
            cached = _load_cached_pricing()
            if cached:
                with _cache_lock:
                    _pricing_cache = cached.get("pricing", {})
                    _last_fetch_time = cached.get("timestamp", time.time())
                return True

        # Fetch from API
        new_pricing = _fetch_pricing_from_api()

        if new_pricing:
            with _cache_lock:
                _pricing_cache = new_pricing
                _last_fetch_time = time.time()
            _save_pricing_cache(new_pricing)
            return True

        return False

    finally:
        with _cache_lock:
            _fetch_in_progress = False


def get_model_pricing(model: str) -> Dict[str, float]:
    """
    Get pricing for a model.

    Args:
        model: The model ID (e.g., "google/gemini-2.5-pro")

    Returns:
        Dict with "input" and "output" keys (per million tokens USD)
        Returns {"input": 0, "output": 0} if model not found
    """
    # Ensure pricing is loaded
    if not _pricing_cache:
        refresh_pricing()

    # Try exact match
    if model in _pricing_cache:
        return _pricing_cache[model]

    # Try without :online suffix
    clean_model = model.replace(":online", "").replace(":free", "")
    if clean_model in _pricing_cache:
        return _pricing_cache[clean_model]

    # Try base model (without version suffixes)
    base_model = model.split(":")[0]
    if base_model in _pricing_cache:
        return _pricing_cache[base_model]

    # Return zero pricing if unknown
    logger.debug(f"No pricing found for model: {model}")
    return {"input": 0.0, "output": 0.0}


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """
    Calculate cost in USD for token usage.

    Args:
        model: The model ID
        input_tokens: Number of input/prompt tokens
        output_tokens: Number of output/completion tokens

    Returns:
        Total cost in USD
    """
    pricing = get_model_pricing(model)
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return input_cost + output_cost


def get_all_pricing() -> Dict[str, Dict[str, float]]:
    """Get all cached pricing data."""
    if not _pricing_cache:
        refresh_pricing()
    return _pricing_cache.copy()


def get_pricing_stats() -> Dict[str, Any]:
    """Get pricing cache statistics."""
    return {
        "models_cached": len(_pricing_cache),
        "cache_age_seconds": time.time() - _last_fetch_time if _last_fetch_time else None,
        "cache_ttl_seconds": CACHE_TTL_SECONDS,
        "cache_file": str(CACHE_FILE),
        "last_refresh": _last_fetch_time,
    }


# Background refresh thread
_refresh_thread: Optional[threading.Thread] = None
_stop_refresh = threading.Event()


def start_background_refresh(interval_seconds: int = None):
    """Start background thread to periodically refresh pricing."""
    global _refresh_thread

    if _refresh_thread and _refresh_thread.is_alive():
        return  # Already running

    interval = interval_seconds or CACHE_TTL_SECONDS

    def refresh_loop():
        while not _stop_refresh.is_set():
            try:
                refresh_pricing()
            except Exception as e:
                logger.error(f"Background pricing refresh failed: {e}")
            _stop_refresh.wait(interval)

    _stop_refresh.clear()
    _refresh_thread = threading.Thread(target=refresh_loop, daemon=True)
    _refresh_thread.start()
    logger.info(f"Started background pricing refresh (interval: {interval}s)")


def stop_background_refresh():
    """Stop background refresh thread."""
    _stop_refresh.set()
    if _refresh_thread:
        _refresh_thread.join(timeout=5)
    logger.info("Stopped background pricing refresh")


# Initialize on import - load from cache if available
def _init():
    """Initialize pricing on module import."""
    cached = _load_cached_pricing()
    if cached:
        global _pricing_cache, _last_fetch_time
        _pricing_cache = cached.get("pricing", {})
        _last_fetch_time = cached.get("timestamp", 0)
        logger.debug(f"Initialized with {len(_pricing_cache)} cached models")


_init()
