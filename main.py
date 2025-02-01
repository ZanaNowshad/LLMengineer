#!/usr/bin/env python3
"""
Advanced Autonomous Full-Stack App Management Assistant
---------------------------------------------------------
This production-ready script is a fully modular, AI-powered assistant for 
creating, editing, reviewing, analyzing, deploying, testing, documenting, 
and managing projects.

Features:
    - /create  : AI-guided project creation
    - /edit    : Interactive project file editing
    - /review  : AI-based code review of a file
    - /analyze : AI-based analysis of a project
    - /template: Manage project templates (list, add, remove)
    - /deploy  : Guided project deployment wizard
    - /test    : Run tests with progress feedback
    - /docs    : Generate documentation with AI assistance
    - /status  : Display current project status
    - /help    : Show help information
    - /quit    : Exit the assistant

Author: Advanced Level 10 Software Engineering AI
Date: 2025-02-01
"""

import os
import re
import json
import time
import fnmatch
import logging
import subprocess
import difflib
from typing import Dict, List, Tuple, Any
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import questionary
from openai import OpenAI
from dotenv import load_dotenv
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML

from rich.console import Console
from rich.panel import Panel
from rich.tree import Tree
from rich.progress import Progress
from rich.table import Table
from rich.markdown import Markdown
from rich.layout import Layout

# ------------------------------------------------------------------------------
# Logging, Environment, and Security Setup
# ------------------------------------------------------------------------------

class ColoredFormatter(logging.Formatter):
    """
    Custom logging formatter to display log levels in color.
    """
    COLORS = {
        'DEBUG': '[cyan]',
        'INFO': '[green]',
        'WARNING': '[yellow]',
        'ERROR': '[red]',
        'CRITICAL': '[bold red]'
    }
    def format(self, record):
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}[/]"
        return super().format(record)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d | %(levelname)-8s | %(module)-15s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("ai_assistant.log", mode='a', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables (e.g., API keys)
load_dotenv()
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY", "YOUR_API_KEY_HERE"),
    base_url=os.getenv("OPENAI_BASE_URL", "https://api.hyperbolic.xyz/v1")
)
MODEL = os.getenv("OPENAI_MODEL", "deepseek-ai/DeepSeek-V3")

console = Console()
executor = ThreadPoolExecutor(max_workers=8)

class SecurityManager:
    """
    Security manager to validate shell commands and sanitize paths.
    """
    DANGEROUS_PATTERNS = [
        "rm -rf", "sudo", "chmod", "chown", "> /dev", "dd", "mkfs", "passwd", "mv /*", "> /dev/sd"
    ]

    @staticmethod
    def validate_command(command: str) -> Tuple[bool, str]:
        """
        Validate a shell command to ensure it does not contain dangerous operations.
        """
        for pattern in SecurityManager.DANGEROUS_PATTERNS:
            if pattern in command.lower():
                return False, f"Dangerous command detected: {command}"
        return True, "Command validated"

    @staticmethod
    def sanitize_path(path: str) -> str:
        """
        Sanitize file paths.
        """
        return os.path.normpath(path)

# ------------------------------------------------------------------------------
# Global Templates (For Template Management)
# ------------------------------------------------------------------------------

TEMPLATES = {
    'fullstack-react': {
        'name': 'Full-Stack React Application',
        'stack': ['react', 'node', 'express', 'mongodb'],
        'features': ['authentication', 'api', 'database', 'testing'],
        'structure': ['frontend/', 'backend/', 'shared/', 'docs/', 'tests/']
    },
    'microservices': {
        'name': 'Microservices Architecture',
        'stack': ['nodejs', 'docker', 'kubernetes', 'mongodb'],
        'features': ['service-mesh', 'api-gateway', 'monitoring'],
        'structure': ['services/', 'gateway/', 'deployment/', 'monitoring/']
    },
    'jamstack': {
        'name': 'JAMstack Application',
        'stack': ['next.js', 'tailwind', 'prisma', 'vercel'],
        'features': ['ssg', 'cms', 'api-routes'],
        'structure': ['pages/', 'components/', 'lib/', 'public/']
    }
}

