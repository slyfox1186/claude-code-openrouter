#!/usr/bin/env python3
"""
OpenRouter MCP Docker Management Script
Enhanced Python version with better capabilities
"""

import os
import sys
import subprocess
import time
import signal
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
import argparse


class Color:
    """ANSI color codes for terminal output"""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    MAGENTA = '\033[0;35m'
    CYAN = '\033[0;36m'
    WHITE = '\033[1;37m'
    GRAY = '\033[0;37m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    NC = '\033[0m'  # No Color


class LogLevel(Enum):
    """Log levels for output"""
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    SUCCESS = "SUCCESS"
    DOCKER = "DOCKER"


@dataclass
class ContainerStatus:
    """Container status information"""
    exists: bool
    running: bool
    name: str
    status: str
    ports: str = ""


class DockerManager:
    """Docker management for OpenRouter MCP Server"""
    
    def __init__(self):
        self.container_name = "openrouter"
        self.image_name = "openrouter:latest"
        self.compose_file = "docker/docker-compose.yml"
        self.env_file = ".env"
        
        # Set environment variable for bake delegation
        os.environ['COMPOSE_BAKE'] = 'true'
        
        # Force color output
        os.environ['FORCE_COLOR'] = '1'
        
        # Initialize
        self._check_dependencies()
        self._load_environment()
    
    def _check_dependencies(self) -> None:
        """Check if required tools are installed"""
        required_tools = ['docker', 'docker-compose']
        missing_tools = []
        
        for tool in required_tools:
            if not self._command_exists(tool):
                missing_tools.append(tool)
        
        if missing_tools:
            self._print_error(f"Missing required tools: {', '.join(missing_tools)}")
            sys.exit(1)
    
    def _command_exists(self, command: str) -> bool:
        """Check if a command exists in PATH"""
        try:
            subprocess.run(['which', command], check=True, 
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def _load_environment(self) -> None:
        """Load environment variables from .env file"""
        if not Path(self.env_file).exists():
            self._print_error(f"{self.env_file} file not found. Please create it with your OPENROUTER_API_KEY")
            sys.exit(1)
        
        # Load .env file
        env_vars = {}
        with open(self.env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value
                    os.environ[key] = value
        
        if not os.getenv('OPENROUTER_API_KEY'):
            self._print_error("OPENROUTER_API_KEY not set in .env file")
            sys.exit(1)
        
        self._print_success("Environment configuration loaded")
    
    def _print_message(self, level: LogLevel, message: str) -> None:
        """Print colored message based on log level"""
        color_map = {
            LogLevel.INFO: Color.GREEN,
            LogLevel.WARN: Color.YELLOW,
            LogLevel.ERROR: Color.RED,
            LogLevel.SUCCESS: Color.CYAN,
            LogLevel.DOCKER: Color.BLUE
        }
        
        color = color_map.get(level, Color.WHITE)
        # Force flush to ensure colors appear
        print(f"{color}[{level.value}]{Color.NC} {message}", flush=True)
    
    def _print_info(self, message: str) -> None:
        self._print_message(LogLevel.INFO, message)
    
    def _print_warning(self, message: str) -> None:
        self._print_message(LogLevel.WARN, message)
    
    def _print_error(self, message: str) -> None:
        self._print_message(LogLevel.ERROR, message)
    
    def _print_success(self, message: str) -> None:
        self._print_message(LogLevel.SUCCESS, message)
    
    def _print_header(self, message: str) -> None:
        self._print_message(LogLevel.DOCKER, message)
    
    def _print_separator(self) -> None:
        """Print a visual separator"""
        print(f"{Color.GRAY}{'─' * 60}{Color.NC}", flush=True)
    
    def test_colors(self) -> None:
        """Test color output"""
        print("\n🎨 Color Test:")
        print(f"{Color.RED}RED{Color.NC} {Color.GREEN}GREEN{Color.NC} {Color.YELLOW}YELLOW{Color.NC} {Color.BLUE}BLUE{Color.NC} {Color.CYAN}CYAN{Color.NC} {Color.MAGENTA}MAGENTA{Color.NC}")
        print(f"{Color.BOLD}BOLD{Color.NC} {Color.UNDERLINE}UNDERLINE{Color.NC}")
        self._print_separator()
    
    def _run_command(self, command: List[str], capture_output: bool = False, 
                    check: bool = True) -> Optional[subprocess.CompletedProcess]:
        """Run a command and handle errors"""
        try:
            if capture_output:
                result = subprocess.run(command, capture_output=True, text=True, check=check)
                return result
            else:
                result = subprocess.run(command, check=check)
                return result
        except subprocess.CalledProcessError as e:
            if capture_output:
                self._print_error(f"Command failed: {' '.join(command)}")
                if e.stderr:
                    print(f"{Color.RED}{e.stderr}{Color.NC}")
            return None
        except KeyboardInterrupt:
            self._print_warning("Operation interrupted by user")
            return None
    
    def _get_container_status(self) -> ContainerStatus:
        """Get current container status"""
        # Check if container exists
        result = self._run_command(['docker', 'ps', '-a', '--format', 'table {{.Names}}'], 
                                 capture_output=True, check=False)
        
        if not result:
            return ContainerStatus(exists=False, running=False, name=self.container_name, status="Not found")
        
        container_exists = self.container_name in result.stdout
        
        if not container_exists:
            return ContainerStatus(exists=False, running=False, name=self.container_name, status="Not found")
        
        # Check if container is running
        result = self._run_command(['docker', 'ps', '--format', 'table {{.Names}}'], 
                                 capture_output=True, check=False)
        
        if not result:
            return ContainerStatus(exists=True, running=False, name=self.container_name, status="Stopped")
        
        container_running = self.container_name in result.stdout
        
        # Get detailed status
        result = self._run_command(['docker', 'ps', '-a', '--filter', f'name={self.container_name}', 
                                  '--format', 'table {{.Status}}\t{{.Ports}}'], 
                                 capture_output=True, check=False)
        
        status_info = "Unknown"
        ports_info = ""
        
        if result and result.stdout:
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:  # Skip header
                parts = lines[1].split('\t')
                status_info = parts[0] if parts else "Unknown"
                ports_info = parts[1] if len(parts) > 1 else ""
        
        return ContainerStatus(
            exists=container_exists,
            running=container_running,
            name=self.container_name,
            status=status_info,
            ports=ports_info
        )
    
    def _image_exists(self) -> bool:
        """Check if Docker image exists"""
        result = self._run_command(['docker', 'images', '--format', 'table {{.Repository}}:{{.Tag}}'], 
                                 capture_output=True, check=False)
        
        if result and result.stdout:
            return self.image_name in result.stdout
        return False
    
    def check_status(self) -> None:
        """Check container and image status"""
        self._print_header("Checking container status...")
        print()
        
        # Check container status
        container_status = self._get_container_status()
        
        if container_status.exists:
            if container_status.running:
                self._print_success(f"Container '{self.container_name}' is RUNNING")
                print(f"  {Color.WHITE}Status:{Color.NC} {container_status.status}")
                if container_status.ports:
                    print(f"  {Color.WHITE}Ports:{Color.NC} {container_status.ports}")
            else:
                self._print_warning(f"Container '{self.container_name}' exists but is STOPPED")
                print(f"  {Color.WHITE}Status:{Color.NC} {container_status.status}")
        else:
            self._print_warning(f"Container '{self.container_name}' does not exist")
        
        print()
        
        # Check image status
        if self._image_exists():
            self._print_success(f"Image '{self.image_name}' exists")
        else:
            self._print_warning(f"Image '{self.image_name}' does not exist")
        
        print()
        self._print_separator()
    
    def stop_container(self) -> None:
        """Stop and remove ALL containers related to this project"""
        self._print_header("Stopping all OpenRouter MCP containers...")
        print()
        
        # Find all containers related to this project
        containers_to_stop = []
        
        # Method 1: Find by image name
        self._print_info("Searching for containers by image (openrouter:latest)...")
        result = self._run_command(['docker', 'ps', '-a', '--filter', 'ancestor=openrouter:latest', 
                                   '--format', '{{.Names}}'], capture_output=True, check=False)
        
        if result and result.stdout.strip():
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    containers_to_stop.append(line.strip())
        
        # Method 2: Find by name pattern (backup method)
        if not containers_to_stop:
            self._print_info("Searching for containers by name pattern (openrouter)...")
            result = self._run_command(['docker', 'ps', '-a', '--filter', 'name=openrouter', 
                                       '--format', '{{.Names}}'], capture_output=True, check=False)
            
            if result and result.stdout.strip():
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        containers_to_stop.append(line.strip())
        
        # Method 3: Include specific container name
        container_status = self._get_container_status()
        if container_status.exists and self.container_name not in containers_to_stop:
            containers_to_stop.append(self.container_name)
        
        if not containers_to_stop:
            self._print_warning("No OpenRouter MCP containers found to stop")
            print()
            self._print_separator()
            return
        
        # Remove duplicates and show what we found
        containers_to_stop = list(set(containers_to_stop))
        self._print_success(f"Found {len(containers_to_stop)} container(s) to stop:")
        for container in containers_to_stop:
            print(f"  - {container}")
        print()
        
        # Stop all running containers
        stopped_count = 0
        for container_name in containers_to_stop:
            # Check if container is running
            result = self._run_command(['docker', 'ps', '--filter', f'name={container_name}', 
                                       '--format', '{{.Names}}'], capture_output=True, check=False)
            
            if result and container_name in result.stdout:
                self._print_info(f"Stopping running container '{container_name}'...")
                if self._run_command(['docker', 'stop', container_name], check=False):
                    self._print_success(f"Container '{container_name}' stopped")
                    stopped_count += 1
                else:
                    self._print_error(f"Failed to stop container '{container_name}'")
            else:
                self._print_warning(f"Container '{container_name}' is not running")
        
        # Remove all containers
        removed_count = 0
        for container_name in containers_to_stop:
            # Check if container exists
            result = self._run_command(['docker', 'ps', '-a', '--filter', f'name={container_name}', 
                                       '--format', '{{.Names}}'], capture_output=True, check=False)
            
            if result and container_name in result.stdout:
                self._print_info(f"Removing container '{container_name}'...")
                if self._run_command(['docker', 'rm', container_name], check=False):
                    self._print_success(f"Container '{container_name}' removed")
                    removed_count += 1
                else:
                    self._print_error(f"Failed to remove container '{container_name}'")
            else:
                self._print_warning(f"Container '{container_name}' does not exist")
        
        print()
        if stopped_count > 0 or removed_count > 0:
            self._print_success(f"Operation completed: {stopped_count} stopped, {removed_count} removed")
        else:
            self._print_warning("No containers were stopped or removed")
        
        print()
        self._print_separator()
    
    def build_image(self) -> None:
        """Build Docker image with bake delegation"""
        self._print_header("Building Docker image...")
        print()
        
        self._print_info(f"Building image '{self.image_name}' with Bake delegation...")
        print(f"{Color.GRAY}Using COMPOSE_BAKE=true for enhanced performance{Color.NC}")
        print()
        
        # Use docker-compose to build with bake delegation
        if self._run_command(['docker-compose', 'build']):
            self._print_success("Image built successfully with Bake delegation")
        else:
            self._print_error("Failed to build image")
        
        print()
        self._print_separator()
    
    def start_container(self) -> None:
        """Start container"""
        self._print_header("Starting container...")
        print()
        
        container_status = self._get_container_status()
        
        # Check if container already exists and is running
        if container_status.running:
            self._print_warning(f"Container '{self.container_name}' is already running")
            print()
            self._print_separator()
            return
        
        # Remove existing stopped container
        if container_status.exists:
            self._print_info("Removing existing stopped container...")
            self._run_command(['docker', 'rm', self.container_name])
        
        # Start with docker-compose (using bake delegation)
        self._print_info("Starting container using docker-compose with Bake delegation...")
        
        if self._run_command(['docker-compose', 'up', '-d']):
            # Wait a moment and check status
            time.sleep(2)
            container_status = self._get_container_status()
            
            if container_status.running:
                self._print_success(f"Container '{self.container_name}' started successfully")
            else:
                self._print_error("Failed to start container")
        else:
            self._print_error("Failed to start container")
        
        print()
        self._print_separator()
    
    def restart_container(self) -> None:
        """Restart container (stop + rebuild + start)"""
        self._print_header("Restarting container (full rebuild)...")
        print()
        
        # Stop and remove
        self.stop_container()
        
        # Build image
        self.build_image()
        
        # Start container
        self.start_container()
        
        self._print_success("Container restart completed")
        print()
        self._print_separator()
    
    def view_logs(self) -> None:
        """View container logs with smart container detection"""
        self._print_header("Viewing container logs...")
        print()
        
        # Find all running openrouter containers (try multiple approaches)
        self._print_info("Searching for openrouter containers...")
        
        # First try: by image name
        result = self._run_command(['docker', 'ps', '--filter', 'ancestor=openrouter:latest', 
                                   '--format', '{{.Names}}\t{{.Status}}\t{{.Image}}'], 
                                 capture_output=True, check=False)
        
        containers = []
        if result and result.stdout.strip():
            self._print_info(f"Found containers by image: {result.stdout.strip()}")
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if line and '\t' in line:
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        containers.append({
                            'name': parts[0],
                            'status': parts[1],
                            'method': 'by_image'
                        })
        
        # Second try: by name pattern
        if not containers:
            result = self._run_command(['docker', 'ps', '--filter', 'name=openrouter', 
                                       '--format', '{{.Names}}\t{{.Status}}\t{{.Image}}'], 
                                     capture_output=True, check=False)
            
            if result and result.stdout.strip():
                self._print_info(f"Found containers by name: {result.stdout.strip()}")
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line and '\t' in line:
                        parts = line.split('\t')
                        if len(parts) >= 2:
                            containers.append({
                                'name': parts[0],
                                'status': parts[1],
                                'method': 'by_name'
                            })
        
        # Third try: show all containers for debugging
        if not containers:
            self._print_warning("No openrouter containers found.")
            print()
            self._print_info("Showing all running containers for debugging:")
            result = self._run_command(['docker', 'ps', '--format', '{{.Names}}\t{{.Image}}\t{{.Status}}'], 
                                     capture_output=True, check=False)
            if result and result.stdout.strip():
                print()
                print(f"{Color.BOLD}{Color.WHITE}{'Container Name':<25} {'Image':<30} {'Status'}{Color.NC}")
                print(f"{Color.GRAY}{'─' * 25} {'─' * 30} {'─' * 20}{Color.NC}")
                
                for line in result.stdout.strip().split('\n'):
                    if line and '\t' in line:
                        parts = line.split('\t')
                        if len(parts) >= 3:
                            name = parts[0][:24]  # Truncate if too long
                            image = parts[1][:29]  # Truncate if too long
                            status = parts[2]
                            
                            # Color code based on image or name
                            if 'openrouter' in name.lower() or 'openrouter' in image.lower():
                                name_color = Color.CYAN
                            else:
                                name_color = Color.WHITE
                            
                            print(f"{name_color}{name:<25}{Color.NC} {Color.YELLOW}{image:<30}{Color.NC} {Color.GREEN}{status}{Color.NC}")
                print()
            else:
                self._print_warning("No containers are currently running!")
                print()
        
        if not containers:
            self._print_warning("No running openrouter containers found")
            self._print_info("Available options:")
            print(f"  1. Start docker-compose container: {Color.CYAN}./docker_manager.py start{Color.NC}")
            print(f"  2. Make a query in Claude Code to start MCP container")
            print()
            self._print_separator()
            return
        
        # If multiple containers, let user choose
        if len(containers) > 1:
            print()
            self._print_info("Multiple openrouter containers found:")
            print()
            print(f"{Color.BOLD}{Color.WHITE}{'#':<3} {'Container Name':<25} {'Status':<20} {'Method'}{Color.NC}")
            print(f"{Color.GRAY}{'─' * 3} {'─' * 25} {'─' * 20} {'─' * 15}{Color.NC}")
            
            for i, container in enumerate(containers, 1):
                method = container.get('method', 'unknown')
                print(f"{Color.CYAN}{i:<3}{Color.NC} {Color.WHITE}{container['name']:<25}{Color.NC} {Color.GREEN}{container['status']:<20}{Color.NC} {Color.GRAY}{method}{Color.NC}")
            
            print()
            try:
                choice = input(f"{Color.BOLD}{Color.WHITE}Select container [1-{len(containers)}]: {Color.NC}").strip()
                container_index = int(choice) - 1
                if container_index < 0 or container_index >= len(containers):
                    self._print_error("Invalid selection")
                    return
                selected_container = containers[container_index]['name']
            except (ValueError, KeyboardInterrupt):
                self._print_error("Invalid selection")
                return
        else:
            selected_container = containers[0]['name']
            self._print_success(f"Found container: {selected_container}")
        
        self._print_info(f"Showing logs for '{selected_container}'...")
        print(f"{Color.YELLOW}Press Ctrl+C to exit log viewer{Color.NC}")
        print()
        self._print_separator()
        
        try:
            # Use subprocess with direct terminal access (no pipe buffering)
            process = subprocess.Popen(
                ['docker', 'logs', '-f', selected_container],
                stdin=sys.stdin,
                stdout=sys.stdout,
                stderr=sys.stderr
            )
            process.wait()
        except KeyboardInterrupt:
            print()
            self._print_info("Log viewer exited")
            if 'process' in locals() and process.poll() is None:
                process.terminate()
                process.wait()
        
        print()
        self._print_separator()
    
    def interactive_mode(self) -> None:
        """Interactive shell in container"""
        self._print_header("Interactive mode - connecting to running container...")
        print()
        
        container_status = self._get_container_status()
        
        if not container_status.running:
            self._print_error(f"Container '{self.container_name}' is not running")
            print()
            self._print_separator()
            return
        
        self._print_info(f"Connecting to '{self.container_name}'...")
        print(f"{Color.YELLOW}Type 'exit' to leave the container shell{Color.NC}")
        print()
        
        try:
            subprocess.run(['docker', 'exec', '-it', self.container_name, '/bin/bash'])
        except KeyboardInterrupt:
            print()
            self._print_info("Interactive session interrupted")
        
        print()
        self._print_separator()
    
    def show_menu(self) -> None:
        """Show interactive menu"""
        print()
        print(f"{Color.BOLD}{Color.BLUE}{'=' * 50}{Color.NC}")
        print(f"{Color.BOLD}{Color.WHITE}    OpenRouter MCP Docker Manager{Color.NC}")
        print(f"{Color.BOLD}{Color.BLUE}{'=' * 50}{Color.NC}")
        print()
        
        menu_items = [
            ("1", "Status", "Check container status", Color.CYAN),
            ("2", "Start", "Start container", Color.GREEN),
            ("3", "Stop", "Stop and remove ALL project containers", Color.RED),
            ("4", "Restart", "Full restart (stop + rebuild + start)", Color.YELLOW),
            ("5", "Build", "Build/rebuild image only", Color.MAGENTA),
            ("6", "Logs", "View container logs (Ctrl+C to exit)", Color.BLUE),
            ("7", "Shell", "Interactive shell in container", Color.CYAN),
            ("8", "Quit", "Exit script", Color.GRAY)
        ]
        
        for number, title, description, color in menu_items:
            print(f"{color}{number}){Color.NC} {Color.BOLD}{title:<12}{Color.NC} - {description}")
        
        print()
        print(f"{Color.BOLD}{Color.BLUE}{'=' * 50}{Color.NC}")
    
    def run_interactive(self) -> None:
        """Run interactive menu"""
        while True:
            self.show_menu()
            
            try:
                choice = input(f"{Color.WHITE}Select an option [1-8]: {Color.NC}").strip()
            except KeyboardInterrupt:
                print()
                self._print_info("Goodbye!")
                sys.exit(0)
            
            print()
            
            if choice == '1':
                self.check_status()
            elif choice == '2':
                self.start_container()
            elif choice == '3':
                self.stop_container()
            elif choice == '4':
                self.restart_container()
            elif choice == '5':
                self.build_image()
            elif choice == '6':
                self.view_logs()
            elif choice == '7':
                self.interactive_mode()
            elif choice == '8':
                self._print_success("Goodbye!")
                break
            else:
                self._print_error("Invalid option. Please select 1-8.")
                print()
                self._print_separator()
            
            if choice != '8':
                input(f"{Color.WHITE}Press Enter to continue...{Color.NC}")


def main():
    """Main function with argument parsing"""
    parser = argparse.ArgumentParser(description="OpenRouter MCP Docker Manager")
    parser.add_argument('command', nargs='?', choices=['status', 'start', 'stop', 'restart', 'build', 'logs', 'shell'],
                       help='Command to execute')
    
    args = parser.parse_args()
    
    try:
        manager = DockerManager()
        
        if args.command:
            # Direct command execution
            if args.command == 'status':
                manager.check_status()
            elif args.command == 'start':
                manager.start_container()
            elif args.command == 'stop':
                manager.stop_container()
            elif args.command == 'restart':
                manager.restart_container()
            elif args.command == 'build':
                manager.build_image()
            elif args.command == 'logs':
                manager.view_logs()
            elif args.command == 'shell':
                manager.interactive_mode()
        else:
            # Interactive mode
            manager.run_interactive()
    
    except KeyboardInterrupt:
        print()
        print(f"{Color.YELLOW}[WARN]{Color.NC} Operation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"{Color.RED}[ERROR]{Color.NC} Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()