"""
The module contains tools to generate a functional workflow with a use of llm given tool 
in a form of annotated functions.
"""

from .components.llm_function.llm_handler import LlmHandler

__package_metadata__ = {
    "author": "Kyrylo Mordan",
    "author_email": "parachute.repo@gmail.com",
    "description": "LLM-based planner and orchestrator that turns existing code into complex functions.",
}