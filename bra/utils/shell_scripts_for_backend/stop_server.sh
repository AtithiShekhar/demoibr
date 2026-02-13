#!/bin/bash

###############################################################################
# Stop Drug Analysis API Server
# Safely stops the background server process
###############################################################################

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_DIR="/home/ubuntu/ibr-backend/demoibr/bra"  # Project directory
PID_FILE="$PROJECT_DIR/server.pid"

echo "=========================================="
echo "Stopping Drug Analysis API Server"
echo "=========================================="

cd "$PROJECT_DIR" || exit 1

# Check if PID file exists
if [ ! -f "$PID_FILE" ]; then
    echo -e "${YELLOW}⚠ PID file not found${NC}"
    echo "Server may not be running or was started manually"
    
    # Try to find process on port 8000
    PORT_PID=$(sudo lsof -ti:8000 2>/dev/null || true)
    if [ ! -z "$PORT_PID" ]; then
        echo -e "${YELLOW}Found process on port 8000 (PID: $PORT_PID)${NC}"
        read -p "Kill this process? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            sudo kill -9 "$PORT_PID"
            echo -e "${GREEN}✓ Process killed${NC}"
        fi
    else
        echo "No process found on port 8000"
    fi
    exit 0
fi

# Read PID from file
SERVER_PID=$(cat "$PID_FILE")
echo "Server PID: $SERVER_PID"

# Check if process is running
if ! ps -p "$SERVER_PID" > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠ Process not running${NC}"
    rm -f "$PID_FILE"
    exit 0
fi

# Graceful shutdown
echo "Attempting graceful shutdown..."
kill -TERM "$SERVER_PID" 2>/dev/null

# Wait up to 10 seconds for graceful shutdown
for i in {1..10}; do
    if ! ps -p "$SERVER_PID" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Server stopped gracefully${NC}"
        rm -f "$PID_FILE"
        exit 0
    fi
    sleep 1
    echo -n "."
done

echo ""
echo -e "${YELLOW}⚠ Graceful shutdown failed, forcing...${NC}"

# Force kill
kill -9 "$SERVER_PID" 2>/dev/null
sleep 1

# Verify stopped
if ps -p "$SERVER_PID" > /dev/null 2>&1; then
    echo -e "${RED}✗ Failed to stop server${NC}"
    exit 1
else
    echo -e "${GREEN}✓ Server stopped (forced)${NC}"
    rm -f "$PID_FILE"
    
    # Also kill anything on port 8000 just to be sure
    PORT_PID=$(sudo lsof -ti:8000 2>/dev/null || true)
    if [ ! -z "$PORT_PID" ]; then
        sudo kill -9 "$PORT_PID" 2>/dev/null || true
    fi
    
    echo -e "${GREEN}✓ Port 8000 freed${NC}"
fi