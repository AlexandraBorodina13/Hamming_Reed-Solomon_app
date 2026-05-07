from pydantic import BaseModel
from typing import Any

class StepDTO(BaseModel):
    type: str
    title: str
    payload: dict[str, Any]

class EncodeResponse(BaseModel):
    codeword: str
    params: dict[str, Any]

class DecodeResponse(BaseModel):
    decoded: str
    success: bool
    steps: list[StepDTO]
    error_positions: list[int] = []
    final_metric: float | None = None