import numpy as np
import galois
import random
from functools import lru_cache

@lru_cache(maxsize=32)
def rs_make(n=255, k=223, m=8):
    GF = galois.GF(2**m)
    RS = galois.ReedSolomon(n, k, field=GF)
    return GF, RS


def rs_encode_bytes(data: bytes, RS):
    assert len(data) == RS.k
    GF = RS.field
    msg = GF(np.frombuffer(data, dtype=np.uint8))
    code = RS.encode(msg)
    return np.array(code, dtype=int)


def rs_decode_symbols(codeword, RS):
    GF = RS.field
    cw = GF(codeword)
    dec = RS.decode(cw)
    return np.array(dec, dtype=int)


def rs_syndromes(codeword, RS):
    """
    Возвращает синдромы для данного кодового слова.
    """
    GF = RS.field
    cw = GF(codeword)
    n, k = RS.n, RS.k
    alpha = GF.primitive_element

    S = []
    for i in range(n - k):
        s = GF(0)  # <-- полевая "нулевая" инициализация
        for j in range(n):
            s += cw[j] * (alpha ** (i * j))
        S.append(int(s))
    return S

def rs_add_errors(codeword, RS, error_positions, error_values=None):
    """
    Вносит ошибки в кодовое слово RS:
    - error_positions: список индексов, где вносим ошибки
    - error_values: список величин ошибок (если None - случайные)
    - возвращает искажённое слово
    """
    GF = RS.field
    noisy = codeword.copy()
    
    for i, pos in enumerate(error_positions):
        if error_values is not None and i < len(error_values):
            # Используем заданную величину ошибки
            error_val = error_values[i]
        else:
            # Выбираем случайную величину ошибки (не 0)
            choices = list(range(1, GF.order))  # все значения кроме 0
            error_val = random.choice(choices)
        
        # Добавляем ошибку (в поле GF это сложение по модулю)
        noisy[pos] = (noisy[pos] + error_val) % 256
    
    return noisy

def extract_message_rs(codeword, RS):
    dec = rs_decode_symbols(codeword, RS)
    decoded_bytes = dec[:RS.k]
    text = bytes(decoded_bytes).decode("latin-1").rstrip("\x00")
    text = "".join(chr(b) for b in decoded_bytes if 32 <= b < 127)
    return text

RS_PRESETS = {
    "RS(255,223) – GF(2^8), t=16": {
        "n": 255,
        "k": 223,
        "m": 8,
        "t": 16
    },
    "RS(255,239) – GF(2^8), t=8": {
        "n": 255,
        "k": 239,
        "m": 8,
        "t": 8
    },
    "RS(255,191) – GF(2^8), t=32": {
        "n": 255,
        "k": 191,
        "m": 8,
        "t": 32
    },
        "RS(255,127) – GF(2^8), t=64": {
        "n": 255,
        "k": 127,
        "m": 8,
        "t": 64
    }
}
