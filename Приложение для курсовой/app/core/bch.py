import numpy as np
import galois
import streamlit as st


class BCHCode:
    def __init__(self, n, k):
        self.n = n
        self.k = k
        self.bch = galois.BCH(n, k)
        self.t = self.bch.t

        m = int(np.log2(n + 1))
        self.GF = galois.GF(2**m)
        self.alpha = self.GF.primitive_element

        # Диагностика
        st.warning(f"INIT: m={m}, GF=GF(2^{m}), alpha={repr(self.alpha)}")
        st.warning(f"INIT: alpha**1={repr(self.alpha**1)}, int={(self.alpha**1).item()}")
        
        field_order = n  # порядок alpha = 2^m - 1 = n
        self._alpha_powers = [(self.alpha ** i).item() for i in range(field_order)]
        self._field_order = field_order
        
        st.warning(f"INIT: alpha_powers = {self._alpha_powers}")

    def encode(self, message):
        if len(message) != self.k:
            raise ValueError(f"Длина сообщения должна быть {self.k}")
        # Кодируем через bch используя его родное поле GF(2)
        msg = self.bch.field(np.array(message, dtype=int))
        codeword = self.bch.encode(msg)
        return np.array(codeword, dtype=int)

    def _compute_syndromes(self, received):
        """
        Вычисление синдромов
        
        """
        t = self.t
        n = self.n
        fo = self._field_order
        pw = self._alpha_powers

        syndromes = []
        for j in range(1, 2 * t + 1):
            s = 0
            for i, bit in enumerate(received):
                if bit:
                    exp = (j * (n - 1 - i)) % fo
                    s ^= pw[exp]
            syndromes.append(s)
        return syndromes

    def decode(self, received):
        if len(received) != self.n:
            raise ValueError(f"Длина принятого слова должна быть {self.n}")
        syndromes = self._compute_syndromes(received)
        rec = self.bch.field(np.array(received, dtype=int))
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