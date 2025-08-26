"""Core domain models for SNOBot."""

from pydantic import Field
from pydantic.dataclasses import dataclass
from typing import Optional
import yaml


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
class ConceptRelation:
    """Represents a parent or child concept relationship."""
    concept_id: str = Field(..., description="The related concept ID.")
    concept_name: str = Field(..., description="The related concept name.")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for YAML serialization."""
        return {
            "concept_id": self.concept_id,
            "concept_name": self.concept_name
        }


@dataclass
class EnhancedConcept:
    """Enhanced concept with hierarchical information for agent reasoning."""
    concept_id: str = Field(..., description="The OMOP concept ID.")
    concept_name: str = Field(..., description="The OMOP concept name.")
    domain_id: str = Field(..., description="The OMOP domain ID.")
    vocabulary_id: str = Field(..., description="The OMOP vocabulary ID.")
    concept_code: str = Field(..., description="The OMOP concept code.")
    standard: bool = Field(False, description="Whether this is a standard OMOP concept.")
    parent_concepts: Optional[list[ConceptRelation]] = Field(default=None, description="Parent concepts in the hierarchy.")
    child_concepts: Optional[list[ConceptRelation]] = Field(default=None, description="Child concepts in the hierarchy.")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for YAML serialization."""
        result = {
            "concept_id": self.concept_id,
            "concept_name": self.concept_name,
            "domain_id": self.domain_id,
            "vocabulary_id": self.vocabulary_id,
            "concept_code": self.concept_code,
            "standard": self.standard
        }
        
        if self.parent_concepts:
            result["parent_concepts"] = [p.to_dict() for p in self.parent_concepts]
        
        if self.child_concepts:
            result["child_concepts"] = [c.to_dict() for c in self.child_concepts]
            
        return result
    
    def to_yaml(self) -> str:
        """Convert to YAML string representation."""
        return yaml.safe_dump(self.to_dict(), default_flow_style=False, sort_keys=False)


@dataclass
class ConceptCollection:
    """A collection of concepts with metadata for agent reasoning."""
    concepts: list[EnhancedConcept] = Field(..., description="List of concept candidates.")
    search_query: Optional[str] = Field(default=None, description="The search query used to find these concepts.")
    total_count: Optional[int] = Field(default=None, description="Total number of concepts found.")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for YAML serialization."""
        result = {
            "concepts": [c.to_dict() for c in self.concepts]
        }
        
        if self.search_query:
            result["search_query"] = self.search_query
        
        if self.total_count is not None:
            result["total_count"] = self.total_count
            
        return result
    
    def to_yaml(self) -> str:
        """Convert to YAML string representation."""
        return yaml.safe_dump(self.to_dict(), default_flow_style=False, sort_keys=False)


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
    
    def to_dict(self) -> dict:
        """Convert to dictionary for easier serialization."""
        return {
            "mention_str": self.mention_str,
            "concept_id": self.concept_id,
            "concept_name": self.concept_name,
            "domain_id": self.domain_id,
            "vocabulary_id": self.vocabulary_id,
            "concept_code": self.concept_code,
            "standard": self.standard,
            "negated": self.negated
        }