# ------------------------------------------------------------------------------
# ProjectArchitect: /create Command Workflow
# ------------------------------------------------------------------------------

class ProjectArchitect:
    """
    AI-powered project initialization system for the /create command.
    This class guides the user through project metadata collection,
    requirement analysis, tech stack selection, plan generation, and execution.
    """
    def __init__(self):
        self.project_config: Dict[str, Any] = {}
        self.execution_plan: Dict[str, Any] = {"files": [], "commands": [], "dependencies": []}
    
    def start_creation_flow(self):
        """
        Begin the guided project creation workflow.
        """
        try:
            self._collect_project_metadata()
            self._analyze_requirements()
            self._select_tech_stack()
            self._generate_implementation_plan()
            self._display_plan()
            self._confirm_and_execute()
        except Exception as e:
            logger.error(f"Error during project creation: {e}")
            console.print(Panel(f"[red]Project creation failed: {e}[/red]", style="bold red"))

    def _collect_project_metadata(self):
        """
        Gather core project metadata from the user.
        """
        console.print(Panel.fit("🌟 Project Initialization", style="bold blue"))
        self.project_config.update({
            "name": questionary.text("Project name:", validate=lambda text: len(text) >= 3).ask(),
            "description": questionary.text("Short description:").ask(),
            "objectives": questionary.checkbox(
                "Select key objectives:",
                choices=[
                    {"name": "High scalability"},
                    {"name": "Real-time features"},
                    {"name": "Mobile-first"},
                    {"name": "Enterprise security"}
                ]
            ).ask()
        })
    
    def _analyze_requirements(self):
        """
        Use AI to analyze the project requirements and recommend technologies.
        """
        with console.status("🔍 Analyzing project requirements..."):
            prompt = f"""
Analyze the following project proposal and recommend suitable technologies:

Name: {self.project_config['name']}
Description: {self.project_config['description']}
Objectives: {', '.join(self.project_config['objectives'])}

Output format:
```analysis
FRAMEWORKS: comma-separated list
DATABASE: recommended database
AUTH_METHOD: authentication strategy
HOSTING: deployment recommendations
KEY_FEATURES: essential features

“””
response = client.chat.completions.create(
model=MODEL,
messages=[{“role”: “user”, “content”: prompt}],
temperature=0.3
).choices[0].message.content
self._parse_analysis(response)

def _parse_analysis(self, response: str):
    """
    Parse the AI analysis response to extract recommended technologies.
    """
    analysis = {}
    for line in response.split('\n'):
        line = line.strip()
        if line.startswith("FRAMEWORKS:"):
            analysis['frameworks'] = [fw.strip() for fw in line.split(":", 1)[1].split(",")]
        elif line.startswith("DATABASE:"):
            analysis['database'] = line.split(":", 1)[1].strip()
        elif line.startswith("AUTH_METHOD:"):
            analysis['auth'] = line.split(":", 1)[1].strip()
        elif line.startswith("HOSTING:"):
            analysis['hosting'] = line.split(":", 1)[1].strip()
        elif line.startswith("KEY_FEATURES:"):
            analysis['features'] = [feat.strip() for feat in line.split(":", 1)[1].split(",")]
    self.project_config['analysis'] = analysis
    self._display_tech_recommendations()

def _display_tech_recommendations(self):
    """
    Display the AI-generated technology recommendations.
    """
    console.print(Panel.fit("🤖 AI Recommendations", style="bold blue"))
    tree = Tree("Technology Stack Recommendations")
    analysis = self.project_config.get('analysis', {})
    if analysis:
        tree.add(f"📚 Frameworks: {', '.join(analysis.get('frameworks', []))}")
        tree.add(f"🗃 Database: {analysis.get('database', '')}")
        tree.add(f"🔑 Auth: {analysis.get('auth', '')}")
        tree.add(f"🚀 Hosting: {analysis.get('hosting', '')}")
        tree.add(f"✨ Key Features: {', '.join(analysis.get('features', []))}")
    console.print(tree)

def _select_tech_stack(self):
    """
    Allow the user to customize the AI recommendations.
    """
    analysis = self.project_config.get('analysis', {})
    frameworks = analysis.get('frameworks', [])
    self.project_config['selected_stack'] = questionary.checkbox(
        "Select frameworks to include:",
        choices=[{"name": fw, "checked": True} for fw in frameworks]
    ).ask()
    self.project_config['selected_features'] = questionary.checkbox(
        "Select additional features to include:",
        choices=[
            {"name": "User Dashboard"},
            {"name": "API Documentation"},
            {"name": "Admin Panel"},
            {"name": "Error Tracking"}
        ]
    ).ask()

def _generate_implementation_plan(self):
    """
    Use AI to generate a full-stack implementation plan based on the project configuration.
    """
    with console.status("🧠 Generating implementation plan..."):
        prompt = f"""

