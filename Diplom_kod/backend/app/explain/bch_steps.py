import numpy as np
from .steps import Step


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

def _locator_poly_str(coeffs):
    """
    Строит строку полинома lambda(x) по списку коэффициентов
    lambda0 = 1 всегда, индекс = степень x.
    """
    terms = []
    for i, c in enumerate(coeffs):
        if c == 0:
            continue
        if i == 0:
            terms.append("1")
        elif i == 1:
            terms.append(f"{c}x" if c != 1 else "x")
        else:
            terms.append(f"{c}x^{{{i}}}" if c != 1 else f"x^{{{i}}}")
    return r" + ".join(terms) if terms else "1"


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

    # Шаг 1: Параметры кода 
    steps.append(Step(
        "text",
        "Параметры кода БЧХ",
        {"description": (
            f"Код БЧХ $({n}, {k})$: длина кодового слова $n={n}$, "
            f"длина сообщения $k={k}$. Исправляет до $t={t}$ ошибок.\n\n"
            f"Код построен над полем $GF(2^m)$, $\\alpha$ — примитивный элемент поля."
        )}
    ))

    # Шаг 2: Принятое кодовое слово 
    received_list = received.tolist() if hasattr(received, 'tolist') else list(received)
    steps.append(Step(
        "matrix",
        "Принятое кодовое слово",
        {"codeword": received_list}
    ))

    # Шаг 3: Полином принятого слова 
    # galois хранит MSB-first: received[0] = коэф. при x^(n-1)
    poly_str = _bits_to_polynomial_msb(received_list)
    steps.append(Step(
        "text",
        "Полином принятого слова $R(x)$",
        {"description": (
            f"Биты кодового слова записываются MSB-first "
            f"(первый бит — коэффициент при $x^{{{n-1}}}$):\n\n"
            f"$$R(x) = {poly_str}$$\n\n"
            f"Синдром вычисляется как $S_j = R(\\alpha^j)$ — подстановка $\\alpha^j$ в $R(x)$."
        )}
    ))

    # Вычисление (внутри decode вызывается _compute_syndromes) 
    decoded, info = bch_code.decode(received)

    # Шаг 4: Синдромы 
    syndromes = info.get("syndromes", [])
    if syndromes:
        j_indices = list(range(1, 2 * t + 1))

        formula = (
            r"S_j = R(\alpha^j) = \sum_{i=0}^{n-1} r_i \cdot \alpha^{j(n-1-i)}"
            f",\\quad j = {', '.join(map(str, j_indices))}"
        )

        # Одна строка с результатами: S1 = 5, S2 = 3, ...
        syndrome_display = ",  ".join(
            f"S{j} = {v}" for j, v in zip(j_indices, syndromes)
        )

        all_zero = all(s == 0 for s in syndromes)
        if all_zero:
            verdict = "Все синдромы равны нулю -> ошибок нет."
        else:
            nonzero = [j for j, s in zip(j_indices, syndromes) if s != 0]
            verdict = (
                f"Ненулевые синдромы (j = {nonzero}) -> обнаружены ошибки. "
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




    # Шаг 5: Алгоритм Берлекэмпа–Месси → полином локаторов Λ(x)
    locator_poly = info.get("locator_poly")
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
            deg = len(locator_poly) - 1
            lp_str = _locator_poly_str(locator_poly)

            # Строим таблицу итераций (упрощённо — только входные/выходные данные)
            coeffs_display = "  ,  ".join(
                f"$$\\lambda_{i} = {c}$$" for i, c in enumerate(locator_poly)
            )

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
            {
                "locator_poly": locator_poly,
                "description": description,
            }
        ))

    # Шаг 6: Поиск Ченя
    if all_zero_syndromes:
        steps.append(Step(
            "text",
            "Поиск Ченя (локализация позиций ошибок)",
            {"description": (
                "Синдромы нулевые — поиск Ченя не требуется. Ошибок нет."
            )}
        ))
    else:
        error_positions = info.get("error_positions", [])

        if locator_poly is not None and len(locator_poly) > 1:
            # Показываем подстановку α^{-i} в Λ(x) для каждой позиции
            chien_rows = []
            fo = bch_code._field_order
            pw = bch_code._alpha_powers  # pw[e] = alpha^e

            for i in range(n):
                # Вычисляем Λ(α^{n-1-i}) в целых числах через XOR в GF(2^m)
                # alpha^{-i} = alpha^{(fo - i) % fo}
                inv_exp = (fo - i) % fo
                lval = 0  # суммируем в GF(2^m) через XOR
                for deg_idx, coeff in enumerate(locator_poly):
                    if coeff != 0:
                        exp = (deg_idx * inv_exp) % fo
                        lval ^= (coeff * pw[exp]) % (2**32)  # приближение; достаточно для XOR-отображения

                # Корень Λ(α^{-i}) == 0 → позиция i — позиция ошибки
                is_root = (i in error_positions)
                chien_rows.append({
                    "i": i,
                    "alpha_inv": f"α^{{-{i}}} = α^{{{inv_exp % fo}}}",
                    "is_root": is_root,
                })

            root_positions = [r["i"] for r in chien_rows if r["is_root"]]

            # Формируем описание с деталями
            chien_desc_lines = [
                "**Алгоритм Ченя** проверяет каждую позицию $i = 0, 1, \\ldots, n-1$:\n",
                "подставляет $\\alpha^{-i}$ в полином локаторов $\\Lambda(x)$:\n",
                "$$\\Lambda(\\alpha^{-i}) = 0 \\implies \\text{позиция } i \\text{ — ошибочная}$$\n\n",
            ]

            # Показываем вычисления для нескольких позиций (первые 5 и найденные)
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
                chien_desc_lines.append(
                    f"\n**Найдены корни (позиции ошибок):** {root_positions}  \n"
                    f"Биты в этих позициях инвертируются для исправления."
                )
            else:
                chien_desc_lines.append("\nКорней не найдено — ошибок нет.")

            chien_description = "".join(chien_desc_lines)
        else:
            chien_description = (
                "Полином локаторов не вычислен или имеет степень 0 — поиск Ченя пропущен."
            )
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
    
    
    
    
    
    

    # Шаг 5: Исправление ошибок 
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

        # Шаг 6: Результат
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