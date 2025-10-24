# MinimalCodeAgent

<div align="right">
  <a href="README_ch.md">中文版</a> | <a href="README.md">English</a>
</div>

MinimalCodeAgent 是一个基于 [Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/) 构建的MinimalCode系统，通过 MCP（模型上下文协议）提供基础的代码代理功能。该项目专注于代码代理最基本的工具使用，没有复杂的工作流程，非常适合作为测试 LLM 代码代理能力的基础，或作为代码代理开发的起点。

## 功能特性

- 🤖 **MinimalCodeAgsnt**：提供基础代码代理功能，无复杂工作流程
- 🔧 **MCP 服务**：Python 解释器、文件操作和系统操作服务
- 📁 **文件管理**：支持多种文件格式的读写操作
- 🛡️ **安全沙箱**：安全的代码执行环境
- 🚀 **一键启动**：简化的部署和启动流程
- 🧪 **测试基础**：理想的 LLM 代码代理能力测试平台

## 系统要求

- Python 3.10+
- Conda 环境管理器

## 🚀 快速开始

### 1. 创建 Conda 环境

```bash
# 创建名为 minimalcodeagent 的 conda 环境，使用 Python 3.10
conda create -n minimalcodeagent python=3.10 -y
# 激活环境
conda activate minimalcodeagent
```

### 2. 安装依赖

```bash
# 进入项目目录
cd MinimalCodeAgent
# 如果您的环境没有 Rust 编译器，请运行：
# conda install -c conda-forge tiktoken
# 安装项目依赖
pip install -r requirements.txt
```

### 3. 配置 API 密钥

编辑 `code_agent_local/config.py` 文件，替换以下配置：

```python
# 替换为您的模型名称、实际 API 密钥和基础 URL
"your_model_name": LiteLlmWithSleep(
        model="openai/gpt-5", # 您的模型
        api_base='https://api.example.com/v1/openai/native', # API 基础 URL
        api_key='your-api-key-here', # API 密钥
        max_tokens_threshold=64000,
        enable_compression=True,
        temperature=0.1
)
```
您也可以更改模型的超参数。

## 启动服务

### 步骤 1：在 tmux 中启动 MCP 服务器

```bash
# 启动 MCP 服务器和代理服务
./start_mcp.sh /path/to/your/workspace
```

### 步骤 2：执行Minimal

您有两种方式启动代码代理：

#### 选项 1：Web 界面（推荐用于测试）

```bash
# 选择您的模型名称
export ADK_MODEL=<your_model_name>
# 设置工作目录（可选，默认为 /home/workspace）
export CODE_AGENT_WORKSPACE_DIR=/path/to/your/workspace

# 启动 Web 界面
adk web --port 8080
```

然后在浏览器中访问 `http://localhost:8080` 使用代码代理。

**注意**：代码代理的工作目录限制在您之前设置的 `CODE_AGENT_WORKSPACE_DIR` 内。出于安全考虑，它无法访问该目录之外的文件。

#### 选项 2：API 服务器

```bash
# 选择您的模型名称
export ADK_MODEL=<your_model_name>
# 设置工作目录（可选，默认为 /home/workspace）
export CODE_AGENT_WORKSPACE_DIR=/path/to/your/workspace

# 启动 API 服务器
adk api_server --port 8080
```

API 服务器将在 `http://localhost:8080` 提供程序化访问。

### 步骤 3：使用客户端脚本（可选）

对于程序化访问，您可以使用提供的客户端脚本：

```bash
# 基本用法
python run_agent.py --prompt "编写一个计算斐波那契数的 Python 函数"

# 使用自定义工作目录
python run_agent.py --prompt "分析此目录中的数据" --workdir /path/to/your/project

# 使用特定模型和输出文件
python run_agent.py --prompt "创建网络爬虫" --model your_model --output response.json

# 完整选项
python run_agent.py \
  --prompt "您的任务" \
  --workdir /path/to/workspace \
  --port 8080 \
  --model your_model_name \
  --output response.json \
  --verbose
```

**脚本选项：**
- `--prompt, -p`：发送给代理的提示（必需）
- `--workdir, -w`：代理的工作目录（可选）
- `--port`：ADK API 服务器端口（默认：8080）
- `--model, -m`：模型名称（如果未指定则使用 ADK_MODEL 环境变量）
- `--session-id, -s`：会话 ID（如果未提供则自动生成）
- `--output, -o`：将响应保存到文件（可选）
- `--verbose, -v`：启用详细输出

## 服务端口

系统使用以下端口：

- **8001**：Python 解释器 MCP 服务
- **8002**：文件操作 MCP 服务  
- **8003**：系统操作 MCP 服务

## 使用方法

### 基本用法

1. 确保所有服务已启动
2. 通过 API 或命令行与代理交互
3. 代理将自动处理代码执行、文件操作和其他任务

### 交互式 Shell

```bash
cd code_agent_local
python interative_shell.py
```

### 健康检查

检查 MCP 服务状态：

```bash
# 检查 Python 解释器服务
curl http://localhost:8001/python-interpreter/health

# 检查文件操作服务
curl http://localhost:8002/file-operations/health
```

## 配置

### 主要配置文件

- `code_agent_local/config.py`：主配置文件
- `requirements.txt`：Python 依赖列表
- `start_mcp.sh`：MCP 服务启动脚本
- `code_agent_local/start.sh`：本地服务启动脚本

### 配置选项

您可以在 `code_agent_local/config.py` 中修改以下设置：

```python
# 安全设置
ALLOWED_EXTENSIONS = ['.py', '.txt', '.md', '.json', '.yaml', '.yml', '.csv', '.sql']
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
SANDBOX_MODE = True
```

还可以在`lite_llm_wrapper.py`中修改MinimalCodeAgent的token上限`max_total_tokens`和运行时间上限`max_session_time`。

### 安全配置

系统默认启用安全沙箱模式，具有以下限制（可修改）：

- 允许的文件扩展名：`.py`、`.txt`、`.md`、`.json`、`.yaml`、`.yml`、`.csv`、`.sql`
- 最大文件大小：10MB
- 工作区隔离


### 查看日志

```bash
# 查看 tmux 会话（如果使用 tmux）
tmux ls
tmux a -t adk_mcp_server

# 查看进程
ps aux | grep mcp_servers
```

## 开发指南

### 项目结构

```
MinimalCodeAgent/
├── code_agent_local/          # 核心代码目录
│   ├── agent.py              # 主代理程序
│   ├── config.py             # 配置文件
│   ├── mcp_servers.py        # MCP 服务器实现
│   ├── mcp_tools.py          # MCP 工具函数
│   └── start.sh              # 启动脚本
├── requirements.txt          # 依赖列表
├── start_mcp.sh             # MCP 服务启动脚本
└── README.md                # 项目文档
```

### 扩展开发

1. 添加新的 MCP 工具：编辑 `mcp_tools.py`
2. 修改代理行为：编辑 `agent.py`
3. 添加新的配置选项：编辑 `config.py`

## 许可证

本项目采用 MIT 许可证。

## 贡献

欢迎提交 Issue 和 Pull Request！

## 联系方式

如有任何问题，请通过以下方式联系我们：

- 提交 GitHub Issue
- 发送邮件到fulingyue@sjtu.edu.cn

## 致谢

本项目基于 [Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/) 构建，该框架为代理开发提供了基础框架。我们感谢 Google ADK 团队创建了这个优秀的框架，使代理开发更加便捷和模块化。

---

**注意**：请确保在生产环境中正确配置 API 密钥和安全设置，以避免泄露敏感信息。
