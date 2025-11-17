"""
Local Code Agent MCP Tools Definition
Provides Python interpreter, file operations and system operations functionality
"""

# JSON error fix patch
import json
import logging

logger_patch = logging.getLogger(__name__)

def _safe_json_loads(json_str: str, fallback_value: dict = None) -> dict:
    """Safe JSON parsing with automatic fixing of common format errors"""
    if fallback_value is None:
        fallback_value = {}
    
    if not json_str or json_str.strip() == "":
        return fallback_value
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger_patch.warning(f"JSON parsing error, attempting to fix: {e}")
        
        # Try to fix common issues
        fixed_attempts = [
            _fix_unterminated_string(json_str),
            _fix_trailing_comma(json_str),
            _extract_partial_json(json_str),
        ]
        
        for fixed_json in fixed_attempts:
            if fixed_json:
                try:
                    result = json.loads(fixed_json)
                    logger_patch.info(f"JSON fix successful")
                    return result
                except json.JSONDecodeError:
                    continue
        
        logger_patch.error(f"JSON fix failed, using default value")
        return fallback_value

def _fix_unterminated_string(json_str: str) -> str:
    """Fix unterminated strings"""
    try:
        if json_str.count('"') % 2 == 1:  # Odd number of quotes
            return json_str + '"}'
    except Exception:
        pass
    return None

def _fix_trailing_comma(json_str: str) -> str:
    """Fix trailing commas"""
    try:
        import re
        fixed = re.sub(r',\s*}', '}', json_str)
        fixed = re.sub(r',\s*]', ']', fixed)
        return fixed
    except Exception:
        pass
    return None

def _extract_partial_json(json_str: str) -> str:
    """Extract partial valid JSON"""
    try:
        start = json_str.find('{')
        if start == -1:
            return None
        
        brace_count = 0
        for i, char in enumerate(json_str[start:], start):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    return json_str[start:i+1]
        
        if brace_count > 0:
            return json_str[start:] + '}' * brace_count
    except Exception:
        pass
    return None


def apply_json_fix():
    """Apply JSON error fix patch to LiteLLM"""
    try:
        import google.adk.models.lite_llm as lite_llm_module
        
       
        original_function = lite_llm_module._message_to_generate_content_response
        
        def patched_function(*args, **kwargs):
            """
            Patched function that handles all possible argument signatures.
            Uses *args and **kwargs to be compatible with any function signature.
            """
            try:
                # Try calling the original function with all arguments
                return original_function(*args, **kwargs)
            except (json.JSONDecodeError, TypeError, ValueError) as e:
                logger_patch.warning(f"Detected error in _message_to_generate_content_response, using fix version: {e}")
                
                # Extract message from args or kwargs
                message = None
                is_partial = False
                
                if args:
                    message = args[0]
                    if len(args) > 1:
                        is_partial = args[1]
                elif 'message' in kwargs:
                    message = kwargs['message']
                    is_partial = kwargs.get('is_partial', False)
                
                if message is None:
                    # If we can't extract message, re-raise the original error
                    raise e
                
                # Fix version response generation
                from google.genai import types
                from google.adk.models.llm_response import LlmResponse
                
                parts = []
                if message.get("content", None):
                    parts.append(types.Part.from_text(text=message.get("content")))

                if message.get("tool_calls", None):
                    for tool_call in message.get("tool_calls"):
                        if tool_call.type == "function":
                            try:
                                # Use safe JSON parsing
                                args_json = _safe_json_loads(tool_call.function.arguments or "{}")
                                part = types.Part.from_function_call(
                                    name=tool_call.function.name,
                                    args=args_json,
                                )
                                part.function_call.id = tool_call.id
                                parts.append(part)
                            except Exception as func_error:
                                logger_patch.error(f"Function call creation failed: {func_error}")
                         
                                error_text = f"[Function call error: {tool_call.function.name}]"
                                parts.append(types.Part.from_text(text=error_text))

                return LlmResponse(
                    content=types.Content(role="model", parts=parts), 
                    partial=is_partial
                )
        
        lite_llm_module._message_to_generate_content_response = patched_function
        logger_patch.info("✅ JSON error fix patch applied")
        
    except Exception as e:
        logger_patch.warning(f"JSON fix patch application failed: {e}")


apply_json_fix()

import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional
from google.adk.tools import ToolContext
try:
    from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
except Exception:  
    from google.adk.tools.mcp_tool.mcp_toolset import McpToolset as MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import SseServerParams
from pydantic import BaseModel
import logging
import pexpect
import asyncio
from aiohttp import web
from typing import Dict, Any, Optional
from code_agent_local.interative_shell import step, terminate

