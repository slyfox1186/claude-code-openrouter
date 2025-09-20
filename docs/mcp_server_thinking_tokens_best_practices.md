# OpenRouter MCP Server Implementation with Thinking Token Control: Best Practices Guide 2025

## Table of Contents

1. [Introduction](#introduction)
2. [OpenRouter MCP Server Implementation](#openrouter-mcp-server-implementation)
3. [Thinking Models Token Control](#thinking-models-token-control)
4. [Implementation Best Practices](#implementation-best-practices)
5. [Advanced Techniques](#advanced-techniques)
6. [Cost Optimization Strategies](#cost-optimization-strategies)
7. [Common Pitfalls and Solutions](#common-pitfalls-and-solutions)
8. [Complete Implementation Examples](#complete-implementation-examples)
9. [References](#references)

## Introduction

The Model Context Protocol (MCP) is an open-source standard from Anthropic for connecting AI assistants to external data sources and tools. This guide provides comprehensive best practices for implementing OpenRouter MCP servers with advanced thinking token control for reasoning models like o1, QwQ, and DeepSeek R1.

### Key Technologies Covered
- **OpenRouter API**: Unified interface for multiple AI models
- **MCP Protocol**: Standardized AI tool integration
- **Thinking Models**: o1, QwQ, DeepSeek R1 with reasoning capabilities
- **TypeScript SDK**: Production-ready implementation patterns
- **Token Optimization**: Cost and performance management

## OpenRouter MCP Server Implementation

### Architecture Overview

OpenRouter provides MCP integration by converting MCP (Anthropic) tool definitions to OpenAI-compatible tool definitions. The architecture involves three key components:

1. **MCP Server**: Provides tools and context to AI models
2. **OpenRouter API**: Unified interface for model access
3. **Client Application**: Consumes MCP tools via OpenRouter

### Authentication and Setup

#### API Key Management

```typescript
// Environment configuration
interface Config {
  OPENROUTER_API_KEY: string;
  DEFAULT_MODEL?: string;
  BASE_URL?: string;
}

const config: Config = {
  OPENROUTER_API_KEY: process.env.OPENROUTER_API_KEY!,
  DEFAULT_MODEL: process.env.DEFAULT_MODEL || "anthropic/claude-3.7-sonnet",
  BASE_URL: "https://openrouter.ai/api/v1"
};

// OpenAI SDK configuration for OpenRouter
import OpenAI from 'openai';

const openai = new OpenAI({
  apiKey: config.OPENROUTER_API_KEY,
  baseURL: config.BASE_URL,
});
```

#### Security Best Practices

- **Never commit API keys** to public repositories
- Use environment variables or secure secret management
- Implement key rotation policies
- Monitor usage to detect unauthorized access
- Use the minimum required permissions

### Server Architecture Patterns

#### Basic MCP Server Setup

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const server = new McpServer({
  name: "openrouter-thinking-server",
  version: "1.0.0"
});

// Transport configuration
const transport = new StdioServerTransport();
```

#### Production-Grade Server Template

```typescript
interface ServerConfig {
  name: string;
  version: string;
  observability?: {
    enableTracing: boolean;
    enableMetrics: boolean;
  };
  auth?: {
    enabled: boolean;
    provider: 'jwt' | 'oauth';
  };
}

class ProductionMCPServer {
  private server: McpServer;
  private config: ServerConfig;

  constructor(config: ServerConfig) {
    this.config = config;
    this.server = new McpServer({
      name: config.name,
      version: config.version
    });
    
    this.setupErrorHandling();
    this.setupObservability();
  }

  private setupErrorHandling() {
    this.server.onerror = (error) => {
      console.error("MCP Server Error:", error);
      // Don't exit - let MCP handle reconnection
    };
  }

  private setupObservability() {
    if (this.config.observability?.enableTracing) {
      // OpenTelemetry integration
      this.setupTracing();
    }
  }
}
```

### Request/Response Handling

#### Tool Registration with Zod Validation

```typescript
// Thinking model completion tool
const thinkingCompletionSchema = z.object({
  model: z.string().describe("Model to use (e.g., 'anthropic/claude-3.7-sonnet')"),
  messages: z.array(z.object({
    role: z.enum(["system", "user", "assistant"]),
    content: z.string()
  })),
  reasoning: z.object({
    effort: z.enum(["minimal", "low", "medium", "high"]).optional(),
    max_tokens: z.number().int().positive().max(32000).optional()
  }).optional(),
  max_tokens: z.number().int().positive().optional(),
  temperature: z.number().min(0).max(2).optional(),
  stream: z.boolean().optional().default(false)
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  if (request.params.name === "thinking_completion") {
    const args = thinkingCompletionSchema.parse(request.params.arguments);
    
    try {
      const response = await handleThinkingCompletion(args);
      return {
        content: [{
          type: "text",
          text: JSON.stringify(response, null, 2)
        }]
      };
    } catch (error) {
      throw new McpError(
        ErrorCode.InternalError,
        `Thinking completion failed: ${error.message}`
      );
    }
  }
});
```

#### Error Management

```typescript
enum MCPErrorType {
  AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED",
  RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED",
  MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE",
  THINKING_TOKENS_EXCEEDED = "THINKING_TOKENS_EXCEEDED",
  VALIDATION_ERROR = "VALIDATION_ERROR"
}

class MCPError extends Error {
  constructor(
    public type: MCPErrorType,
    message: string,
    public details?: any
  ) {
    super(message);
    this.name = "MCPError";
  }
}

// Error handling with automatic retry
async function handleThinkingCompletion(args: ThinkingCompletionArgs) {
  const maxRetries = 3;
  let attempt = 0;

  while (attempt < maxRetries) {
    try {
      return await performCompletion(args);
    } catch (error) {
      attempt++;
      
      if (error.status === 429) { // Rate limit
        const delay = Math.pow(2, attempt) * 1000; // Exponential backoff
        await new Promise(resolve => setTimeout(resolve, delay));
        continue;
      }
      
      if (error.status >= 500 && attempt < maxRetries) {
        continue; // Retry server errors
      }
      
      throw new MCPError(
        MCPErrorType.MODEL_UNAVAILABLE,
        `Completion failed after ${attempt} attempts: ${error.message}`,
        { originalError: error, attempt }
      );
    }
  }
}
```

### Rate Limiting and Cost Management

#### Built-in Rate Limiting

```typescript
interface RateLimitConfig {
  requestsPerMinute: number;
  requestsPerDay: number;
  tokensPerMinute: number;
  costLimitPerDay: number; // In dollars
}

class RateLimiter {
  private requests: Map<string, number[]> = new Map();
  private costs: Map<string, number> = new Map();

  constructor(private config: RateLimitConfig) {}

  async checkLimits(userId: string, estimatedCost: number): Promise<void> {
    const now = Date.now();
    const userRequests = this.requests.get(userId) || [];
    
    // Remove old requests (older than 1 minute)
    const recentRequests = userRequests.filter(time => now - time < 60000);
    
    if (recentRequests.length >= this.config.requestsPerMinute) {
      throw new MCPError(
        MCPErrorType.RATE_LIMIT_EXCEEDED,
        "Rate limit exceeded: too many requests per minute"
      );
    }

    // Check daily cost limit
    const dailyCost = this.costs.get(userId) || 0;
    if (dailyCost + estimatedCost > this.config.costLimitPerDay) {
      throw new MCPError(
        MCPErrorType.RATE_LIMIT_EXCEEDED,
        "Daily cost limit exceeded"
      );
    }

    // Update tracking
    recentRequests.push(now);
    this.requests.set(userId, recentRequests);
  }

  updateCost(userId: string, actualCost: number): void {
    const currentCost = this.costs.get(userId) || 0;
    this.costs.set(userId, currentCost + actualCost);
  }
}
```

## Thinking Models Token Control

### Understanding Thinking Tokens

Thinking tokens are internal reasoning tokens that models use before generating their final response. Different models implement thinking tokens differently:

- **OpenAI o1/o3 Series**: Uses `reasoning_effort` parameter
- **Claude 3.7/4.x**: Uses `budget_tokens` parameter
- **DeepSeek R1**: Uses Chain of Thought (CoT) with automatic reasoning

### OpenAI o1 Series Configuration

#### Reasoning Effort Control

```typescript
interface OpenAIReasoningConfig {
  model: string;
  reasoning_effort: "minimal" | "low" | "medium" | "high";
  max_completion_tokens: number;
}

// Effort level mapping
const EFFORT_RATIOS = {
  minimal: 0.05,  // ~5% of max_tokens for reasoning
  low: 0.2,       // ~20% of max_tokens for reasoning
  medium: 0.5,    // ~50% of max_tokens for reasoning
  high: 0.8       // ~80% of max_tokens for reasoning
};

async function createO1Completion(config: OpenAIReasoningConfig, messages: any[]) {
  const reasoningBudget = Math.floor(
    config.max_completion_tokens * EFFORT_RATIOS[config.reasoning_effort]
  );

  // Ensure max_tokens > reasoning budget for final response
  const adjustedMaxTokens = Math.max(
    config.max_completion_tokens,
    reasoningBudget + 100 // Minimum 100 tokens for final response
  );

  const response = await openai.chat.completions.create({
    model: config.model,
    messages,
    reasoning_effort: config.reasoning_effort,
    max_completion_tokens: adjustedMaxTokens,
    // Note: temperature, top_p not supported with reasoning models
  });

  return {
    content: response.choices[0].message.content,
    reasoning_tokens: response.usage?.reasoning_tokens || 0,
    completion_tokens: response.usage?.completion_tokens || 0,
    total_cost: calculateCost(response.usage, config.model)
  };
}
```

#### Dynamic Reasoning Effort

```typescript
function determineReasoningEffort(
  queryComplexity: "simple" | "medium" | "complex",
  userBudget: number
): "minimal" | "low" | "medium" | "high" {
  const complexityMapping = {
    simple: {
      budget_low: "minimal",
      budget_medium: "low",
      budget_high: "medium"
    },
    medium: {
      budget_low: "low",
      budget_medium: "medium",
      budget_high: "high"
    },
    complex: {
      budget_low: "medium",
      budget_medium: "high",
      budget_high: "high"
    }
  };

  const budgetLevel = userBudget < 0.01 ? "budget_low" :
                     userBudget < 0.05 ? "budget_medium" : "budget_high";

  return complexityMapping[queryComplexity][budgetLevel];
}
```

### Claude 3.7+ Budget Tokens

#### Budget Token Implementation

```typescript
interface ClaudeThinkingConfig {
  model: string;
  budget_tokens: number;
  max_tokens: number;
}

async function createClaudeThinking(
  config: ClaudeThinkingConfig, 
  messages: any[]
) {
  // Validate budget constraints
  if (config.budget_tokens > 32000) {
    throw new MCPError(
      MCPErrorType.THINKING_TOKENS_EXCEEDED,
      "Budget tokens cannot exceed 32,000"
    );
  }

  if (config.budget_tokens < 1024) {
    config.budget_tokens = 1024; // Minimum budget
  }

  const response = await openai.chat.completions.create({
    model: config.model,
    messages,
    max_tokens: config.max_tokens,
    thinking: {
      budget_tokens: config.budget_tokens
    }
  });

  return {
    content: response.choices[0].message.content,
    thinking_content: response.choices[0].message.thinking,
    thinking_tokens: response.usage?.thinking_tokens || 0,
    output_tokens: response.usage?.completion_tokens || 0,
    total_cost: calculateClaudeCost(response.usage)
  };
}
```

#### Adaptive Budget Allocation

```typescript
class AdaptiveBudgetManager {
  private performanceHistory: Map<string, ThinkingPerformance[]> = new Map();

  calculateOptimalBudget(
    taskType: string,
    targetQuality: number,
    maxCost: number
  ): number {
    const history = this.performanceHistory.get(taskType) || [];
    
    if (history.length === 0) {
      return 4096; // Default starting budget
    }

    // Find the minimum budget that achieves target quality
    const qualityMet = history
      .filter(h => h.qualityScore >= targetQuality)
      .sort((a, b) => a.budgetUsed - b.budgetUsed);

    if (qualityMet.length === 0) {
      return Math.min(16384, maxCost * 0.8); // Conservative approach
    }

    const optimalBudget = qualityMet[0].budgetUsed;
    
    // Add 20% buffer for safety
    return Math.min(Math.floor(optimalBudget * 1.2), 32000);
  }

  recordPerformance(
    taskType: string,
    budgetUsed: number,
    qualityScore: number,
    cost: number
  ): void {
    const history = this.performanceHistory.get(taskType) || [];
    history.push({
      budgetUsed,
      qualityScore,
      cost,
      timestamp: Date.now()
    });

    // Keep only recent history (last 100 entries)
    if (history.length > 100) {
      history.splice(0, history.length - 100);
    }

    this.performanceHistory.set(taskType, history);
  }
}

interface ThinkingPerformance {
  budgetUsed: number;
  qualityScore: number;
  cost: number;
  timestamp: number;
}
```

### DeepSeek R1 Implementation

#### Chain of Thought Access

```typescript
interface DeepSeekR1Config {
  model: "deepseek-reasoner";
  max_tokens: number;
  enable_cot_display: boolean;
}

async function createDeepSeekCompletion(
  config: DeepSeekR1Config,
  messages: any[]
) {
  const response = await openai.chat.completions.create({
    model: config.model,
    messages,
    max_tokens: config.max_tokens
    // Note: DeepSeek R1 automatically manages thinking tokens
  });

  const choice = response.choices[0];
  
  return {
    content: choice.message.content,
    reasoning_content: choice.message.reasoning_content || null,
    reasoning_tokens: calculateReasoningTokens(choice.message.reasoning_content),
    output_tokens: response.usage?.completion_tokens || 0,
    total_cost: calculateDeepSeekCost(response.usage)
  };
}

function calculateReasoningTokens(reasoningContent: string | null): number {
  if (!reasoningContent) return 0;
  
  // Rough estimation: ~4 characters per token
  return Math.floor(reasoningContent.length / 4);
}
```

### Unified Thinking Token Interface

```typescript
interface UnifiedThinkingRequest {
  model: string;
  messages: any[];
  thinking_config: {
    effort?: "minimal" | "low" | "medium" | "high";
    budget_tokens?: number;
    max_thinking_tokens?: number;
  };
  max_tokens: number;
  stream?: boolean;
}

class UnifiedThinkingClient {
  async createThinkingCompletion(request: UnifiedThinkingRequest) {
    const provider = this.detectProvider(request.model);
    
    switch (provider) {
      case "openai":
        return this.handleOpenAIReasoning(request);
      case "anthropic":
        return this.handleClaudeThinking(request);
      case "deepseek":
        return this.handleDeepSeekReasoning(request);
      default:
        throw new MCPError(
          MCPErrorType.MODEL_UNAVAILABLE,
          `Thinking tokens not supported for provider: ${provider}`
        );
    }
  }

  private detectProvider(model: string): string {
    if (model.includes("openai/") || model.includes("o1") || model.includes("o3")) {
      return "openai";
    }
    if (model.includes("anthropic/") || model.includes("claude")) {
      return "anthropic";
    }
    if (model.includes("deepseek")) {
      return "deepseek";
    }
    return "unknown";
  }

  private async handleOpenAIReasoning(request: UnifiedThinkingRequest) {
    const effort = request.thinking_config.effort || "medium";
    return createO1Completion({
      model: request.model,
      reasoning_effort: effort,
      max_completion_tokens: request.max_tokens
    }, request.messages);
  }

  private async handleClaudeThinking(request: UnifiedThinkingRequest) {
    const budget = request.thinking_config.budget_tokens || 4096;
    return createClaudeThinking({
      model: request.model,
      budget_tokens: budget,
      max_tokens: request.max_tokens
    }, request.messages);
  }
}
```

## Implementation Best Practices

### TypeScript Architecture

#### Strict Type Safety

```typescript
// Never use 'any' - always define proper types
interface MCPToolResponse<T = unknown> {
  content: Array<{
    type: "text" | "image" | "resource";
    text?: string;
    data?: string;
    mimeType?: string;
  }>;
  metadata?: {
    thinking_tokens?: number;
    cost?: number;
    model_used?: string;
    response_time_ms?: number;
  };
}

// Use discriminated unions for tool configurations
type ThinkingModelConfig = 
  | { provider: "openai"; reasoning_effort: "minimal" | "low" | "medium" | "high" }
  | { provider: "anthropic"; budget_tokens: number }
  | { provider: "deepseek"; enable_cot: boolean };

// Proper error typing
type MCPResult<T> = 
  | { success: true; data: T }
  | { success: false; error: MCPError };
```

#### Zod Schema Patterns

```typescript
// Comprehensive validation schemas
const ThinkingRequestSchema = z.object({
  model: z.string().min(1),
  messages: z.array(z.object({
    role: z.enum(["system", "user", "assistant"]),
    content: z.union([
      z.string(),
      z.array(z.object({
        type: z.enum(["text", "image_url"]),
        text: z.string().optional(),
        image_url: z.object({
          url: z.string().url()
        }).optional()
      }))
    ])
  })),
  thinking_config: z.object({
    effort: z.enum(["minimal", "low", "medium", "high"]).optional(),
    budget_tokens: z.number().int().min(1024).max(32000).optional(),
    quality_threshold: z.number().min(0).max(1).optional()
  }).optional(),
  optimization: z.object({
    enable_caching: z.boolean().default(true),
    max_cost: z.number().positive().optional(),
    timeout_ms: z.number().int().positive().default(30000)
  }).optional()
});

// Schema composition for complex tools
const BaseToolSchema = z.object({
  metadata: z.object({
    user_id: z.string(),
    session_id: z.string(),
    timestamp: z.number()
  })
});

const ThinkingToolSchema = BaseToolSchema.extend({
  thinking_request: ThinkingRequestSchema
});
```

#### Modular Tool Architecture

```typescript
abstract class BaseMCPTool<TInput, TOutput> {
  abstract name: string;
  abstract description: string;
  abstract inputSchema: z.ZodSchema<TInput>;

  constructor(protected config: ToolConfig) {}

  async execute(input: TInput): Promise<MCPToolResponse<TOutput>> {
    try {
      const validatedInput = this.inputSchema.parse(input);
      const result = await this.process(validatedInput);
      
      return {
        content: [{
          type: "text",
          text: JSON.stringify(result, null, 2)
        }],
        metadata: {
          response_time_ms: Date.now() - this.startTime,
          cost: this.calculateCost(result)
        }
      };
    } catch (error) {
      throw this.handleError(error);
    }
  }

  protected abstract process(input: TInput): Promise<TOutput>;
  protected abstract calculateCost(result: TOutput): number;
  protected abstract handleError(error: unknown): MCPError;
}

// Concrete implementation
class ThinkingCompletionTool extends BaseMCPTool<ThinkingRequest, ThinkingResponse> {
  name = "thinking_completion";
  description = "Generate responses using thinking models with controlled reasoning";
  inputSchema = ThinkingRequestSchema;

  protected async process(input: ThinkingRequest): Promise<ThinkingResponse> {
    const client = new UnifiedThinkingClient();
    return client.createThinkingCompletion(input);
  }

  protected calculateCost(result: ThinkingResponse): number {
    const inputCost = result.input_tokens * this.getInputRate(result.model);
    const outputCost = result.output_tokens * this.getOutputRate(result.model);
    const thinkingCost = result.thinking_tokens * this.getOutputRate(result.model);
    
    return inputCost + outputCost + thinkingCost;
  }
}
```

### Server Configuration

#### Environment-Based Configuration

```typescript
interface ServerEnvironment {
  NODE_ENV: "development" | "staging" | "production";
  OPENROUTER_API_KEY: string;
  LOG_LEVEL: "debug" | "info" | "warn" | "error";
  ENABLE_TELEMETRY: boolean;
  MAX_THINKING_TOKENS: number;
  COST_LIMIT_PER_USER: number;
}

class ConfigManager {
  private static instance: ConfigManager;
  private config: ServerEnvironment;

  private constructor() {
    this.config = this.loadConfiguration();
    this.validateConfiguration();
  }

  static getInstance(): ConfigManager {
    if (!ConfigManager.instance) {
      ConfigManager.instance = new ConfigManager();
    }
    return ConfigManager.instance;
  }

  private loadConfiguration(): ServerEnvironment {
    return {
      NODE_ENV: (process.env.NODE_ENV as any) || "development",
      OPENROUTER_API_KEY: process.env.OPENROUTER_API_KEY!,
      LOG_LEVEL: (process.env.LOG_LEVEL as any) || "info",
      ENABLE_TELEMETRY: process.env.ENABLE_TELEMETRY === "true",
      MAX_THINKING_TOKENS: parseInt(process.env.MAX_THINKING_TOKENS || "16384"),
      COST_LIMIT_PER_USER: parseFloat(process.env.COST_LIMIT_PER_USER || "10.0")
    };
  }

  private validateConfiguration(): void {
    if (!this.config.OPENROUTER_API_KEY) {
      throw new Error("OPENROUTER_API_KEY is required");
    }

    if (this.config.MAX_THINKING_TOKENS > 32000) {
      console.warn("MAX_THINKING_TOKENS exceeds recommended limit of 32,000");
    }
  }

  get<K extends keyof ServerEnvironment>(key: K): ServerEnvironment[K] {
    return this.config[key];
  }
}
```

#### Transport Management

```typescript
class TransportManager {
  private transports: Map<string, Transport> = new Map();

  registerTransport(name: string, transport: Transport): void {
    this.transports.set(name, transport);
  }

  async connectAll(server: McpServer): Promise<void> {
    const connections = Array.from(this.transports.entries()).map(
      async ([name, transport]) => {
        try {
          await server.connect(transport);
          console.log(`Connected transport: ${name}`);
        } catch (error) {
          console.error(`Failed to connect transport ${name}:`, error);
          throw error;
        }
      }
    );

    await Promise.all(connections);
  }

  async disconnectAll(): Promise<void> {
    for (const [name, transport] of this.transports) {
      try {
        await transport.close();
        console.log(`Disconnected transport: ${name}`);
      } catch (error) {
        console.error(`Error disconnecting ${name}:`, error);
      }
    }
  }
}

// Usage
const transportManager = new TransportManager();

// Stdio transport for local development
transportManager.registerTransport(
  "stdio",
  new StdioServerTransport()
);

// HTTP transport for production
transportManager.registerTransport(
  "http",
  new SSEServerTransport(
    new Server(app), // Hono or Express server
    "/mcp"
  )
);
```

### Streaming Implementation

#### Server-Sent Events (SSE)

```typescript
interface StreamingConfig {
  enable_streaming: boolean;
  chunk_size: number;
  heartbeat_interval: number;
}

class StreamingThinkingClient {
  private config: StreamingConfig;

  constructor(config: StreamingConfig) {
    this.config = config;
  }

  async createStreamingCompletion(
    request: UnifiedThinkingRequest
  ): Promise<AsyncIterable<ThinkingChunk>> {
    if (!this.config.enable_streaming) {
      throw new MCPError(
        MCPErrorType.VALIDATION_ERROR,
        "Streaming is not enabled"
      );
    }

    const response = await openai.chat.completions.create({
      ...this.buildRequestParams(request),
      stream: true
    });

    return this.processStreamingResponse(response);
  }

  private async* processStreamingResponse(
    stream: AsyncIterable<any>
  ): AsyncIterable<ThinkingChunk> {
    let thinkingTokens = 0;
    let outputTokens = 0;

    for await (const chunk of stream) {
      const delta = chunk.choices[0]?.delta;
      
      if (delta?.reasoning) {
        thinkingTokens += this.estimateTokens(delta.reasoning);
        yield {
          type: "thinking",
          content: delta.reasoning,
          tokens: thinkingTokens
        };
      }

      if (delta?.content) {
        outputTokens += this.estimateTokens(delta.content);
        yield {
          type: "output",
          content: delta.content,
          tokens: outputTokens
        };
      }

      if (chunk.choices[0]?.finish_reason) {
        yield {
          type: "complete",
          thinking_tokens: thinkingTokens,
          output_tokens: outputTokens,
          finish_reason: chunk.choices[0].finish_reason
        };
      }
    }
  }

  private estimateTokens(text: string): number {
    // Rough estimation: ~4 characters per token
    return Math.ceil(text.length / 4);
  }
}

interface ThinkingChunk {
  type: "thinking" | "output" | "complete";
  content?: string;
  tokens?: number;
  thinking_tokens?: number;
  output_tokens?: number;
  finish_reason?: string;
}
```

#### Stream Cancellation

```typescript
class CancellableStream {
  private abortController: AbortController;
  private onCancel?: () => void;

  constructor() {
    this.abortController = new AbortController();
  }

  async createCancellableCompletion(
    request: UnifiedThinkingRequest
  ): Promise<AsyncIterable<ThinkingChunk>> {
    const signal = this.abortController.signal;

    const response = await openai.chat.completions.create({
      ...this.buildRequestParams(request),
      stream: true
    }, {
      signal // Pass abort signal to request
    });

    // Set up cancellation handler
    signal.addEventListener('abort', () => {
      if (this.onCancel) {
        this.onCancel();
      }
    });

    return this.processStreamingResponse(response);
  }

  cancel(): void {
    this.abortController.abort();
  }

  onCancellation(callback: () => void): void {
    this.onCancel = callback;
  }
}

// Usage in MCP tool
class StreamingThinkingTool extends BaseMCPTool<any, any> {
  private activeStreams: Map<string, CancellableStream> = new Map();

  async execute(input: any): Promise<MCPToolResponse<any>> {
    const streamId = this.generateStreamId();
    const stream = new CancellableStream();
    
    this.activeStreams.set(streamId, stream);
    
    try {
      const completion = await stream.createCancellableCompletion(input);
      
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            stream_id: streamId,
            message: "Streaming started. Use cancel_stream tool to stop."
          })
        }]
      };
    } finally {
      this.activeStreams.delete(streamId);
    }
  }

  cancelStream(streamId: string): boolean {
    const stream = this.activeStreams.get(streamId);
    if (stream) {
      stream.cancel();
      this.activeStreams.delete(streamId);
      return true;
    }
    return false;
  }
}
```

## Advanced Techniques

### Dynamic Token Allocation

#### Complexity-Based Budgeting

```typescript
interface QueryComplexity {
  syntactic_complexity: number;    // 0-1 based on sentence structure
  semantic_complexity: number;     // 0-1 based on topic difficulty
  reasoning_required: number;      // 0-1 based on logical steps needed
  domain_complexity: number;       // 0-1 based on specialized knowledge
}

class ComplexityAnalyzer {
  analyzeQuery(query: string): QueryComplexity {
    return {
      syntactic_complexity: this.analyzeSyntax(query),
      semantic_complexity: this.analyzeSemantics(query),
      reasoning_required: this.analyzeReasoning(query),
      domain_complexity: this.analyzeDomain(query)
    };
  }

  private analyzeSyntax(query: string): number {
    const sentences = query.split(/[.!?]+/).filter(s => s.trim());
    const avgWordsPerSentence = sentences.reduce((acc, s) => 
      acc + s.trim().split(/\s+/).length, 0) / sentences.length;
    
    // Normalize to 0-1 scale
    return Math.min(avgWordsPerSentence / 30, 1);
  }

  private analyzeSemantics(query: string): number {
    const complexityIndicators = [
      /\b(analyze|compare|evaluate|synthesize|integrate)\b/i,
      /\b(multiple|various|several|different)\b/i,
      /\b(relationship|correlation|causation)\b/i,
      /\b(implication|consequence|impact)\b/i
    ];

    const matches = complexityIndicators.reduce((count, pattern) => 
      count + (pattern.test(query) ? 1 : 0), 0);

    return matches / complexityIndicators.length;
  }

  private analyzeReasoning(query: string): number {
    const reasoningKeywords = [
      /\bwhy\b/i, /\bhow\b/i, /\bexplain\b/i, /\bprove\b/i,
      /\bif.*then\b/i, /\bassume\b/i, /\bgiven.*find\b/i,
      /\bstep.*step\b/i, /\blogical\b/i, /\breason\b/i
    ];

    const matches = reasoningKeywords.reduce((count, pattern) => 
      count + (pattern.test(query) ? 1 : 0), 0);

    return Math.min(matches / 3, 1);
  }

  private analyzeDomain(query: string): number {
    const specializedDomains = [
      /\b(quantum|molecular|biochemical|neurological)\b/i,
      /\b(algorithm|cryptographic|computational)\b/i,
      /\b(legal|constitutional|statutory)\b/i,
      /\b(financial|actuarial|economic)\b/i,
      /\b(medical|clinical|diagnostic)\b/i
    ];

    return specializedDomains.some(pattern => pattern.test(query)) ? 0.8 : 0.2;
  }
}

class DynamicTokenAllocator {
  private complexityAnalyzer = new ComplexityAnalyzer();

  calculateOptimalTokens(
    query: string,
    maxBudget: number,
    qualityTarget: number
  ): number {
    const complexity = this.complexityAnalyzer.analyzeQuery(query);
    
    // Weighted complexity score
    const weights = {
      syntactic_complexity: 0.1,
      semantic_complexity: 0.3,
      reasoning_required: 0.4,
      domain_complexity: 0.2
    };

    const overallComplexity = Object.entries(complexity).reduce(
      (sum, [key, value]) => sum + value * weights[key as keyof typeof weights],
      0
    );

    // Calculate base allocation
    const baseAllocation = Math.floor(maxBudget * 0.3); // 30% minimum
    const complexityAllocation = Math.floor(
      maxBudget * 0.7 * overallComplexity
    );

    // Quality adjustment
    const qualityMultiplier = 0.5 + (qualityTarget * 0.5);
    
    const finalAllocation = Math.floor(
      (baseAllocation + complexityAllocation) * qualityMultiplier
    );

    return Math.max(1024, Math.min(finalAllocation, maxBudget));
  }
}
```

#### Adaptive Learning System

```typescript
interface LearningData {
  query_hash: string;
  allocated_tokens: number;
  actual_tokens_used: number;
  quality_score: number;
  cost: number;
  response_time: number;
  user_feedback?: number; // 1-5 rating
}

class AdaptiveLearningSystem {
  private learningData: LearningData[] = [];
  private modelWeights: Map<string, number> = new Map();

  recordExecution(data: LearningData): void {
    this.learningData.push(data);
    this.updateModelWeights();
    
    // Cleanup old data (keep last 10,000 entries)
    if (this.learningData.length > 10000) {
      this.learningData = this.learningData.slice(-10000);
    }
  }

  private updateModelWeights(): void {
    // Simple gradient descent-like approach
    const recentData = this.learningData.slice(-100); // Last 100 executions
    
    for (const data of recentData) {
      const efficiency = data.actual_tokens_used / data.allocated_tokens;
      const qualityPerCost = data.quality_score / data.cost;
      
      // Adjust weights based on efficiency and quality/cost ratio
      const currentWeight = this.modelWeights.get(data.query_hash) || 1.0;
      const adjustment = this.calculateAdjustment(efficiency, qualityPerCost);
      
      this.modelWeights.set(data.query_hash, currentWeight + adjustment);
    }
  }

  private calculateAdjustment(efficiency: number, qualityPerCost: number): number {
    // Reward efficient token usage and high quality per cost
    const efficiencyScore = efficiency > 0.8 ? 0.1 : -0.05;
    const qualityScore = qualityPerCost > 0.5 ? 0.1 : -0.05;
    
    return (efficiencyScore + qualityScore) * 0.1; // Small adjustments
  }

  predictOptimalTokens(queryHash: string, baseAllocation: number): number {
    const weight = this.modelWeights.get(queryHash) || 1.0;
    return Math.floor(baseAllocation * weight);
  }

  getPerformanceMetrics(): {
    averageEfficiency: number;
    averageQuality: number;
    costEffectiveness: number;
  } {
    if (this.learningData.length === 0) {
      return { averageEfficiency: 0, averageQuality: 0, costEffectiveness: 0 };
    }

    const recent = this.learningData.slice(-1000);
    
    const avgEfficiency = recent.reduce((sum, d) => 
      sum + (d.actual_tokens_used / d.allocated_tokens), 0) / recent.length;
    
    const avgQuality = recent.reduce((sum, d) => 
      sum + d.quality_score, 0) / recent.length;
    
    const costEffectiveness = recent.reduce((sum, d) => 
      sum + (d.quality_score / d.cost), 0) / recent.length;

    return { averageEfficiency, avgQuality, costEffectiveness };
  }
}
```

### Caching Strategies

#### Prompt Caching Implementation

```typescript
interface CacheEntry {
  key: string;
  response: any;
  thinking_tokens: number;
  cost: number;
  timestamp: number;
  hit_count: number;
  quality_score?: number;
}

class ThinkingCache {
  private cache: Map<string, CacheEntry> = new Map();
  private maxSize: number;
  private ttlMs: number;

  constructor(maxSize: number = 10000, ttlMs: number = 24 * 60 * 60 * 1000) {
    this.maxSize = maxSize;
    this.ttlMs = ttlMs;
  }

  generateKey(
    model: string,
    messages: any[],
    thinkingConfig: any
  ): string {
    const content = {
      model,
      messages: messages.map(m => ({ role: m.role, content: m.content })),
      thinking: thinkingConfig
    };
    
    return this.hashObject(content);
  }

  private hashObject(obj: any): string {
    const str = JSON.stringify(obj, Object.keys(obj).sort());
    return require('crypto').createHash('sha256').update(str).digest('hex');
  }

  get(key: string): CacheEntry | null {
    const entry = this.cache.get(key);
    
    if (!entry) return null;
    
    // Check TTL
    if (Date.now() - entry.timestamp > this.ttlMs) {
      this.cache.delete(key);
      return null;
    }

    // Update hit count and return
    entry.hit_count++;
    return entry;
  }

  set(
    key: string,
    response: any,
    thinking_tokens: number,
    cost: number,
    quality_score?: number
  ): void {
    // Evict if cache is full
    if (this.cache.size >= this.maxSize) {
      this.evictLeastUsed();
    }

    this.cache.set(key, {
      key,
      response,
      thinking_tokens,
      cost,
      timestamp: Date.now(),
      hit_count: 0,
      quality_score
    });
  }

  private evictLeastUsed(): void {
    let leastUsedKey = '';
    let minHits = Infinity;
    let oldestTime = Infinity;

    for (const [key, entry] of this.cache) {
      // Prefer evicting entries with fewer hits, then older entries
      if (entry.hit_count < minHits || 
          (entry.hit_count === minHits && entry.timestamp < oldestTime)) {
        leastUsedKey = key;
        minHits = entry.hit_count;
        oldestTime = entry.timestamp;
      }
    }

    if (leastUsedKey) {
      this.cache.delete(leastUsedKey);
    }
  }

  getCacheStats(): {
    size: number;
    hitRate: number;
    totalSavings: number;
    averageQuality: number;
  } {
    const entries = Array.from(this.cache.values());
    
    const totalHits = entries.reduce((sum, e) => sum + e.hit_count, 0);
    const totalRequests = entries.length + totalHits;
    const hitRate = totalRequests > 0 ? totalHits / totalRequests : 0;
    
    const totalSavings = entries.reduce((sum, e) => 
      sum + (e.cost * e.hit_count), 0);
    
    const qualityEntries = entries.filter(e => e.quality_score !== undefined);
    const averageQuality = qualityEntries.length > 0 
      ? qualityEntries.reduce((sum, e) => sum + e.quality_score!, 0) / qualityEntries.length
      : 0;

    return {
      size: this.cache.size,
      hitRate,
      totalSavings,
      averageQuality
    };
  }
}

// Integration with thinking client
class CachedThinkingClient extends UnifiedThinkingClient {
  private cache = new ThinkingCache();

  async createThinkingCompletion(request: UnifiedThinkingRequest) {
    const cacheKey = this.cache.generateKey(
      request.model,
      request.messages,
      request.thinking_config
    );

    // Check cache first
    const cached = this.cache.get(cacheKey);
    if (cached) {
      return {
        ...cached.response,
        cache_hit: true,
        cached_cost_savings: cached.cost
      };
    }

    // Generate new response
    const response = await super.createThinkingCompletion(request);
    
    // Cache the response
    this.cache.set(
      cacheKey,
      response,
      response.thinking_tokens || 0,
      response.cost || 0,
      response.quality_score
    );

    return {
      ...response,
      cache_hit: false
    };
  }
}
```

### Parallel Processing

#### Concurrent Model Requests

```typescript
interface ParallelRequest {
  id: string;
  model: string;
  messages: any[];
  thinking_config: any;
  priority: number;
}

interface ParallelResponse {
  id: string;
  response: any;
  thinking_tokens: number;
  cost: number;
  response_time: number;
  error?: Error;
}

class ParallelThinkingProcessor {
  private maxConcurrency: number;
  private queue: ParallelRequest[] = [];
  private processing: Set<string> = new Set();

  constructor(maxConcurrency: number = 5) {
    this.maxConcurrency = maxConcurrency;
  }

  async processRequests(
    requests: ParallelRequest[]
  ): Promise<ParallelResponse[]> {
    // Sort by priority (higher number = higher priority)
    const sortedRequests = [...requests].sort((a, b) => b.priority - a.priority);
    
    this.queue.push(...sortedRequests);
    
    const results = await Promise.allSettled(
      this.queue.map(request => this.processRequest(request))
    );

    return results.map((result, index) => {
      const request = this.queue[index];
      
      if (result.status === 'fulfilled') {
        return result.value;
      } else {
        return {
          id: request.id,
          response: null,
          thinking_tokens: 0,
          cost: 0,
          response_time: 0,
          error: result.reason
        };
      }
    });
  }

  private async processRequest(request: ParallelRequest): Promise<ParallelResponse> {
    // Wait for available slot
    await this.waitForSlot();
    
    this.processing.add(request.id);
    const startTime = Date.now();

    try {
      const client = new CachedThinkingClient();
      const response = await client.createThinkingCompletion({
        model: request.model,
        messages: request.messages,
        thinking_config: request.thinking_config
      });

      return {
        id: request.id,
        response,
        thinking_tokens: response.thinking_tokens || 0,
        cost: response.cost || 0,
        response_time: Date.now() - startTime
      };
    } finally {
      this.processing.delete(request.id);
    }
  }

  private async waitForSlot(): Promise<void> {
    while (this.processing.size >= this.maxConcurrency) {
      await new Promise(resolve => setTimeout(resolve, 100));
    }
  }

  getQueueStatus(): {
    queued: number;
    processing: number;
    capacity: number;
  } {
    return {
      queued: this.queue.length,
      processing: this.processing.size,
      capacity: this.maxConcurrency
    };
  }
}

// Usage in MCP tool
class BatchThinkingTool extends BaseMCPTool<any, any> {
  private processor = new ParallelThinkingProcessor();

  async execute(input: {
    requests: Array<{
      model: string;
      messages: any[];
      thinking_config?: any;
      priority?: number;
    }>
  }): Promise<MCPToolResponse<any>> {
    const parallelRequests: ParallelRequest[] = input.requests.map((req, index) => ({
      id: `req_${index}`,
      model: req.model,
      messages: req.messages,
      thinking_config: req.thinking_config || {},
      priority: req.priority || 1
    }));

    const results = await this.processor.processRequests(parallelRequests);
    
    const summary = {
      total_requests: results.length,
      successful: results.filter(r => !r.error).length,
      failed: results.filter(r => r.error).length,
      total_thinking_tokens: results.reduce((sum, r) => sum + r.thinking_tokens, 0),
      total_cost: results.reduce((sum, r) => sum + r.cost, 0),
      average_response_time: results.reduce((sum, r) => sum + r.response_time, 0) / results.length
    };

    return {
      content: [{
        type: "text",
        text: JSON.stringify({ summary, results }, null, 2)
      }]
    };
  }
}
```

## Cost Optimization Strategies

### Real-Time Cost Monitoring

```typescript
interface CostTracker {
  input_tokens: number;
  output_tokens: number;
  thinking_tokens: number;
  total_cost: number;
  model_used: string;
  timestamp: number;
}

class CostMonitor {
  private costs: CostTracker[] = [];
  private dailyLimits: Map<string, number> = new Map();
  private monthlyLimits: Map<string, number> = new Map();

  // Model pricing (per 1M tokens)
  private modelPricing = {
    "openai/o1": { input: 15.0, output: 60.0 },
    "openai/o1-mini": { input: 3.0, output: 12.0 },
    "openai/o3-mini": { input: 1.25, output: 10.0 },
    "anthropic/claude-3.7-sonnet": { input: 3.0, output: 15.0 },
    "deepseek/deepseek-reasoner": { input: 0.55, output: 2.19 }
  };

  calculateCost(
    model: string,
    inputTokens: number,
    outputTokens: number,
    thinkingTokens: number = 0
  ): number {
    const pricing = this.modelPricing[model];
    if (!pricing) {
      throw new Error(`Pricing not found for model: ${model}`);
    }

    const inputCost = (inputTokens / 1000000) * pricing.input;
    const outputCost = ((outputTokens + thinkingTokens) / 1000000) * pricing.output;
    
    return inputCost + outputCost;
  }

  trackUsage(
    model: string,
    inputTokens: number,
    outputTokens: number,
    thinkingTokens: number,
    userId?: string
  ): CostTracker {
    const cost = this.calculateCost(model, inputTokens, outputTokens, thinkingTokens);
    
    const tracker: CostTracker = {
      input_tokens: inputTokens,
      output_tokens: outputTokens,
      thinking_tokens: thinkingTokens,
      total_cost: cost,
      model_used: model,
      timestamp: Date.now()
    };

    this.costs.push(tracker);
    
    // Check limits
    if (userId) {
      this.checkUserLimits(userId, cost);
    }

    return tracker;
  }

  private checkUserLimits(userId: string, newCost: number): void {
    const dailySpent = this.getDailySpent(userId);
    const monthlySpent = this.getMonthlySpent(userId);
    
    const dailyLimit = this.dailyLimits.get(userId) || 50.0;
    const monthlyLimit = this.monthlyLimits.get(userId) || 1000.0;

    if (dailySpent + newCost > dailyLimit) {
      throw new MCPError(
        MCPErrorType.RATE_LIMIT_EXCEEDED,
        `Daily cost limit exceeded: $${dailySpent + newCost} > $${dailyLimit}`
      );
    }

    if (monthlySpent + newCost > monthlyLimit) {
      throw new MCPError(
        MCPErrorType.RATE_LIMIT_EXCEEDED,
        `Monthly cost limit exceeded: $${monthlySpent + newCost} > $${monthlyLimit}`
      );
    }
  }

  getDailySpent(userId: string): number {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    return this.costs
      .filter(c => c.timestamp >= today.getTime())
      .reduce((sum, c) => sum + c.total_cost, 0);
  }

  getMonthlySpent(userId: string): number {
    const thisMonth = new Date();
    thisMonth.setDate(1);
    thisMonth.setHours(0, 0, 0, 0);
    
    return this.costs
      .filter(c => c.timestamp >= thisMonth.getTime())
      .reduce((sum, c) => sum + c.total_cost, 0);
  }

  getCostReport(userId?: string): {
    totalCost: number;
    totalThinkingTokens: number;
    totalOutputTokens: number;
    averageCostPerRequest: number;
    modelBreakdown: Map<string, number>;
    dailyTrend: Array<{ date: string; cost: number }>;
  } {
    const relevantCosts = userId 
      ? this.costs // In real implementation, filter by userId
      : this.costs;

    const totalCost = relevantCosts.reduce((sum, c) => sum + c.total_cost, 0);
    const totalThinkingTokens = relevantCosts.reduce((sum, c) => sum + c.thinking_tokens, 0);
    const totalOutputTokens = relevantCosts.reduce((sum, c) => sum + c.output_tokens, 0);
    const averageCostPerRequest = relevantCosts.length > 0 ? totalCost / relevantCosts.length : 0;

    const modelBreakdown = new Map<string, number>();
    for (const cost of relevantCosts) {
      const current = modelBreakdown.get(cost.model_used) || 0;
      modelBreakdown.set(cost.model_used, current + cost.total_cost);
    }

    // Daily trend for last 30 days
    const dailyTrend: Array<{ date: string; cost: number }> = [];
    for (let i = 29; i >= 0; i--) {
      const date = new Date();
      date.setDate(date.getDate() - i);
      date.setHours(0, 0, 0, 0);
      
      const nextDay = new Date(date);
      nextDay.setDate(nextDay.getDate() + 1);
      
      const dayCost = relevantCosts
        .filter(c => c.timestamp >= date.getTime() && c.timestamp < nextDay.getTime())
        .reduce((sum, c) => sum + c.total_cost, 0);
      
      dailyTrend.push({
        date: date.toISOString().split('T')[0],
        cost: dayCost
      });
    }

    return {
      totalCost,
      totalThinkingTokens,
      totalOutputTokens,
      averageCostPerRequest,
      modelBreakdown,
      dailyTrend
    };
  }
}
```

### Budget-Aware Model Selection

```typescript
interface ModelCapability {
  reasoning_quality: number;  // 0-1 scale
  speed: number;             // tokens/second
  cost_per_1k_tokens: number;
  max_thinking_tokens: number;
  supports_streaming: boolean;
}

class BudgetAwareModelSelector {
  private modelCapabilities: Map<string, ModelCapability> = new Map([
    ["openai/o1", {
      reasoning_quality: 0.95,
      speed: 15,
      cost_per_1k_tokens: 0.075,
      max_thinking_tokens: 65536,
      supports_streaming: true
    }],
    ["openai/o1-mini", {
      reasoning_quality: 0.85,
      speed: 25,
      cost_per_1k_tokens: 0.015,
      max_thinking_tokens: 65536,
      supports_streaming: true
    }],
    ["anthropic/claude-3.7-sonnet", {
      reasoning_quality: 0.88,
      speed: 30,
      cost_per_1k_tokens: 0.018,
      max_thinking_tokens: 32000,
      supports_streaming: true
    }],
    ["deepseek/deepseek-reasoner", {
      reasoning_quality: 0.80,
      speed: 21,
      cost_per_1k_tokens: 0.0027,
      max_thinking_tokens: 23000,
      supports_streaming: false
    }]
  ]);

  selectOptimalModel(
    requirements: {
      min_quality: number;
      max_cost_per_request: number;
      estimated_tokens: number;
      require_streaming?: boolean;
      max_response_time?: number;
    }
  ): string {
    const candidates = Array.from(this.modelCapabilities.entries())
      .filter(([model, caps]) => {
        // Filter by quality requirement
        if (caps.reasoning_quality < requirements.min_quality) return false;
        
        // Filter by streaming requirement
        if (requirements.require_streaming && !caps.supports_streaming) return false;
        
        // Filter by cost requirement
        const estimatedCost = (requirements.estimated_tokens / 1000) * caps.cost_per_1k_tokens;
        if (estimatedCost > requirements.max_cost_per_request) return false;
        
        // Filter by response time requirement
        if (requirements.max_response_time) {
          const estimatedTime = requirements.estimated_tokens / caps.speed;
          if (estimatedTime > requirements.max_response_time) return false;
        }
        
        return true;
      });

    if (candidates.length === 0) {
      throw new MCPError(
        MCPErrorType.MODEL_UNAVAILABLE,
        "No models meet the specified requirements"
      );
    }

    // Select the most cost-effective model that meets requirements
    const selected = candidates.reduce((best, current) => {
      const [bestModel, bestCaps] = best;
      const [currentModel, currentCaps] = current;
      
      // Calculate value score (quality per dollar)
      const bestValue = bestCaps.reasoning_quality / bestCaps.cost_per_1k_tokens;
      const currentValue = currentCaps.reasoning_quality / currentCaps.cost_per_1k_tokens;
      
      return currentValue > bestValue ? current : best;
    });

    return selected[0];
  }

  estimateRequestCost(
    model: string,
    inputTokens: number,
    expectedOutputTokens: number,
    thinkingTokensRatio: number = 0.5
  ): number {
    const caps = this.modelCapabilities.get(model);
    if (!caps) {
      throw new Error(`Unknown model: ${model}`);
    }

    const thinkingTokens = expectedOutputTokens * thinkingTokensRatio;
    const totalTokens = inputTokens + expectedOutputTokens + thinkingTokens;
    
    return (totalTokens / 1000) * caps.cost_per_1k_tokens;
  }

  getModelRecommendations(
    taskType: "simple" | "medium" | "complex",
    budgetTier: "budget" | "standard" | "premium"
  ): string[] {
    const taskRequirements = {
      simple: { min_quality: 0.7, complexity_factor: 1.0 },
      medium: { min_quality: 0.8, complexity_factor: 1.5 },
      complex: { min_quality: 0.9, complexity_factor: 2.0 }
    };

    const budgetLimits = {
      budget: 0.01,      // $0.01 per request
      standard: 0.05,    // $0.05 per request
      premium: 0.20      // $0.20 per request
    };

    const task = taskRequirements[taskType];
    const budget = budgetLimits[budgetTier];

    const estimatedTokens = 2000 * task.complexity_factor;

    try {
      const primary = this.selectOptimalModel({
        min_quality: task.min_quality,
        max_cost_per_request: budget,
        estimated_tokens: estimatedTokens
      });

      // Also suggest alternatives
      const alternatives = Array.from(this.modelCapabilities.entries())
        .filter(([model, caps]) => 
          model !== primary && 
          caps.reasoning_quality >= task.min_quality * 0.9
        )
        .sort((a, b) => a[1].cost_per_1k_tokens - b[1].cost_per_1k_tokens)
        .slice(0, 2)
        .map(([model]) => model);

      return [primary, ...alternatives];
    } catch (error) {
      // If no models meet requirements, return cheapest options
      return Array.from(this.modelCapabilities.entries())
        .sort((a, b) => a[1].cost_per_1k_tokens - b[1].cost_per_1k_tokens)
        .slice(0, 3)
        .map(([model]) => model);
    }
  }
}
```

### Provider Routing Optimization

```typescript
interface ProviderRoute {
  provider: string;
  models: string[];
  latency_avg: number;
  reliability_score: number;
  cost_multiplier: number;
  fallback_providers: string[];
}

class ProviderRouter {
  private routes: Map<string, ProviderRoute> = new Map();
  private failureHistory: Map<string, number[]> = new Map();

  constructor() {
    this.initializeRoutes();
  }

  private initializeRoutes(): void {
    this.routes.set("openai", {
      provider: "openai",
      models: ["o1", "o1-mini", "o3-mini"],
      latency_avg: 2500,
      reliability_score: 0.99,
      cost_multiplier: 1.0,
      fallback_providers: ["anthropic"]
    });

    this.routes.set("anthropic", {
      provider: "anthropic",
      models: ["claude-3.7-sonnet", "claude-4"],
      latency_avg: 1800,
      reliability_score: 0.98,
      cost_multiplier: 0.8,
      fallback_providers: ["openai", "deepseek"]
    });

    this.routes.set("deepseek", {
      provider: "deepseek",
      models: ["deepseek-reasoner"],
      latency_avg: 3200,
      reliability_score: 0.95,
      cost_multiplier: 0.2,
      fallback_providers: ["anthropic"]
    });
  }

  async routeRequest(
    model: string,
    request: any,
    preferences: {
      prioritize: "cost" | "speed" | "reliability";
      max_retries: number;
    }
  ): Promise<any> {
    const provider = this.getProviderForModel(model);
    const route = this.routes.get(provider);
    
    if (!route) {
      throw new MCPError(
        MCPErrorType.MODEL_UNAVAILABLE,
        `No route found for model: ${model}`
      );
    }

    // Try primary provider
    try {
      return await this.executeRequest(provider, model, request);
    } catch (error) {
      this.recordFailure(provider);
      
      if (preferences.max_retries <= 0) {
        throw error;
      }

      // Try fallback providers
      for (const fallbackProvider of route.fallback_providers) {
        try {
          // Find equivalent model on fallback provider
          const fallbackModel = this.findEquivalentModel(model, fallbackProvider);
          if (fallbackModel) {
            return await this.executeRequest(fallbackProvider, fallbackModel, request);
          }
        } catch (fallbackError) {
          this.recordFailure(fallbackProvider);
          continue;
        }
      }

      throw new MCPError(
        MCPErrorType.MODEL_UNAVAILABLE,
        `All providers failed for model: ${model}`
      );
    }
  }

  private getProviderForModel(model: string): string {
    for (const [provider, route] of this.routes) {
      if (route.models.some(m => model.includes(m))) {
        return provider;
      }
    }
    throw new Error(`Unknown provider for model: ${model}`);
  }

  private findEquivalentModel(model: string, targetProvider: string): string | null {
    const route = this.routes.get(targetProvider);
    if (!route) return null;

    // Simple mapping - in production, use more sophisticated logic
    const modelMappings = {
      "o1": "claude-3.7-sonnet",
      "o1-mini": "claude-3.7-sonnet", 
      "claude-3.7-sonnet": "o1-mini",
      "deepseek-reasoner": "claude-3.7-sonnet"
    };

    const baseModel = model.split('/').pop() || model;
    const equivalent = modelMappings[baseModel];
    
    return equivalent && route.models.includes(equivalent) 
      ? `${targetProvider}/${equivalent}` 
      : null;
  }

  private async executeRequest(
    provider: string,
    model: string,
    request: any
  ): Promise<any> {
    // Provider-specific request execution
    // This would integrate with actual provider SDKs
    console.log(`Executing request on ${provider} with model ${model}`);
    
    // Simulate request execution
    await new Promise(resolve => setTimeout(resolve, 100));
    
    return { provider, model, result: "success" };
  }

  private recordFailure(provider: string): void {
    const failures = this.failureHistory.get(provider) || [];
    failures.push(Date.now());
    
    // Keep only failures from last hour
    const oneHourAgo = Date.now() - 60 * 60 * 1000;
    const recentFailures = failures.filter(time => time > oneHourAgo);
    
    this.failureHistory.set(provider, recentFailures);
    
    // Update reliability score
    const route = this.routes.get(provider);
    if (route && recentFailures.length > 5) {
      route.reliability_score = Math.max(0.5, route.reliability_score * 0.95);
    }
  }

  getProviderHealth(): Map<string, {
    reliability: number;
    recent_failures: number;
    avg_latency: number;
    status: "healthy" | "degraded" | "unhealthy";
  }> {
    const health = new Map();
    
    for (const [provider, route] of this.routes) {
      const failures = this.failureHistory.get(provider) || [];
      const status = route.reliability_score > 0.95 ? "healthy" :
                    route.reliability_score > 0.8 ? "degraded" : "unhealthy";
      
      health.set(provider, {
        reliability: route.reliability_score,
        recent_failures: failures.length,
        avg_latency: route.latency_avg,
        status
      });
    }
    
    return health;
  }
}
```

## Common Pitfalls and Solutions

### Authentication Issues

**Problem**: API key exposure and rotation challenges
```typescript
// ❌ Bad: Hardcoded API keys
const API_KEY = "sk-1234567890abcdef";

// ✅ Good: Secure key management
class SecureKeyManager {
  private keyRotationInterval = 24 * 60 * 60 * 1000; // 24 hours
  private lastRotation = 0;

  async getValidKey(): Promise<string> {
    if (this.shouldRotateKey()) {
      await this.rotateKey();
    }
    return this.getCurrentKey();
  }

  private shouldRotateKey(): boolean {
    return Date.now() - this.lastRotation > this.keyRotationInterval;
  }

  private async rotateKey(): Promise<void> {
    // Implement key rotation logic
    this.lastRotation = Date.now();
  }

  private getCurrentKey(): string {
    const key = process.env.OPENROUTER_API_KEY;
    if (!key) {
      throw new MCPError(
        MCPErrorType.AUTHENTICATION_FAILED,
        "API key not found in environment"
      );
    }
    return key;
  }
}
```

### Token Budget Misconfiguration

**Problem**: Thinking tokens exceeding limits or inefficient allocation
```typescript
// ❌ Bad: No validation or optimization
async function createCompletion(budgetTokens: number) {
  return await openai.chat.completions.create({
    thinking: { budget_tokens: budgetTokens } // No validation
  });
}

// ✅ Good: Proper validation and optimization
class BudgetValidator {
  private static readonly MIN_BUDGET = 1024;
  private static readonly MAX_BUDGET = 32000;
  private static readonly RECOMMENDED_RATIOS = {
    simple: 0.1,   // 10% of max_tokens
    medium: 0.3,   // 30% of max_tokens
    complex: 0.6   // 60% of max_tokens
  };

  static validateAndOptimize(
    requestedBudget: number,
    maxTokens: number,
    complexity: keyof typeof BudgetValidator.RECOMMENDED_RATIOS
  ): number {
    // Validate range
    if (requestedBudget < this.MIN_BUDGET) {
      console.warn(`Budget ${requestedBudget} below minimum, using ${this.MIN_BUDGET}`);
      requestedBudget = this.MIN_BUDGET;
    }
    
    if (requestedBudget > this.MAX_BUDGET) {
      console.warn(`Budget ${requestedBudget} above maximum, using ${this.MAX_BUDGET}`);
      requestedBudget = this.MAX_BUDGET;
    }

    // Optimize based on complexity
    const recommendedRatio = this.RECOMMENDED_RATIOS[complexity];
    const recommendedBudget = Math.floor(maxTokens * recommendedRatio);
    
    // Use the minimum of requested and recommended
    const optimizedBudget = Math.min(requestedBudget, recommendedBudget);
    
    // Ensure we leave room for final response
    const maxAllowedBudget = Math.floor(maxTokens * 0.8);
    
    return Math.min(optimizedBudget, maxAllowedBudget);
  }
}
```

### Error Handling Anti-patterns

**Problem**: Poor error handling leading to cascading failures
```typescript
// ❌ Bad: Swallowing errors or crashing
async function badErrorHandling() {
  try {
    return await someAsyncOperation();
  } catch (error) {
    console.log("Something went wrong"); // Lost error details
    return null; // Hides the problem
  }
}

// ✅ Good: Comprehensive error handling
class RobustErrorHandler {
  static async withRetry<T>(
    operation: () => Promise<T>,
    options: {
      maxRetries: number;
      backoffMs: number;
      retryableErrors: string[];
    }
  ): Promise<T> {
    let lastError: Error;
    
    for (let attempt = 1; attempt <= options.maxRetries; attempt++) {
      try {
        return await operation();
      } catch (error) {
        lastError = error as Error;
        
        // Check if error is retryable
        const isRetryable = options.retryableErrors.some(errType => 
          error.message.includes(errType) || error.code === errType
        );
        
        if (!isRetryable || attempt === options.maxRetries) {
          break;
        }
        
        // Exponential backoff
        const delay = options.backoffMs * Math.pow(2, attempt - 1);
        await new Promise(resolve => setTimeout(resolve, delay));
        
        console.warn(
          `Attempt ${attempt} failed, retrying in ${delay}ms: ${error.message}`
        );
      }
    }
    
    throw new MCPError(
      MCPErrorType.INTERNAL_ERROR,
      `Operation failed after ${options.maxRetries} attempts`,
      { originalError: lastError }
    );
  }
}

// Usage
const result = await RobustErrorHandler.withRetry(
  () => thinkingClient.createCompletion(request),
  {
    maxRetries: 3,
    backoffMs: 1000,
    retryableErrors: ["rate_limit", "timeout", "server_error"]
  }
);
```

### Memory Leaks in Streaming

**Problem**: Unclosed streams and event listeners
```typescript
// ❌ Bad: Memory leaks from unclosed streams
async function badStreaming() {
  const stream = await openai.chat.completions.create({
    stream: true
  });
  
  for await (const chunk of stream) {
    console.log(chunk);
    // No cleanup, potential memory leak
  }
}

// ✅ Good: Proper stream management
class StreamManager {
  private activeStreams = new Set<AbortController>();

  async createManagedStream(request: any): Promise<AsyncIterable<any>> {
    const abortController = new AbortController();
    this.activeStreams.add(abortController);
    
    try {
      const stream = await openai.chat.completions.create({
        ...request,
        stream: true
      }, {
        signal: abortController.signal
      });
      
      return this.wrapStreamWithCleanup(stream, abortController);
    } catch (error) {
      this.activeStreams.delete(abortController);
      throw error;
    }
  }

  private async* wrapStreamWithCleanup(
    stream: AsyncIterable<any>,
    controller: AbortController
  ): AsyncIterable<any> {
    try {
      for await (const chunk of stream) {
        if (controller.signal.aborted) {
          break;
        }
        yield chunk;
      }
    } finally {
      this.activeStreams.delete(controller);
    }
  }

  cleanup(): void {
    for (const controller of this.activeStreams) {
      controller.abort();
    }
    this.activeStreams.clear();
  }
}

// Ensure cleanup on process exit
process.on('SIGTERM', () => {
  streamManager.cleanup();
});
```

### Schema Validation Errors

**Problem**: Runtime errors due to invalid tool inputs
```typescript
// ❌ Bad: No validation, runtime errors
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const model = request.params.arguments.model; // Might be undefined
  const messages = request.params.arguments.messages; // Might be wrong format
  
  // Will crash if arguments are invalid
  return await client.createCompletion({ model, messages });
});

// ✅ Good: Comprehensive validation with helpful errors
const ThinkingToolInputSchema = z.object({
  model: z.string()
    .min(1, "Model name cannot be empty")
    .refine(model => 
      model.includes("openai/") || 
      model.includes("anthropic/") || 
      model.includes("deepseek/"),
      "Model must be from supported provider"
    ),
  messages: z.array(
    z.object({
      role: z.enum(["system", "user", "assistant"]),
      content: z.string().min(1, "Message content cannot be empty")
    })
  ).min(1, "At least one message is required"),
  thinking_config: z.object({
    effort: z.enum(["minimal", "low", "medium", "high"]).optional(),
    budget_tokens: z.number()
      .int("Budget tokens must be an integer")
      .min(1024, "Minimum budget is 1024 tokens")
      .max(32000, "Maximum budget is 32000 tokens")
      .optional()
  }).optional()
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  try {
    const validatedArgs = ThinkingToolInputSchema.parse(request.params.arguments);
    return await client.createCompletion(validatedArgs);
  } catch (error) {
    if (error instanceof z.ZodError) {
      throw new McpError(
        ErrorCode.InvalidParams,
        `Invalid tool arguments: ${error.errors.map(e => e.message).join(", ")}`,
        { validationErrors: error.errors }
      );
    }
    throw error;
  }
});
```

## Complete Implementation Examples

### Basic OpenRouter MCP Server

```typescript
#!/usr/bin/env node

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListToolsRequestSchema } from "@modelcontextprotocol/sdk/types.js";
import { z } from "zod";
import OpenAI from "openai";

// Configuration
const config = {
  apiKey: process.env.OPENROUTER_API_KEY!,
  baseURL: "https://openrouter.ai/api/v1",
  defaultModel: "anthropic/claude-3.7-sonnet"
};

// Initialize OpenAI client for OpenRouter
const openai = new OpenAI({
  apiKey: config.apiKey,
  baseURL: config.baseURL
});

// Input validation schemas
const ThinkingCompletionSchema = z.object({
  model: z.string().default(config.defaultModel),
  messages: z.array(z.object({
    role: z.enum(["system", "user", "assistant"]),
    content: z.string()
  })),
  thinking_config: z.object({
    effort: z.enum(["minimal", "low", "medium", "high"]).optional(),
    budget_tokens: z.number().int().min(1024).max(32000).optional()
  }).optional(),
  max_tokens: z.number().int().positive().optional().default(4096),
  stream: z.boolean().optional().default(false)
});

// Initialize MCP server
const server = new McpServer({
  name: "openrouter-thinking-server",
  version: "1.0.0"
});

// Register tools
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "thinking_completion",
      description: "Generate responses using thinking models with controlled reasoning",
      inputSchema: {
        type: "object",
        properties: {
          model: {
            type: "string",
            description: "Model to use (default: anthropic/claude-3.7-sonnet)",
            default: config.defaultModel
          },
          messages: {
            type: "array",
            items: {
              type: "object",
              properties: {
                role: { type: "string", enum: ["system", "user", "assistant"] },
                content: { type: "string" }
              },
              required: ["role", "content"]
            },
            description: "Array of chat messages"
          },
          thinking_config: {
            type: "object",
            properties: {
              effort: {
                type: "string",
                enum: ["minimal", "low", "medium", "high"],
                description: "Reasoning effort level"
              },
              budget_tokens: {
                type: "number",
                minimum: 1024,
                maximum: 32000,
                description: "Maximum thinking tokens to use"
              }
            },
            description: "Thinking/reasoning configuration"
          },
          max_tokens: {
            type: "number",
            minimum: 1,
            default: 4096,
            description: "Maximum response tokens"
          },
          stream: {
            type: "boolean",
            default: false,
            description: "Enable streaming response"
          }
        },
        required: ["messages"]
      }
    }
  ]
}));

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  if (request.params.name === "thinking_completion") {
    try {
      const args = ThinkingCompletionSchema.parse(request.params.arguments);
      
      // Build request parameters
      const requestParams: any = {
        model: args.model,
        messages: args.messages,
        max_tokens: args.max_tokens,
        stream: args.stream
      };

      // Add thinking/reasoning parameters based on model
      if (args.thinking_config) {
        if (args.model.includes("anthropic/") && args.thinking_config.budget_tokens) {
          requestParams.thinking = {
            budget_tokens: args.thinking_config.budget_tokens
          };
        } else if (args.model.includes("openai/") && args.thinking_config.effort) {
          requestParams.reasoning_effort = args.thinking_config.effort;
        }
      }

      // Make API request
      const response = await openai.chat.completions.create(requestParams);
      
      // Extract response data
      const choice = response.choices[0];
      const usage = response.usage;
      
      const result = {
        content: choice.message.content,
        thinking_content: choice.message.thinking || null,
        reasoning_content: choice.message.reasoning || null,
        finish_reason: choice.finish_reason,
        usage: {
          input_tokens: usage?.prompt_tokens || 0,
          output_tokens: usage?.completion_tokens || 0,
          thinking_tokens: usage?.thinking_tokens || 0,
          reasoning_tokens: usage?.reasoning_tokens || 0,
          total_tokens: usage?.total_tokens || 0
        },
        model_used: args.model
      };

      return {
        content: [{
          type: "text",
          text: JSON.stringify(result, null, 2)
        }]
      };

    } catch (error) {
      console.error("Thinking completion error:", error);
      
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            error: "Thinking completion failed",
            message: error.message,
            type: error.constructor.name
          }, null, 2)
        }],
        isError: true
      };
    }
  }

  throw new Error(`Unknown tool: ${request.params.name}`);
});

