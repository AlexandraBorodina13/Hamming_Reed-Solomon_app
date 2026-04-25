import numpy as np
from .steps import Step


def _bits_to_polynomial(bits):
    """Строит строку полинома из списка битов (индекс = степень x)."""
    terms = []
    for i, bit in enumerate(bits):
        if bit == 1:
            if i == 0:
                terms.append("1")
            elif i == 1:
                terms.append("x")
            else:
                terms.append(f"x^{i}")
    return " + ".join(terms) if terms else "0"


def _bits_to_polynomial_msb(bits):
    """
    Строит строку полинома из списка битов MSB-first:
    bits[0] = коэффициент при x^(n-1), bits[n-1] = коэффициент при x^0.
    Это порядок, который использует galois.
    """
    n = len(bits)
    terms = []
    for i, bit in enumerate(bits):
        power = n - 1 - i
        if bit == 1:
            if power == 0:
                terms.append("1")
            elif power == 1:
                terms.append("x")
            else:
                terms.append(f"x^{power}")
    return " + ".join(terms) if terms else "0"


def explain_bch(received, bch_code):
    """
    Формирует пошаговое объяснение декодирования кода БЧХ.

    Параметры:
    - received: принятое кодовое слово (массив из n бит, MSB-first как в galois)
    - bch_code: объект BCHCode

    Возвращает список объектов Step.
    """
    n = bch_code.n
    k = bch_code.k
    t = bch_code.t

    steps = []

    # ── Шаг 1: Параметры кода ──────────────────────────────────────────────
    steps.append(Step(
        "text",
        "Параметры кода БЧХ",
        {"description": (
            f"Код БЧХ ({n}, {k}): длина кодового слова n={n}, "
            f"длина сообщения k={k}. Исправляет до t={t} ошибок.\n"
            f"Код построен над полем GF(2^m), α — примитивный элемент поля."
        )}
    ))

    # ── Шаг 2: Принятое кодовое слово ──────────────────────────────────────
    received_list = received.tolist() if hasattr(received, 'tolist') else list(received)
    steps.append(Step(
        "matrix",
        "Принятое кодовое слово",
        {"codeword": received_list}
    ))

    # ── Шаг 3: Полином принятого слова ─────────────────────────────────────
    # galois хранит MSB-first: received[0] = коэф. при x^(n-1)
    poly_str = _bits_to_polynomial_msb(received_list)
    steps.append(Step(
        "text",
        "Полином принятого слова R(x)",
        {"description": (
            f"Биты кодового слова записываются MSB-first "
            f"(первый бит — коэффициент при x^{n-1}):\n"
            f"R(x) = {poly_str}\n\n"
            f"Синдром вычисляется как Sⱼ = R(αʲ) — подстановка αʲ в R(x)."
        )}
    ))

    # ── Вычисление (внутри decode вызывается _compute_syndromes) ───────────
    decoded, info = bch_code.decode(received)

    # ── Шаг 4: Синдромы ────────────────────────────────────────────────────
    syndromes = info.get("syndromes", [])
    if syndromes:
        j_indices = list(range(1, 2 * t + 1))

        formula = (
            r"S_j = R(\alpha^j) = \sum_{i=0}^{n-1} r_i \cdot \alpha^{j(n-1-i)}"
            f",\quad j = {', '.join(map(str, j_indices))}"
        )

        # Одна строка с результатами: S1 = 5, S2 = 3, ...
        syndrome_display = ",  ".join(
            f"S{j} = {v}" for j, v in zip(j_indices, syndromes)
        )

        all_zero = all(s == 0 for s in syndromes)
        if all_zero:
            verdict = "Все синдромы равны нулю → ошибок нет."
        else:
            nonzero = [j for j, s in zip(j_indices, syndromes) if s != 0]
            verdict = (
                f"Ненулевые синдромы (j = {nonzero}) → обнаружены ошибки. "
                "Алгоритм Берлекэмпа–Месси определит локаторы ошибок."
            )

        steps.append(Step(
            "calc",
            "Вычисление синдромов",
            {
                "syndromes": syndromes,
                "syndrome_indices": j_indices,   # для UI: S1, S2, ...
                "formula": formula,
                "description": f"{syndrome_display}\n\n{verdict}",
            }
        ))

    # ── Шаг 5: Исправление ошибок ──────────────────────────────────────────
    if info["success"]:
        error_positions = info["error_positions"]
        if error_positions:
            error_desc = (
                f"Алгоритм Берлекэмпа–Месси нашёл локаторы ошибок. "
                f"Ошибки исправлены в позициях: {error_positions}."
            )
        else:
            error_desc = "Ошибок не обнаружено — кодовое слово принято без искажений."

        steps.append(Step(
            "calc",
            "Декодирование и исправление ошибок",
            {
                "error_positions": error_positions,
                "description": error_desc,
                "formula": "Алгоритм Берлекэмпа–Месси",
            }
        ))

        # ── Шаг 6: Результат ───────────────────────────────────────────────
        steps.append(Step(
            "result",
            "Результат декодирования",
            {
                "corrected": decoded,
                "decoded": ''.join(str(b) for b in decoded),
                "success": True,
            }
        ))
    else:
        steps.append(Step(
            "result",
            "Ошибка декодирования",
            {
                "description": info.get(
                    "error",
                    "Не удалось исправить ошибки — возможно, превышена "
                    "исправляющая способность кода (более t ошибок)."
                ),
                "success": False,
            }
        ))

    return steps