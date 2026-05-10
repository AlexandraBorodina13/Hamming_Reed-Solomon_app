import numpy as np
from fastapi import HTTPException
import uuid
from datetime import datetime
from typing import Dict, Any

from app.core.hamming import encode_general, decode_general
from app.explain.hamming_steps import explain_hamming_general, explain_hamming_encode
from app.core.bch import get_bch_code, BCH_PRESETS
#from app.explain.bch_steps import explain_bch, explain_bch_encode
from app.explain.bch_steps import explain_bch_encode, explain_bch_decode
from app.core.reed_solomon import rs_make, rs_encode_bytes, rs_decode_symbols, rs_add_errors, RS_PRESETS
from app.explain.rs_steps import explain_rs
from app.core.convolutional import ConvolutionalCode, STANDARD_CONVOLUTIONAL_CODES
from app.explain.convolutional_steps import explain_convolutional
from app.models.responses import DecodeResponse, StepDTO, EncodeResponse
from app.core.hamming import info_positions

def _make_serializable(obj):
    """Рекурсивно преобразует numpy-типы в JSON-совместимые."""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_make_serializable(v) for v in obj]
    return obj

# Временное хранилище задач (для асинхронного RS)
tasks_db: Dict[str, Dict[str, Any]] = {}

# Вспомогательная функция для Хэмминга (длина информационных битов)
def info_positions_len(m):
    n = 2**m - 1
    return sum(1 for j in range(n) if ((j+1) & j) != 0)

# --- Хэмминг ---
class HammingService:
    @staticmethod
    def encode(m: int, message: str) -> EncodeResponse:
        bits = np.array([int(b) for b in message], dtype=int)
        try:
            codeword = encode_general(bits, m)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
        n = 2**m - 1
        k = n - m
        # Генерация шагов кодирования
        steps = explain_hamming_encode(m, bits)
        return EncodeResponse(
            codeword="".join(map(str, codeword)),
            params={"n": n, "k": k, "m": m},
            steps=[StepDTO(type=s.type, title=s.title, payload=_make_serializable(s.payload)) for s in steps]
        )

    @staticmethod
    def decode(m: int, received: str) -> DecodeResponse:
        bits = np.array([int(b) for b in received], dtype=int)
        corrected, info = decode_general(bits, m)
        steps = explain_hamming_general(bits, m)
        err_pos = info.get("error_pos")
        if err_pos == "uncorrectable":
            err_pos = []
        elif err_pos is not None:
            err_pos = [err_pos]
        else:
            err_pos = []
        # Информационные биты
        pos = info_positions(m)
        decoded_bits = corrected[pos]
        return DecodeResponse(
            decoded="".join(map(str, decoded_bits)),
            success=info["error_pos"] != "uncorrectable",
            steps=[StepDTO(type=s.type, title=s.title, payload=_make_serializable(s.payload)) for s in steps],
            error_positions=err_pos  # это уже список
        )


# --- БЧХ ---
class BCHService:
    @staticmethod
    def encode(preset: str, message: str) -> EncodeResponse:
        params = BCH_PRESETS[preset]
        n, k = params["n"], params["k"]
        bits = np.array([int(b) for b in message], dtype=int)
        codec = get_bch_code(n, k)
        codeword = codec.encode(bits)
        steps = explain_bch_encode(codec, bits)
        return EncodeResponse(
            codeword="".join(map(str, codeword)),
            params={"n": n, "k": k, "t": codec.t},
            steps=[StepDTO(type=s.type, title=s.title, payload=_make_serializable(s.payload)) for s in steps]
        )

    @staticmethod
    def decode(preset: str, received: str) -> DecodeResponse:
        params = BCH_PRESETS[preset]
        n, k = params["n"], params["k"]
        bits = np.array([int(b) for b in received], dtype=int)
        codec = get_bch_code(n, k)
        decoded, info = codec.decode(bits)
        steps = explain_bch_decode(bits, codec)   # <-- заменили на новую функцию
        return DecodeResponse(
            decoded="".join(map(str, decoded)),
            success=info.get("success", False),
            steps=[StepDTO(type=s.type, title=s.title, payload=_make_serializable(s.payload)) for s in steps],
            error_positions=info.get("error_positions", [])
        )