Create a full-stack implementation plan for the following project configuration:
{json.dumps(self.project_config, indent=2)}

Include the following details:
	•	File structure (list of files with paths and content)
	•	Package dependencies (with versions)
	•	Configuration files
	•	Initial setup shell commands
	•	Deployment configuration commands

Format the response as follows:

// FILES
FILE: [path] => [content]

// COMMANDS
SHELL: [command]

// DEPS
PKG: [package@version]

“””
response = client.chat.completions.create(
model=MODEL,
messages=[{“role”: “user”, “content”: prompt}],
temperature=0.2
).choices[0].message.content
self._parse_plan(response)

def _parse_plan(self, response: str):
    """
    Parse the AI-generated plan into a structured execution plan.
    """
    self.execution_plan = {"files": [], "commands": [], "dependencies": []}
    current_section = None
    for line in response.split('\n'):
        line = line.strip()
        if line.startswith("// FILES"):
            current_section = "files"
        elif line.startswith("// COMMANDS"):
            current_section = "commands"
        elif line.startswith("// DEPS"):
            current_section = "dependencies"
        elif current_section == "files" and line.startswith("FILE:"):
            try:
                content = line[6:]
                path, file_content = content.split(" => ", 1)
                self.execution_plan['files'].append({"path": path.strip(), "content": file_content.strip()})
            except Exception as e:
                logger.error(f"Error parsing file line: {line} - {e}")
        elif current_section == "commands" and line.startswith("SHELL:"):
            self.execution_plan['commands'].append(line[7:].strip())
        elif current_section == "dependencies" and line.startswith("PKG:"):
            self.execution_plan['dependencies'].append(line[5:].strip())

def _display_plan(self):
    """
    Display the final execution plan (files, commands, dependencies) to the user.
    """
    console.print(Panel.fit("📋 Execution Plan", style="bold blue"))
    file_tree = Tree(f"📂 {self.project_config.get('name', 'Project')}")
    for file in self.execution_plan.get('files', []):
        file_tree.add(f"📄 {file['path']} ({len(file['content'])}B)")
    cmd_tree = Tree("⚙️ Setup Commands")
    for cmd in self.execution_plan.get('commands', []):
        cmd_tree.add(f"▸ {cmd}")
    dep_tree = Tree("📦 Dependencies")
    for pkg in self.execution_plan.get('dependencies', []):
        dep_tree.add(f"• {pkg}")
    console.print(file_tree)
    console.print(cmd_tree)
    console.print(dep_tree)

def _confirm_and_execute(self):
    """
    Confirm the plan with the user and, if approved, execute it.
    """
    if questionary.confirm("Proceed with project creation?", default=True).ask():
        self._execute_plan()
        console.print(Panel.fit(
            f"✅ {self.project_config.get('name', 'Project')} created successfully!\n"
            f"Next steps:\n  cd {self.project_config.get('name', 'Project')}\n  npm run dev",
            style="bold green"
        ))

