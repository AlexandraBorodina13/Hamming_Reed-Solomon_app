from pydantic import BaseModel, Field
from typing import Literal

class HammingEncodeRequest(BaseModel):
    m: int = Field(ge=3, le=6, description="Параметр m кода Хэмминга")
    message: str = Field(description="Строка из 0 и 1")

class HammingDecodeRequest(BaseModel):
    m: int = Field(ge=3, le=6)
    received: str