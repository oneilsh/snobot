# bioner_ui/examples.py
from typing import Dict, List

EXAMPLES: Dict[str, str] = {
    "Clinic note (basic)":
        "Pt with chronic kidney disease (CKD) and history of diabetes mellitus type 2. "
        "Complains of dyspnea; started on metformin 500 mg. Possible polycystic kidney disease.",

    "ED triage (negation)":
        "42yo F presents with fever and non-productive cough x5d. Reports dyspnea on exertion; "
        "started azithromycin yesterday by urgent care. Denies chest pain.",

    "Discharge summary (alternative phrasing)":
        "Admitted for NSTEMI. Started on aspirin 81 mg daily and atorvastatin 80 mg nightly. "
        "Echo shows reduced LVEF 35%. Follow up with cardiology in 1–2 weeks.",
}

def example_names() -> List[str]:
    return list(EXAMPLES.keys())

def get_example(name: str) -> str:
    return EXAMPLES.get(name, "")
