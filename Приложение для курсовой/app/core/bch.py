import numpy as np
import galois
import streamlit as st   # временно для отладки


class BCHCode:
    def __init__(self, n, k):
        self.n = n
        self.k = k
        self.bch = galois.BCH(n, k)
        self.t = self.bch.t
        self.field = self.bch.field
        self.alpha = self.field.primitive_element

        # ВАЖНО: int(galois_element) всегда возвращает 1 из-за особенности galois!
        # Правильный способ получить числовое значение: .item()
        field_order = n
        self._alpha_powers = [(self.alpha ** k).item() for k in range(field_order)]
        self._field_order = field_order

    def encode(self, message):
        if len(message) != self.k:
            raise ValueError(f"Длина сообщения должна быть {self.k}")
        msg = self.field(np.array(message, dtype=int))
        codeword = self.bch.encode(msg)
        return np.array(codeword, dtype=int)

    def _compute_syndromes(self, received):
        """
        Sⱼ = R(αʲ) = Σᵢ received[i] · αʲ⁽ⁿ⁻¹⁻ⁱ⁾,  j = 1…2t
        galois хранит кодовое слово MSB-first: received[0] = коэф. при x^(n-1).
        Сложение в GF(2^m) = XOR. Значения α^k берутся из таблицы .item().
        """
        t = self.t
        n = self.n
        fo = self._field_order
        pw = self._alpha_powers

        # ===== ОТЛАДКА =====
        st.warning(f"DEBUG received = {list(received)}")
        st.warning(f"DEBUG alpha_powers = {pw}")
        # ===================

        syndromes = []
        for j in range(1, 2 * t + 1):
            s = 0
            for i, bit in enumerate(received):
                if bit:
                    exp = (j * (n - 1 - i)) % fo
                    s ^= pw[exp]
            st.warning(f"DEBUG S{j} = {s}")
            syndromes.append(s)
        return syndromes

    def decode(self, received):
        if len(received) != self.n:
            raise ValueError(f"Длина принятого слова должна быть {self.n}")

        syndromes = self._compute_syndromes(received)

        rec = self.field(np.array(received, dtype=int))
        try:
            decoded_message = self.bch.decode(rec)
            corrected_codeword = self.bch.encode(decoded_message)
            error_positions = [
                i for i in range(self.n)
                if int(received[i]) != int(corrected_codeword[i])
            ]
            return np.array(decoded_message, dtype=int), {
                "success": True,
                "error_positions": error_positions,
                "t": self.t,
                "syndromes": syndromes,
            }
        except Exception as e:
            return np.zeros(self.k, dtype=int), {
                "success": False,
                "error": str(e),
                "t": self.t,
                "error_positions": [],
                "syndromes": syndromes,
            }


def get_bch_code(n, k):
    return BCHCode(n, k)