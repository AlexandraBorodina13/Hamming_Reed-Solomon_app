import numpy as np
import galois
import random
from functools import lru_cache
import galois as _galois
logs = []

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


#  Вспомогательные алгоритмы для пошагового RS-декодирования

def _field_order(m: int) -> int:
    return 2**m - 1


def rs_compute_syndromes_gf(codeword, GF, n, k):
    """Правильные синдромы: S_j = sum_{i=0}^{n-1} r_i * alpha^{j*i}"""
    alpha = GF.primitive_element
    cw = GF(codeword)
    t = (n - k) // 2
    syndromes = []
    for j in range(1, 2*t + 1):
        s = GF(0)
        for i in range(n):
            s += cw[i] * (alpha ** (j * i))
        syndromes.append(int(s))   # сохраняем int для удобства
    return syndromes


def rs_berlekamp_massey_gf(syndromes, GF):
    """Классический алгоритм Берлекэмпа–Месси для RS (недвоичный)"""
    syn = [GF(s) for s in syndromes]
    n_syn = len(syn)
    C = [GF(1)]          # полином локаторов
    B = [GF(1)]          # предыдущий полином
    L = 0
    m = 1
    b = GF(1)
    delta = GF(0)

    for r in range(1, n_syn + 1):
        # Вычисление невязки delta
        delta += syn[r-1]
        for j in range(1, L+1):
            delta += C[j] * syn[r-1-j]

        if delta == 0:
            m += 1
        else:
            T = C[:]
            # C = C - delta/b * x^m * B
            coeff = delta / b
            # Удлиняем C до нужной длины
            while len(C) < len(B) + m:
                C.append(GF(0))
            for i, coeff_b in enumerate(B):
                C[i + m] -= coeff * coeff_b

            if 2 * L <= r - 1:   # классическое условие (r начинается с 1)
                L = r - L
                B = T
                b = delta
                m = 1
            else:
                m += 1

    # Удаляем лишние нули в конце
    while len(C) > 1 and C[-1] == 0:
        C.pop()
    return C, len(C) - 1


def rs_chien_search_gf(Lambda_poly, n, GF):
    """Поиск позиций ошибок: корни Lambda(x) = 0 для x = alpha^i"""
    alpha = GF.primitive_element
    error_positions = []
    for i in range(n):
        x = alpha ** i
        val = GF(0)
        for coeff in Lambda_poly:
            val = val * x + coeff   # схема Горнера
        if val == 0:
            error_positions.append(i)
    return error_positions


def rs_forney_gf(syndromes, Lambda, error_positions, n, k, GF):
    """Вычисление величин ошибок через алгоритм Форни"""
    t = (n - k) // 2
    # Полином синдромов S(x) = sum_{j=1}^{2t} S_j * x^{j-1}
    S_poly = galois.Poly([GF(s) for s in syndromes], field=GF)
    # Полином локаторов Lambda(x)
    Lambda_poly = galois.Poly(Lambda, field=GF)
    # Омега(x) = S(x) * Lambda(x) mod x^{2t}
    x2t = galois.Poly([1] + [0]*t, field=GF)   # x^{2t}
    Omega_poly = (S_poly * Lambda_poly) % x2t

    # Производная Lambda'(x) – только нечётные степени
    deriv_coeffs = []
    for i in range(1, len(Lambda)):
        if i % 2 == 1:
            deriv_coeffs.append(Lambda[i])
    Lambda_prime = galois.Poly(deriv_coeffs, field=GF) if deriv_coeffs else galois.Poly([0], field=GF)

    magnitudes = []
    for pos in error_positions:
        x = GF.primitive_element ** pos
        x_inv = GF(1) / x
        omega_val = Omega_poly(x_inv)
        lambda_prime_val = Lambda_prime(x_inv)
        if lambda_prime_val == 0:
            magnitudes.append(0)
        else:
            e = omega_val / lambda_prime_val
            magnitudes.append(int(e))
    return magnitudes
