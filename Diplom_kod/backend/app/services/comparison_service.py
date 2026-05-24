# services/comparison_service.py
from app.core.bch import BCH_PRESETS
from app.core.reed_solomon import RS_PRESETS
from app.core.convolutional import STANDARD_CONVOLUTIONAL_CODES
from app.core.ber_estimator import block_code_ber_union_bound, conv_code_ber_bound
import math

# Свободные расстояния для свёрточных кодов (если ещё нет)
CONV_FREE_DIST = {
    "K=3, R=1/2 (7,5)": 5,
    "K=3, R=1/3 (7,5,3)": 8,
    "K=4, R=1/2 (13,17)": 6,
    "K=5, R=1/2 (23,35)": 7,
    "K=6, R=1/2 (53,75)": 8,
    "K=7, R=1/2 (133,171)": 10,
}

def generate_ber_curve(code_type, params, snr_range_db):
    """Возвращает список {'snr': snr, 'ber': ber} для заданного типа кода"""
    curve = []
    for snr in snr_range_db:
        if code_type == "Свёрточный":
            d_free = params["d_free"]
            rate = params["rate_num"] / params["rate_den"]
            ber = conv_code_ber_bound(d_free, rate, snr)
        else:  # блочные коды
            n = params["n"]
            k = params["k"]
            t = params.get("t", 1)
            if code_type == "Рид–Соломон":
                # Для РС t символьных ошибок, но формула BER должна быть адаптирована.
                # Пересчитываем символьную ошибку в битовую: обычно BER ≈ (t/n) * символьная ошибка.
                # Простейший вариант: используем ту же формулу, но p = Q(sqrt(2 * Eb/N0 * m))?
                # Для упрощения примем, что каждый ошибочный символ содержит в среднем m/2 битовых ошибок.
                m = int(math.log2(params["field_size"]))  # m=8 для GF(256)
                # Символьная вероятность ошибки
                p_sym = block_code_ber_union_bound(n, k, t, snr)  # здесь t символьных исправлений
                # Битовый BER ≈ p_sym * (m/2) / m? Грубо: BER ≈ p_sym / 2 (при равновероятных ошибках символов)
                ber = p_sym * (m / 2) / m  # просто p_sym/2
            else:
                ber = block_code_ber_union_bound(n, k, t, snr)
        curve.append({"snr": snr, "ber": ber})
    return curve

def get_comparison_data() -> list[dict]:
    """Возвращает список словарей с характеристиками всех доступных кодов."""
    codes = []
    snr_range = list(range(0, 11))  # 0..10 дБ

    # 1. Коды Хэмминга
    for m_val in range(3, 7):
        n = 2 ** m_val - 1
        k = n - m_val
        params = {"n": n, "k": k, "t": 1}
        codes.append({
            "type": "Хэмминг",
            "preset": f"Hamming({n},{k})",
            "n": n,
            "k": k,
            "rate": round(k / n, 4),
            "redundancy": round((n - k) / n, 4),
            "error_capability": "1 битовая ошибка (t=1)",
            "field_size": 2,
            "notes": "Минимальная избыточность, исправляет однократную ошибку.",
            "complexity_time": "m·n операций XOR",
            "complexity_memory": "O(n) бит",
            "complexity_class": "Низкая",
            "ber_samples": generate_ber_curve("Хэмминг", params, snr_range)
        })

    # 2. БЧХ
    for preset, preset_params in BCH_PRESETS.items():
        params = {"n": preset_params["n"], "k": preset_params["k"], "t": preset_params["t"]}
        codes.append({
            "type": "БЧХ",
            "preset": preset,
            "n": preset_params["n"],
            "k": preset_params["k"],
            "rate": round(preset_params["k"] / preset_params["n"], 4),
            "redundancy": round((preset_params["n"] - preset_params["k"]) / preset_params["n"], 4),
            "error_capability": f"t = {preset_params['t']} битовых ошибок",
            "field_size": 2,
            "notes": "Двоичный БЧХ, исправляет кратные независимые битовые ошибки.",
            "complexity_time": "O(n·t)",
            "complexity_memory": "O(n)",
            "complexity_class": "Средняя",
            "ber_samples": generate_ber_curve("БЧХ", params, snr_range)
        })

    # 3. Рид–Соломон
    for preset, preset_params in RS_PRESETS.items():
        params = {
            "n": preset_params["n"],
            "k": preset_params["k"],
            "t": preset_params["t"],
            "field_size": 2 ** preset_params["m"]
        }
        codes.append({
            "type": "Рид–Соломон",
            "preset": preset,
            "n": preset_params["n"],
            "k": preset_params["k"],
            "rate": round(preset_params["k"] / preset_params["n"], 4),
            "redundancy": round((preset_params["n"] - preset_params["k"]) / preset_params["n"], 4),
            "error_capability": f"t = {preset_params['t']} символьных ошибок",
            "field_size": 2 ** preset_params["m"],
            "notes": "Не-двоичный код, эффективен против пакетных ошибок.",
            "complexity_time": "O(n·t)",
            "complexity_memory": "O(n)",
            "complexity_class": "Высокая",
            "ber_samples": generate_ber_curve("Рид–Соломон", params, snr_range)
        })

    # 4. Свёрточные коды
    for preset, preset_params in STANDARD_CONVOLUTIONAL_CODES.items():
        d_free = CONV_FREE_DIST.get(preset, 1)
        rate = preset_params["rate"][0] / preset_params["rate"][1]
        params = {
            "d_free": d_free,
            "rate_num": preset_params["rate"][0],
            "rate_den": preset_params["rate"][1]
        }
        memory = preset_params["constraint_length"] - 1
        codes.append({
            "type": "Свёрточный",
            "preset": preset,
            "n": f"K={preset_params['constraint_length']}, R={preset_params['rate'][0]}/{preset_params['rate'][1]}",
            "k": "поток",
            "rate": round(rate, 4),
            "redundancy": round(1 - rate, 4),
            "error_capability": f"d_free = {d_free}",
            "field_size": 2,
            "notes": f"Потоковый код, память {memory}, декодирование Витерби.",
            "complexity_time": "O(2^{K-1} * L)",
            "complexity_memory": f"2^{memory} состояний",
            "complexity_class": "Экспоненциальная по K",
            "ber_samples": generate_ber_curve("Свёрточный", params, snr_range)
        })

    return codes