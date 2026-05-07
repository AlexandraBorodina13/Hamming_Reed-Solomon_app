import numpy as np
from .steps import Step
from pathlib import Path
import sys
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
    
from app.core.reed_solomon import rs_syndromes, extract_message_rs, rs_decode_symbols

def explain_rs(codeword, RS):
    steps = []
    n = RS.n
    k = RS.k
    t = (n - k) // 2

    steps.append(Step(
        "text",
        "Кодирование RS",
        {"description": f"Исходное сообщение длины k={k} кодируется в кодовое слово длины n={n}. t={t} символов может быть исправлено."}
    ))

    steps.append(Step(
        "matrix",
        "Кодовое слово",
        {"codeword": codeword}
    ))

    syndromes = rs_syndromes(codeword, RS)
    steps.append(Step(
        "calc",
        "Вычисление синдромов",
        {"syndromes": syndromes, "formula": "S_i = sum(c_j * α^{i*j})"}
    ))

    # Декодируем и получаем результат
    try:
        decoded_symbols = rs_decode_symbols(codeword, RS)
        decoded_message = extract_message_rs(codeword, RS)
        
        steps.append(Step(
            "result",
            "Результат декодирования",
            {
                "description": f"Декодирование завершено успешно!",
                "corrected": decoded_symbols,
                "decoded": decoded_message,
                "success": True
            }
        ))
    except Exception as e:
        steps.append(Step(
            "result",
            "Ошибка декодирования",
            {
                "description": f"Не удалось декодировать: {str(e)}",
                "success": False
            }
        ))

    return steps