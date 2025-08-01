# Custom Model Usage Guide

This guide explains how to use custom OpenRouter models with the MCP server through natural language commands.

## Overview

The OpenRouter MCP server now supports using any model available on OpenRouter through a custom model interface. This allows you to use specific models not covered by the standard aliases.

## Natural Language Commands

You can use commands like:

- "Claude, call the OpenRouter MCP and let me input the model myself"
- "I want to use a custom model with OpenRouter"
- "Let me specify my own OpenRouter model"
- "Use a specific model code with OpenRouter"

## How It Works

When you use these natural language commands, Claude Code will:

1. Launch the OpenRouter MCP server (if not already running)
2. Use the `chat_with_custom_model` tool
3. Ask you for the specific model code you want to use
4. Handle the conversation with your chosen model

## Supported Model Codes

You can use any model available on OpenRouter. Examples include:

- `anthropic/claude-3-opus`
- `anthropic/claude-3-sonnet`
- `meta-llama/llama-3.3-70b-instruct`
- `mistralai/mixtral-8x7b-instruct`
- `openai/gpt-4-turbo`
- `google/gemini-pro`
- And many more...

## Example Usage

### Basic Usage
```
You: "Claude, call the OpenRouter MCP and let me input the model myself"
Claude: "I'll help you use a custom OpenRouter model. What model code would you like to use?"
You: "meta-llama/llama-3.3-70b-instruct"
Claude: [Uses the specified model for the conversation]
```

### With Context
```
You: "I want to use anthropic/claude-3-opus to analyze this code file"
Claude: [Automatically uses claude-3-opus model with your file]
```

## Features

The custom model tool supports:

- **Custom model selection**: Use any OpenRouter model by its exact code
- **Conversation continuity**: Continue existing conversations with the same model
- **File attachments**: Include code files for context
- **Image support**: Attach images for models with vision capabilities
- **Parameter control**: Optionally specify temperature and max_tokens
- **Full context**: All conversation history is maintained

## Technical Details

The `chat_with_custom_model` tool accepts:

- `prompt` (required): Your message
- `custom_model` (required): The exact OpenRouter model code
- `continuation_id` (optional): To continue an existing conversation
- `files` (optional): Array of file paths to include
- `images` (optional): Array of image paths for vision models
- `temperature` (optional): 0.0-2.0, default 0.7
- `max_tokens` (optional): Maximum response tokens

## Benefits

1. **Flexibility**: Use any model available on OpenRouter
2. **Experimentation**: Try different models for different tasks
3. **Specific needs**: Use specialized models for particular use cases
4. **Cost control**: Choose models based on your budget
5. **Latest models**: Access newly released models immediately

## Notes

- Make sure you have a valid OpenRouter API key configured
- Model availability and pricing varies - check OpenRouter's documentation
- Some models may have specific capabilities (vision, function calling, etc.)
- Response quality and speed varies by model