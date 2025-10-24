#!/bin/bash

# Local Code Agent startup script
# One-click startup of MCP servers and main program

set -e

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
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

# 检查 Python 是否安装
check_python() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed, please install Python 3"
        exit 1
    fi
     # check python version >= 3.9
    python3 -c "import sys; sys.exit(0) if sys.version_info >= (3, 9) else sys.exit(1)" || {
        print_error "Python version is less than 3.9, please install Python 3.9"
        exit 1
    }
    print_success "Python version is >= 3.9"
}

# check dependencies
check_dependencies() {
    print_info "checking dependencies..."
    
    # check necessary Python packages
    python3 -c "import aiohttp" 2>/dev/null || {
        print_warning "aiohttp is not installed, installing..."
        pip3 install aiohttp
    }
    
    python3 -c "import google.adk" 2>/dev/null || {
        print_error "google.adk is not installed, please run pip3 install google-adk"
        exit 1
    }
    
    print_success "dependencies checked successfully"
}


# start MCP servers
start_mcp_servers() {
    print_info "starting MCP servers..."
    
    # check if port is occupied
    if lsof -Pi :8001 -sTCP:LISTEN -t >/dev/null ; then
        print_warning "port 8001 is occupied, maybe MCP servers are running"
    fi
    
    if lsof -Pi :8002 -sTCP:LISTEN -t >/dev/null ; then
        print_warning "port 8002 is occupied, maybe MCP servers are running"
    fi
    
    # start MCP servers (background running)
    python3 mcp_servers.py &
    MCP_PID=$!
    
    # wait for servers to start
    sleep 3
    
    # check if servers started successfully
    if curl -s http://localhost:8001/python-interpreter/health > /dev/null; then
        print_success "Python interpreter MCP server started successfully (port 8001)"
    else
        print_error "Python interpreter MCP server started failed"
        exit 1
    fi
    
    if curl -s http://localhost:8002/file-operations/health > /dev/null; then
        print_success "file operations MCP server started successfully (port 8002)"
    else
        print_error "file operations MCP server started failed"
        exit 1
    fi
    
    print_success "all MCP servers started successfully"
}


# cleanup function
cleanup() {
    print_info "cleaning up..."
    
    # stop MCP servers
    if [ ! -z "$MCP_PID" ]; then
        kill $MCP_PID 2>/dev/null || true
        print_info "MCP servers stopped"
    fi
    
    # stop all related Python processes
    pkill -f "mcp_servers.py" 2>/dev/null || true
    
    print_success "cleanup completed"
}

# show help message
show_help() {
    echo "local Code Agent startup script"
    echo ""
    echo "usage: $0 [options]"
    echo ""
    echo "options:"
    echo "  --test-only     only run tests, not start main program"
    echo "  --mcp-only      only start MCP servers"
    echo "  --help          show this help message"
    echo ""
    echo "example:"
    echo "  $0                    # full start (recommended)"
    echo "  $0 --test-only        # only run tests"
    echo "  $0 --mcp-only         # only start MCP servers"
    echo "  $0 -t '计算 2+2'      # execute specific task"
}

# main function
main() {
    # set signal handling
    trap cleanup EXIT INT TERM
    
    print_info "starting local Code Agent system"
    echo ""
    
    # parse command line arguments
    TEST_ONLY=false
    MCP_ONLY=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --test-only)
                TEST_ONLY=true
                shift
                ;;
            --mcp-only)
                MCP_ONLY=true
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                break
                ;;
        esac
    done
    
    # check environment
    check_python
    check_dependencies
    
    # start MCP servers
    start_mcp_servers
    print_info "MCP servers started, press Ctrl+C to stop"
    wait
}

# run main function
main "$@" 