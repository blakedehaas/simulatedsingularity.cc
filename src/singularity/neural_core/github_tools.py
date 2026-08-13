"""Tools for the GitHub Swarm agents."""

import os
import subprocess
import logging
from typing import Any

logger = logging.getLogger(__name__)

WORKSPACE_DIR = "/tmp/swarm_workspace"

def ensure_workspace() -> None:
    """Ensure the workspace exists and is a git repository."""
    if not os.path.exists(WORKSPACE_DIR):
        os.makedirs(WORKSPACE_DIR)
        
    if not os.path.exists(os.path.join(WORKSPACE_DIR, ".git")):
        # Clone if token is available, else init dummy
        token = os.environ.get("GITHUB_TOKEN", "")
        repo_url = f"https://oauth2:{token}@github.com/blakedehaas/simulatedsingularity.cc.git" if token else "https://github.com/blakedehaas/simulatedsingularity.cc.git"
        
        try:
            subprocess.run(["git", "clone", repo_url, "."], cwd=WORKSPACE_DIR, check=True, capture_output=True)
            logger.info("Cloned repository into swarm workspace.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Clone failed: {e.stderr.decode('utf-8')}")
            # Init empty for local testing fallback
            subprocess.run(["git", "init"], cwd=WORKSPACE_DIR, check=True)

def execute_git_command(command: str) -> str:
    """Execute a git command in the swarm workspace."""
    ensure_workspace()
    
    # Simple sanity check
    if not command.startswith("git "):
        command = f"git {command}"
        
    try:
        result = subprocess.run(command.split(), cwd=WORKSPACE_DIR, check=True, capture_output=True, text=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}"

def read_file(filepath: str) -> str:
    """Read a file from the swarm workspace."""
    ensure_workspace()
    full_path = os.path.join(WORKSPACE_DIR, filepath)
    
    # Security: prevent directory traversal
    if not os.path.abspath(full_path).startswith(os.path.abspath(WORKSPACE_DIR)):
        return "Error: Access denied to path outside workspace."
        
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error: {str(e)}"

def write_file(filepath: str, content: str) -> str:
    """Write content to a file in the swarm workspace."""
    ensure_workspace()
    full_path = os.path.join(WORKSPACE_DIR, filepath)
    
    if not os.path.abspath(full_path).startswith(os.path.abspath(WORKSPACE_DIR)):
        return "Error: Access denied to path outside workspace."
        
    try:
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote to {filepath}"
    except Exception as e:
        return f"Error: {str(e)}"

def create_github_issue(title: str, body: str) -> str:
    """Create a new issue on GitHub using the gh CLI."""
    ensure_workspace()
    try:
        result = subprocess.run(
            ["gh", "issue", "create", "--title", title, "--body", body],
            cwd=WORKSPACE_DIR, check=True, capture_output=True, text=True
        )
        return f"Issue created successfully: {result.stdout.strip()}"
    except subprocess.CalledProcessError as e:
        return f"Error creating issue: {e.stderr}"
    except FileNotFoundError:
        return "Error: GitHub CLI (gh) is not installed on this system."

def create_pull_request(head_branch: str, base_branch: str, title: str, body: str) -> str:
    """Create a pull request on GitHub using the gh CLI."""
    ensure_workspace()
    
    # Run static analysis check first (compile all python files)
    try:
        import compileall
        compile_result = compileall.compile_dir(WORKSPACE_DIR, force=True, quiet=1)
        if not compile_result:
            return "Error: Static analysis failed. There are syntax errors in your Python code. Please fix them before creating a PR."
    except Exception as e:
        pass
        
    try:
        result = subprocess.run(
            ["gh", "pr", "create", "--head", head_branch, "--base", base_branch, "--title", title, "--body", body],
            cwd=WORKSPACE_DIR, check=True, capture_output=True, text=True
        )
        return f"Pull request created successfully: {result.stdout.strip()}"
    except subprocess.CalledProcessError as e:
        return f"Error creating pull request: {e.stderr}"
    except FileNotFoundError:
        return "Error: GitHub CLI (gh) is not installed on this system."

def update_agent_system_prompt(node_name: str, new_prompt: str) -> str:
    """Update the underlying system prompt instructions for any agent in the simulation matrix. This allows agents to rewrite their own logic."""
    pass

SWARM_TOOLS = [
    execute_git_command,
    read_file,
    write_file,
    create_github_issue,
    create_pull_request,
    update_agent_system_prompt
]
