#!/usr/bin/env bash

# OpenRouter MCP Server Troubleshooting Script
# This script diagnoses and fixes common MCP connection issues

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

# Function to get project directory
get_project_dir() {
    if [ -n "$OPENROUTER_DIR" ]; then
        echo "$OPENROUTER_DIR"
        return
    fi
    
    local script_path="$(readlink -f "$0")"
    local script_dir="$(dirname "$script_path")"
    local project_dir="$(dirname "$script_dir")"
    
    if [ -f "$project_dir/.env.example" ] && [ -f "$project_dir/src/server.py" ]; then
        echo "$project_dir"
    else
        print_error "Could not find OpenRouter project directory"
        exit 1
    fi
}

# Function to check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"
    
    local missing_tools=()
    
    # Check for required tools
    for tool in docker claude python3; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools+=("$tool")
        fi
    done
    
    if [ ${#missing_tools[@]} -gt 0 ]; then
        print_error "Missing required tools: ${missing_tools[*]}"
        exit 1
    fi
    
    print_success "All required tools are installed"
}

# Function to check container status
check_container_status() {
    print_header "Checking Container Status"
    
    if docker ps --format '{{.Names}}' | grep -q "^openrouter$"; then
        print_success "OpenRouter container is running"
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep openrouter
        return 0
    elif docker ps -a --format '{{.Names}}' | grep -q "^openrouter$"; then
        print_warning "OpenRouter container exists but is not running"
        return 1
    else
        print_warning "OpenRouter container does not exist"
        return 2
    fi
}

# Function to check MCP connection
check_mcp_connection() {
    print_header "Checking MCP Connection"
    
    if claude mcp list | grep -q "openrouter-docker"; then
        print_success "MCP connection 'openrouter-docker' is registered"
        return 0
    else
        print_warning "MCP connection 'openrouter-docker' is not registered"
        return 1
    fi
}

# Function to test MCP server directly
test_mcp_server() {
    print_header "Testing MCP Server Directly"
    
    local test_message='{"jsonrpc": "2.0", "method": "initialize", "params": {}, "id": 1}'
    
    print_status "Sending test message to MCP server..."
    
    if timeout 10 bash -c "echo '$test_message' | docker exec -i openrouter python3 -m src.server" &>/dev/null; then
        print_success "MCP server responds to test messages"
        return 0
    else
        print_error "MCP server does not respond to test messages"
        return 1
    fi
}

# Function to check container logs
check_container_logs() {
    print_header "Checking Container Logs"
    
    print_status "Recent container logs:"
    docker logs openrouter --tail=10 2>/dev/null || {
        print_error "Could not retrieve container logs"
        return 1
    }
    
    # Check for specific error patterns
    if docker logs openrouter 2>&1 | grep -q "ERROR\|FATAL\|Exception"; then
        print_warning "Found errors in container logs"
        return 1
    else
        print_success "No critical errors found in container logs"
        return 0
    fi
}

# Function to fix container issues
fix_container_issues() {
    print_header "Fixing Container Issues"
    
    local container_status
    check_container_status
    container_status=$?
    
    case $container_status in
        0)
            print_success "Container is running - no action needed"
            ;;
        1)
            print_status "Starting stopped container..."
            docker start openrouter
            sleep 2
            ;;
        2)
            print_status "Creating and starting new container..."
            local project_dir=$(get_project_dir)
            cd "$project_dir"
            
            # Remove any existing container
            docker rm -f openrouter 2>/dev/null || true
            
            # Start new container in persistent mode
            docker run -d --name openrouter -i \
                --env-file .env \
                -v $HOME:/host$HOME:ro \
                openrouter:latest
            
            sleep 3
            ;;
    esac
}

# Function to fix MCP connection
fix_mcp_connection() {
    print_header "Fixing MCP Connection"
    
    # Remove existing connection if present
    if claude mcp list | grep -q "openrouter-docker"; then
        print_status "Removing existing MCP connection..."
        claude mcp remove openrouter-docker
    fi
    
    # Add new connection
    print_status "Adding MCP connection..."
    claude mcp add openrouter-docker -s user -- docker exec -i openrouter python3 -m src.server
    
    sleep 2
    
    if claude mcp list | grep -q "openrouter-docker"; then
        print_success "MCP connection added successfully"
        return 0
    else
        print_error "Failed to add MCP connection"
        return 1
    fi
}

# Function to run comprehensive diagnostics
run_diagnostics() {
    print_header "Running Comprehensive Diagnostics"
    
    local issues_found=0
    
    # Test container health
    if docker exec openrouter python3 -c "import src.server; print('OK')" &>/dev/null; then
        print_success "Container Python environment is healthy"
    else
        print_error "Container Python environment has issues"
        ((issues_found++))
    fi
    
    # Test API key configuration
    if docker exec openrouter python3 -c "import os; from dotenv import load_dotenv; load_dotenv(); print('OK' if os.getenv('OPENROUTER_API_KEY') else 'MISSING')" 2>/dev/null | grep -q "OK"; then
        print_success "API key is configured"
    else
        print_error "API key is not configured or accessible"
        ((issues_found++))
    fi
    
    # Test container resource usage
    local cpu_usage=$(docker stats openrouter --no-stream --format "{{.CPUPerc}}" | sed 's/%//')
    local mem_usage=$(docker stats openrouter --no-stream --format "{{.MemPerc}}" | sed 's/%//')
    
    if (( $(echo "$cpu_usage < 80" | bc -l) )); then
        print_success "Container CPU usage is normal (${cpu_usage}%)"
    else
        print_warning "Container CPU usage is high (${cpu_usage}%)"
        ((issues_found++))
    fi
    
    if (( $(echo "$mem_usage < 80" | bc -l) )); then
        print_success "Container memory usage is normal (${mem_usage}%)"
    else
        print_warning "Container memory usage is high (${mem_usage}%)"
        ((issues_found++))
    fi
    
    return $issues_found
}

