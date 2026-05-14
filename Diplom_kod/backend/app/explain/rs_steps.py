import numpy as np
import galois
from .steps import Step
from app.core.reed_solomon import (
    rs_make,
    rs_compute_syndromes_gf,
    _field_order,
    rs_encode_bytes
)


# ──────────────────────────────────────────────────────────────────
#  Вспомогательные функции
# ──────────────────────────────────────────────────────────────────

def _poly_str(coeffs_asc, var='x'):
    """
    Строит строку полинома по коэффициентам в восходящем порядке (coeffs_asc[i] – при x^i).
    Пример: [1, 2, 0, 3] → '1 + 2x + 3x^{3}'
    """
    terms = []
    for i, c in enumerate(coeffs_asc):
        if c == 0:
            continue
        if i == 0:
            terms.append(str(c))
        elif i == 1:
            terms.append(f"{c}{var}" if c != 1 else var)
        else:
            terms.append(f"{c}{var}^{{{i}}}" if c != 1 else f"{var}^{{{i}}}")
    return " + ".join(terms) if terms else "0"


def _poly_str_desc(coeffs_desc, var='x'):
    """
    Строит строку полинома по убывающим коэффициентам (coeffs_desc[0] – старший).
    """
    n = len(coeffs_desc) - 1
    terms = []
    for i, c in enumerate(coeffs_desc):
        deg = n - i
        if c == 0:
            continue
        if deg == 0:
            terms.append(str(c))
        elif deg == 1:
            terms.append(f"{c}{var}" if c != 1 else var)
        else:
            terms.append(f"{c}{var}^{{{deg}}}" if c != 1 else f"{var}^{{{deg}}}")
    return " + ".join(terms) if terms else "0"


# ──────────────────────────────────────────────────────────────────
#  Кодирование
# ──────────────────────────────────────────────────────────────────

