from app.core.bch import BCH_PRESETS
from app.core.reed_solomon import RS_PRESETS
from app.core.convolutional import STANDARD_CONVOLUTIONAL_CODES

# Свободные расстояния (d_free) для стандартных свёрточных кодов
# (значения известны из теории кодирования, не вычисляются динамически)
CONV_FREE_DIST = {
    "K=3, R=1/2 (7,5)": 5,
    "K=3, R=1/3 (7,5,3)": 8,
    "K=4, R=1/2 (13,17)": 6,
    "K=5, R=1/2 (23,35)": 7,
    "K=6, R=1/2 (53,75)": 8,
    "K=7, R=1/2 (133,171)": 10,
}


def get_comparison_data() -> list[dict]:
    """Возвращает список словарей с характеристиками всех доступных кодов."""
    codes = []

    # 1. Коды Хэмминга (m = 3..6)
    for m in range(3, 7):
        n = 2 ** m - 1
        k = n - m
        codes.append({
            "type": "Хэмминг",
            "preset": f"Hamming({n},{k})",
            "n": n,
            "k": k,
            "rate": round(k / n, 4),
            "redundancy": round((n - k) / n, 4),
            "error_capability": "1 битовая ошибка (t=1)",
            "field_size": 2,
            "notes": "Минимальная избыточность, исправляет однократную ошибку."
        })

    # 2. Двоичные БЧХ-коды
    for preset, params in BCH_PRESETS.items():
        codes.append({
            "type": "БЧХ",
            "preset": preset,
            "n": params["n"],
            "k": params["k"],
            "rate": round(params["k"] / params["n"], 4),
            "redundancy": round((params["n"] - params["k"]) / params["n"], 4),
            "error_capability": f"t = {params['t']} битовых ошибок",
            "field_size": 2,
            "notes": "Двоичный БЧХ, исправляет кратные независимые битовые ошибки."
        })

    # 3. Коды Рида–Соломона
    for preset, params in RS_PRESETS.items():
        codes.append({
            "type": "Рид–Соломон",
            "preset": preset,
            "n": params["n"],
            "k": params["k"],
            "rate": round(params["k"] / params["n"], 4),
            "redundancy": round((params["n"] - params["k"]) / params["n"], 4),
            "error_capability": f"t = {params['t']} символьных ошибок",
            "field_size": 2 ** params["m"],
            "notes": "Не-двоичный код, эффективен против пакетных ошибок."
        })

    # 4. Свёрточные коды
    for preset, params in STANDARD_CONVOLUTIONAL_CODES.items():
        n_eff = params["rate"][1]
        k_eff = params["rate"][0]
        d_free = CONV_FREE_DIST.get(preset, "?")
        memory = params["constraint_length"] - 1
        codes.append({
            "type": "Свёрточный",
            "preset": preset,
            "n": f"K={params['constraint_length']}, R={k_eff}/{n_eff}",
            "k": "поток",
            "rate": round(k_eff / n_eff, 4),
            "redundancy": round(1 - k_eff / n_eff, 4),
            "error_capability": f"d_free = {d_free}",
            "field_size": 2,
            "notes": f"Потоковый код, память {memory}, декодирование Витерби."
        })

    return codes