logger = logging.getLogger(__name__)
safe_commands = ['ls', 'pwd', 'echo', 'cat', 'head', 'tail', 'grep', 'find', 'python', 'python3', 'chmod', 'cd', 'lsof', 'mkdir']

from .config import (
    PYTHON_INTERPRETER_MCP_URL, 
    FILE_OPERATIONS_MCP_URL, 
    SYSTEM_OPERATIONS_MCP_URL,
    MCP_SSE_TIMEOUT,
    WORKSPACE_DIR,
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE,
    SANDBOX_MODE,
    CURRENT_EXECUTION_ID
)


try:
    from mcp_retry_wrapper import apply_mcp_monkey_patches
    patch_info = apply_mcp_monkey_patches()
    logger.info(f"MCP monkey patch results: {patch_info}")
except Exception as _patch_err:
    logger.warning(f"MCP monkey patch failed (does not affect running):{_patch_err}")

# Data model definition
class PythonCode(BaseModel):
    """Python code execution request"""
    code: str
    timeout: int = 30
    capture_output: bool = True

class FileOperation(BaseModel):
    """File operation request"""
    operation: str  # read, write, delete, list, copy, move
    path: str
    content: Optional[str] = None
    destination: Optional[str] = None

class SystemCommand(BaseModel):
    """System command execution request"""
    command: str
    timeout: int = 30
    capture_output: bool = True
    working_directory: Optional[str] = None

# Basic tool functions
def exit_loop(tool_context: ToolContext):
    """When task is completed, exit the loop"""
    # Set escalate flag, this will make the agent stop executing
    tool_context.actions.escalate = True
    
    # Add additional stop flag
    if hasattr(tool_context, 'stop_execution'):
        tool_context.stop_execution = True
    
    # Record exit log
    import logging
    logger = logging.getLogger(__name__)
    logger.info("exit_loop tool called, stopping agent execution")
    
    return {
        "status": "completed", 
        "message": "Agent execution stopped by exit_loop tool",
        "stop_reason": "user_requested_exit"
    }

def create_workspace(tool_context: ToolContext, workspace_name: Optional[str] = None, create_venv: bool = True):
    """
    Create workspace
    
    Args:
        tool_context: Tool context
        workspace_name: Workspace name, if None then use current execution ID
        create_venv: Whether to create virtual environment, default True
    
    Returns:
        dict: Dictionary with workspace information
    """
    if workspace_name is None:
        workspace_name = CURRENT_EXECUTION_ID
    
    workspace_path = Path(WORKSPACE_DIR) / workspace_name
    workspace_path.mkdir(parents=True, exist_ok=True)
    
    
    (workspace_path / "src").mkdir(exist_ok=True)
    (workspace_path / "tests").mkdir(exist_ok=True)
    (workspace_path / "data").mkdir(exist_ok=True)
    (workspace_path / "docs").mkdir(exist_ok=True)
    
    result = {
        "workspace_path": str(workspace_path),
        "workspace_name": workspace_name,
        "status": "created",
        "directories": ["src", "tests", "data", "docs"]
    }
    

    if create_venv:
        try:
            venv_path = workspace_path / "venv"
            
    
            subprocess.run(
                ['python', '-m', 'venv', str(venv_path)],
                check=True,
                capture_output=True,
                text=True
            )
            
 
            activate_script = workspace_path / "activate_venv.sh"
            with open(activate_script, 'w', encoding='utf-8') as f:
                f.write(f"""#!/bin/bash
# Activate virtual environment script
echo "Activate virtual environment: {venv_path}"
source "{venv_path}/bin/activate"
echo "Virtual environment activated, Python path: $(which python)"
echo "Current working directory: $(pwd)"
""")
            
      
            os.chmod(activate_script, 0o755)
            
            
            requirements_file = workspace_path / "requirements.txt"
            with open(requirements_file, 'w', encoding='utf-8') as f:
                f.write("# Project dependencies\n# Example:\n# requests==2.31.0\n# pandas==2.0.3\n")
            

            gitignore_file = workspace_path / ".gitignore"
            with open(gitignore_file, 'w', encoding='utf-8') as f:
                f.write("""# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log

# Data files
data/*.csv
data/*.json
""")
            
            result.update({
                "venv_created": True,
                "venv_path": str(venv_path),
                "activate_script": str(activate_script),
                "requirements_file": str(requirements_file),
                "gitignore_file": str(gitignore_file)
            })
            
            logger.info(f"Virtual environment created successfully: {venv_path}")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Virtual environment creation failed: {e}")
            result.update({
                "venv_created": False,
                "venv_error": str(e)
            })
        except Exception as e:
            logger.error(f"Error occurred while creating virtual environment: {e}")
            result.update({
                "venv_created": False,
                "venv_error": str(e)
            })
    else:
        result["venv_created"] = False
    
    return result

