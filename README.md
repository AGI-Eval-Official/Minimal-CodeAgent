# MinimalCodeAgent

<div align="right">
  <a href="README_ch.md">中文版</a> | <a href="README.md">English</a>
</div>

MinimalCodeAgent is a minimal code agent system built on [Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/) that provides essential code agent capabilities through MCP (Model Context Protocol). This project focuses on the most fundamental tool usage for code agents without complex workflows, making it ideal as a foundation for testing LLM code agent capabilities or as a starting point for code agent development.


## Features

- 🤖 **Minimal Code Agent**: Essential code agent capabilities without complex workflows
- 🔧 **MCP Services**: Python interpreter, file operations, and system operations services
- 📁 **File Management**: Support for reading and writing multiple file formats
- 🛡️ **Security Sandbox**: Secure code execution environment
- 🚀 **One-Click Startup**: Simplified deployment and startup process
- 🧪 **Testing Foundation**: Ideal for testing LLM code agent capabilities

## Requirements

- Python 3.10+
- Conda environment manager

## 🚀 Quick Start

### 1. Create Conda Environment

```bash
# Create a conda environment named minimalcodeagent with Python 3.10
conda create -n minimalcodeagent python=3.10 -y
# Activate the environment
conda activate minimalcodeagent
```

### 2. Install Dependencies

```bash
# Navigate to the project directory
cd MinimalCodeAgent
# If your environment do no have Rust compiler, run:
# conda install -c conda-forge tiktoken
# Install project dependencies
pip install -r requirements.txt
```

### 3. Configure API Keys

Edit the `code_agent_local/config.py` file and replace the following configurations:

```python
# Replace with your model name, actual API keys and base URLs
"your_model_name": LiteLlmWithSleep(
        model="openai/gpt-5", # your model
        api_base='https://api.example.com/v1/openai/native', # api base url
        api_key='your-api-key-here', # api key
        max_tokens_threshold=64000,
        enable_compression=True,
        temperature=0.1
)
```
and also you can change hyper-parameters of your model.

## Starting Services

### Step 1: start MCP servers in tmux.

```bash
# Start MCP servers and agent services
./start_mcp.sh /path/to/your/workspace
```

### Step 2: Execute minimal code agent

You have two options to start the code agent:

#### Option 1: Web Interface (Recommended for testing)

```bash
# choose your model name
export ADK_MODEL=<your_model_name>
# Set workspace directory (optional, defaults to /home/workspace)
export CODE_AGENT_WORKSPACE_DIR=/path/to/your/workspace

# Start the web interface
adk web --port 8080
```

Then access the code agent at `http://localhost:8080` in your browser.

**Note**: The code agent's working directory is restricted to the `CODE_AGENT_WORKSPACE_DIR` you set earlier. It cannot access files outside this directory for security reasons.

#### Option 2: API Server

```bash
# choose your model name
export ADK_MODEL=<your_model_name>
# Set workspace directory (optional, defaults to /home/workspace)
export CODE_AGENT_WORKSPACE_DIR=/path/to/your/workspace

# Start the API server
adk api_server --port 8080
```

The API server will be available at `http://localhost:8080` for programmatic access.

### Step 3: Use the Client Script (Optional)

For programmatic access, you can use the provided client script:

```bash
# Basic usage
python run_agent.py --prompt "Write a Python function to calculate fibonacci numbers"

# With custom working directory
python run_agent.py --prompt "Analyze the data in this directory" --workdir /path/to/your/project

# With specific model and output file
python run_agent.py --prompt "Create a web scraper" --model your_model --output response.json

# Full options
python run_agent.py \
  --prompt "Your task here" \
  --workdir /path/to/workspace \
  --port 8080 \
  --model your_model_name \
  --output response.json \
  --verbose
```

**Script Options:**
- `--prompt, -p`: The prompt to send to the agent (required)
- `--workdir, -w`: Working directory for the agent (optional)
- `--port`: ADK API server port (default: 8080)
- `--model, -m`: Model name (uses ADK_MODEL env var if not specified)
- `--session-id, -s`: Session ID (auto-generated if not provided)
- `--output, -o`: Save response to file (optional)
- `--verbose, -v`: Enable verbose output


## Service Ports

The system uses the following ports:

- **8001**: Python interpreter MCP service
- **8002**: File operations MCP service  
- **8003**: System operations MCP service

## Usage

### Basic Usage

1. Ensure all services are started
2. Interact with the agent through API or command line
3. The agent will automatically handle code execution, file operations, and other tasks

### Interactive Shell

```bash
cd code_agent_local
python interative_shell.py
```

### Health Checks

Check MCP service status:

```bash
# Check Python interpreter service
curl http://localhost:8001/python-interpreter/health

# Check file operations service
curl http://localhost:8002/file-operations/health
```

## Configuration

### Main Configuration Files

- `code_agent_local/config.py`: Main configuration file
- `requirements.txt`: Python dependencies list
- `start_mcp.sh`: MCP service startup script
- `code_agent_local/start.sh`: Local service startup script

### Configuration Options

You can modify the following settings in `code_agent_local/config.py`:

```python
# Security settings
ALLOWED_EXTENSIONS = ['.py', '.txt', '.md', '.json', '.yaml', '.yml', '.csv', '.sql']
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
SANDBOX_MODE = True
```


### Security Configuration

The system enables security sandbox mode by default with the following restrictions:

- Allowed file extensions: `.py`, `.txt`, `.md`, `.json`, `.yaml`, `.yml`, `.csv`, `.sql`
- Maximum file size: 10MB
- Workspace isolation


## Development Guide

### Project Structure

```
MinimalCodeAgent/
├── code_agent_local/          # Core code directory
│   ├── agent.py              # Main agent program
│   ├── config.py             # Configuration file
│   ├── mcp_servers.py        # MCP server implementation
│   ├── mcp_tools.py          # MCP tool functions
│   └── start.sh              # Startup script
├── requirements.txt          # Dependencies list
├── start_mcp.sh             # MCP service startup script
└── README.md                # Project documentation
```

### Extension Development

1. Add new MCP tools: Edit `mcp_tools.py`
2. Modify agent behavior: Edit `agent.py`
3. Add new configuration options: Edit `config.py`

## License

This project is licensed under the MIT License.

## Contributing

Issues and Pull Requests are welcome!

## Contact

If you have any questions, please contact us through:

- Submit a GitHub Issue
- Send an email to the project maintainers

## Acknowledgments

This project is built on the [Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/), which provides the foundational framework for agent development. We thank the Google ADK team for creating this excellent framework that makes agent development more accessible and modular.

---

**Note**: Please ensure that API keys and security settings are properly configured in production environments to avoid exposing sensitive information.