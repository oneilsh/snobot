# Stub resolver — replace with your backend call
from typing import Dict, Any, Tuple
from models import Settings, FullCodedConcept, ExtractionLogger
import time
from agents.extract_agent import extract_and_code_mentions
import pandas as pd

def resolve_entities_api(text: str, settings: Settings, status_widget) -> Tuple[Dict[str, Any], pd.DataFrame, ExtractionLogger]:
    """Resolve entities using the enhanced agent and return DataFrame for UI compatibility."""

    coded_concepts, extraction_logger = extract_and_code_mentions(text, status_widget)
    
    # Convert FullCodedConcept objects to dictionaries for DataFrame creation
    concept_dicts = [concept.to_dict() for concept in coded_concepts]
    df = pd.DataFrame(concept_dicts)

    meta = {
        "backend": settings.backend,
        "domains": settings.domains,
        "chars": len(text)
    }

    return (meta, df, extraction_logger)