def explain_rs_encode(message_str: str, n: int, k: int, m: int):
    """
    Пошаговое объяснение кодирования RS.
    Возвращает (steps, codeword_as_int_list).
    """
    GF, RS = rs_make(n, k, m)
    alpha = GF.primitive_element

    # Подготовка сообщения
    msg_bytes = message_str.encode("utf-8")[:k]
    msg_bytes = msg_bytes.ljust(k, b'\x00')
    msg_symbols = list(msg_bytes)     # список int 0-255

    steps = []

    # ── Шаг 1: u(x) ──────────────────────────────────────────────
    preview = msg_symbols[:20]
    preview_str = "[" + ", ".join(str(s) for s in preview)
    if k > 20:
        preview_str += ", …"
    preview_str += "]"

    u_poly_str = _poly_str(list(reversed(msg_symbols)), 'x')  # старший при x^{k-1}
    steps.append(Step(
        "text",
        "Представление сообщения как полинома $u(x)$",
        {"description": (
            f"Сообщение `'{message_str[:40]}{'…' if len(message_str) > 40 else ''}'` "
            f"представляется как {k} байт (незаполненные позиции — нули).\n\n"
            f"Символы (десятичные): {preview_str}\n\n"
            f"Полином:\n\n"
            f"$$u(x) = \\sum_{{i=0}}^{{k-1}} u_i\\cdot x^{{k-1-i}},\\quad \\deg u(x) < k = {k}$$"
        )}
    ))

    # ── Шаг 2: u(x)·x^{n-k} ──────────────────────────────────────
    shift = n - k
    steps.append(Step(
        "text",
        f"Умножение на $x^{{n-k}} = x^{{{shift}}}$",
        {"description": (
            f"Умножаем $u(x)$ на $x^{{{shift}}}$, чтобы освободить {shift} позиций для проверочных символов:\n\n"
            f"$$u(x)\\cdot x^{{{shift}}} — \\text{{полином степени}} < {k + shift} = {n}$$\n\n"
            f"В виде массива: к символам сообщения дописываем {shift} нулей справа."
        )}
    ))

    # ── Шаг 3: g(x) ──────────────────────────────────────────────
    g_poly = RS.generator_poly               # galois.Poly, убывающий порядок
    g_coeffs_desc = [int(c) for c in g_poly.coeffs]
    g_poly_str = _poly_str_desc(g_coeffs_desc, 'x')

    steps.append(Step(
        "text",
        "Порождающий полином $g(x)$",
        {"description": (
            f"Порождающий полином — произведение {shift} множителей:\n\n"
            f"$$g(x) = \\prod_{{j=1}}^{{n-k={shift}}} (x - \\alpha^j)$$\n\n"
            f"Степень $g(x) = n - k = {shift}$, исправляет до $t = {shift // 2}$ ошибок.\n\n"
            f"$$g(x) = {g_poly_str}$$\n\n"
            f"Коэффициенты (от старшего): "
            f"$[{', '.join(str(c) for c in g_coeffs_desc[:16])}{'…' if len(g_coeffs_desc) > 16 else ''}]$"
        )}
    ))

    # ── Шаг 4: деление, остаток r(x) ─────────────────────────────
    msg_gf = GF(np.array(msg_symbols, dtype=int))
    #codeword_gf = RS.encode(msg_gf)
    #codeword = [int(c) for c in codeword_gf]
    codeword = list(rs_encode_bytes(msg_bytes, RS))
    remainder = codeword[k:]          # n-k проверочных символов

    r_poly_str = _poly_str(list(reversed(remainder)), 'x')

    steps.append(Step(
        "text",
        "Деление $u(x)\\cdot x^{n-k}$ на $g(x)$, остаток $r(x)$",
        {"description": (
            f"Выполняем полиномиальное деление в $GF(2^{{{m}}})$:\n\n"
            f"$$u(x)\\cdot x^{{{shift}}} = q(x)\\cdot g(x) + r(x),\\quad \\deg r(x) < {shift}$$\n\n"
            f"**Остаток** $r(x)$ — {shift} проверочных символов:\n\n"
            f"$$r(x) = {r_poly_str}$$\n\n"
            f"Проверочные символы: [{', '.join(str(c) for c in remainder)}]"
        )}
    ))

    # ── Шаг 5: кодовое слово ─────────────────────────────────────
    steps.append(Step(
        "text",
        "Кодовое слово $c(x)$",
        {"description": (
            f"$$c(x) = u(x)\\cdot x^{{{shift}}} + r(x)$$\n\n"
            f"**Систематический вид:**\n"
            f"- Первые $k = {k}$ символов — информационные (исходное сообщение)\n"
            f"- Последние $n - k = {shift}$ символов — проверочные\n\n"
            f"Информационные: $[{', '.join(str(c) for c in codeword[:15])}{'…' if k > 15 else ''}]$\n\n"
            f"Проверочные: [{', '.join(str(c) for c in remainder)}]\n\n"
            f"**Длина кодового слова: {n} символов.**"
        )}
    ))

    return steps, codeword


# ──────────────────────────────────────────────────────────────────
#  Декодирование
# ──────────────────────────────────────────────────────────────────

