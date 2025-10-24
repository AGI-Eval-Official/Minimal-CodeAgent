import os
import uuid
from datetime import datetime
from google.adk.models.lite_llm import LiteLlm
from lite_llm_wrapper import LiteLlmWithSleep

# IMPORTANT: Replace 'your-api-key-here' with your actual API keys
# IMPORTANT: Replace 'https://api.example.com' with your actual API base URLs
# For security reasons, never commit real API keys to version control

MAX_TOKENS = int(32768)

# Friday's models all start with openai
# api_key should not be leaked
model_dict = {
    "gpt-5": LiteLlmWithSleep(
        model="openai/gpt-5",
        api_base='https://api.example.com/v1/openai/native',
        api_key='your-api-key-here',
        max_tokens_threshold=64000,
        enable_compression=True,
        temperature=0.1
    )
}



# Basic model configuration
BASIC_MODEL = LiteLlmWithSleep(
    model="openai/Doubao-Seed-1.6",
    api_base='https://api.example.com/v1/openai/native',
    api_key='your-api-key-here',
    max_tokens_threshold=300,
    # for debug 
    enable_compression=True,
    max_total_tokens=2000,
    temperature=0.6
)




# Generate random execution ID
def generate_execution_id():
    """Generate unique execution ID"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    return f"exec_{timestamp}_{unique_id}"

# Current execution ID
CURRENT_EXECUTION_ID = generate_execution_id()

# Local MCP server configuration
PYTHON_INTERPRETER_MCP_URL = "http://localhost:8001/python-interpreter"
FILE_OPERATIONS_MCP_URL = "http://localhost:8002/file-operations"
SYSTEM_OPERATIONS_MCP_URL = "http://localhost:8003/system-operations"

# MCP connection configuration
MCP_SSE_TIMEOUT = 30
MAX_ITERATIONS = 10

# System configuration
SYSTEM_NAME = "MinimalCodeAgent"
BASE_WORKSPACE_DIR = "/home/workspace"

# example: export CODE_AGENT_WORKSPACE_DIR=/path/to/your/workspace
WORKSPACE_DIR = os.getenv('CODE_AGENT_WORKSPACE_DIR', BASE_WORKSPACE_DIR)

# if the workspace path is a relative path, convert it to an absolute path
if not os.path.isabs(WORKSPACE_DIR):
    WORKSPACE_DIR = os.path.abspath(WORKSPACE_DIR)

# Security configuration
ALLOWED_EXTENSIONS = ['.py', '.txt', '.md', '.json', '.yaml', '.yml', '.csv', '.sql']
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
SANDBOX_MODE = True

print(f"🚀 Current execution ID: {CURRENT_EXECUTION_ID}")
print(f"📁 Workspace path: {WORKSPACE_DIR}") 