# Function to apply advanced fixes
apply_advanced_fixes() {
    print_header "Applying Advanced Fixes"
    
    local project_dir=$(get_project_dir)
    cd "$project_dir"
    
    # Fix 1: Restart container with optimized settings
    print_status "Restarting container with optimized settings..."
    docker stop openrouter 2>/dev/null || true
    docker rm openrouter 2>/dev/null || true
    
    docker run -d --name openrouter -i \
        --env-file .env \
        -v $HOME:/host$HOME:ro \
        --restart unless-stopped \
        --memory=512m \
        --cpus="1.0" \
        openrouter:latest
    
    sleep 3
    
    # Fix 2: Recreate MCP connection with retry logic
    print_status "Recreating MCP connection with retry logic..."
    claude mcp remove openrouter-docker 2>/dev/null || true
    
    # Wait for container to be fully ready
    for i in {1..10}; do
        if docker exec openrouter python3 -c "import src.server; print('Ready')" &>/dev/null; then
            break
        fi
        print_status "Waiting for container to be ready... ($i/10)"
        sleep 2
    done
    
    claude mcp add openrouter-docker -s user -- docker exec -i openrouter python3 -m src.server
    
    sleep 2
    
    # Fix 3: Test the connection multiple times
    print_status "Testing connection stability..."
    local success_count=0
    for i in {1..5}; do
        if echo '{"jsonrpc": "2.0", "method": "initialize", "params": {}, "id": 1}' | docker exec -i openrouter python3 -m src.server &>/dev/null; then
            ((success_count++))
        fi
        sleep 1
    done
    
    if [ $success_count -ge 3 ]; then
        print_success "Connection stability test passed ($success_count/5 successful)"
        return 0
    else
        print_error "Connection stability test failed ($success_count/5 successful)"
        return 1
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  --check        Run diagnostics only (no fixes)"
    echo "  --fix          Run diagnostics and apply fixes"
    echo "  --advanced     Run diagnostics and apply advanced fixes"
    echo "  --reset        Complete reset (rebuild container and MCP connection)"
    echo "  --help         Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0             # Run full troubleshooting with fixes"
    echo "  $0 --check    # Check status without making changes"
    echo "  $0 --reset    # Complete reset and rebuild"
}

# Function to reset everything
reset_everything() {
    print_header "Resetting Everything"
    
    local project_dir=$(get_project_dir)
    cd "$project_dir"
    
    # Remove MCP connection
    print_status "Removing MCP connection..."
    claude mcp remove openrouter-docker 2>/dev/null || true
    
    # Stop and remove container
    print_status "Stopping and removing container..."
    docker stop openrouter 2>/dev/null || true
    docker rm openrouter 2>/dev/null || true
    
    # Rebuild image
    print_status "Rebuilding Docker image..."
    python tools/docker_manager.py build
    
    # Create new container
    print_status "Creating new container..."
    docker run -d --name openrouter -i \
        --env-file .env \
        -v $HOME:/host$HOME:ro \
        --restart unless-stopped \
        openrouter:latest
    
    sleep 5
    
    # Recreate MCP connection
    print_status "Recreating MCP connection..."
    claude mcp add openrouter-docker -s user -- docker exec -i openrouter python3 -m src.server
    
    sleep 2
    
    print_success "Complete reset finished"
}

# Main function
main() {
    local action="${1:-fix}"
    
    case "$action" in
        "--help"|"-h")
            show_usage
            exit 0
            ;;
        "--check")
            check_prerequisites
            check_container_status
            check_mcp_connection
            test_mcp_server
            check_container_logs
            run_diagnostics
            ;;
        "--fix")
            check_prerequisites
            check_container_status
            check_mcp_connection
            
            # Apply fixes if needed
            if ! check_container_status &>/dev/null; then
                fix_container_issues
            fi
            
            if ! check_mcp_connection &>/dev/null; then
                fix_mcp_connection
            fi
            
            test_mcp_server
            run_diagnostics
            ;;
        "--advanced")
            check_prerequisites
            apply_advanced_fixes
            test_mcp_server
            run_diagnostics
            ;;
        "--reset")
            check_prerequisites
            reset_everything
            test_mcp_server
            run_diagnostics
            ;;
        *)
            # Default: run diagnostics and apply fixes
            print_header "OpenRouter MCP Server Troubleshooting"
            echo "This script will diagnose and fix common MCP connection issues."
            echo ""
            
            check_prerequisites
            
            local issues_found=0
            
            # Run diagnostics
            if ! check_container_status &>/dev/null; then
                fix_container_issues
                ((issues_found++))
            fi
            
            if ! check_mcp_connection &>/dev/null; then
                fix_mcp_connection
                ((issues_found++))
            fi
            
            if ! test_mcp_server &>/dev/null; then
                print_warning "MCP server test failed, applying advanced fixes..."
                apply_advanced_fixes
                ((issues_found++))
            fi
            
            check_container_logs
            run_diagnostics
            
            if [ $issues_found -eq 0 ]; then
                print_success "No issues found! MCP server should be working correctly."
            else
                print_status "Fixed $issues_found issue(s). MCP server should be working now."
            fi
            
            print_header "Quick Test Commands"
            echo "You can test the MCP server manually with:"
            echo "  claude mcp list"
            echo "  echo '{\"jsonrpc\": \"2.0\", \"method\": \"initialize\", \"params\": {}, \"id\": 1}' | docker exec -i openrouter python3 -m src.server"
            ;;
    esac
}

# Run main function with all arguments
main "$@"