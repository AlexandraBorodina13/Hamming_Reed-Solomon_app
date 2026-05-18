from pydantic import BaseModel
from typing import Any, Optional

class StepDTO(BaseModel):
    type: str
    title: str
    payload: dict[str, Any]

class EncodeResponse(BaseModel):
    codeword: str
    params: dict[str, Any]
    steps: Optional[list[StepDTO]] = None

class DecodeResponse(BaseModel):
    decoded: str
    success: bool
    steps: list[StepDTO]
    error_positions: list[int] = []
    final_metric: float | None = None
    
class CodecSummary(BaseModel):
    type: str
    preset: str
    n: Any
    k: Any
    rate: float
    redundancy: float
    error_capability: str
    field_size: int
    notes: str

class ComparisonResponse(BaseModel):
    codes: list[CodecSummary]