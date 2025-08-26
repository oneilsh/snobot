# Stub resolver — replace with your backend call
from typing import Dict, Any, Tuple
from models import Settings, FullCodedConcept
import time
from agents.extract_agent import extract_and_code_mentions
import pandas as pd

def resolve_entities_api(text: str, settings: Settings, status_widget) -> Tuple[Dict[str, Any], pd.DataFrame]:


    coded_concepts: list[FullCodedConcept] = extract_and_code_mentions(text, status_widget)
    df = pd.DataFrame(coded_concepts)

    meta = {
        "backend": settings.backend,
        "domains": settings.domains,
        "chars": len(text)
    }

    return (meta, df)