"""
Multi-Agent system module.

This module contains the agent implementations for the CT-MA system,
including Logic Agent, Think Agent, Answer Agent, and Coordinator.
"""

from .base_agent import BaseAgent
from .logic_agent import LogicAgent
from .think_agent import ThinkAgent
from .answer_agent import AnswerAgent
from .coordinator import Coordinator
from .unified_cot_agent import UnifiedCoTAgent

__all__ = [
    "BaseAgent",
    "LogicAgent",
    "ThinkAgent",
    "AnswerAgent",
    "Coordinator",
    "UnifiedCoTAgent"
]
