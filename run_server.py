#!/usr/bin/env python3
"""
OpenRouter MCP Server Launcher
"""
import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the server
from src.server import main

if __name__ == "__main__":
    main()