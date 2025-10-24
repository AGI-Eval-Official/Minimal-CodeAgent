#!/usr/bin/env python3
"""
MinimalCodeAgent Client Script
A simple script to send prompts to the MinimalCodeAgent and receive responses.
"""

import requests
import json
import os
import argparse
import time
from datetime import datetime

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="MinimalCodeAgent Client Script")
    parser.add_argument("--prompt", "-p", type=str, required=True, 
                       help="The prompt to send to the code agent")
    parser.add_argument("--workdir", "-w", type=str, default=None,
                       help="Working directory for the code agent (optional)")
    parser.add_argument("--port", type=int, default=8080,
                       help="Port of the ADK API server (default: 8080)")
    parser.add_argument("--agent", "-m", type=str, default='code_agent_local',
                       help="Agent name to use (default: code_agent_local)")
    parser.add_argument("--session-id", "-s", type=str, default=None,
                       help="Session ID (if not provided, generates one)")
    parser.add_argument("--output", "-o", type=str, default=None,
                       help="Output file to save the response (optional)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose output")
    
    return parser.parse_args()

def generate_session_id():
    """Generate a unique session ID"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"session_{timestamp}"

def create_session(port, model_name, session_id, verbose=False):
    """Create a new session with the ADK API server"""
    session_url = f"http://localhost:{port}/apps/code_agent_local/users/{model_name}/sessions/{session_id}"
    
    if verbose:
        print(f"Creating session: {session_url}")
    
    try:
        # Delete existing session if it exists
        delete_response = requests.delete(session_url, timeout=10)
        if verbose and delete_response.status_code == 200:
            print(f"Deleted existing session: {delete_response.status_code}")
        
        # Create new session
        response = requests.post(session_url, timeout=10)
        
        if verbose:
            print(f"Session creation response: {response.status_code}")
            print(f"Session creation content: {response.text}")
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to create session, status code: {response.status_code}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Network error during session creation: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"JSON decode error during session creation: {e}")
        return None

def send_query(port, model_name, session_id, prompt, verbose=False):
    """Send a query to the ADK API server"""
    query_url = f"http://localhost:{port}/run"
    
    query_data = {
        "appName": "code_agent_local",
        "userId": model_name,
        "sessionId": session_id,
        "newMessage": {
            "role": "user",
            "parts": [{
                "text": prompt
            }]
        }
    }
    
    if verbose:
        print(f"Sending query to: {query_url}")
        print(f"Query data: {json.dumps(query_data, indent=2)}")
    
    try:
        response = requests.post(
            query_url, 
            json=query_data,
            timeout=3600  # 1 hour timeout for long-running tasks (matches MAX_SESSION_TIME)
        )
        
        if verbose:
            print(f"Query response status: {response.status_code}")
            print(f"Query response content: {response.text}")
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Query failed, status code: {response.status_code}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Network error during query: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"JSON decode error during query: {e}")
        return None

def save_response(response_data, output_file, verbose=False):
    """Save response to file"""
    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(response_data, f, indent=2, ensure_ascii=False)
            if verbose:
                print(f"Response saved to: {output_file}")
        except Exception as e:
            print(f"Error saving response to file: {e}")

def main():
    """Main function"""
    args = parse_arguments()
    
    
    agent_name = args.agent
    if not agent_name:
        print("Error: Agent name not provided. Use --agent argument.")
        return 1
    
    # Generate session ID if not provided
    session_id = args.session_id or generate_session_id()
    
    # Set working directory if provided
    if args.workdir:
        os.environ['CODE_AGENT_WORKSPACE_DIR'] = os.path.abspath(args.workdir)
        if args.verbose:
            print(f"Working directory set to: {os.environ['CODE_AGENT_WORKSPACE_DIR']}")
    
    print(f"🚀 Starting MinimalCodeAgent interaction")
    print(f"📝 Prompt: {args.prompt[:100]}{'...' if len(args.prompt) > 100 else ''}")
    print(f"🤖 Agent Name: {agent_name}")
    print(f"📁 Working directory: {os.environ.get('CODE_AGENT_WORKSPACE_DIR', 'default')}")
    print(f"🔗 Session ID: {session_id}")
    print(f"🌐 API Server: http://localhost:{args.port}")
    print("-" * 50)
    
    # Create session
    print("Creating session...")
    session_response = create_session(args.port, agent_name, session_id, args.verbose)
    if not session_response:
        print("❌ Failed to create session")
        return 1
    
    print("✅ Session created successfully")
    
    # Send query
    print("Sending query to agent...")
    start_time = time.time()
    query_response = send_query(args.port, agent_name, session_id, args.prompt, args.verbose)
    end_time = time.time()
    
    if not query_response:
        print("❌ Failed to send query")
        return 1
    
    print(f"✅ Query completed in {end_time - start_time:.2f} seconds")
    
    # Display response
    print("\n" + "="*50)
    print("🤖 AGENT RESPONSE:")
    print("="*50)
    
    # Extract and display the response text
    if 'response' in query_response:
        response_text = query_response['response']
        if isinstance(response_text, dict) and 'parts' in response_text:
            for part in response_text['parts']:
                if 'text' in part:
                    print(part['text'])
        elif isinstance(response_text, str):
            print(response_text)
        else:
            print(json.dumps(response_text, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(query_response, indent=2, ensure_ascii=False))
    
    # Save response if requested
    if args.output:
        save_response(query_response, args.output, args.verbose)
    
    print("\n✅ Interaction completed successfully!")
    return 0

if __name__ == "__main__":
    exit(main())
