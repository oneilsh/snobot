"""Core domain models for SNOBot."""

from pydantic import Field
from pydantic.dataclasses import dataclass


@dataclass
class Mention:
    """A potential OMOP concept mention found in text."""
    mention_str: str = Field(..., description="The string containing a potential OMOP concept or synonym to identify.")


@dataclass
class MentionList:
    """A list of potential OMOP concept mentions."""
    mentions: list[Mention] = Field(..., description="A list of potential OMOP concepts or synonyms to identify.")


@dataclass
class AgentCodedConcept:
    """A concept coded by the AI agent with basic information."""
    concept_id: str = Field(..., description="The OMOP concept ID.")
    concept_name: str = Field(..., description="The OMOP concept name.")
    negated: bool = Field(False, description="Whether the concept is negated in the input text.")


@dataclass
class FullCodedConcept:
    """A fully coded concept with complete OMOP metadata."""
    mention_str: str = Field(..., description="The string containing a potential OMOP concept or synonym to identify.")
    concept_id: str = Field(..., description="The OMOP concept ID.")
    concept_name: str = Field(..., description="The OMOP concept name.")
    domain_id: str = Field(..., description="The OMOP domain ID.")
    vocabulary_id: str = Field(..., description="The OMOP vocabulary ID.")
    concept_code: str = Field(..., description="The OMOP concept code.")
    standard: bool = Field(False, description="Whether this is a standard OMOP concept (True if 'S', False otherwise).")
    negated: bool = Field(False, description="Whether the concept is negated in the input text.")