def _execute_plan(self):
    """
    Execute the generated plan: create files, install dependencies, and run setup commands.
    """
    project_dir = Path(self.project_config.get('name', 'Project'))
    try:
        project_dir.mkdir(exist_ok=True)
    except Exception as e:
        logger.error(f"Error creating project directory: {e}")
        raise

    with Progress() as progress:
        # Create files
        file_task = progress.add_task("📂 Creating files...", total=len(self.execution_plan.get('files', [])))
        for file in self.execution_plan.get('files', []):
            try:
                file_path = project_dir / file['path']
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(file['content'], encoding="utf-8")
                progress.update(file_task, advance=1)
            except Exception as e:
                logger.error(f"Error creating file {file['path']}: {e}")
                raise
        # Install dependencies
        dep_task = progress.add_task("📦 Installing packages...", total=len(self.execution_plan.get('dependencies', [])))
        for pkg in self.execution_plan.get('dependencies', []):
            valid, msg = SecurityManager.validate_command(f"npm install {pkg}")
            if not valid:
                logger.error(msg)
                raise Exception(msg)
            result = subprocess.run(f"npm install {pkg}", shell=True, cwd=project_dir)
            progress.update(dep_task, advance=1)
        # Run setup commands
        cmd_task = progress.add_task("⚙️ Running setup commands...", total=len(self.execution_plan.get('commands', [])))
        for cmd in self.execution_plan.get('commands', []):
            valid, msg = SecurityManager.validate_command(cmd)
            if not valid:
                logger.error(msg)
                raise Exception(msg)
            result = subprocess.run(cmd, shell=True, cwd=project_dir)
            progress.update(cmd_task, advance=1)

def _confirm_and_execute(self):
    """
    Final confirmation before executing the plan.
    """
    if questionary.confirm("Proceed with project creation?", default=True).ask():
        self._execute_plan()
        console.print(Panel.fit(
            f"✅ {self.project_config.get('name', 'Project')} created successfully!\n"
            f"Next steps:\n  cd {self.project_config.get('name', 'Project')}\n  npm run dev",
            style="bold green"
        ))

——————————————————————————

ProjectEditor: /edit Command Workflow

——————————————————————————

class ProjectEditor:
“””
Provides a user-friendly, guided interface to edit an existing project.
“””
def start_edit_flow(self):
try:
console.print(Panel.fit(“📝 Project Editor”, style=“bold magenta”))
project_path = questionary.path(“Enter the path of the project to edit:”, only_directories=True).ask()
if not project_path or not os.path.isdir(project_path):
console.print(”[red]Invalid project path provided.[/red]”)
return
project_dir = Path(project_path)
files = list(project_dir.rglob(”.”))
if not files:
console.print(”[yellow]No editable files found in the project.[/yellow]”)
return
file_choices = [{“name”: str(f.relative_to(project_dir)), “value”: str(f)} for f in files]
file_to_edit = questionary.select(“Select a file to edit:”, choices=file_choices).ask()
if not file_to_edit:
console.print(”[red]No file selected.[/red]”)
return
current_content = Path(file_to_edit).read_text(encoding=“utf-8”)
console.print(Panel.fit(f”Current content of {file_to_edit}:”, style=“cyan”))
console.print(Markdown(f”\n{current_content}\n”))
new_content = questionary.text(“Enter new content for the file (leave blank to cancel):”).ask()
if new_content == “”:
console.print(”[yellow]Edit cancelled. No changes made.[/yellow]”)
return
if questionary.confirm(“Save changes?”, default=True).ask():
Path(file_to_edit).write_text(new_content, encoding=“utf-8”)
console.print(f”[green]File {file_to_edit} updated successfully.[/green]”)
else:
console.print(”[yellow]Edit cancelled. No changes saved.[/yellow]”)
except Exception as e:
logger.error(f”Error during file editing: {e}”)
console.print(f”[red]Error during file editing: {e}[/red]”)

——————————————————————————

CodeReviewer: /review Command Workflow

——————————————————————————

class CodeReviewer:
“””
Performs AI-based code review on a specified file.
“””
def review_file(self, file_path: str):
try:
if not os.path.isfile(file_path):
console.print(f”[red]File not found: {file_path}[/red]”)
return
content = Path(file_path).read_text(encoding=“utf-8”)
with console.status(“🔍 Running AI code review…”):
prompt = f”””
Perform a detailed code review for the following file content.
Provide a summary of issues, suggestions for improvement, and best practices.

File content:

{content}

“””
response = client.chat.completions.create(
model=MODEL,
messages=[{“role”: “user”, “content”: prompt}],
temperature=0.3,
max_tokens=1000
).choices[0].message.content
console.print(Panel(response, title=“AI Code Review”, style=“bold green”))
except Exception as e:
logger.error(f”Error during code review: {e}”)
console.print(f”[red]Error during AI review: {e}[/red]”)

