#!/bin/bash
# MinimalCodeAgent MCP Server Startup Script
WORKING_DIR=$1
# Clean up existing tmux sessions to avoid port conflicts
tmux kill-session -t adk_mcp_server 2>/dev/null

# Define tmux session name
SESSION_NAME="adk_mcp_server"

# Set workspace directory
export CODE_AGENT_WORKSPACE_DIR=$WORKING_DIR

# Create new tmux session
tmux new-session -d -s $SESSION_NAME -n $SESSION_NAME

# Build startup command
# 1. Activate googleadk environment
# 2. Set proxy environment variables
# 3. Change to project directory
# 4. Start ADK MCP server
CMD="conda deactivate ; conda activate googleadk ; export CODE_AGENT_WORKSPACE_DIR=$WORKING_DIR ; cd ./code_agent_local ; ./start.sh"

# Execute startup command in tmux session
tmux send-keys -t $SESSION_NAME "$CMD" C-m

echo "ADK MCP server started in tmux session: $SESSION_NAME"
echo "To attach to the session: tmux a -t $SESSION_NAME"
echo "To check status: tmux ls"
