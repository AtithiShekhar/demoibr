#!/bin/bash

###############################################################################
# Check Drug Analysis API Server Status
###############################################################################

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_DIR="/home/ubuntu/ibr-backend/demoibr/bra"
PID_FILE="$PROJECT_DIR/server.pid"
LOG_FILE="$PROJECT_DIR/server.log"

echo "=========================================="
echo "Drug Analysis API Server Status"
echo "=========================================="

# Check PID file
if [ -f "$PID_FILE" ]; then
    SERVER_PID=$(cat "$PID_FILE")
    echo -e "PID File: ${GREEN}Found${NC} (PID: $SERVER_PID)"
    
    # Check if process is running
    if ps -p "$SERVER_PID" > /dev/null 2>&1; then
        echo -e "Process: ${GREEN}Running${NC}"
        
        # Get process details
        PS_INFO=$(ps -p "$SERVER_PID" -o %cpu,%mem,etime,cmd --no-headers)
        echo -e "Details: ${BLUE}$PS_INFO${NC}"
    else
        echo -e "Process: ${RED}Not Running${NC} (stale PID file)"
    fi
else
    echo -e "PID File: ${RED}Not Found${NC}"
fi

# Check port 8000
echo ""
PORT_CHECK=$(sudo lsof -i:8000 2>/dev/null)
if [ ! -z "$PORT_CHECK" ]; then
    echo -e "Port 8000: ${GREEN}In Use${NC}"
    echo "$PORT_CHECK"
else
    echo -e "Port 8000: ${RED}Free${NC}"
fi

# API Health Check
echo ""
echo "API Health Check:"
HEALTH_RESPONSE=$(curl -s http://localhost:8000/health 2>/dev/null)

if [ $? -eq 0 ]; then
    echo -e "Status: ${GREEN}Healthy${NC}"
    echo "$HEALTH_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$HEALTH_RESPONSE"
else
    echo -e "Status: ${RED}Unreachable${NC}"
fi

# Show recent logs
if [ -f "$LOG_FILE" ]; then
    echo ""
    echo "Recent Logs (last 10 lines):"
    echo "----------------------------------------"
    tail -10 "$LOG_FILE"
    echo "----------------------------------------"
fi

# Database status
echo ""
echo "Database Status:"
DB_STATS=$(curl -s http://localhost:8000/database/stats 2>/dev/null)
if [ $? -eq 0 ]; then
    echo "$DB_STATS" | python3 -m json.tool 2>/dev/null || echo "$DB_STATS"
else
    echo -e "${YELLOW}Unable to fetch database stats${NC}"
fi

# Queue stats
echo ""
echo "Queue Status:"
QUEUE_STATS=$(curl -s http://localhost:8000/queue/stats 2>/dev/null)
if [ $? -eq 0 ]; then
    echo "$QUEUE_STATS" | python3 -m json.tool 2>/dev/null || echo "$QUEUE_STATS"
else
    echo -e "${YELLOW}Unable to fetch queue stats${NC}"
fi

echo ""
echo "=========================================="