# --- Рид-Соломон ---
class RSService:
    @staticmethod
    def encode(preset: str, message: str) -> EncodeResponse:
        params = RS_PRESETS[preset]
        n, k, m, t = params["n"], params["k"], params["m"], params["t"]
        try:
            GF, RS = rs_make(n, k, m)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Ошибка создания RS кода: {e}")
        msg_bytes = message.encode("utf-8")[:k]
        msg_bytes = msg_bytes.ljust(k, b'\0')
        try:
            codeword = rs_encode_bytes(msg_bytes, RS)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Ошибка кодирования RS: {e}")
        return EncodeResponse(
            codeword=",".join(map(str, codeword)),
            params={"n": n, "k": k, "m": m, "t": t}
        )

    @staticmethod
    def decode_async(preset: str, received: str) -> str:
        task_id = str(uuid.uuid4())
        tasks_db[task_id] = {"status": "pending", "result": None, "steps": None}
        # Параметры получим внутри perform_decode
        # Сохраним preset в задаче
        tasks_db[task_id]["preset"] = preset
        tasks_db[task_id]["received"] = received
        return task_id

    @staticmethod
    def perform_decode(task_id: str, preset: str, received: str):
        params = RS_PRESETS[preset]
        n, k, m, t = params["n"], params["k"], params["m"], params["t"]
        try:
            GF, RS = rs_make(n, k, m)
        except Exception as e:
            tasks_db[task_id] = {"status": "error", "detail": str(e)}
            return
        received_list = [int(x.strip()) for x in received.split(",") if x.strip() != ""]
        codeword = np.array(received_list, dtype=int)
        steps = explain_rs(codeword, RS)
        try:
            decoded_symbols = rs_decode_symbols(codeword, RS)
            decoded_bytes = decoded_symbols[:k].tobytes()
            decoded_text = decoded_bytes.decode("latin-1").rstrip("\x00")
            decoded_text = "".join(chr(b) for b in decoded_bytes if 32 <= b < 127)
        except Exception as e:
            tasks_db[task_id] = {"status": "error", "detail": str(e)}
            return
        tasks_db[task_id] = {
            "status": "done",
            "result": {"decoded": decoded_text},
            "steps": [StepDTO(type=s.type, title=s.title, payload=_make_serializable(s.payload)).dict() for s in steps]
        }

# --- Свёрточный код ---
class ConvolutionalService:
    @staticmethod
    def get_codec(preset: str) -> ConvolutionalCode:
        if preset not in STANDARD_CONVOLUTIONAL_CODES:
            raise HTTPException(status_code=422, detail=f"Неизвестный пресет: {preset}")
        config = STANDARD_CONVOLUTIONAL_CODES[preset]
        return ConvolutionalCode(
            config["constraint_length"],
            config["rate"],
            config["generators"]
        )

    @staticmethod
    def encode(preset: str, message: str) -> EncodeResponse:
        codec = ConvolutionalService.get_codec(preset)
        bits = np.array([int(b) for b in message], dtype=int)
        encoded = codec.encode(bits)
        return EncodeResponse(
            codeword="".join(map(str, encoded)),
            params={
                "constraint_length": codec.constraint_length,
                "rate": f"{codec.rate_num}/{codec.rate_den}",
                "generators": codec.generators
            }
        )

    @staticmethod
    def decode(preset: str, received: str) -> DecodeResponse:
        codec = ConvolutionalService.get_codec(preset)
        bits = np.array([int(b) for b in received], dtype=int)
        steps, decoded, info = explain_convolutional(bits, codec)
        return DecodeResponse(
            decoded="".join(map(str, decoded)),
            success=info.get("success", False),
            # ВАЖНО: сериализуем payload шагов
            steps=[StepDTO(type=s.type, title=s.title, payload=_make_serializable(s.payload)) for s in steps],
            final_metric=info.get("final_metric")
        )