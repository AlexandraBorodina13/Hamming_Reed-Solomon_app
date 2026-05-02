import numpy as np
from .steps import Step
from app.core.convolutional import ConvolutionalCode


def explain_convolutional(received, conv_code, original_message=None, original_encoded=None):
    """
    Формирует пошаговое объяснение декодирования сверточного кода.
    """
    steps = []
    n = conv_code.rate_den
    k = conv_code.rate_num
    K = conv_code.constraint_length
    memory = conv_code.memory
    
    # Шаг 1: Параметры кода
    steps.append(Step(
        "text",
        "Параметры сверточного кода",
        {"description": (
            f"**Сверточный код** с параметрами:\n\n"
            f"- Длина ограничения: $K = {K}$\n"
            f"- Память кода: $m = {memory}$\n"
            f"- Скорость: $R = {k}/{n}$\n"
            f"- Количество состояний: $2^{{m}} = {conv_code.num_states}$\n"
            f"- Порождающие полиномы (восьмеричные): {conv_code.generators}\n\n"
            f"Восьмеричные полиномы преобразуются в двоичные маски:\n"
            + "\n".join([f"  $g_{i}(x)$ = {g} (восьм.) → "
                        f"{conv_code._octal_to_binary_poly(g, K)}$"
                        for i, g in enumerate(conv_code.generators)])
        )}
    ))
    
    # Шаг 2: Диаграмма состояний (текстовое описание)
    steps.append(Step(
        "text",
        "Структура кодера",
        {"description": (
            f"**Регистр сдвига** длины {K}:\n\n"
            f"```\n"
            f"Вход → [{K-1}] → [{K-2}] → ... → [1] → [0] → выход\n"
            f"          ↓         ↓              ↓\n"
            f"        g{conv_code.generators[0]}       g{conv_code.generators[1]}\n"
            f"          ↓         ↓\n"
            f"          ⊕─────────⊕ → выходные биты\n"
            f"```\n\n"
            f"**Количество состояний:** {conv_code.num_states}\n\n"
            f"Состояние определяется содержимым {memory} ячеек памяти."
        )}
    ))
    
    # Шаг 3: Принятая последовательность
    received_list = received.tolist() if hasattr(received, 'tolist') else list(received)
    steps.append(Step(
        "matrix",
        "Принятая последовательность",
        {"codeword": received_list, "type": "received"}
    ))
    
    # Шаг 4: Декодирование Витерби
    decoded, info = conv_code.decode(received)
    
    # Создаем описание алгоритма Витерби
    viterbi_desc = (
        f"**Алгоритм Витерби** ищет путь с наименьшей метрикой на решетчатой диаграмме.\n\n"
        f"**Основные этапы:**\n\n"
        f"1. **Инициализация:** Начальная метрика пути для состояния 0 = 0, для остальных = ∞\n\n"
        f"2. **Для каждого шага (блока из {n} бит):**\n"
        f"   - Для каждого текущего состояния рассматриваются 2 возможных перехода (вход 0 или 1)\n"
        f"   - Вычисляется расстояние Хэмминга между принятыми битами и ожидаемыми выходными битами\n"
        f"   - Новая метрика = текущая метрика + расстояние\n"
        f"   - Выбирается переход с наименьшей метрикой для каждого нового состояния\n"
        f"   - Запоминается выбранный переход (для обратного прохода)\n\n"
        f"3. **Завершение:** Выбирается состояние с наименьшей метрикой (обычно состояние 0)\n\n"
        f"4. **Обратный проход:** Восстанавливается последовательность входных битов\n\n"
        f"**Результат:** Финальная метрика = {info.get('final_metric', 'N/A')}"
    )
    
    steps.append(Step(
        "viterbi",
        "Декодирование алгоритмом Витерби",
        {
            "description": viterbi_desc,
            "num_states": conv_code.num_states,
            "block_size": n,
            "final_metric": info.get('final_metric', 0)
        }
    ))
    
    # Шаг 5: Результат
    steps.append(Step(
        "result",
        "Результат декодирования",
        {
            "decoded": decoded,
            "decoded_str": ''.join(str(b) for b in decoded),
            "success": info.get("success", True),
            "final_metric": info.get("final_metric", 0)
        }
    ))
    
    return steps, decoded, info


def explain_convolutional_with_trellis(received, conv_code):
    """
    Расширенная визуализация с решетчатой диаграммой.
    """
    steps = []
    
    # Основные шаги
    steps.append(Step(
        "text",
        "Параметры кода",
        {"description": f"K={conv_code.constraint_length}, "
                       f"скорость={conv_code.rate_num}/{conv_code.rate_den}, "
                       f"состояний={conv_code.num_states}"}
    ))
    
    # Показываем таблицу переходов состояний
    transitions = []
    for state in range(conv_code.num_states):
        for inp in [0, 1]:
            next_state = conv_code.next_states[(state, inp)]
            output = conv_code.outputs[(state, inp)]
            transitions.append({
                "Текущее состояние": f"s{state}",
                "Вход": inp,
                "Выход": ''.join(map(str, output)),
                "След. состояние": f"s{next_state}"
            })
    
    steps.append(Step(
        "matrix",
        "Таблица переходов состояний",
        {"transitions": transitions, "type": "transitions"}
    ))
    
    # Декодирование
    decoded, info = conv_code.decode(received)
    
    steps.append(Step(
        "result",
        "Результат",
        {
            "decoded": decoded,
            "decoded_str": ''.join(map(str, decoded.tolist())) if hasattr(decoded, 'tolist') else ''.join(map(str, decoded)),
            "success": True
        }
    ))
    
    return steps, decoded, info