// Start server
async function main() {
  if (!config.apiKey) {
    console.error("OPENROUTER_API_KEY environment variable is required");
    process.exit(1);
  }

  const transport = new StdioServerTransport();
  
  await server.connect(transport);
  console.error("OpenRouter Thinking MCP Server running on stdio");
}

main().catch((error) => {
  console.error("Failed to start server:", error);
  process.exit(1);
});
```

### Package.json Configuration

```json
{
  "name": "openrouter-thinking-mcp-server",
  "version": "1.0.0",
  "description": "Production-grade OpenRouter MCP server with thinking token control",
  "main": "dist/server.js",
  "type": "module",
  "scripts": {
    "build": "tsc",
    "dev": "tsx watch src/server.ts",
    "start": "node dist/server.js",
    "test": "vitest",
    "test:coverage": "vitest --coverage",
    "lint": "eslint src/**/*.ts",
    "lint:fix": "eslint src/**/*.ts --fix",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "@modelcontextprotocol/sdk": "^1.0.0",
    "@hono/node-server": "^1.8.2",
    "hono": "^4.0.0",
    "openai": "^5.10.2",
    "zod": "^3.25.76",
    "winston": "^3.11.0",
    "dotenv": "^16.3.1"
  },
  "devDependencies": {
    "@types/node": "^20.11.0",
    "@typescript-eslint/eslint-plugin": "^6.19.0",
    "@typescript-eslint/parser": "^6.19.0",
    "eslint": "^8.56.0",
    "tsx": "^4.7.0",
    "typescript": "^5.3.3",
    "vitest": "^1.2.0",
    "@vitest/coverage-v8": "^1.2.0"
  },
  "engines": {
    "node": ">=18.0.0"
  },
  "keywords": [
    "mcp",
    "openrouter",
    "thinking-models",
    "ai",
    "typescript"
  ]
}
```

## References

### Official Documentation
- [OpenRouter API Documentation](https://openrouter.ai/docs/api-reference/overview)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/specification/2025-06-18)
- [OpenRouter MCP Integration Guide](https://openrouter.ai/docs/use-cases/mcp-servers)
- [Anthropic Extended Thinking Guide](https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking)
- [DeepSeek R1 API Documentation](https://api-docs.deepseek.com/guides/reasoning_model)

### GitHub Repositories
- [MCP TypeScript SDK](https://github.com/modelcontextprotocol/typescript-sdk)
- [MCP Production Template](https://github.com/cyanheads/mcp-ts-template)
- [OpenRouter MCP Multimodal](https://github.com/stabgan/openrouter-mcp-multimodal)
- [MCP Server Examples](https://github.com/modelcontextprotocol/servers)

### Technical Resources
- [OpenRouter Reasoning Tokens](https://openrouter.ai/docs/use-cases/reasoning-tokens)
- [OpenRouter Streaming API](https://openrouter.ai/docs/api-reference/streaming)
- [Zod Schema Validation](https://zod.dev/)
- [TypeScript Best Practices](https://www.typescriptlang.org/docs/)

### Cost Optimization
- [OpenRouter Pricing](https://openrouter.ai/docs/api-reference/limits)
- [Model Performance Analysis](https://artificialanalysis.ai/models)
- [Provider Routing Options](https://openrouter.ai/docs/features/provider-routing)

### Community Resources
- [MCP Community Examples](https://lobehub.com/mcp)
- [OpenRouter Community](https://discord.gg/openrouter)
- [Stack Overflow MCP Tag](https://stackoverflow.com/questions/tagged/model-context-protocol)

---

*This guide represents best practices as of August 2025. For the most current information, always consult the official documentation and community resources.*