def explain_rs_decode(received, n: int, k: int, m: int):
    """
    Пошаговое объяснение декодирования RS с использованием встроенного декодера galois.
    Все величины ошибок и позиции берутся из библиотечного декодирования.
    """
    from app.core.reed_solomon import rs_decode_symbols
    GF, RS = rs_make(n, k, m)
    alpha = GF.primitive_element
    t = (n - k) // 2

    steps = []

    # ── Шаг 1: Синдромы ──────────────────────────────────────────
    syndromes = rs_compute_syndromes_gf(received, GF, n, k)
    syn_ints = [int(s) for s in syndromes]
    all_zero = all(v == 0 for v in syn_ints)

    syn_preview = ", ".join(
        f"$S_{{{j+1}}} = {syn_ints[j]}$" for j in range(min(8, len(syn_ints)))
    )
    if len(syn_ints) > 8:
        syn_preview += ", …"

    steps.append(Step(
        "rs_syndromes",
        "Вычисление синдромов",
        {
            "syndromes": syn_ints,
            "all_zero": all_zero,
            "description": (
                f"$$S_j = r(\\alpha^j) = \\sum_{{i=0}}^{{n-1}} r_i \\cdot \\alpha^{{j \\cdot i}},\\quad j = 1,\\ldots,{n-k}$$\n\n"
                + syn_preview + "\n\n"
                + ("**Все синдромы равны 0 — ошибок нет!**" if all_zero
                   else f"Обнаружены ненулевые синдромы — **есть ошибки**.")
            )
        }
    ))

    if all_zero:
        info_symbols = [int(c) for c in GF(np.array(received, dtype=int))[:k]]
        decoded_text = "".join(chr(b) for b in info_symbols if 32 <= b < 127)
        steps.append(Step(
            "result",
            "Результат декодирования",
            {
                "corrected": list(received)[:k],
                "decoded": decoded_text,
                "success": True,
                "description": "Ошибок нет. Информационные символы извлечены успешно."
            }
        ))
        return steps, decoded_text, True

    # ── Встроенное декодирование для получения реальных ошибок ──
    try:
        dec_msg = rs_decode_symbols(received, RS)          # информационные символы (k)
        corrected_cw = RS.encode(GF(dec_msg))              # полное исправленное кодовое слово
        corrected_ints = [int(c) for c in corrected_cw]
    except Exception as e:
        steps.append(Step(
            "result",
            "Ошибка декодирования",
            {"success": False, "description": str(e)}
        ))
        return steps, "", False

    # Вычисляем позиции и величины ошибок как разность с принятым словом
    error_positions = [i for i in range(n) if int(received[i]) != corrected_ints[i]]
    error_magnitudes = [(int(received[i]) ^ corrected_ints[i]) for i in error_positions]
    L = len(error_positions)

    # ── Шаг 2: Полином локаторов (строим реальный) ─────────────
    # Λ(x) = ∏ (1 - X_i·x), где X_i = α^{pos}
    C_poly = galois.Poly([1], field=GF)
    for pos in error_positions:
        X = alpha ** pos
        factor = galois.Poly([-X, 1], field=GF)   # соответствует 1 - X·x
        C_poly = C_poly * factor
    coeffs_desc = [int(c) for c in C_poly.coeffs]   # убывающий порядок
    coeffs_asc = list(reversed(coeffs_desc))        # восходящий: [λ0, λ1, …, λL]
    lambda_str = _poly_str(coeffs_asc, 'x')

    steps.append(Step(
        "rs_bm",
        "Алгоритм Берлекэмпа–Месси (полином локаторов $\\Lambda(x)$)",
        {
            "locator_poly": coeffs_asc,
            "L": L,
            "iterations": [],
            "description": (
                "Алгоритм итеративно строит РСЛОС минимальной длины, "
                "порождающий последовательность синдромов.\n\n"
                "**Инициализация:** $\\Lambda(x) = 1,\\; B(x) = 1,\\; L = 0$\n\n"
                "На шаге $r$ вычисляется невязка:\n\n"
                "$$\\Delta_r = S_r + \\sum_{i=1}^{L} \\lambda_i \\cdot S_{r-i}$$\n\n"
                f"После {len(syndromes)} итераций:\n\n"
                f"$$\\Lambda(x) = {lambda_str}$$\n\n"
                f"Степень $L = {L}$ — **число ошибок**."
                + (f"\n\n$L = {L} > t = {t}$ — декодирование невозможно!" if L > t else "")
            )
        }
    ))

    if L > t:
        steps.append(Step(
            "result",
            "Ошибка декодирования",
            {
                "success": False,
                "description": f"Степень полинома локаторов L = {L} > t = {t}. Слишком много ошибок."
            }
        ))
        return steps, "", False

    # ── Шаг 3: Поиск Ченя (позиции) ─────────────────────────────
    steps.append(Step(
        "rs_chien",
        "Поиск Ченя — локализация позиций ошибок",
        {
            "error_positions": error_positions,
            "chien_preview": [],
            "n": n,
            "description": (
                "Перебираем все позиции $i = 0, 1, \\ldots, n-1$ и проверяем:\n\n"
                "$$\\Lambda(\\alpha^{-i}) = 0 \\implies \\text{позиция } i \\text{ — ошибочная}$$\n\n"
                + (f"**Найденные позиции ошибок:** {error_positions}" if error_positions
                   else "Корней не найдено.")
            )
        }
    ))

    if not error_positions:
        steps.append(Step(
            "result",
            "Ошибка декодирования",
            {
                "success": False,
                "description": "Поиск Ченя не нашёл корней, хотя синдромы ненулевые. Возможно, ошибок больше t."
            }
        ))
        return steps, "", False

    # ── Шаг 4: Алгоритм Форни (величины) ────────────────────────
    forney_rows = [{"pos": p, "magnitude": mag} for p, mag in zip(error_positions, error_magnitudes)]
    steps.append(Step(
        "rs_forney",
        "Алгоритм Форни — вычисление величин ошибок",
        {
            "forney_rows": forney_rows,
            "description": (
                "Вычисляем полином значений ошибок и применяем формулу Форни:\n\n"
                "$$\\Omega(x) = \\Lambda(x) \\cdot S(x) \\bmod x^{2t}$$\n\n"
                "$$e_i = \\frac{\\Omega(\\alpha^{-i})}{\\Lambda'(\\alpha^{-i})}$$\n\n"
                "где $S(x) = S_1 + S_2 x + \\cdots + S_{2t}x^{2t-1}$,\n"
                "$\\Lambda'(x)$ — формальная производная $\\Lambda(x)$ в $GF(2^m)$:\n\n"
                "$$\\Lambda'(x) = \\lambda_1 + \\lambda_3 x^2 + \\lambda_5 x^4 + \\cdots$$"
                "\n\n(В характеристике 2 чётные слагаемые обнуляются.)"
            )
        }
    ))

    # ── Шаг 5: Исправление ошибок ────────────────────────────────
    corrected = corrected_ints
    corr_desc_lines = []
    for pos, mag in zip(error_positions, error_magnitudes):
        old_val = received[pos] if not isinstance(received[pos], int) else received[pos]
        corr_desc_lines.append(
            f"- Позиция {pos}: $r_{{{pos}}} = {old_val}$ ⊕ $e_{{{pos}}} = {mag}$ → ${corrected[pos]}$"
        )
    steps.append(Step(
        "text",
        "Исправление ошибок",
        {"description": (
            "Исправляем ошибки сложением в $GF(2^8)$ (XOR):\n\n"
            f"$$\\hat{{c}}_i = r_i \\oplus e_i$$\n\n"
            + "\n".join(corr_desc_lines)
        )}
    ))

    # ── Шаг 6: Извлечение информационных символов ─────────────────
    info_symbols = [int(c) for c in dec_msg]
    decoded_text = "".join(chr(b) for b in info_symbols if 32 <= b < 127)

    steps.append(Step(
        "result",
        "Извлечение информационных символов",
        {
            "corrected": info_symbols,
            "decoded": decoded_text,
            "success": True,
            "description": (
                f"Берём первые $k = {k}$ символов исправленного кодового слова.\n\n"
                f"Информационные символы: $[{', '.join(str(s) for s in info_symbols[:20])}{'…' if k > 20 else ''}]$\n\n"
                f"**Декодированное сообщение:** `{decoded_text}`"
            )
        }
    ))

    return steps, decoded_text, True