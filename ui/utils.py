import io
from typing import Dict, Any, List, Literal
import pandas as pd


OMOP_DOMAINS = [
    "Condition",
    "Observation",
    "Procedure",
    "Measurement",
    "Device",
    "Drug",
]

OMOP_DOMAINS_LITERAL = Literal[*OMOP_DOMAINS]

DOMAIN_COLORS = {
    "Condition": "#E0F0FF",
    "Observation": "#EFE0FF",
    "Procedure": "#E8FFE8",
    "Measurement": "#FFF6CC",
    "Device": "#EEEEEE",
    "Drug": "#F0F0F0",
}


def payload_to_df(payload: Dict[str, Any]) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for i, e in enumerate(payload.get("entities", [])):
        rows.append({
            "row_id": i,
            "mention": e.get("mention",""),
            "start": int(e.get("start", 0)),
            "end": int(e.get("end", 0)),
            "canonical_label": e.get("label",""),
            "id": e.get("id",""),
            "domain": e.get("domain",""),
            "confidence": e.get("confidence", None),
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.astype({
            "row_id":"int",
            "mention":"string","start":"int","end":"int",
            "canonical_label":"string","id":"string","domain":"string",
            #"confidence":"float"
        })
    return df

def csv_text(df: pd.DataFrame) -> str:
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue()
