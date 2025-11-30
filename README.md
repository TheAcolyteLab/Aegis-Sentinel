# Aegis-Sentinel
Aegis Sentinel is an autonomous, multi-agent framework designed to assess, synthesize, and verify security-related intelligence from diverse sources. The system orchestrates specialized agents to simulate a full Retrieve–Analyze–Report pipeline, enabling rapid evaluation of security events in specific regions.

💻 Setup and Execution
Prerequisites
Python 3.10+

[] Ollama Installation: You must have Ollama installed and running locally to serve the LLM.

[] Model Download: Download the required local model (Gemma 2B) using Ollama:

Bash

ollama pull gemma:2b
Environment Setup
Clone the Repository: (Assume this project is available on GitHub)

Bash

[] git clone [repository_url]
[] cd aegis-sentinel
[] Create and Activate Virtual Environment:

Bash

# Create the environment
[] python -m venv ssia_env

# Activate (Windows PowerShell):
[] .\ssia_env\Scripts\Activate.ps1

# Activate (Linux/macOS/Git Bash):
[] source ssia_env/bin/activate
[] Install Dependencies:

Bash
#Install
[] requests, pydantic, opentelemetry-sdk)
Running a Mission
The core execution loop is handled by the main_runner.py (assumed entry point).

Bash

# Run a sample mission query
python main_runner.py "Assess the credibility of recent reports regarding regional fiber optic network disruptions near the capital."
The output will display the execution trajectory, the final verification score, and the scrubbed, verified intelligence report.
