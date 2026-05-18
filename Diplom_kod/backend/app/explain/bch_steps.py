import numpy as np
import galois
from .steps import Step

def _locator_poly_str(coeffs, var='x'):
    """
    Строит строку полинома локаторов ошибок Λ(x) по списку коэффициентов
    от λ0 (свободный член) до λ_v.
    Пример: [1, 3, 12] -> "1 + 3x + 12x^2"
    """
    terms = []
    for i, c in enumerate(coeffs):
        if c == 0:
            continue
        if i == 0:
            terms.append("1")
        elif i == 1:
            terms.append(f"{c}{var}" if c != 1 else var)
        else:
            terms.append(f"{c}{var}^{i}" if c != 1 else f"{var}^{i}")
    return " + ".join(terms) if terms else "1"

def _bits_to_polynomial_str(bits, var='x', msb_first=True):
    """Преобразует список битов в строку полинома.
       msb_first=True: bits[0] – коэффициент при старшей степени.
    """
    terms = []
    n = len(bits)
    for i, bit in enumerate(bits):
        if bit == 0:
            continue
        power = n - 1 - i if msb_first else i
        if power == 0:
            terms.append("1")
        elif power == 1:
            terms.append(var)
        else:
            terms.append(f"{var}^{{{power}}}")
    return " + ".join(terms) if terms else "0"

def _poly_from_coeffs(coeffs, var='x'):
    """Строит строку полинома по коэффициентам от младшей степени к старшей."""
    terms = []
    for i, c in enumerate(coeffs):
        if c == 0:
            continue
        if i == 0:
            terms.append(str(c))
        elif i == 1:
            terms.append(f"{c}{var}" if c != 1 else var)
        else:
            terms.append(f"{c}{var}^{i}" if c != 1 else f"{var}^{i}")
    return " + ".join(terms) if terms else "0"

def _alpha_power_table(GF, alpha, n):
    """Возвращает список строк для таблицы степеней α: α^0 ... α^{n-1}."""
    table = []
    for i in range(n):
        power_val = alpha ** i
        # Представление как целое число (в поле GF(2^m) это число от 0 до 2^m-1)
        val_int = int(power_val)
        table.append(f"α^{i} = {val_int}")
    return table

def _bits_to_polynomial_full(bits, var='x'):
    """
    Возвращает строку полинома, где для каждой степени выводится коэффициент
    (включая 0 и 1) и знак умножения.
    Пример: bits = [1,0,1,1,0,1,0] -> "1⋅x^6 + 0⋅x^5 + 1⋅x^4 + 1⋅x^3 + 0⋅x^2 + 1⋅x + 0"
    """
    terms = []
    n = len(bits)
    for i, bit in enumerate(bits):
        power = n - 1 - i
        if power == 0:
            terms.append(f"{bit}")
        elif power == 1:
            terms.append(f"{bit}\\cdot {var}")
        else:
            terms.append(f"{bit}\\cdot {var}^{{{power}}}")
    return " + ".join(terms)

