import numpy as np
from .steps import Step
from app.core.convolutional import ConvolutionalCode


def _state_str(state: int, memory: int) -> str:
    """Состояние как двоичная строка, старший бит первым."""
    return format(state, f'0{memory}b')


def _hamming_dist(a, b) -> int:
    return sum(x != y for x, y in zip(a, b))


# ─────────────────────────────────────────────────────────────────────────────
#  КОДИРОВАНИЕ
# ─────────────────────────────────────────────────────────────────────────────

def explain_conv_encode(message, conv_code: ConvolutionalCode):
    """
    Пошаговое объяснение кодирования.
    Возвращает (steps, encoded_array).
    """
    K = conv_code.constraint_length
    memory = conv_code.memory
    rate_den = conv_code.rate_den
    gens = conv_code.generators
    gen_masks = conv_code.gen_masks

    msg_list = list(int(b) for b in message)
    tail = [0] * memory
    full_input = msg_list + tail

    steps = []

    # ── Параметры кодера ───────────────────────────────────────────────────
    output_formulas = []
    for g_idx, mask in enumerate(gen_masks):
        terms = []
        if mask[0] == 1:
            terms.append("вход")
        for r in range(1, K):
            if mask[r] == 1:
                terms.append(f"рег{r}")
        latex_terms = []
        if mask[0] == 1:
            latex_terms.append("\\text{вход}")
        for r in range(1, K):
            if mask[r] == 1:
                latex_terms.append(f"\\text{{рег}}_{r}")
        formula_latex = " \\oplus ".join(latex_terms)
        output_formulas.append(f"$$c_{g_idx} = {formula_latex}$$")

    steps.append(Step(
        "text",
        "Параметры кодера",
        {"description": (
            f"**Длина ограничения:** $K = {K}$\n\n"
            f"**Память:** $m = {memory}$ (ячеек регистра сдвига)\n\n"
            f"**Скорость:** $R = {conv_code.rate_num}/{rate_den}$\n\n"
            f"**Количество состояний:** $2^m = {conv_code.num_states}$\n\n"
            f"**Порождающие полиномы (восьм.):** {gens}\n\n"
            f"**Формулы выходных битов:**\n\n"
            + "\n\n".join(output_formulas)
            + f"\n\n**Начальное состояние регистра:** `{'0' * memory}`\n\n"
            f"**Хвостовые биты:** добавляем {memory} нулей — регистр возвращается в `{'0' * memory}`."
        )}
    ))

    # ── Трассировка регистра ───────────────────────────────────────────────
    trace = []
    state = 0

    for step_i, inp in enumerate(full_input):
        state_bits = [(state >> (memory - 1 - r)) & 1 for r in range(memory)]
        reg_before_str = _state_str(state, memory)

        out = conv_code.outputs[(state, inp)]
        next_state = conv_code.next_states[(state, inp)]
        reg_after_str = _state_str(next_state, memory)

        # Подробные формулы с подстановкой значений
        formulas = []
        for g_idx, mask in enumerate(gen_masks):
            terms_vals = []
            if mask[0] == 1:
                terms_vals.append(str(inp))
            for r in range(1, K):
                if mask[r] == 1:
                    terms_vals.append(str(state_bits[r - 1]))
            formulas.append(" ⊕ ".join(terms_vals) + f" = {out[g_idx]}")

        trace.append({
            "step": step_i + 1,
            "input": inp,
            "is_tail": step_i >= len(msg_list),
            "reg_before": reg_before_str,
            "output": list(out),
            "output_str": "".join(str(b) for b in out),
            "reg_after": reg_after_str,
            "formulas": formulas,
        })

        state = next_state

    # Кодовое слово
    encoded_bits = []
    for row in trace:
        encoded_bits.extend(row["output"])

    pairs = [
        "".join(str(b) for b in encoded_bits[i:i + rate_den])
        for i in range(0, len(encoded_bits), rate_den)
    ]

    steps.append(Step(
        "conv_encode_trace",
        "Пошаговое кодирование (трассировка регистра)",
        {
            "trace": trace,
            "memory": memory,
            "rate_den": rate_den,
            "message_len": len(msg_list),
            "codeword_pairs": pairs,
            "codeword": "".join(str(b) for b in encoded_bits),
            "description": (
                f"Сообщение: `{''.join(str(b) for b in msg_list)}` + "
                f"хвост: `{''.join(str(b) for b in tail)}`\n\n"
                f"Для каждого входного бита вычисляем {rate_den} выходных бита, "
                f"затем сдвигаем регистр (новый бит входит слева)."
            )
        }
    ))

    steps.append(Step(
        "text",
        "Кодовое слово",
        {"description": (
            f"**Кодовое слово** ({len(encoded_bits)} бит):\n\n"
            f"`{''.join(str(b) for b in encoded_bits)}`\n\n"
            f"Разбито на пары: `{' '.join(pairs)}`\n\n"
            f"*(Первые {len(msg_list)} пар — информационные, "
            f"последние {memory} пар — хвостовые)*"
        )}
    ))

    return steps, np.array(encoded_bits, dtype=int)