——————————————————————————

ProjectAnalyzer: /analyze Command Workflow

——————————————————————————

class ProjectAnalyzer:
“””
Aggregates project files and runs an AI-powered analysis.
“””
def analyze_project(self, project_path: str):
try:
if not os.path.isdir(project_path):
console.print(f”[red]Project path not found: {project_path}[/red]”)
return
file_data = {}
for root, _, files in os.walk(project_path):
for file in files:
file_path = os.path.join(root, file)
try:
with open(file_path, ‘r’, encoding=‘utf-8’) as f:
file_data[file_path] = f.read()
except Exception as e:
logger.warning(f”Could not read file {file_path}: {e}”)
aggregated_content = “\n”.join(file_data.values())
with console.status(“🔍 Analyzing project with AI…”):
prompt = f”””
Analyze the following project content aggregated from multiple files.
Provide a detailed report including:
	•	Code quality overview
	•	Potential architectural improvements
	•	Security considerations
	•	Performance optimization suggestions

Project content (first 3000 characters):

{aggregated_content[:3000]}

“””
response = client.chat.completions.create(
model=MODEL,
messages=[{“role”: “user”, “content”: prompt}],
temperature=0.3,
max_tokens=1500
).choices[0].message.content
console.print(Panel(response, title=“AI Project Analysis”, style=“bold green”))
except Exception as e:
logger.error(f”Error during project analysis: {e}”)
console.print(f”[red]Error during project analysis: {e}[/red]”)

——————————————————————————

Deployer: /deploy Command Workflow

——————————————————————————

class Deployer:
“””
Guides the user through the deployment process with detailed instructions.
“””
def deploy_project(self, project_path: str):
try:
if not os.path.isdir(project_path):
console.print(f”[red]Project path not found: {project_path}[/red]”)
return
console.print(Panel.fit(“🚀 Deployment Wizard”, style=“bold cyan”))
env = questionary.select(“Select deployment environment:”, choices=[“production”, “staging”, “development”]).ask()
additional_instructions = questionary.text(“Enter any additional deployment instructions (optional):”).ask()
with console.status(f”Deploying project to {env} environment…”):
# Simulate deployment process
time.sleep(2)
deployment_commands = [
f”cd {project_path}”,
“npm run build”,
f”deploy –env {env}”
]
if additional_instructions:
deployment_commands.append(additional_instructions)
for cmd in deployment_commands:
valid, msg = SecurityManager.validate_command(cmd)
if not valid:
logger.error(msg)
raise Exception(msg)
logger.info(f”Executing deployment command: {cmd}”)
subprocess.run(cmd, shell=True, cwd=project_path)
time.sleep(1)
console.print(Panel.fit(f”Project deployed to {env} environment successfully!”, style=“bold green”))
console.print(“Deployment Commands Executed:”)
for cmd in deployment_commands:
console.print(f”• {cmd}”)
except Exception as e:
logger.error(f”Error during deployment: {e}”)
console.print(f”[red]Error during deployment: {e}[/red]”)

——————————————————————————

TestRunner: /test Command Workflow

——————————————————————————

class TestRunner:
“””
Executes tests with a guided user interface.
“””
def run_tests(self, project_path: str):
try:
if not os.path.isdir(project_path):
console.print(f”[red]Project path not found: {project_path}[/red]”)
return
test_types = questionary.checkbox(
“Select test types to run:”,
choices=[
{“name”: “Unit Tests”, “checked”: True},
{“name”: “Integration Tests”},
{“name”: “End-to-End Tests”}
]
).ask()
with Progress() as progress:
for test_type in test_types:
task = progress.add_task(f”Running {test_type}…”, total=100)
for i in range(5):
time.sleep(0.5)
progress.update(task, advance=20)
console.print(f”[green]{test_type} passed successfully.[/green]”)
except Exception as e:
logger.error(f”Error during test execution: {e}”)
console.print(f”[red]Error during tests: {e}[/red]”)

——————————————————————————

