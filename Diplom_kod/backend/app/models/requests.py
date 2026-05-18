from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional
from app.core.reed_solomon import RS_PRESETS

# --- Хэмминг ---
class HammingEncodeRequest(BaseModel):
    m: int = Field(ge=3, le=6, description="Параметр m кода Хэмминга")
    message: str = Field(description="Строка из 0 и 1")
    original_message: Optional[str] = Field(None, description="Исходное сообщение для проверки корректности")

    @field_validator('message')
    @classmethod
    def check_length(cls, v, info):
        m = info.data.get('m')
        if m is not None:
            n = 2**m - 1
            k = n - m
            if len(v) != k:
                raise ValueError(f'Длина сообщения должна быть {k} бит (сейчас {len(v)})')
        # проверка на символы
        if not set(v).issubset({'0','1'}):
            raise ValueError('Сообщение должно содержать только 0 и 1')
        return v

class HammingDecodeRequest(BaseModel):
    m: int = Field(ge=3, le=6)
    received: str
    original_message: Optional[str] = Field(None, description="Исходное сообщение для проверки")

    @field_validator('received')
    @classmethod
    def check_received(cls, v, info):
        m = info.data.get('m')
        if m is not None:
            n = 2**m - 1
            if len(v) != n:
                raise ValueError(f'Длина принятого слова должна быть {n} бит (сейчас {len(v)})')
        if not set(v).issubset({'0','1'}):
            raise ValueError('Принятое слово должно содержать только 0 и 1')
        return v

# --- БЧХ ---
class BCHEncodeRequest(BaseModel):
    preset: str = Field(description="Название пресета БЧХ")
    message: str

    @field_validator('preset')
    @classmethod
    def check_preset(cls, v):
        from app.core.bch import BCH_PRESETS   # локальный импорт, чтобы избежать циклической зависимости
        if v not in BCH_PRESETS:
            raise ValueError(f'Неизвестный пресет: {v}')
        return v

    @field_validator('message')
    @classmethod
    def check_message(cls, v, info):
        if not set(v).issubset({'0','1'}):
            raise ValueError('Сообщение должно содержать только 0 и 1')
        preset = info.data.get('preset')
        if preset:
            from app.core.bch import BCH_PRESETS
            k = BCH_PRESETS[preset]['k']
            if len(v) != k:
                raise ValueError(f'Длина сообщения должна быть {k} бит (сейчас {len(v)})')
        return v

class BCHDecodeRequest(BaseModel):
    preset: str
    received: str

    @field_validator('preset')
    @classmethod
    def check_preset_decode(cls, v):
        from app.core.bch import BCH_PRESETS
        if v not in BCH_PRESETS:
            raise ValueError(f'Неизвестный пресет: {v}')
        return v

    @field_validator('received')
    @classmethod
    def check_received(cls, v, info):
        if not set(v).issubset({'0','1'}):
            raise ValueError('Принятое слово должно содержать только 0 и 1')
        preset = info.data.get('preset')
        if preset:
            from app.core.bch import BCH_PRESETS
            n = BCH_PRESETS[preset]['n']
            if len(v) != n:
                raise ValueError(f'Длина принятого слова должна быть {n} бит (сейчас {len(v)})')
        return v

# --- Рид-Соломон ---
class RSEncodeRequest(BaseModel):
    preset: str = Field(description="Название предустановленной конфигурации RS")
    message: str = Field(description="Текст (байты) для кодирования")

    @field_validator('preset')
    @classmethod
    def check_preset(cls, v):
        # Импорт внутри валидатора, чтобы избежать циклических зависимостей
        if v not in RS_PRESETS:
            raise ValueError(f'Неизвестный пресет: {v}')
        return v

class RSDecodeRequest(BaseModel):
    preset: str
    received: str = Field(description="Список целых чисел через запятую")

    @field_validator('preset')
    @classmethod
    def check_preset_decode(cls, v):
        if v not in RS_PRESETS:
            raise ValueError(f'Неизвестный пресет: {v}')
        return v

# --- Свёрточный код ---
class ConvEncodeRequest(BaseModel):
    preset: str = Field(description="Название пресета из STANDARD_CONVOLUTIONAL_CODES")
    message: str

    @field_validator('message')
    @classmethod
    def check_binary(cls, v):
        if not set(v).issubset({'0','1'}):
            raise ValueError('Только 0 и 1')
        return v

class ConvDecodeRequest(BaseModel):
    preset: str
    received: str

    @field_validator('received')
    @classmethod
    def check_binary_received(cls, v):
        if not set(v).issubset({'0','1'}):
            raise ValueError('Только 0 и 1')
        return v
    
    
class AWGNRequest(BaseModel):
    bits: str = Field(..., description="Кодовое слово (строка 0/1)")
    snr_db: float = Field(..., ge=-10, le=30, description="SNR в дБ (Es/N0)")
    n: Optional[int] = Field(None, description="Длина кодового слова")
    k: Optional[int] = Field(None, description="Число информационных бит")
    