def list_workspace(tool_context: ToolContext, workspace_name: Optional[str] = None):
    """
    List workspace content
    
    Args:
        tool_context: Tool context
        workspace_name: Workspace name, if None then use current execution ID
    
    Returns:
        dict: Dictionary with workspace file list
    """
    if workspace_name is None:
        workspace_name = CURRENT_EXECUTION_ID
    
    workspace_path = Path(WORKSPACE_DIR) / workspace_name
    
    if not workspace_path.exists():
        return {"error": "Workspace does not exist"}
    
    files = []
    for item in workspace_path.rglob("*"):
        if item.is_file():
            files.append({
                "path": str(item.relative_to(workspace_path)),
                "size": item.stat().st_size,
                "type": "file"
            })
        elif item.is_dir():
            files.append({
                "path": str(item.relative_to(workspace_path)),
                "type": "directory"
            })
    
    return {
        "workspace_path": str(workspace_path),
        "workspace_name": workspace_name,
        "files": files
    }

def validate_file_path(file_path: str) -> bool:
    """Validate file path is safe"""
    # tmp directory is not checked
    if file_path.startswith("/tmp"):
        return True
    if SANDBOX_MODE:
        # In sandbox mode, only allow access to files in the workspace
        workspace_path = Path(WORKSPACE_DIR).resolve()
        file_path = Path(file_path).resolve()
        
        if not str(file_path).startswith(str(workspace_path)) or not str(file_path).startswith("/tmp"):
            return False
    # Check file extensions
    if Path(file_path).suffix not in ALLOWED_EXTENSIONS:
        return False
    
    return True

def read_file(tool_context: ToolContext, file_path: str):
    """
    Read file content
    
    Args:
        tool_context: Tool context
        file_path: File path
    
    Returns:
        dict: Dictionary with file content
    """
    if not validate_file_path(file_path):
        return {"error": "File path is not safe or file type is not allowed"}
    
    try:
        file_path = Path(file_path)
        if not file_path.exists():
            return {"error": "File does not exist"}
        
        if file_path.stat().st_size > MAX_FILE_SIZE:
            return {"error": "File is too large"}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            "file_path": str(file_path),
            "content": content,
            "size": len(content)
        }
    except Exception as e:
        return {"error": f"Failed to read file: {str(e)}"}

def write_file(tool_context: ToolContext, file_path: str, content: str):
    """
    Write file content
    
    Args:
        tool_context: Tool context
        file_path: File path (required)
        content: Content to write (required)
    
    Returns:
        dict: Dictionary with operation result
    """
    if not validate_file_path(file_path):
        return {"error": "File path is not safe or file type is not allowed"}
    
    try:
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {
            "file_path": str(file_path),
            "status": "written",
            "size": len(content)
        }
    except Exception as e:
        return {"error": f"Failed to write file: {str(e)}"}

def delete_file(tool_context: ToolContext, file_path: str):
    """
    Delete file
    
    Args:
        tool_context: Tool context
        file_path: File path
    
    Returns:
        dict: Dictionary with operation result
    """
    if not validate_file_path(file_path):
        return {"error": "File path is not safe or file type is not allowed"}
    
    try:
        file_path = Path(file_path)
        if not file_path.exists():
            return {"error": "File does not exist"}
        
        file_path.unlink()
        return {
            "file_path": str(file_path),
            "status": "deleted"
        }
    except Exception as e:
        return {"error": f"Failed to delete file: {str(e)}"}

