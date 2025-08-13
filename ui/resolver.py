# Stub resolver — replace with your backend call
from typing import Dict, Any
from .models import Settings
import time
from agents.extract_agent import extract_concepts, SearchConcept

def resolve_entities_api(text: str, settings: Settings, status_widget) -> Dict[str, Any]:
    meta = {
        "backend": settings.backend,
        "domains": settings.domains,
        "chars": len(text)
    }

    extracted_concepts = extract_concepts(text)
    entities = []
    for concept in extracted_concepts.concepts:
        entities.append({
            "mention": concept.concept_string,
            "start": text.find(concept.concept_string),
            "end": text.find(concept.concept_string) + len(concept.concept_string),
            "domain": concept.probable_domain,
            "id": "SNOMED:" + str(hash(concept.concept_string)),  # Placeholder ID generation
            "label": concept.concept_string,  # Placeholder label
            "vocab": "SNOMED",  # Placeholder vocabulary
            "confidence": None  # Placeholder confidence
        })

    return {
        "meta": meta,
        "entities": entities
    }



    # return {
    #     "meta": {
    #         "backend": settings.backend,
    #         "domains": settings.domains,
    #         "chars": len(text)
    #     },
    #     "entities": [
    #         {
    #             "mention": "chronic kidney disease",
    #             "start": 7, "end": 29, "domain": "Condition",
    #             "id":"MONDO:0005161","label":"Chronic kidney disease","vocab":"MONDO","confidence":0.91
    #         },
    #         {
    #             "mention": "diabetes mellitus type 2",
    #             "start": 49, "end": 74, "domain": "Condition",
    #             "id":"MONDO:0005148","label":"Type 2 diabetes mellitus","vocab":"MONDO","confidence":0.89
    #         },
    #         {
    #             "mention": "metformin",
    #             "start": 105, "end": 114, "domain": "Drug",
    #             "id":"RxCUI:860975","label":"metformin","vocab":"RxNorm","confidence":0.88
    #         },
    #         {
    #             "mention": "polycystic kidney disease",
    #             "start": 136, "end": 162, "domain": "Condition",
    #             "id":"MONDO:0008315","label":"Polycystic kidney disease","vocab":"MONDO","confidence":0.84
    #         },
    #     ],
    # }
