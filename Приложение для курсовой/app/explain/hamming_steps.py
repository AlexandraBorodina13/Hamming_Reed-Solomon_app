import numpy as np
from .steps import Step
from app.core.hamming import hamming_general_matrices, syndrome_general, extract_message


def explain_hamming_general(received, m):
    G, H, n, k = hamming_general_matrices(m)
    s = syndrome_general(received, m)

    steps = [
        Step("matrix", f"Проверочная матрица H ({m}x{n})", {"H": H, "m": m, "n": n}),
        Step("calc", "Вычисление синдрома", {"received": received, "syndrome": s}),
    ]

    error_pos = None
    if s.any():
        # LSB-first
        idx = 0
        for r, bit in enumerate(s):
            if bit:
                idx += (1 << r)
        error_pos = idx - 1
        if not (0 <= error_pos < n):
            error_pos = "uncorrectable"

    steps.append(Step("bit", "Локализация ошибки", {
        "error_pos": error_pos,
        "received": received,
        "syndrome": s,
        "m": m
    }))

    if error_pos is not None and error_pos != "uncorrectable":
        corrected = received.copy()
        corrected[error_pos] ^= 1
        steps.append(Step("result", "Исправление ошибки", {
            "corrected": corrected,
            "original_length": k,
            "info_bits": extract_message(corrected, m)
        }))
    elif error_pos is None:
        steps.append(Step("result", "Результат", {
            "corrected": received,
            "original_length": k,
            "info_bits": extract_message(received, m)
        }))

    return steps
