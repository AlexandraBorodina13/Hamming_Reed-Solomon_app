import numpy as np
from .steps import Step
from app.core.hamming import (
    hamming_general_matrices,
    syndrome_general,
    extract_message,
    info_positions,
    matrix_to_latex,
)


def explain_hamming_general(received, m, original_message=None):
    """
    Подробное пошаговое объяснение декодирования кода Хэмминга.
    Соответствует структуре документа:
    1. Построение проверочной матрицы H
    2. Вычисление синдрома s = r * H^T
    3. Локализация ошибки (интерпретация синдрома как числа LSB‑first)
    4. Исправление ошибки и извлечение информационных битов
    """
    G, H, n, k = hamming_general_matrices(m)
    s = syndrome_general(received, m)

    steps = []

    # Шаг 1: Построение проверочной матрицы H
    H_latex = matrix_to_latex(H, "H")
    desc1 = (
        f"Столбцы $H$ — все ненулевые векторы длины ${m}$, записанные в порядке возрастания чисел "
        f"(LSB‑first, т.е. младший бит — верхняя строка). Получается:\n\n$${H_latex}$$"
    )
    steps.append(Step(
        "text",
        "Построение проверочной матрицы H",
        {"description": desc1}
    ))

    # Шаг 2: Вычисление синдрома s = r * H^T
    calc_lines = [
        "Вычисляем синдром $s = r \\cdot H^{{\\top}}$:",
        ""
    ]
    for i in range(m):
        terms = []
        for j in range(n):
            if received[j] == 1 and H[i, j] == 1:
                terms.append(f"r_{{{j}}}")
        if terms:
            xor_str = " \\oplus ".join(terms)
            calc_lines.append(f"$$s_{{{i}}} = {xor_str} = {s[i]}$$")
        else:
            calc_lines.append(f"$$s_{{{i}}} = 0$$")
    syndrome_vec = ", ".join(str(x) for x in s)
    calc_lines.append(f"$\\rightarrow s = ({syndrome_vec})$")
    desc2 = "\n\n".join(calc_lines)
    steps.append(Step(
        "calc",
        "Вычисление синдрома",
        {
            "received": received.tolist(),
            "syndrome": s.tolist(),
            "description": desc2,
        }
    ))

    # Шаг 3: Локализация ошибки
    error_pos = None
    if s.any():
        # LSB‑first: синдром --> десятичное число
        idx = 0
        for r_bit, bit in enumerate(s):
            if bit:
                idx += (1 << r_bit)
        error_pos = idx - 1          # 0‑индексация
        pos_valid = 0 <= error_pos < n
        binary_str = ''.join(str(bit) for bit in reversed(s.tolist()))
        if pos_valid and np.array_equal(H[:, error_pos], s):
            loc_desc = (
                f"Синдром не нулевой. Число ${binary_str}_{{2}} = {idx}_{{10}}$ (LSB‑first). "
                f"Это номер столбца $H$ (1‑индексация). Столбец ${idx}$ соответствует "
                f"позиции **{error_pos}** (0‑индексация)."
            )
        else:
            loc_desc = (
                f"Синдром не нулевой, но его значение ${idx}$ не соответствует ни одному "
                f"столбцу матрицы $H$ (все столбцы — числа от 1 до {n}). "
                "Ошибка не может быть исправлена."
            )
            error_pos = "uncorrectable"
    else:
        loc_desc = "Синдром равен нулю — ошибок не обнаружено."

    steps.append(Step(
        "bit",
        "Локализация ошибки",
        {
            "error_pos": error_pos,
            "received": received.tolist(),
            "syndrome": s.tolist(),
            "m": m,
            "description": loc_desc,
        }
    ))

    # Шаг 4: Исправление ошибки и результат
    if error_pos is not None and error_pos != "uncorrectable":
        corrected = received.copy()
        corrected[error_pos] ^= 1
        pos = info_positions(m)
        info_bits = corrected[pos]
        decoded_str = ''.join(str(b) for b in info_bits)

        # Проверка соответствия исходному сообщению
        success = True
        if original_message is not None and decoded_str != original_message:
            success = False
            corr_desc = (
                f"Инвертируем $r_{{{error_pos}}}$: было {received[error_pos]} → "
                f"стало {corrected[error_pos]}.\n"
                f"Исправленное слово: $({' '.join(str(b) for b in corrected)})$.\n\n"
                f"Извлекаем информационные биты: **{decoded_str}**.\n"
                f"**Ошибка!** Полученное сообщение не совпадает с исходным (**{original_message}**). "
                f"Вероятно, произошло более одной ошибки — код не смог их исправить."
            )
        else:
            corr_desc = (
                f"Инвертируем $r_{{{error_pos}}}$: было {received[error_pos]} → "
                f"стало {corrected[error_pos]}.\n"
                f"Исправленное слово: $({' '.join(str(b) for b in corrected)})$.\n\n"
                f"Извлекаем информационные биты с позиций {pos} (0‑индексация): "
                f"${' '.join(str(b) for b in info_bits)} \\to$ сообщение "
                f"**{decoded_str}**."
            )

        steps.append(Step(
            "result",
            "Исправление ошибки и результат",
            {
                "corrected": corrected,
                "original_length": k,
                "info_bits": info_bits,
                "description": corr_desc,
                "success": success,
                "decoded_str": decoded_str,
            }
        ))

    elif error_pos is None:
        # Синдром нулевой — ошибок не обнаружено
        pos = info_positions(m)
        info_bits = received[pos]
        decoded_str = ''.join(str(b) for b in info_bits)

        success = True
        if original_message is not None and decoded_str != original_message:
            success = False
            desc = (
                f"Синдром равен нулю — ошибок не обнаружено.\n"
                f"Однако выделенное сообщение **{decoded_str}** не совпадает с исходным "
                f"**{original_message}**. Это означает, что в принятом слове произошли ошибки, "
                f"которые код не смог обнаружить (например, чётное число ошибок)."
            )
        else:
            desc = "Ошибок нет, информационные биты выделены успешно."

        steps.append(Step(
            "result",
            "Результат",
            {
                "corrected": received,
                "original_length": k,
                "info_bits": info_bits,
                "description": desc,
                "success": success,
                "decoded_str": decoded_str,
            }
        ))

    else:
        # uncorrectable — уже было, оставляем как есть
        steps.append(Step(
            "result",
            "Ошибка",
            {
                "description": "Неисправимая ошибка: синдром не соответствует ни одному столбцу.",
                "success": False,
            }
        ))

    return steps