def activate_venv(tool_context: ToolContext, workspace_name: Optional[str] = None):
    """
    Activate virtual environment of workspace
    
    Args:
        tool_context: Tool context
        workspace_name: Workspace name, if None then use current execution ID
    
    Returns:
        dict: Dictionary with activation result
    """
    if workspace_name is None:
        workspace_name = CURRENT_EXECUTION_ID
    
    workspace_path = Path(WORKSPACE_DIR) / workspace_name
    venv_path = workspace_path / "venv"
    
    if not venv_path.exists():
        return {"error": "Virtual environment does not exist, please create virtual environment first"}
    
    try:
        # Get Python interpreter path of virtual environment
        if os.name == 'nt':  # Windows
            python_path = venv_path / "Scripts" / "python.exe"
        else:  # Unix/Linux/macOS
            python_path = venv_path / "bin" / "python"
        
        if not python_path.exists():
            return {"error": "Virtual environment Python interpreter does not exist"}

        result = subprocess.run(
            [str(python_path), '-m', 'pip', 'list'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        return {
            "workspace_name": workspace_name,
            "venv_path": str(venv_path),
            "python_path": str(python_path),
            "status": "activated",
            "installed_packages": result.stdout if result.returncode == 0 else "Failed to get package list"
        }
        
    except Exception as e:
        return {"error": f"Failed to activate virtual environment: {str(e)}"}

def execute_python_code(tool_context: ToolContext, code: str, timeout: int = 30, use_venv: bool = True):
    """
    Execute Python code
    
    Args:
        tool_context: Tool context
        code: Python code to execute (required)
        timeout: Execution timeout (seconds), default 30 seconds
        use_venv: Whether to use virtual environment, default True
    
    Returns:
        dict: Dictionary with execution result
    """
    try:
        # Determine the Python interpreter to use
        if use_venv:
            workspace_path = Path(WORKSPACE_DIR) / CURRENT_EXECUTION_ID
            venv_path = workspace_path / "venv"
            
            if venv_path.exists():
                if os.name == 'nt':  # Windows
                    python_executable = str(venv_path / "Scripts" / "python.exe")
                else:  # Unix/Linux/macOS
                    python_executable = str(venv_path / "bin" / "python")
                
                if not Path(python_executable).exists():
                    python_executable = 'python'  # Fall back to system Python
            else:
                python_executable = 'python'  # Fall back to system Python
        else:
            python_executable = 'python'
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
       
        result = subprocess.run(
            [python_executable, temp_file],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=WORKSPACE_DIR
        )
        
        os.unlink(temp_file)
        
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode,
            "execution_time": "completed",
            "python_executable": python_executable,
            "used_venv": use_venv and venv_path.exists() if use_venv else False
        }
    except subprocess.TimeoutExpired:
        return {"error": "Code execution timed out"}
    except Exception as e:
        return {"error": f"Failed to execute code: {str(e)}"}

def run_system_command(tool_context: ToolContext, command: str, timeout: int = 15):
    """
    Run system command
    
    Args:
        tool_context: Tool context
        command: System command to execute
        timeout: Execution timeout (seconds), default 30 seconds
    
    Returns:
        dict: Dictionary with execution result
    """
    # Open restrictions
    SANDBOX_MODE = False

    if SANDBOX_MODE:
            
        if not any(cmd in command for cmd in safe_commands):
            return {"error": "The command you executed is not allowed in sandbox mode; safe command list: " + str(safe_commands)}
    try:
        logger.info(f"Running system command: {command}")
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=WORKSPACE_DIR
        )
        
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"error": "Command execution timed out"}
    except Exception as e:
        return {"error": f"Failed to execute command: {str(e)}"}

def interactive_system_command(
    tool_context: ToolContext,
    command: str,
    inputs: Optional[List[str]] = None,
    timeout: int = 15
):
    """
    Interactive running system command, support input and output interaction

    Args:
        tool_context: Tool context
        command: System command to execute
        inputs: Content to input to command (string list, each element enter once)
        timeout: Execution timeout (seconds)

    Returns:
        dict: Dictionary with execution result
    """
    SANDBOX_MODE = False
    if SANDBOX_MODE:
        safe_commands = ['ls', 'pwd', 'echo', 'cat', 'head', 'tail', 'grep', 'find', 'python', 'python3', 'lsof']
        if not any(cmd in command for cmd in safe_commands):
            return {"error": "The command you executed is not allowed in sandbox mode; safe command list: " + str(safe_commands)}

    try:
        logger.info(f"Interactive executing system command: {command}")
        child = pexpect.spawn(command, cwd=WORKSPACE_DIR, timeout=timeout, encoding='utf-8')
        output = ""
        if inputs:
            for inp in inputs:
                child.expect([pexpect.TIMEOUT, pexpect.EOF], timeout=1)
                child.sendline(inp)
        child.expect(pexpect.EOF)
        output = child.before
        return_code = child.exitstatus
        return {
            "stdout": output,
            "stderr": "", 
            "return_code": return_code
        }
    except pexpect.TIMEOUT:
        return {"error": "Command execution timed out"}
    except Exception as e:
        return {"error": f"Failed to execute interactive command: {str(e)}"}

