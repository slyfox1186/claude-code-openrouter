#!/usr/bin/env node

/**
 * Focused test for qwen-thinking model JSON parsing issues
 */

const { spawn } = require('child_process');

class ThinkingModelTester {
    constructor() {
        this.server = null;
        this.messageId = 1;
    }

    async startServer() {
        console.log('🚀 Starting MCP server for thinking model test...');
        
        this.server = spawn('docker', ['exec', '-i', 'openrouter', 'python3', '-m', 'src.server'], {
            stdio: ['pipe', 'pipe', 'pipe']
        });

        let responseBuffer = '';
        
        this.server.stderr.on('data', (data) => {
            const log = data.toString();
            console.log('📝 Server log:', log.trim());
        });

        this.server.stdout.on('data', (data) => {
            responseBuffer += data.toString();
            
            // Try to extract complete JSON messages
            const lines = responseBuffer.split('\n');
            responseBuffer = lines.pop() || ''; // Keep incomplete line
            
            for (const line of lines) {
                if (line.trim()) {
                    this.handleResponse(line.trim());
                }
            }
        });

        // Wait for server to start
        await new Promise(resolve => setTimeout(resolve, 2000));
    }

    handleResponse(line) {
        console.log('\n📥 Raw response length:', line.length);
        console.log('📥 Response start:', line.substring(0, 500));
        if (line.length > 1000) {
            console.log('📥 Response end:', line.substring(line.length - 500));
        }
        
        try {
            const response = JSON.parse(line);
            console.log('✅ JSON parsing successful');
            
            if (response.result && response.result.content) {
                const content = response.result.content[0].text;
                console.log('📄 Response content length:', content.length);
                console.log('📄 Content preview:', content.substring(0, 300) + '...');
            }
            
            if (response.error) {
                console.error('❌ API Error:', response.error);
            }
            
        } catch (error) {
            console.error('💥 JSON Parse Error:', error.message);
            console.error('🔍 Error position:', error.message.match(/position (\d+)/)?.[1] || 'unknown');
            
            // Try to find where JSON breaks
            const errorPos = parseInt(error.message.match(/position (\d+)/)?.[1]) || 0;
            if (errorPos > 0) {
                console.log('🔍 Context around error:');
                console.log(line.substring(Math.max(0, errorPos - 100), errorPos + 100));
            }
        }
    }

    sendMessage(message) {
        const messageStr = JSON.stringify(message);
        console.log('📤 Sending:', messageStr);
        this.server.stdin.write(messageStr + '\n');
    }

    async testThinkingModelSteps() {
        console.log('\n🧪 Testing thinking model with different configurations...\n');

        // Initialize
        console.log('1️⃣ Initialize...');
        this.sendMessage({
            jsonrpc: "2.0",
            method: "initialize",
            id: this.messageId++
        });
        await new Promise(resolve => setTimeout(resolve, 1000));

        // Test with LOW effort first
        console.log('\n2️⃣ Testing with LOW effort...');
        this.sendMessage({
            jsonrpc: "2.0",
            method: "tools/call",
            params: {
                name: "chat",
                arguments: {
                    prompt: "What is 2+2?",
                    model: "qwen-thinking",
                    thinking_effort: "low"
                }
            },
            id: this.messageId++
        });
        await new Promise(resolve => setTimeout(resolve, 30000));

        // Test with MEDIUM effort
        console.log('\n3️⃣ Testing with MEDIUM effort...');
        this.sendMessage({
            jsonrpc: "2.0",
            method: "tools/call",
            params: {
                name: "chat",
                arguments: {
                    prompt: "What is 2+2?",
                    model: "qwen-thinking", 
                    thinking_effort: "medium"
                }
            },
            id: this.messageId++
        });
        await new Promise(resolve => setTimeout(resolve, 45000));

        // Test GPT-5 model
        console.log('\n4️⃣ Testing GPT-5 model...');
        this.sendMessage({
            jsonrpc: "2.0",
            method: "tools/call",
            params: {
                name: "chat",
                arguments: {
                    prompt: "What is 2+2? Explain your reasoning.",
                    model: "gpt-5"
                }
            },
            id: this.messageId++
        });
        await new Promise(resolve => setTimeout(resolve, 30000));

        console.log('\n✅ Test completed');
    }

    async run() {
        try {
            await this.startServer();
            await this.testThinkingModelSteps();
        } catch (error) {
            console.error('💥 Test failed:', error);
        } finally {
            if (this.server) {
                console.log('\n🛑 Stopping server...');
                this.server.kill();
            }
        }
    }
}

// Run the test
const tester = new ThinkingModelTester();
tester.run().catch(console.error);