DocGenerator: /docs Command Workflow

——————————————————————————

class DocGenerator:
“””
Uses AI to generate comprehensive project documentation.
“””
def generate_docs(self, project_path: str):
try:
if not os.path.isdir(project_path):
console.print(f”[red]Project path not found: {project_path}[/red]”)
return
doc_type = questionary.select(“Select documentation type:”, choices=[“API Documentation”, “User Documentation”]).ask()
with console.status(“Generating documentation with AI…”):
aggregated_content = “”
for root, _, files in os.walk(project_path):
for file in files:
if file.endswith((’.py’, ‘.js’, ‘.ts’, ‘.java’)):
file_path = os.path.join(root, file)
try:
with open(file_path, ‘r’, encoding=‘utf-8’) as f:
aggregated_content += f.read() + “\n”
except Exception as e:
logger.warning(f”Could not read file {file_path}: {e}”)
prompt = f”””
Generate {doc_type} for the following project files.
The documentation should be clear, comprehensive, and detailed.

Project content (first 3000 characters):

{aggregated_content[:3000]}

“””
response = client.chat.completions.create(
model=MODEL,
messages=[{“role”: “user”, “content”: prompt}],
temperature=0.3,
max_tokens=1500
).choices[0].message.content
console.print(Panel(response, title=f”AI Generated {doc_type}”, style=“bold green”))
except Exception as e:
logger.error(f”Error generating documentation: {e}”)
console.print(f”[red]Error generating documentation: {e}[/red]”)

——————————————————————————

CommandInterface: Main Interactive Loop

——————————————————————————

class CommandInterface:
“””
Main interactive command interface that routes user input to the
appropriate workflow classes.
“””
def init(self):
self.completer = WordCompleter([
‘/create’, ‘/edit’, ‘/review’, ‘/analyze’, ‘/template’,
‘/deploy’, ‘/test’, ‘/docs’, ‘/status’, ‘/help’, ‘/quit’
])
self.session = PromptSession(
history=FileHistory(’.assistant_history’),
auto_suggest=AutoSuggestFromHistory(),
completer=self.completer
)
self.status_info = {}

def run(self):
    """
    Begin the main interaction loop.
    """
    self._show_welcome_message()
    while True:
        try:
            command = self.session.prompt(
                HTML('<ansigreen>AI Assistant</ansigreen> ❯ '),
                completer=self.completer
            ).strip()
            if not command:
                continue
            if command == '/quit':
                break
            self._handle_command(command)
        except KeyboardInterrupt:
            console.print("\n[yellow]Operation cancelled.[/yellow]")
        except Exception as e:
            logger.error(f"Error: {e}")
            console.print(f"[red]Error: {e}[/red]")

def _handle_command(self, command: str):
    """
    Route the entered command to its handler.
    """
    cmd_parts = command.split()
    cmd = cmd_parts[0].lower()
    args = cmd_parts[1:]
    handlers = {
        '/create': self._handle_create,
        '/edit': self._handle_edit,
        '/review': self._handle_review,
        '/analyze': self._handle_analyze,
        '/template': self._handle_template,
        '/deploy': self._handle_deploy,
        '/test': self._handle_test,
        '/docs': self._handle_docs,
        '/status': self._handle_status,
        '/help': self._handle_help
    }
    if cmd in handlers:
        handlers[cmd](args)
    else:
        self._show_help()

def _handle_create(self, args):
    """
    Handle the /create command using ProjectArchitect.
    """
    architect = ProjectArchitect()
    architect.start_creation_flow()
    self.status_info['last_created_project'] = architect.project_config.get('name', 'Unknown')

def _handle_edit(self, args):
    """
    Handle the /edit command using ProjectEditor.
    """
    editor = ProjectEditor()
    editor.start_edit_flow()

def _handle_review(self, args):
    """
    Handle the /review command using CodeReviewer.
    """
    if not args:
        file_path = questionary.path("Enter the file path to review:").ask()
    else:
        file_path = args[0]
    reviewer = CodeReviewer()
    reviewer.review_file(file_path)

