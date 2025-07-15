"""
Chain-of-Thought (CoT) data generation module.

This module provides components for generating, validating, and quality-checking
CoT data in the required three-part format: <logic>, <think>, <answer>.
"""

from .data_generator import COTDataGenerator
from .format_validator import FormatValidator
from .quality_checker import QualityChecker

__all__ = [
    "COTDataGenerator",
    "FormatValidator",
    "QualityChecker"
]
