#!/usr/bin/env node

/**
 * Direct MCP Server Test Script
 * Tests the OpenRouter MCP server directly without Claude Code
 */

const { spawn } = require('child_process');
const readline = require('readline');

class MCPTester {
    constructor() {
        this.server = null;
        this.messageId = 1;
        this.responses = new Map();
    }

    async startServer() {
        console.log('🚀 Starting MCP server...');
        
        this.server = spawn('docker', ['exec', '-i', 'openrouter', 'python3', '-m', 'src.server'], {
            stdio: ['pipe', 'pipe', 'pipe']
        });

        this.server.stderr.on('data', (data) => {
            console.log('📝 Server log:', data.toString().trim());
        });

        this.server.stdout.on('data', (data) => {
            const lines = data.toString().trim().split('\n');
            for (const line of lines) {
                if (line.trim()) {
                    this.handleResponse(line);
                }
            }
        });

        this.server.on('error', (error) => {
            console.error('❌ Server error:', error);
        });

        // Wait a bit for server to start
        await new Promise(resolve => setTimeout(resolve, 2000));
    }

    handleResponse(line) {
        try {
            const response = JSON.parse(line);
            console.log('📥 Received:', JSON.stringify(response, null, 2));
            
            if (response.id) {
                this.responses.set(response.id, response);
            }
        } catch (error) {
            console.log('📥 Raw response:', line);
            console.error('⚠️  JSON parse error:', error.message);
        }
    }

    sendMessage(message) {
        const messageStr = JSON.stringify(message);
        console.log('📤 Sending:', messageStr);
        this.server.stdin.write(messageStr + '\n');
        return message.id;
    }

    async waitForResponse(messageId, timeout = 30000) {
        const start = Date.now();
        while (Date.now() - start < timeout) {
            if (this.responses.has(messageId)) {
                return this.responses.get(messageId);
            }
            await new Promise(resolve => setTimeout(resolve, 100));
        }
        throw new Error(`Timeout waiting for response to message ${messageId}`);
    }

    async testInitialize() {
        console.log('\n🔧 Testing initialize...');
        const id = this.sendMessage({
            jsonrpc: "2.0",
            method: "initialize",
            id: this.messageId++
        });

        const response = await this.waitForResponse(id);
        console.log('✅ Initialize successful');
        return response;
    }

    async testToolsList() {
        console.log('\n🛠️  Testing tools/list...');
        const id = this.sendMessage({
            jsonrpc: "2.0",
            method: "tools/list",
            id: this.messageId++
        });

        const response = await this.waitForResponse(id);
        console.log('✅ Tools list successful');
        console.log('📋 Available tools:', response.result.tools.map(t => t.name));
        return response;
    }

    async testBasicChat() {
        console.log('\n💬 Testing basic chat with qwen model...');
        const id = this.sendMessage({
            jsonrpc: "2.0",
            method: "tools/call",
            params: {
                name: "chat",
                arguments: {
                    prompt: "What is 2+2? Give a brief answer.",
                    model: "qwen"
                }
            },
            id: this.messageId++
        });

        const response = await this.waitForResponse(id, 60000);
        console.log('✅ Basic chat successful');
        return response;
    }

    async testThinkingModel() {
        console.log('\n🧠 Testing qwen-thinking model...');
        const id = this.sendMessage({
            jsonrpc: "2.0",
            method: "tools/call",
            params: {
                name: "chat",
                arguments: {
                    prompt: "What is 2+2? Show your thinking process.",
                    model: "qwen-thinking",
                    thinking_effort: "low"  // Start with low to avoid large responses
                }
            },
            id: this.messageId++
        });

        try {
            const response = await this.waitForResponse(id, 120000); // 2 min timeout
            console.log('✅ Thinking model successful');
            return response;
        } catch (error) {
            console.error('❌ Thinking model failed:', error.message);
            return null;
        }
    }

    async testCustomModel() {
        console.log('\n⚙️  Testing custom model...');
        const id = this.sendMessage({
            jsonrpc: "2.0",
            method: "tools/call",
            params: {
                name: "chat_with_custom_model",
                arguments: {
                    prompt: "What is 2+2?",
                    custom_model: "qwen/qwen3-235b-a22b-thinking-2507",
                    thinking_effort: "low"
                }
            },
            id: this.messageId++
        });

        try {
            const response = await this.waitForResponse(id, 120000);
            console.log('✅ Custom model successful');
            return response;
        } catch (error) {
            console.error('❌ Custom model failed:', error.message);
            return null;
        }
    }

    async runAllTests() {
        try {
            await this.startServer();
            
            console.log('🧪 Running MCP Server Tests...\n');
            
            await this.testInitialize();
            await this.testToolsList();
            await this.testBasicChat();
            await this.testThinkingModel();
            await this.testCustomModel();
            
            console.log('\n🎉 All tests completed!');
            
        } catch (error) {
            console.error('\n💥 Test failed:', error);
        } finally {
            if (this.server) {
                this.server.kill();
            }
        }
    }
}

// Run tests
if (require.main === module) {
    const tester = new MCPTester();
    tester.runAllTests().catch(console.error);
}

module.exports = MCPTester;