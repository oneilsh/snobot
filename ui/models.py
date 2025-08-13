from dataclasses import dataclass
from typing import List

@dataclass
class Settings:
    backend: str
    domains: List[str]