def explain_hamming_encode(m, message_bits):
    """
    Генерирует шаги, объясняющие процесс кодирования кодом Хэмминга.
    message_bits – numpy‑массив информационных бит (длина k).
    """
    G, H, n, k = hamming_general_matrices(m)
    # Позиции проверочных бит (степени двойки, 0‑индексация)
    check_pos = [(1 << r) - 1 for r in range(m)]  # [0,1,3] для m=3
    info_pos  = [j for j in range(n) if j not in check_pos]

    steps = []

    # Шаг 2: Система уравнений для проверочных битов
    eq_lines = []
    for r in range(m):
        terms = []
        for j in range(n):
            if H[r, j] == 1:
                terms.append(f"c_{{{j}}}")
        eq_lines.append(f"{' + '.join(terms)} = 0")
    eq_system = r"\left\{ \begin{array}{r}" + r" \\ ".join(eq_lines) + r"\end{array} \right."

    check_expr_lines = []
    for r, cp in enumerate(check_pos):
        xor_terms = [f"c_{{{j}}}" for j in range(n) if H[r, j] == 1 and j != cp]
        check_expr_lines.append(f"c_{{{cp}}} = " + r" \oplus ".join(xor_terms))

    steps.append(Step(
        "text",
        "Система уравнений для проверочных битов",
        {"description": (
            f"Условие $H c^{{\\top}} = 0$ даёт $m$ уравнений (сложение по модулю 2):\n\n"
            f"$${eq_system}$$\n\n"
            f"Здесь $c_{{{check_pos}}}$ — проверочные биты, остальные — информационные.\n\n"
            f"Выражаем проверочные биты:\n\n"
            + "\n\n".join(f"$${expr}$$" for expr in check_expr_lines)
        )}
    ))

    # Шаг 3: Конкретный пример вычисления проверочных битов
    codeword = np.zeros(n, dtype=int)
    for idx, pos in enumerate(info_pos):
        codeword[pos] = message_bits[idx]

    for r, cp in enumerate(check_pos):
        bit = 0
        for j in range(n):
            if H[r, j] == 1 and j != cp:
                bit ^= codeword[j]
        codeword[cp] = bit

    info_bits_str = ", ".join(f"c_{{{p}}}={codeword[p]}" for p in info_pos)
    calc_lines = [
        f"Берём информационные биты из сообщения: ${info_bits_str}$.",
        "Вычисляем:"
    ]
    for r, cp in enumerate(check_pos):
        terms = [f"c_{{{j}}}={codeword[j]}" for j in range(n) if H[r, j] == 1 and j != cp]
        xor_str = " \\oplus ".join(terms)
        calc_lines.append(f"$$c_{{{cp}}} = {xor_str} = {codeword[cp]}$$")

    calc_lines.append(
        f"\nКодовое слово (по порядку позиций $0\\ldots{n-1}$):\n"
        f"$$[c_0, c_1, \\dots, c_{{{n-1}}}] = [{', '.join(str(codeword[j]) for j in range(n))}]$$"
    )

    steps.append(Step(
        "calc",
        "Вычисление проверочных битов",
        {
            "description": "\n\n".join(calc_lines),
            "formula": None,
            "received": None,
            "syndrome": None,
        }
    ))

    return steps