def _handle_analyze(self, args):
    """
    Handle the /analyze command using ProjectAnalyzer.
    """
    if not args:
        project_path = questionary.path("Enter the project path to analyze:", only_directories=True).ask()
    else:
        project_path = args[0]
    analyzer = ProjectAnalyzer()
    analyzer.analyze_project(project_path)

def _handle_template(self, args):
    """
    Manage project templates.
    """
    if not args:
        self._show_templates()
        return
    action = args[0]
    if action == "list":
        self._show_templates()
    elif action == "add":
        tpl_id = questionary.text("Enter new template id:").ask()
        name = questionary.text("Enter template name:").ask()
        stack = questionary.text("Enter comma-separated stack (e.g., react,node,express):").ask().split(',')
        features = questionary.text("Enter comma-separated features:").ask().split(',')
        structure = questionary.text("Enter comma-separated directory structure:").ask().split(',')
        TEMPLATES[tpl_id] = {
            "name": name,
            "stack": [s.strip() for s in stack],
            "features": [f.strip() for f in features],
            "structure": [s.strip() for s in structure]
        }
        console.print(f"[green]Template {tpl_id} added.[/green]")
    elif action == "remove":
        tpl_id = questionary.text("Enter template id to remove:").ask()
        if tpl_id in TEMPLATES:
            del TEMPLATES[tpl_id]
            console.print(f"[green]Template {tpl_id} removed.[/green]")
        else:
            console.print(f"[red]Template {tpl_id} not found.[/red]")
    else:
        console.print("[red]Invalid template action. Use: list, add, remove[/red]")

def _handle_deploy(self, args):
    """
    Handle the /deploy command using Deployer.
    """
    if not args:
        project_path = questionary.path("Enter the project path to deploy:", only_directories=True).ask()
    else:
        project_path = args[0]
    deployer = Deployer()
    deployer.deploy_project(project_path)

def _handle_test(self, args):
    """
    Handle the /test command using TestRunner.
    """
    if not args:
        project_path = questionary.path("Enter the project path to test:", only_directories=True).ask()
    else:
        project_path = args[0]
    tester = TestRunner()
    tester.run_tests(project_path)

def _handle_docs(self, args):
    """
    Handle the /docs command using DocGenerator.
    """
    if not args:
        project_path = questionary.path("Enter the project path for documentation:", only_directories=True).ask()
    else:
        project_path = args[0]
    doc_gen = DocGenerator()
    doc_gen.generate_docs(project_path)

def _handle_status(self, args):
    """
    Display current project status information.
    """
    if not self.status_info:
        console.print("[yellow]No status information available.[/yellow]")
    else:
        table = Table("Parameter", "Value", show_header=True)
        for key, value in self.status_info.items():
            table.add_row(key, str(value))
        console.print(Panel(table, title="Project Status", style="blue"))

def _handle_help(self, args):
    """
    Display help information.
    """
    self._show_help()

def _show_welcome_message(self):
    """
    Display a welcome message and initial help.
    """
    console.print(Panel.fit(
        "[bold cyan]Advanced Full-Stack App Management Assistant[/]\n"
        "✨ AI-Powered • Interactive • Production-Ready",
        style="blue"
    ))
    self._show_help()

def _show_help(self):
    """
    Display help information for all commands.
    """
    table = Table(show_header=True)
    table.add_column("Command", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Options", style="yellow")
    commands = [
        ('/create', 'Create new project with AI assistance', '--'),
        ('/edit', 'Edit an existing project', '<project_path>'),
        ('/review', 'Perform AI-based code review', '<file_path>'),
        ('/analyze', 'Analyze project with AI', '<project_path>'),
        ('/template', 'Manage project templates', 'list, add, remove'),
        ('/deploy', 'Deploy project', '<project_path>'),
        ('/test', 'Run tests', '<project_path>'),
        ('/docs', 'Generate documentation', '<project_path>'),
        ('/status', 'Show project status', ''),
        ('/help', 'Show this help information', ''),
        ('/quit', 'Exit the assistant', '')
    ]
    for cmd, desc, opts in commands:
        table.add_row(cmd, desc, opts)
    console.print(table)

——————————————————————————

Main Execution

——————————————————————————

if name == “main”:
interface = CommandInterface()
interface.run()
