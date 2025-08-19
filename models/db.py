"""Database-related models for SNOBot."""

from pydantic.dataclasses import dataclass


@dataclass
class VecDBHit:
    """A hit result from vector database search."""
    search_string: str
    concept_id: str
    concept_name: str
    distance: float