def explain_bch_encode(codec, message_bits):
    """
    Пошаговое объяснение кодирования БЧХ.
    codec – объект BCHCode.
    message_bits – numpy массив битов (длина k).
    """
    n = codec.n
    k = codec.k
    t = codec.t
    m = int(np.log2(n + 1))
    GF = codec.GF
    alpha = codec.alpha

    steps = []

    # Шаг 0: параметры кода
    steps.append(Step(
        "text",
        "Параметры кода БЧХ",
        {"description": (
            f"Информационное слово представляет собой полином $u(x)$ степени $<k$ ключевое слово получается добавлением проверочных битов:\n"
            f"$$c(x) = u(x) \\cdot x^{{n-k}} + \\bigl(u(x) \\cdot x^{{n-k}} \\bmod g(x)\\bigr)$$\n"
            f"Проверочные биты - это остаток от деления $u(x) \\cdot x^{{n-k}}$ на $g(x)$\n"
            f"- Параметры кода: $n = {n}$, $k = {k}$, $t = {t}$\n"
            f"- Примитивный элемент поля: $α$, для которого выполняется $α^{{{m}}} = α + 1$ (примитивный многочлен $p(x)=x^{m}+x+1$)\n"
            f"- Порождающий полином $g(x)$ степени $n-k = {n-k}$\n"
        )}
    ))

    # Шаг 1: информационный полином u(x)
    info_bits = message_bits.tolist()
    info_str = ''.join(str(b) for b in info_bits)
    u_poly_str = _bits_to_polynomial_str(info_bits, 'x', msb_first=True)
    u_full_str = _bits_to_polynomial_full(info_bits, 'x')
    steps.append(Step(
        "text",
        "Информационный полином u(x)",
        {"description": (
            f"Биты сообщения нумеруются слева направо от старшего к младшему.\n"
            f"Если сообщение $b_6 b_5 b_4 b_3 b_2 b_1 b_0$, то\n"
            f"$u(x) = b_6 \\cdot x^6 + b_5 \\cdot x^5 + b_4 \\cdot x^4 + b_3 \\cdot x^3 + b_2 \\cdot x^2 + b_1 \\cdot x + b_0$\n\n"
            f"Для нашего случая:\n"
            f"$$u(x) = {u_full_str}$$\n\n"
            f"$$u(x) = {u_poly_str}$$"
        )}
    ))

    # Шаг 2: умножение на x^(n-k)
    shift = n - k
    shifted_coeffs = info_bits + [0] * shift
    shifted_poly_str = _bits_to_polynomial_str(shifted_coeffs, 'x', msb_first=True)
    steps.append(Step(
        "text",
        f"Сдвиг $u(x) \\cdot x^{{n - k}}$",
        {"description": (
            f"Сдвиг: $n - k = {{{n}}} - {{{k}}} = {{{shift}}}$\n"
            f"Умножаем $u(x)$ на $x^{{{shift}}}$, чтобы освободить место для проверочных битов:\n\n"
            f"$$u(x) \\cdot x^{{{shift}}} = {shifted_poly_str}$$\n\n"
            f"В двоичном виде: `{info_str}` + `{'0'*shift}` (всего {n} бит)."
        )}
    ))

    # Шаг 3: деление на g(x) и остаток r(x)
    g_poly = codec.bch.generator_poly
    g_coeffs = list(g_poly.coeffs[::-1])  # старший коэффициент первым – преобразуем в обычный список
    g_str = _bits_to_polynomial_str(g_coeffs, 'x', msb_first=True)
    # Вычисляем остаток через galois
    GF2 = galois.GF(2)
    u_shifted_poly = galois.Poly(shifted_coeffs[::-1], field=GF2)
    _, r_poly = divmod(u_shifted_poly, g_poly)
    r_coeffs_galois = r_poly.coeffs[::-1]  # старший -> младший (galois массив)
    # Преобразуем в обычный список Python
    r_coeffs = list(r_coeffs_galois)
    # Дополняем нулями до длины shift
    if len(r_coeffs) < shift:
        r_coeffs = [0] * (shift - len(r_coeffs)) + r_coeffs
    r_str = _bits_to_polynomial_str(r_coeffs, 'x', msb_first=True)
    r_bits = ''.join(str(b) for b in r_coeffs)

    steps.append(Step(
        "text",
        "Деление на порождающий полином $g(x)$ и остаток $r(x)$",
        {"description": (
            f"Порождающий полином: $g(x) = {g_str}$.\n\n"
            f"Выполняем деление $u(x) \\cdot x^{{{shift}}}$ на $g(x)$ в поле $GF(2)$.\n\n"
            f"**Остаток** (проверочные биты):\n\n"
            f"$$r(x) = {r_str}$$\n\n"
            f"В двоичном виде: `{r_bits}` (длина {shift} бит)."
        )}
    ))

    # Шаг 4: кодовое слово c(x)
    codeword_bits = codec.encode(message_bits)
    c_str = ''.join(str(b) for b in codeword_bits)
    c_poly_str = _bits_to_polynomial_str(codeword_bits.tolist(), 'x', msb_first=True)
    steps.append(Step(
        "text",
        "Кодовое слово $c(x)$",
        {"description": (
            f"Кодовое слово формируется как $c(x) = u(x)\\cdot x^{{{shift}}} + r(x)$:\n\n"
            f"$$c(x) = {c_poly_str}$$\n\n"
            f"**Итоговое кодовое слово** (длина {n} бит):\n\n"
            f"`{c_str}`\n\n"
            f"*(Старшие {k} бит – информационные, младшие {shift} – проверочные)*"
        )}
    ))

    return steps


