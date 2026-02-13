#!/bin/bash

###############################################################################
# Start Drug Analysis API Server in Background
# Runs with virtual environment support
###############################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=========================================="
echo "Starting Drug Analysis API Server"
echo "=========================================="

# Configuration
VENV_NAME="new_env"  # Virtual environment name
VENV_PATH="/home/ubuntu/ibr-backend/demoibr/bra/new_env"  # Full path to venv
PROJECT_DIR="/home/ubuntu/ibr-backend/demoibr/bra"  # Project directory
PYTHON_CMD="python3.12"  # Python version
SERVER_FILE="server.py"
LOG_FILE="server.log"
PID_FILE="server.pid"

# Function to check if virtual environment exists
check_venv() {
    if [ ! -d "$VENV_PATH" ]; then
        echo -e "${RED}✗ Virtual environment not found at: $VENV_PATH${NC}"
        echo "Please set VENV_PATH correctly in this script"
        exit 1
    fi
    echo -e "${GREEN}✓ Virtual environment found${NC}"
}

# Function to check if server is already running
check_running() {
    if [ -f "$PID_FILE" ]; then
        OLD_PID=$(cat "$PID_FILE")
        if ps -p "$OLD_PID" > /dev/null 2>&1; then
            echo -e "${YELLOW}⚠ Server already running (PID: $OLD_PID)${NC}"
            read -p "Stop and restart? (y/n): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                echo "Stopping old server..."
                kill -TERM "$OLD_PID" 2>/dev/null || kill -9 "$OLD_PID" 2>/dev/null
                sleep 2
                rm -f "$PID_FILE"
            else
                echo "Exiting..."
                exit 0
            fi
        else
            # PID file exists but process is dead
            rm -f "$PID_FILE"
        fi
    fi
}

# Function to kill any process on port 8000
free_port() {
    echo -e "${YELLOW}Checking port 8000...${NC}"
    PORT_PID=$(sudo lsof -ti:8000 2>/dev/null || true)
    
    if [ ! -z "$PORT_PID" ]; then
        echo "Port 8000 in use by PID: $PORT_PID"
        echo "Killing process..."
        sudo kill -9 "$PORT_PID" 2>/dev/null || true
        sleep 1
    fi
    
    if sudo lsof -ti:8000 > /dev/null 2>&1; then
        echo -e "${RED}✗ Failed to free port 8000${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Port 8000 is free${NC}"
}

# Function to check if .env file exists
check_env() {
    if [ ! -f "$PROJECT_DIR/.env" ]; then
        echo -e "${RED}✗ .env file not found in $PROJECT_DIR${NC}"
        echo "Please create .env file with database credentials"
        exit 1
    fi
    echo -e "${GREEN}✓ .env file found${NC}"
}

# Main execution
cd "$PROJECT_DIR" || exit 1
echo -e "${BLUE}Working directory: $PROJECT_DIR${NC}"

# Run checks
check_venv
check_running
free_port
check_env

# Activate virtual environment and start server
echo -e "\n${YELLOW}Starting server in background...${NC}"

# Create start command
START_CMD="source $VENV_PATH/bin/activate && cd $PROJECT_DIR && $PYTHON_CMD $SERVER_FILE"

# Start in background with nohup
nohup bash -c "$START_CMD" > "$LOG_FILE" 2>&1 &
SERVER_PID=$!

# Save PID
echo $SERVER_PID > "$PID_FILE"

# Wait a moment for server to start
sleep 3

# Check if process is still running
if ps -p $SERVER_PID > /dev/null 2>&1; then
    echo -e "${GREEN}=========================================="
    echo "✓ Server started successfully!"
    echo "==========================================${NC}"
    echo -e "PID: ${GREEN}$SERVER_PID${NC}"
    echo -e "Log file: ${BLUE}$PROJECT_DIR/$LOG_FILE${NC}"
    echo -e "URL: ${BLUE}http://localhost:8000${NC}"
    echo ""
    echo "Useful commands:"
    echo "  View logs:    tail -f $LOG_FILE"
    echo "  Stop server:  kill -TERM $SERVER_PID"
    echo "  Check status: curl http://localhost:8000/health"
    echo ""
    echo "Latest log output:"
    echo "----------------------------------------"
    tail -20 "$LOG_FILE"
    echo "----------------------------------------"
else
    echo -e "${RED}✗ Server failed to start${NC}"
    echo "Check log file: $LOG_FILE"
    cat "$LOG_FILE"
    rm -f "$PID_FILE"
    exit 1
fi