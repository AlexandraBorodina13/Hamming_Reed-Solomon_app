from dataclasses import dataclass

@dataclass
class Step:
    type: str
    title: str
    payload: dict