def run_interactive_python_code(tool_context: ToolContext, cmd: str, session_id: Optional[str] = None, user_input: Optional[str] = None, timeout: int = 30):
    """
    Run an interactive Python code session.
    
    The first call needs to provide the code parameter to start a new session, and the subsequent call needs to provide the session_id to continue the previous session.
    If you need to input content to the Python code, provide the user_input parameter.
    
    Args:
        tool_context: Tool context
        cmd: Python code to execute
        session_id: Session ID, for continuing the previous session
        user_input: Content to input to Python code
        timeout: Execution timeout (seconds)
    Returns:
        dict: Dictionary with execution result
    """
    try:
        result = step(
            cmd=cmd,
            session_id=session_id,
            user_input=user_input
        )
        return result
    except Exception as e:
        return {
            "error": str(e),
            "session_id": session_id,
            "output": "",
            "waiting": False,
            "finished": True
        }

def start_interative_shell(tool_context: ToolContext, cmd: str = "bash") -> Dict[str, Any]:
    """
    Start an interactive shell session.
    
    Args:
        tool_context: Tool context
        cmd: Shell command to execute
    Returns:
        dict: Dictionary with execution result
    """
    session_id = None
    try:
        result = step(
            cmd=cmd,
        )
        return result
    except Exception as e:
        return {
            "error": str(e),
            "session_id": session_id,
            "output": session_id,
            "waiting": False,
            "finished": True
        }

IS_IN_PYTHON_ENV = False

def run_interactive_shell(tool_context: ToolContext, session_id: Optional[str] = None, user_input: Optional[str] = None) -> Dict[str, Any]:
    """
    Run an interactive shell session.
    
    The first call needs to provide the cmd parameter to start a new session, and the subsequent call needs to provide the session_id to continue the previous session.
    If you need to input content to the shell, provide the user_input parameter.
    
    Args:
        tool_context: Tool context
        session_id: Session ID, for continuing the previous session
        user_input: Content to input to shell
    Returns:
        dict: Dictionary with execution result
    """
    # Get the state of the current session
    session_state = getattr(tool_context, 'python_env_state', {})
    if session_id not in session_state:
        session_state[session_id] = False
    is_in_python = session_state[session_id]
    
    SANDBOX_MODE = False

    # Check the safety of the command
    if SANDBOX_MODE and is_in_python and user_input:
        current_command = user_input.split()[0] if user_input else ''
        if not any(cmd in current_command for cmd in safe_commands):
            return {"error": "The command you executed is not allowed in sandbox mode; safe command list: " + str(safe_commands)}
    
    # Update the state of the Python environment
    if user_input and user_input.startswith("python"):
        session_state[session_id] = True
    elif user_input == "exit":
        session_state[session_id] = False
    
    # Save the state back to the context
    setattr(tool_context, 'python_env_state', session_state)
    
    try:
        result = step(
            session_id=session_id,
            user_input=user_input
        )
        return result
    except Exception as e:
        return {
            "error": str(e),
            "session_id": session_id,
            "output": "",
            "waiting": False,
            "finished": True
        }

def kill_shell_session(tool_context: ToolContext, session_id: str) -> Dict[str, Any]:
    """
    Terminate a shell session.
    
    Args:
        session_id (str): Session ID to terminate
    Returns:
        dict: Dictionary with execution result
    """
    try:
        terminate(session_id)
        return {
            "message": f"Session {session_id} has been terminated",
            "output": f"Session {session_id} has been terminated"
        }
    except Exception as e:
        return {
            "error": str(e),
            "output": "",
        }


# Create MCP toolset
def create_python_interpreter_toolset():
    """Create Python interpreter MCP toolset"""
    return MCPToolset(
        connection_params=SseServerParams(
            url=PYTHON_INTERPRETER_MCP_URL,
            sse_read_timeout=MCP_SSE_TIMEOUT
        )
    )

def create_file_operations_toolset():
    """Create file operations MCP toolset"""
    return MCPToolset(
        connection_params=SseServerParams(
            url=FILE_OPERATIONS_MCP_URL,
            sse_read_timeout=MCP_SSE_TIMEOUT
        )
    )

def create_system_operations_toolset():
    """Create system operations MCP toolset"""
    return MCPToolset(
        connection_params=SseServerParams(
            url=SYSTEM_OPERATIONS_MCP_URL,
            sse_read_timeout=MCP_SSE_TIMEOUT
        )
    )






BASIC_TOOLS = [
    exit_loop,
    create_workspace,
    list_workspace,
    read_file,
    write_file,
    delete_file,
    activate_venv,
    execute_python_code,
    run_system_command,
    interactive_system_command,
    run_interactive_shell,
    # interactive_python_code,
]


ALL_TOOLS = BASIC_TOOLS 

