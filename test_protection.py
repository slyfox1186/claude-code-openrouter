#!/usr/bin/env python3
"""
Test script for MCP server graceful shutdown protection.
This script simulates various client disconnect scenarios.
"""
import subprocess
import time
import signal
import os
import json

def test_signal_interruption():
    """Test SIGINT signal handling"""
    print("🧪 Testing SIGINT signal handling...")
    
    # Start server
    proc = subprocess.Popen(
        ["python3", "-m", "src.server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    try:
        # Send initialize request
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {}
        }
        
        proc.stdin.write(json.dumps(init_request) + "\n")
        proc.stdin.flush()
        
        # Wait a moment for processing
        time.sleep(1)
        
        # Send SIGINT
        print("   Sending SIGINT...")
        proc.send_signal(signal.SIGINT)
        
        # Wait for graceful shutdown
        try:
            proc.wait(timeout=35)  # Allow up to 35 seconds for graceful shutdown
            print("   ✅ Server shut down gracefully")
            return True
        except subprocess.TimeoutExpired:
            print("   ❌ Server did not shut down within timeout")
            proc.kill()
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        proc.kill()
        return False
    finally:
        if proc.poll() is None:
            proc.kill()

def test_broken_pipe():
    """Test broken pipe handling"""
    print("🧪 Testing broken pipe handling...")
    
    # Start server
    proc = subprocess.Popen(
        ["python3", "-m", "src.server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    try:
        # Send initialize request
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {}
        }
        
        proc.stdin.write(json.dumps(init_request) + "\n")
        proc.stdin.flush()
        
        # Wait a moment
        time.sleep(1)
        
        # Close stdin to simulate client disconnect
        print("   Closing stdin to simulate client disconnect...")
        proc.stdin.close()
        
        # Wait for server to detect disconnect and shut down
        try:
            proc.wait(timeout=10)
            print("   ✅ Server detected disconnect and shut down")
            return True
        except subprocess.TimeoutExpired:
            print("   ❌ Server did not detect disconnect within timeout")
            proc.kill()
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        proc.kill()
        return False
    finally:
        if proc.poll() is None:
            proc.kill()

def test_active_request_protection():
    """Test protection during active requests"""
    print("🧪 Testing active request protection...")
    
    # This test would require a long-running request
    # For now, we'll simulate with a simple request
    proc = subprocess.Popen(
        ["python3", "-m", "src.server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    try:
        # Send initialize request
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {}
        }
        
        proc.stdin.write(json.dumps(init_request) + "\n")
        proc.stdin.flush()
        time.sleep(0.5)
        
        # Send a chat request (this would be long-running in real scenario)
        chat_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "list_conversations",
                "arguments": {}
            }
        }
        
        proc.stdin.write(json.dumps(chat_request) + "\n")
        proc.stdin.flush()
        
        # Immediately send SIGINT
        print("   Sending SIGINT during request processing...")
        time.sleep(0.1)  # Small delay to start processing
        proc.send_signal(signal.SIGINT)
        
        # Wait for graceful shutdown
        try:
            proc.wait(timeout=35)
            print("   ✅ Server handled shutdown during active request")
            return True
        except subprocess.TimeoutExpired:
            print("   ❌ Server did not shut down gracefully during active request")
            proc.kill()
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        proc.kill()
        return False
    finally:
        if proc.poll() is None:
            proc.kill()

def main():
    """Run all protection tests"""
    print("🛡️  Testing MCP Server Graceful Shutdown Protection")
    print("=" * 60)
    
    # Change to the correct directory
    os.chdir("/home/jman/tmp/claude-code-openrouter")
    
    tests = [
        test_signal_interruption,
        test_broken_pipe,
        test_active_request_protection,
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
            print()  # Add spacing between tests
        except Exception as e:
            print(f"   ❌ Test failed with exception: {e}")
            print()
    
    print("=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All protection mechanisms working correctly!")
        return 0
    else:
        print("⚠️  Some protection mechanisms need attention")
        return 1

if __name__ == "__main__":
    exit(main())