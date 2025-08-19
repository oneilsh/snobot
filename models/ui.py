"""UI-related models for SNOBot."""

from dataclasses import dataclass
from typing import List


@dataclass
class Settings:
    """Configuration settings for the UI."""
    backend: str
    domains: List[str]
