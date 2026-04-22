import numpy as np
import galois
from functools import lru_cache

class BCHCode:
    def __init__(self, n, k):
        self.n = n
        self.k = k
        self.bch = galois.BCH(n, k)  # Параметр systematic=True по умолчанию
        self.t = self.bch.t

    def encode(self, message):
        """message: список/массив из k бит (0/1)"""
        if len(message) != self.k:
            raise ValueError(f"Длина сообщения должна быть {self.k}")
        msg = self.bch.field(np.array(message, dtype=int))
        codeword = self.bch.encode(msg)
        return np.array(codeword, dtype=int)

    def decode(self, received):
        """received: список/массив из n бит"""
        if len(received) != self.n:
            raise ValueError(f"Длина принятого слова должна быть {self.n}")

        rec = self.bch.field(np.array(received, dtype=int))
        try:
            # 1. Декодируем — получаем сообщение
            decoded_message = self.bch.decode(rec)

            # 2. Находим исправленное кодовое слово, закодировав сообщение заново
            corrected_codeword = self.bch.encode(decoded_message)

            # 3. Сравниваем исходное и исправленное кодовые слова, чтобы найти ошибки
            error_positions = [i for i in range(self.n) if received[i] != corrected_codeword[i]]

            return np.array(decoded_message, dtype=int), {
                "success": True,
                "error_positions": error_positions,
                "t": self.t,
            }
        except Exception as e:
            return np.zeros(self.k, dtype=int), {
                "success": False,
                "error": str(e),
                "t": self.t,
                "error_positions": [],
            }


@lru_cache(maxsize=8)
def get_bch_code(n, k):
    return BCHCode(n, k)