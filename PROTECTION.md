# MCP Server Graceful Shutdown Protection

## Overview

This document describes the protection mechanisms implemented to prevent MCP server connection breaks when Claude Code sends abrupt stop signals (ESC key presses).

## Problem

When users press ESC in Claude Code while the MCP server is processing a request (especially long-running API calls to OpenRouter), the sudden termination can:
- Break the MCP server connection
- Leave requests in an inconsistent state
- Require full Claude Code restart to reconnect
- Lose conversation state mid-request

## Solution

### 1. Request State Tracking

The server now tracks all active requests using the `GracefulShutdownProtection` class:

```python
# Register request when starting
GracefulShutdownProtection.register_request(req_id, "chat", continuation_id)

# Always unregister when done (try/finally block)
GracefulShutdownProtection.unregister_request(req_id)
```

**Benefits:**
- Knows which requests are currently processing
- Can wait for completion before shutdown
- Preserves conversation state during shutdown

### 2. Signal Handlers

Proper signal handling for SIGINT and SIGTERM:

```python
def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"PROTECTION: Received signal {signum}, initiating graceful shutdown...")
    GracefulShutdownProtection.handle_shutdown()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
```

**Benefits:**
- Intercepts Ctrl+C and termination signals
- Gives active requests up to 30 seconds to complete
- Preserves conversation state for incomplete requests

### 3. Client Disconnect Detection

Enhanced main loop detects various disconnect scenarios:

```python
# EOF detection (client closed stdin)
if not line:
    eof_count += 1
    if eof_count >= max_eof_retries:
        logger.warning("Client likely disconnected")
        GracefulShutdownProtection.handle_shutdown()
        break

# Broken pipe detection
except BrokenPipeError:
    logger.warning("Broken pipe detected, client disconnected")
    GracefulShutdownProtection.handle_shutdown()
    break
```

**Benefits:**
- Detects when Claude Code closes the connection
- Prevents hanging processes
- Ensures clean shutdown even on abrupt disconnects

### 4. Response Protection

The `send_response()` function is protected against client disconnects:

```python
def send_response(response_data):
    try:
        if shutdown_requested:
            return  # Skip response if shutting down
        # ... send response ...
    except BrokenPipeError:
        GracefulShutdownProtection.handle_shutdown()
```

**Benefits:**
- Won't crash when trying to send to disconnected client
- Triggers graceful shutdown on disconnect detection

## Graceful Shutdown Process

When a shutdown is detected:

1. **Mark shutdown requested** - No new requests accepted
2. **Wait for active requests** - Up to 30 seconds for completion
3. **Preserve conversation state** - Any incomplete conversations are saved
4. **Log protection events** - Clear audit trail of shutdown process
5. **Clean exit** - Proper process termination

## Testing

Run the protection test suite:

```bash
python3 test_protection.py
```

Tests verify:
- ✅ SIGINT signal handling
- ✅ Broken pipe detection  
- ✅ Active request protection

## Configuration

Key configuration parameters:

```python
max_wait = 30          # Maximum seconds to wait for active requests
max_eof_retries = 5    # EOF retries before assuming disconnect
```

## Logging

Protection events are logged with `PROTECTION:` prefix:

```
PROTECTION: Registered active request abc123 (chat)
PROTECTION: Shutdown requested with 2 active requests
PROTECTION: Waiting for 2 active requests to complete... (5s/30s)
PROTECTION: All requests completed, proceeding with shutdown
PROTECTION: Main loop exited, server shutdown complete
```

## Benefits

1. **Connection Stability** - MCP server survives client disconnects
2. **Data Integrity** - Conversation state preserved during shutdowns
3. **User Experience** - No need to restart Claude Code after ESC presses
4. **Observability** - Clear logging of protection events
5. **Robustness** - Handles multiple disconnect scenarios gracefully

## Implementation Notes

- Uses thread-safe request tracking with locks
- Minimal performance overhead (tracking is lightweight)
- Backwards compatible with existing MCP protocol
- Works in Docker containers with proper signal forwarding
- Preserves all existing functionality while adding protection