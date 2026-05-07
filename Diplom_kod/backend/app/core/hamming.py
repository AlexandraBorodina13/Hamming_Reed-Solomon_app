import numpy as np
import math
from functools import lru_cache

@lru_cache(maxsize=128)
def hamming_general_matrices(m):
    """
    Генерация матриц Хэмминга для n = 2^m - 1, k = n - m.
    Порядок битов в H — LSB-first: строка 0 соответствует младшему разряду.
    Позиции кодового слова 0..n-1 соответствуют числам 1..n.
    Столбцы-степени-двойки (1,2,4,...) — проверочные биты.
    """
    n = 2**m - 1
    k = n - m

    # H: m x n, столбец j — двоичное представление (j+1) в LSB-first
    H = np.zeros((m, n), dtype=int)
    for j in range(n):
        val = j + 1
        for r in range(m):              # r = 0 .. m-1  (строка 0 — LSB)
            H[r, j] = (val >> r) & 1

    # Позиции информационных битов (все, кроме степеней двойки)
    info_pos = [j for j in range(n) if ((j + 1) & j) != 0]  # not power of two
    # Позиции проверочных битов (степени двойки)
    check_pos = [ (1 << r) - 1 for r in range(m) ]          # 0-индексация

    # G: k x n, систематический вид с "распылёнными" информационными столбцами:
    # в каждом ряду ставим 1 в своей информационной позиции, а в проверочных —
    # коэффициенты по строкам H (LSB-first).
    G = np.zeros((k, n), dtype=int)
    for i, j in enumerate(info_pos):
        G[i, j] = 1
        for r in range(m):              # если информационная позиция участвует в r-й проверке
            if H[r, j] == 1:
                G[i, (1 << r) - 1] ^= 1  # добавляем в соответствующий проверочный столбец

    return G, H, n, k

def encode_general(message_bits, m):
    """Кодирование для обобщенного кода Хэмминга"""
    G, _, n, k = hamming_general_matrices(m)
    if len(message_bits) != k:
        raise ValueError(f"Длина сообщения должна быть {k} бит")
    return (message_bits @ G) % 2


def syndrome_general(received, m):
    """Вычисление синдрома для обобщенного кода"""
    _, H, _, _ = hamming_general_matrices(m)
    return (received @ H.T) % 2

def decode_general(received, m):
    _, H, n, _ = hamming_general_matrices(m)
    s = syndrome_general(received, m)

    if not s.any():
        return received, {"syndrome": s, "error_pos": None}

    # Поиск столбца H, совпадающего с синдромом
    for j in range(n):
        if np.array_equal(H[:, j], s):
            corr = received.copy()
            corr[j] ^= 1
            return corr, {"syndrome": s, "error_pos": j}

    return received, {"syndrome": s, "error_pos": "uncorrectable"}

def info_positions(m):
    n = 2**m - 1
    # все позиции, кроме степеней двойки (1,2,4,8,...) в 1-индексации
    return [j for j in range(n) if ((j + 1) & j) != 0]

def extract_message(codeword, m):
    pos = info_positions(m)
    return codeword[pos]

def matrix_to_latex(mat, name=None):
    """Преобразует numpy матрицу в LaTeX bmatrix"""
    rows = []
    for row in mat:
        rows.append(" & ".join(map(str, row)))
    body = r" \\ ".join(rows)
    matrix_latex = r"\begin{bmatrix}" + body + r"\end{bmatrix}"
    if name:
        return f"{name} = {matrix_latex}"
    return matrix_latex

