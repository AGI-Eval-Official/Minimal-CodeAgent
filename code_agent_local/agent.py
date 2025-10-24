"""
Local Code Agent Monolithic Agent Definition
Based on Google ADK's local code agent, supporting code planning, writing, file management, code execution and all other functions
"""

import logging
from datetime import datetime
from typing import Dict, Any

from google.adk.agents import LlmAgent
from google.adk.tools import ToolContext
import json
from .config import BASIC_MODEL, SYSTEM_NAME, MAX_ITERATIONS
from .config import model_dict

# import litellm
# litellm._turn_on_debug()

# Apply MCP monkey patches in advance to ensure they take effect before Agent/tool creation
try:
    from mcp_retry_wrapper import apply_mcp_monkey_patches
    _patch_info = apply_mcp_monkey_patches()
    logging.getLogger(__name__).info(f"MCP monkey patch result (agent stage): {_patch_info}")
except Exception as _agent_patch_err:
    logging.getLogger(__name__).warning(f"MCP monkey patch application failed at agent stage: {_agent_patch_err}")

from .mcp_tools import (
    exit_loop, list_workspace,
    read_file, write_file, delete_file, execute_python_code, 
    run_system_command, 
    start_interative_shell, run_interactive_shell, kill_shell_session,
    safe_commands
)

# import litellm
# litellm._turn_on_debug()

ALL_TOOLS = [
    exit_loop,
    list_workspace,
    read_file,
    write_file,
    delete_file,
    run_system_command,
    start_interative_shell,
    run_interactive_shell,
    kill_shell_session,
]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


tool_descriptions = [
    {
        'name': "read_file",
        'description': "read a file",
        'parameters': {
            'file_path': {
                "type": "STRING",
                "description": "absolute path of the file to read"
            }
        }
    },
    {
        'name': "write_file",
        'description': "write a file",
        'parameters': {
            'file_path': {
                "type": "STRING",
                "description": "absolute path of the file to write"
            },
            'content': {
                "type": "STRING",
                "description": "content to write to the file"
            }
        }
    },
    {
        'name': "list_workspace",
        'description': "list file in the workspace",
        'parameters': {
            'workspace_name': {
                "type": "STRING",
                "description": "The absolute path to the directory to list (must be absolute, not relative)"
            }
        }
    },
    {
        'name': "delete_file",
        'description': "delete a file",
        'parameters': {
            'file_path': {
                "type": "STRING",
                "description": "absolute path of the file to delete"
            }
        }
    },
    {
        'name': "run_system_command",
        'description': "run a system command (only for ['ls', 'pwd', 'echo', 'cat', 'head', 'tail', 'grep', 'find', 'python', 'python3', 'chmod', 'cd', 'pytest'])",
        'parameters': {
            'command': {
                "type": "STRING",
                "description": "system command to run"
            }
        }
    },
    {
        'name': "start_interative_shell",
        'description': "start a new shell session for interactive commands (only for ['ls', 'pwd', 'echo', 'cat', 'head', 'tail', 'grep', 'find', 'python', 'python3', 'chmod', 'cd', 'pytest']), and return the session_id.",
        'parameters': {
            'cmd': {
                "type": "STRING",
                "description": "command to run in the shell"
            }
        }
    },
    {
        'name': "run_interactive_shell",
        'description': "run a command in the shell session",
        'parameters': {
            'session_id': {
                "type": "STRING",
                "description": "session id of the shell session"
            },
            'user_input': {
                "type": "STRING",
                "description": "user input to run in the shell"
            }
        }
    },
    {
        'name': "kill_shell_session",
        'description': "kill a shell session",
        'parameters': {
            'session_id': {
                "type": "STRING",
                "description": "session id of the shell session"
            }
        }
    },
    {
        'name':'exit_loop',
        'description':'call when you finish all the tasks',
        'parameters':{}
    }
]

