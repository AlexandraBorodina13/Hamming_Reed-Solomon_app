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

def validate_rs_params(n=None, k=None, m=None):
    """
    Проверяет корректность параметров RS.
    Автоматически подставляет недостающие параметры, если возможно.
    """
    errors = []
    
    # m должно быть >=1
    if m is not None and (m < 1 or m > 16):
        errors.append("m должно быть от 1 до 16")
    
    max_n = 2**m - 1 if m else None

    # n проверка
    if n is not None:
        if n <= 0:
            errors.append("n должно быть положительным")
        elif m and n > max_n:
            errors.append(f"n не может быть больше {max_n} для m={m}")

    # k проверка
    if k is not None:
        if n is not None and k >= n:
            errors.append("k должно быть меньше n")
        elif k <= 0:
            errors.append("k должно быть положительным")

    # Если есть только n и m, подставляем k максимально возможное
    if n is not None and m is not None and k is None:
        k = n - m
    
    # Если есть n и k, подставляем минимальное m
    if n is not None and k is not None and m is None:
        min_m = 1
        while 2**min_m - 1 < n:
            min_m += 1
        m = min_m
    
    return n, k, m, errors

def valid_n_for_m(m):
    n_max = 2**m - 1
    # допустимые n — все делители n_max
    divisors = [i for i in range(1, n_max+1) if n_max % i == 0]
    return divisors

def extract_message_rs(codeword, RS):
    dec = rs_decode_symbols(codeword, RS)
    decoded_bytes = dec[:RS.k]
    text = bytes(decoded_bytes).decode("latin-1").rstrip("\x00")
    text = "".join(chr(b) for b in decoded_bytes if 32 <= b < 127)
    return text