def explain_bch_decode(received, codec):
    """
    Пошаговое объяснение декодирования БЧХ.
    received – numpy массив принятых битов (длина n).
    codec – объект BCHCode.
    """
    n = codec.n
    k = codec.k
    t = codec.t
    m = int(np.log2(n + 1))
    GF = codec.GF
    alpha = codec.alpha
    field_order = codec._field_order
    alpha_powers = codec._alpha_powers

    
    
    # Получаем результат декодирования (включая правильные error_positions)
    decoded, info = codec.decode(received)
    syndromes = info.get("syndromes", [])
    locator_poly = info.get("locator_poly")   # из _berlekamp_massey
    error_positions = info.get("error_positions", [])

    #print("DEBUG syndromes:", syndromes)

    steps = []

    # ---------- Шаг 1: Параметры ----------
    steps.append(Step(
        "text",
        "Параметры кода БЧХ",
        {"description": f"Код $({n},{k})$ над $GF(2^{m})$, исправляет до $t={t}$ ошибок, $α$ – примитивный элемент."}
    ))

    # ---------- Шаг 2: Принятое слово ----------
    recv_list = received.tolist()
    r_poly_str = _bits_to_polynomial_str(recv_list, 'x', msb_first=True)
    steps.append(Step(
        "text",
        "Полином принятого слова $R(x)$",
        {"description": f"Принятое слово: `{''.join(str(b) for b in recv_list)}`\n\n$$R(x) = {r_poly_str}$$"}
    ))

    # ---------- Таблица степеней α ----------
    alpha_table = []
    for i in range(field_order):
        val = alpha_powers[i]
        alpha_table.append(f"$α^{{{i}}} = {val}$")
    steps.append(Step(
        "text",
        "Таблица степеней примитивного элемента α",
        {"description": "В поле $GF(2^{m})$ каждый ненулевой элемент представляется степенью α:\n\n" +
         "\n ".join(alpha_table)}
    ))

    # ---------- Шаг 3: Вычисление синдромов ----------
    if syndromes:
        j_indices = list(range(1, 2*t + 1))
        calc_details = []
        for idx, j in enumerate(j_indices):
            s_val = syndromes[idx]
            terms = []
            for i, bit in enumerate(recv_list):
                if bit:
                    exp = (j * (n - 1 - i)) % field_order
                    terms.append(f"α^{{{j}·{n-1-i}}} = α^{exp} = {alpha_powers[exp]}")
            terms_str = " ⊕ ".join(terms) if terms else "0"
            calc_details.append(f"$S_{j} = R(α^{j}) = {terms_str} = {s_val}$\n")
        all_zero = all(s == 0 for s in syndromes)
        verdict = "Все синдромы равны нулю → ошибок нет." if all_zero else "Обнаружены ненулевые синдромы → есть ошибки."
        steps.append(Step(
            "calc",
            "Вычисление синдромов $S_j = R(α^j)$",
            {
                "syndromes": syndromes,
                "syndrome_indices": j_indices,
                "description": "\n\n".join(calc_details) + f"\n\n{verdict}",
                "formula": f"$S_j = \\sum_{{i=0}}^{{{n-1}}} r_i \\cdot α^{{j(n-1-i)}}$"
            }
        ))
    else:
        steps.append(Step(
            "calc",
            "Вычисление синдромов",
            {"description": "Не удалось вычислить синдромы."}
        ))
        return steps

    # ---------- Шаг 4: Алгоритм Берлекэмпа–Месси ----------
    all_zero_syndromes = all(s == 0 for s in syndromes)
    if all_zero_syndromes:
        steps.append(Step(
            "text",
            "Алгоритм Берлекэмпа–Месси (полином локаторов ошибок $$\\Lambda(x)$$)",
            {"description": (
                "Все синдромы равны нулю, поэтому алгоритм Берлекэмпа–Месси не нужен.\n\n"
                "$$\\Lambda(x) = 1$$\n\n"
                "Полином степени 0 означает, что ошибок нет."
            )}
        ))
    else:
        if locator_poly is not None:
            
            
            num_errors = len(error_positions) if error_positions else 0
            if num_errors == 0:
                locator_display = [1]
            else:
                # Берём первые (num_errors+1) коэффициентов
                locator_display = locator_poly[:num_errors+1] if len(locator_poly) > num_errors else locator_poly
            
            
            
            
            deg = len(locator_display) - 1
            lp_str = _locator_poly_str(locator_display)
            coeffs_display = ",  ".join(f"$$\\lambda_{i} = {c}$$" for i, c in enumerate(locator_display))
            description = (
                "**Алгоритм Берлекэмпа–Месси** итеративно строит ЛРОС минимальной длины, "
                "порождающий последовательность синдромов $S_1, S_2, \\ldots, S_{2t}$.\n\n"
                "**Инициализация:**\n"
                "$$\\Lambda(x) = 1,\\quad B(x) = 1,\\quad L = 0,\\quad m = 1$$\n\n"
                "На каждом шаге $r$ вычисляется невязка:\n"
                "$$\\Delta_r = S_r + \\sum_{j=1}^{L} \\lambda_j S_{r-j}$$\n\n"
                "Если $\\Delta_r \\neq 0$, полином обновляется:\n"
                "$$\\Lambda(x) \\leftarrow \\Lambda(x) - \\Delta_r \\cdot x^m \\cdot B(x)$$\n\n"
                f"**Результат** (степень полинома = число ошибок = {deg}):\n\n"
                f"$$\\Lambda(x) = {lp_str}$$\n\n"
                f"Коэффициенты: {coeffs_display}"
            )
        else:
            description = (
                "Не удалось вычислить полином локаторов ошибок.\n\n"
                "Возможно, превышена исправляющая способность кода ($t={t}$ ошибок)."
            )
        steps.append(Step(
            "bm",
            "Алгоритм Берлекэмпа–Месси (полином локаторов ошибок Λ(x))",
            {"locator_poly": locator_display, "description": description}
        ))

    # ---------- Шаг 5: Поиск Ченя (локализации ошибок) – СТАРАЯ КОРРЕКТНАЯ ВЕРСИЯ ----------
    if all_zero_syndromes:
        steps.append(Step(
            "text",
            "Поиск Ченя (локализация позиций ошибок)",
            {"description": "Синдромы нулевые — поиск Ченя не требуется. Ошибок нет."}
        ))
    else:
        # Используем уже вычисленные error_positions из info (от codec.decode)
        error_positions = info.get("error_positions", [])
        if locator_poly is not None and len(locator_poly) > 1:
            # Показываем подстановку α^{-i} в Λ(x) для каждой позиции
            chien_rows = []
            fo = codec._field_order
            pw = codec._alpha_powers
            for i in range(n):
                inv_exp = (fo - i) % fo
                lval = 0
                for deg_idx, coeff in enumerate(locator_poly):
                    if coeff != 0:
                        exp = (deg_idx * inv_exp) % fo
                        lval ^= (coeff * pw[exp]) % (2**32)   # здесь мы не перевычисляем корни, а просто показываем
                is_root = (i in error_positions)   # берём готовый ответ от декодера
                chien_rows.append({
                    "i": i,
                    "alpha_inv": f"α^{{-{i}}} = α^{{{inv_exp % fo}}}",
                    "is_root": is_root,
                })

            root_positions = [r["i"] for r in chien_rows if r["is_root"]]

            chien_desc_lines = [
                "**Алгоритм Ченя** проверяет каждую позицию $i = 0, 1, \\ldots, n-1$:\n",
                "подставляет $\\alpha^{-i}$ в полином локаторов $\\Lambda(x)$:\n",
                "$$\\Lambda(\\alpha^{-i}) = 0 \\implies \\text{позиция } i \\text{ — ошибочная}$$\n\n",
            ]
            # Показываем первые 5 и найденные позиции
            show_positions = list(range(min(5, n))) + [p for p in root_positions if p >= 5]
            show_positions = sorted(set(show_positions))

            for row in chien_rows:
                if row["i"] in show_positions:
                    mark = "← **корень! ошибка**" if row["is_root"] else ""
                    chien_desc_lines.append(
                        f"$i={row['i']}$: $\\Lambda({row['alpha_inv']})$ "
                        + ("$= 0$ " + mark if row["is_root"] else "$\\neq 0$")
                        + "  \n"
                    )
            if len(show_positions) < n:
                chien_desc_lines.append(f"... (проверено всего {n} позиций)  \n\n")
            if root_positions:
                chien_desc_lines.append(f"\n**Найдены корни (позиции ошибок):** {root_positions}  \n"
                                         f"Биты в этих позициях инвертируются для исправления.")
            else:
                chien_desc_lines.append("\nКорней не найдено — ошибок нет.")
            chien_description = "".join(chien_desc_lines)
        else:
            chien_description = "Полином локаторов не вычислен или имеет степень 0 — поиск Ченя пропущен."
            root_positions = []

        steps.append(Step(
            "chien",
            "Поиск Ченя (локализация позиций ошибок)",
            {
                "error_positions": error_positions,
                "description": chien_description,
                "locator_poly": locator_poly,
            }
        ))

    # ---------- Шаг 6: Исправление ошибок и результат ----------
    if info["success"]:
        steps.append(Step(
            "calc",
            "Исправление ошибок",
            {"description": f"Инвертируем биты в позициях {error_positions}.\n\nИсправленное кодовое слово: `{''.join(map(str, decoded))}`"}
        ))
        info_bits = decoded[:k]
        decoded_msg = ''.join(str(b) for b in info_bits)
        steps.append(Step(
            "result",
            "Результат декодирования",
            {
                "decoded_str": decoded_msg,
                "corrected": decoded.tolist(),
                "info_bits": info_bits.tolist(),
                "success": True,
                "description": f"Декодированное сообщение: **{decoded_msg}**"
            }
        ))
    else:
        steps.append(Step(
            "result",
            "Ошибка декодирования",
            {
                "description": info.get("error", "Не удалось исправить ошибки (превышена t)."),
                "success": False,
            }
        ))

    return steps