# ─────────────────────────────────────────────────────────────────────────────
#  ДЕКОДИРОВАНИЕ (ВИТЕРБИ)
# ─────────────────────────────────────────────────────────────────────────────

def explain_conv_decode(received, conv_code: ConvolutionalCode):
    """
    Декодирование Витерби с пошаговой трассировкой.
    Возвращает (steps, decoded_array, info).
    """
    received = np.asarray(received, dtype=int)
    K = conv_code.constraint_length
    memory = conv_code.memory
    rate_den = conv_code.rate_den
    num_states = conv_code.num_states

    remainder = len(received) % rate_den
    if remainder:
        received = np.append(received, [0] * (rate_den - remainder))

    num_steps = len(received) // rate_den
    INF = 10 ** 9

    state_labels = [_state_str(s, memory) for s in range(num_states)]
    steps = []

    # ── Шаг 1: Параметры решётки ───────────────────────────────────────────
    blocks_preview = " | ".join(
        '`' + ''.join(str(b) for b in received[t * rate_den:(t + 1) * rate_den]) + '`'
        for t in range(min(num_steps, 12))
    )
    if num_steps > 12:
        blocks_preview += " | …"

    steps.append(Step(
        "text",
        "Шаг 1: Параметры решётки",
        {"description": (
            f"**Состояния:** {num_states} штук "
            f"({', '.join('`' + l + '`' for l in state_labels)})\n\n"
            f"**Число тактов:** {num_steps} "
            f"(принято {len(received)} бит / {rate_den} = {num_steps} тактов)\n\n"
            f"**Принятая последовательность:** `{''.join(map(str, received))}`\n\n"
            f"По {rate_den} бита на такт: {blocks_preview}\n\n"
            f"Алгоритм Витерби ищет путь с **минимальным суммарным расстоянием Хэмминга**."
        )}
    ))

    # ── Шаг 2: Инициализация ──────────────────────────────────────────────
    metrics = [INF] * num_states
    metrics[0] = 0

    init_desc = "**Начальное состояние** — `" + "0" * memory + "` (регистр обнулён).\n\n"
    for s in range(num_states):
        init_desc += (f"- `{state_labels[s]}`: **метрика = 0**\n"
                      if s == 0 else f"- `{state_labels[s]}`: метрика = ∞\n")

    steps.append(Step("text", "Шаг 2: Инициализация метрик", {"description": init_desc}))

    # ── Шаг 3: Прямой проход Витерби ──────────────────────────────────────
    prev_state_table = [[-1] * num_states for _ in range(num_steps)]
    input_bit_table = [[0] * num_states for _ in range(num_steps)]

    viterbi_steps_data = []

    for t in range(num_steps):
        block = received[t * rate_den:(t + 1) * rate_den]
        block_str = ''.join(str(b) for b in block)
        new_metrics = [INF] * num_states
        transitions = []

        for state in range(num_states):
            if metrics[state] == INF:
                continue
            for inp in [0, 1]:
                nxt = conv_code.next_states[(state, inp)]
                out = conv_code.outputs[(state, inp)]
                hd = _hamming_dist(out, tuple(block))
                candidate = metrics[state] + hd
                transitions.append({
                    "from_state": state,
                    "from_label": state_labels[state],
                    "input": inp,
                    "to_state": nxt,
                    "to_label": state_labels[nxt],
                    "expected": list(out),
                    "expected_str": ''.join(str(b) for b in out),
                    "hd": hd,
                    "old_metric": metrics[state],
                    "candidate": candidate,
                    "survived": False,
                })
                if candidate < new_metrics[nxt]:
                    new_metrics[nxt] = candidate
                    prev_state_table[t][nxt] = state
                    input_bit_table[t][nxt] = inp

        # Помечаем выживших
        for tr in transitions:
            if (tr["candidate"] == new_metrics[tr["to_state"]]
                    and prev_state_table[t][tr["to_state"]] == tr["from_state"]
                    and input_bit_table[t][tr["to_state"]] == tr["input"]):
                tr["survived"] = True

        viterbi_steps_data.append({
            "t": t,
            "received_str": block_str,
            "transitions": transitions,
            "metrics_before": [m if m < INF else None for m in metrics],
            "metrics_after": [m if m < INF else None for m in new_metrics],
        })

        metrics = new_metrics

    steps.append(Step(
        "conv_viterbi_table",
        "Шаг 3: Пошаговый перебор метрик (алгоритм Витерби)",
        {
            "num_steps": num_steps,
            "num_states": num_states,
            "state_labels": state_labels,
            "viterbi_steps": viterbi_steps_data,
            "description": (
                "Для каждого такта рассматриваются все возможные переходы. "
                "Для каждого **следующего состояния** выбирается путь с **наименьшей метрикой** — "
                "это «выживший» переход. "
                "Таблица показывает метрики всех состояний после каждого такта."
            ),
        }
    ))

    # ── Шаг 4: Обратный проход ────────────────────────────────────────────
    best_state = min(range(num_states), key=lambda s: metrics[s])
    best_metric = metrics[best_state]

    path_bits = []
    path_states = [best_state]
    cur = best_state
    for t in range(num_steps - 1, -1, -1):
        path_bits.append(input_bit_table[t][cur])
        cur = prev_state_table[t][cur]
        path_states.append(cur)
    path_bits.reverse()
    path_states.reverse()

    decoded = path_bits[:-memory] if memory > 0 else path_bits

    traceback_rows = [
        {
            "t": t + 1,
            "state_label": state_labels[path_states[t]],
            "input": path_bits[t],
            "is_tail": t >= len(decoded),
            "next_state_label": state_labels[path_states[t + 1]],
        }
        for t in range(num_steps)
    ]

    final_metrics_display = {
        state_labels[s]: (metrics[s] if metrics[s] < INF else "∞")
        for s in range(num_states)
    }

    tb_desc = "**Конечные метрики:**\n\n" + "\n".join(
        f"- `{state_labels[s]}`: "
        + (str(metrics[s]) if metrics[s] < INF else "∞")
        + (" ← **минимум, выбираем**" if s == best_state else "")
        for s in range(num_states)
    ) + (f"\n\n**Выбрано состояние:** `{state_labels[best_state]}` "
         f"(метрика = {best_metric})\n\n"
         f"Восстанавливаем путь от такта {num_steps} до такта 0 (обратный проход).")

    steps.append(Step(
        "conv_traceback",
        "Шаг 4: Завершение и обратный проход",
        {
            "best_state": state_labels[best_state],
            "best_metric": best_metric,
            "final_metrics": final_metrics_display,
            "traceback_rows": traceback_rows,
            "decoded_bits": decoded,
            "tail_len": memory,
            "description": tb_desc,
        }
    ))

    # ── Шаг 5: Результат ───────────────────────────────────────────────────
    steps.append(Step(
        "result",
        "Шаг 5: Результат декодирования",
        {
            "decoded": decoded,
            "decoded_str": ''.join(str(b) for b in decoded),
            "success": True,
            "final_metric": best_metric,
            "description": (
                f"**Декодированное сообщение:** `{''.join(str(b) for b in decoded)}`\n\n"
                f"**Финальная метрика:** {best_metric} "
                f"(расстояние Хэмминга между принятым и восстановленным кодовым словом)\n\n"
                + (f"Метрика **0** — ошибок не обнаружено."
                   if best_metric == 0
                   else f"Метрика **{best_metric}** означает, что обнаружено и исправлено "
                        f"~{best_metric} ошибочных бита.")
            )
        }
    ))

    return steps, np.array(decoded, dtype=int), {"success": True, "final_metric": best_metric}


# ─────────────────────────────────────────────────────────────────────────────
#  Обратная совместимость (старый вызов из сервиса)
# ─────────────────────────────────────────────────────────────────────────────

def explain_convolutional(received, conv_code, original_message=None, original_encoded=None):
    return explain_conv_decode(received, conv_code)


def explain_convolutional_with_trellis(received, conv_code):
    return explain_conv_decode(received, conv_code)