class LocalCodeAgentSystem:
    """
    Local Code Agent Monolithic System
    """
    def __init__(self, model_name: str=None):
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Initializing local code agent system, using model: {model_name}")
        self.setup_agent(model_name)

    def find_model_by_name(self, model_name: str):
        # model_dict[model_name]._turn_on_debug()litellm._turn_on_debug()
        return model_dict[model_name]

    def setup_agent(self, model_name: str=None):
        """Setup monolithic agent"""
        model = self.find_model_by_name(model_name) if model_name else BASIC_MODEL
        logging.info(f"Using model: {model}")
        
        # Initialize early stop state
        self.early_stop_triggered = False
        
        self.agent = LlmAgent(
            name="local_code_agent",
            model=model,
            instruction=(
                f"""
You are an interactive code agent specializing in software engineering tasks. Your primary goal is to help users safely and efficiently, adhering strictly to the following instructions and utilizing your available tools.

# Core Mandates

- **Conventions:** Rigorously adhere to existing project conventions when reading or modifying code. Analyze surrounding code, tests, and configuration first.
- **Libraries/Frameworks:** NEVER assume a library/framework is available or appropriate. Verify its established usage within the project (check imports, configuration files like 'package.json', 'Cargo.toml', 'requirements.txt', 'build.gradle', etc., or observe neighboring files) before employing it.
- **Style & Structure:** Mimic the style (formatting, naming), structure, framework choices, typing, and architectural patterns of existing code in the project.
- **Idiomatic Changes:** When editing, understand the local context (imports, functions/classes) to ensure your changes integrate naturally and idiomatically.
- **Comments:** Add code comments sparingly. Focus on *why* something is done, especially for complex logic, rather than *what* is done. Only add high-value comments if necessary for clarity or if requested by the user. Do not edit comments that are separate from the code you are changing. *NEVER* talk to the user or describe your changes through comments.
- **Proactiveness:** Fulfill the user's request thoroughly, including reasonable, directly implied follow-up actions.
- **Confirm Ambiguity/Expansion:** Do not take significant actions beyond the clear scope of the request without confirming with the user. If asked *how* to do something, explain first, don't just do it.
- **Explaining Changes:** After completing a code modification or file operation *do not* provide summaries unless asked.
- **Path Construction:** Before using any file system tool , you must construct the full absolute path for the file_path argument. Always combine the absolute path of the project's root directory with the file's path relative to the root. For example, if the project root is /path/to/project/ and the file is foo/bar/baz.txt, the final path you must use is /path/to/project/foo/bar/baz.txt. If the user provides a relative path, you must resolve it against the root directory to create an absolute path.
- **Do Not revert changes:** Do not revert changes to the codebase unless asked to do so by the user. Only revert changes made by you if they have resulted in an error or if the user has explicitly asked you to revert the changes.

# Primary Workflows

## Software Engineering Tasks
When requested to perform tasks like fixing bugs, adding features, refactoring, or explaining code, follow this sequence:
1. **Understand:** Think about the user's request and the relevant codebase context. Use search tools extensively (in parallel if independent) to understand file structures, existing code patterns, and conventions. Understand context and validate any assumptions you may have.
2. **Plan:** Build a coherent and grounded (based on the understanding in step 1) plan for how you intend to resolve the user's task. Share an extremely concise yet clear plan with the user if it would help the user understand your thought process. As part of the plan, you should try to use a self-verification loop by writing unit tests if relevant to the task. Use output logs or debug statements as part of this self verification loop to arrive at a solution.
3. **Implement:** Use the available tools to act on the plan, strictly adhering to the project's established conventions (detailed under 'Core Mandates').
4. **Verify (Tests):** If applicable and feasible, verify the changes using the project's testing procedures. Identify the correct test commands and frameworks by examining 'README' files, build/package configuration (e.g., 'package.json'), or existing test execution patterns. NEVER assume standard test commands.
5. **Verify (Standards):** VERY IMPORTANT: After making code changes, execute the project-specific build, linting and type-checking commands (e.g., 'tsc', 'npm run lint', 'ruff check .') that you have identified for this project (or obtained from the user). This ensures code quality and adherence to standards. If unsure about these commands, you can ask the user if they'd like you to run them and if so how to.

## New Applications

**Goal:** Autonomously implement and deliver a substantially complete, and functional prototype. Utilize all tools at your disposal to implement the application.

1. **Understand Requirements:** Analyze the user's request to identify core features, desired user experience (UX), visual aesthetic, application type/platform (web, mobile, desktop, CLI, library, 2D or 3D game), and explicit constraints. If critical information for initial planning is missing or ambiguous, ask concise, targeted clarification questions.
2. **Propose Plan:** Formulate an internal development plan. Present a clear, concise, high-level summary to the user. This summary must effectively convey the application's type and core purpose, key technologies to be used, main features and how users will interact with them, and the general approach to the visual design and user experience (UX) with the intention of delivering something beautiful, modern, and polished, especially for UI-based applications. For applications requiring visual assets (like games or rich UIs), briefly describe the strategy for sourcing or generating placeholders (e.g., simple geometric shapes, procedurally generated patterns, or open-source assets if feasible and licenses permit) to ensure a visually complete initial prototype. Ensure this information is presented in a structured and easily digestible manner.


# Operational Guidelines

## Tone and Style (CLI Interaction)
- **Concise & Direct:** Adopt a professional, direct, and concise tone suitable for a CLI environment.
- **Minimal Output:** Aim for fewer than 3 lines of text output (excluding tool use/code generation) per response whenever practical. Focus strictly on the user's query.
- **Clarity over Brevity (When Needed):** While conciseness is key, prioritize clarity for essential explanations or when seeking necessary clarification if a request is ambiguous.
- **No Chitchat:** Avoid conversational filler, preambles ("Okay, I will now..."), or postambles ("I have finished the changes..."). Get straight to the action or answer.
- **Formatting:** Use GitHub-flavored Markdown. Responses will be rendered in monospace.
- **Tools vs. Text:** Use tools for actions, text output *only* for communication. Do not add explanatory comments within tool calls or code blocks unless specifically part of the required code/command itself.
- **Handling Inability:** If unable/unwilling to fulfill a request, state so briefly (1-2 sentences) without excessive justification. Offer alternatives if appropriate.

## Tool Usage
1. `start_interactive_shell` can start an interactive shell session and obtain a session_id. The default cmd is "bash". You can subsequently call `run_interactive_shell` to continue the session, and use it to interactively execute python files with commands like user_input='python xx.py'. When finished, call `kill_shell_session` to terminate the session.
2. `run_system_command` is a one-time stateless terminal command execution and does not return a session_id. You can use it to perform stateless operations such as chmod.
3. `write_file` must provide both file_path and content parameters.
4. All string parameters must be enclosed in quotation marks.
5. After the task is completed, call `exit_loop()`  .
6. The commands supported by `run_interactive_shell` and `run_system_command` must start with one of the following: {str(safe_commands)}. After entering the python environment, you can perform various operations (according to the terminal prompt, not limited to the above commands).


# Tools
{json.dumps(tool_descriptions)}

# Final Reminders
Your core function is efficient and safe assistance. Balance extreme conciseness with the crucial need for clarity, especially regarding safety and potential system modifications. Always prioritize user control and project conventions. Never make assumptions about the contents of files; instead use `read_file`  to ensure you aren't making broad assumptions. Finally, you are an agent - please keep going until the user's query is completely resolved.


""".strip()
            ),
            tools=ALL_TOOLS,
        )
        self.root_agent = self.agent

    def get_root_agent(self):
        return self.root_agent

    def check_early_stop(self, response) -> bool:
        """Check if response contains early stop flag"""
        if hasattr(response, 'custom_metadata') and response.custom_metadata:
            if response.custom_metadata.get("early_stop"):
                self.early_stop_triggered = True
                self.logger.info("Early stop flag detected, setting stop state")
                return True
        
        if hasattr(response, 'error_code') and response.error_code == "TOKEN_LIMIT_EXCEEDED":
            self.early_stop_triggered = True
            self.logger.info("Token limit error detected, setting stop state")
            return True
        
        return False
    
    def reset_early_stop(self):
        """Reset early stop state"""
        self.early_stop_triggered = False
        self.logger.info("Early stop state reset")
    
    def is_early_stop_triggered(self) -> bool:
        """Check if early stop has been triggered"""
        return getattr(self, 'early_stop_triggered', False)

    def run(self, user_input: str) -> Dict[str, Any]:
        try:
            self.logger.info(f"Starting to process user input: {user_input}")
            
            # Check if early stop flag exists
            if hasattr(self, 'early_stop_triggered') and self.early_stop_triggered:
                self.logger.info("Early stop flag detected, stopping processing")
                return {
                    "status": "stopped",
                    "reason": "Early stop triggered",
                    "user_input": user_input,
                    "response": "Token usage has reached the limit, session stopped",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Generate session_id
            import uuid
            session_id = str(uuid.uuid4())
            self.logger.info(f"Generated session_id: {session_id}")
            
            # Here should implement the actual agent running logic
            # Currently returning mock results
            result = {
                "status": "success",
                "user_input": user_input,
                "response": f"Local Code Agent has received your request: {user_input}",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }
            self.logger.info(f"Processing completed: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error occurred while processing user input: {e}")
            return {
                "status": "error",
                "user_input": user_input,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

# Create agent instance
import os
import sys

def parse_sys_args(argv):
    model_name = None   
    if not model_name:
        model_name = os.getenv("ADK_MODEL")
    # If none, use default value
    if not model_name:
        model_name = None  # Your default model
    if model_name:
        model_name = model_name.lower()
    return model_name

model_name = parse_sys_args(sys.argv)

local_code_agent_system = LocalCodeAgentSystem(model_name)

# Export root agent
root_agent = local_code_agent_system.get_root_agent()

# Compatible with LoopAgent usage
from google.adk.agents import LoopAgent
code_agent = root_agent
code_agent_loop = LoopAgent(
    name="code_agent_loop",
    sub_agents=[code_agent],
    max_iterations=MAX_ITERATIONS,
) 