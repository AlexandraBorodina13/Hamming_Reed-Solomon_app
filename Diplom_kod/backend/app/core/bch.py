import numpy as np
import galois
#import streamlit as st


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
        #st.warning(f"INIT: m={m}, GF=GF(2^{m}), alpha={repr(self.alpha)}")
        #st.warning(f"INIT: alpha**1={repr(self.alpha**1)}, int={(self.alpha**1).item()}")
        
        field_order = n  # порядок alpha = 2^m - 1 = n
        self._alpha_powers = [(self.alpha ** i).item() for i in range(field_order)]
        self._field_order = field_order
        
        #st.warning(f"INIT: alpha_powers = {self._alpha_powers}")

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
        
        # Вычисляем lambda(x) если есть ненулевые синдромы
        locator_poly = None
        if any(s != 0 for s in syndromes):
            locator_poly = self._berlekamp_massey(syndromes)
    
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
                "locator_poly": locator_poly, #NEW
            }
        except Exception as e:
            return np.zeros(self.k, dtype=int), {
                "success": False,
                "error": str(e),
                "t": self.t,
                "error_positions": [],
                "syndromes": syndromes,
                "locator_poly": locator_poly, #NEW
            }
            
            
    """def _berlekamp_massey(self, syndromes):
        #GF = self.field
        
        GF = self.GF
        
        t = self.t
    
        # Конвертируем синдромы в элементы поля
        S = [GF(s) if s != 0 else GF(0) for s in syndromes]
    
        # Инициализация
        Lambda = [GF(1)]  # лямбда(x) = 1
        B = [GF(1)]       # B(x) = 1
        L = 0             # текущая длина регистра
        m = 1             # количество итераций с момента последнего изменения L
    
        for r in range(1, 2*t + 1):
            # Вычисляем невязку дельтаr
            delta = S[r-1]
            for j in range(1, min(L, r) + 1):
                if j < len(Lambda):
                    delta += Lambda[j] * S[r-1-j]
        
            if delta == 0:
                m += 1
            else:
                # Сохраняем старую Lambda
                T = Lambda.copy()
            
                # Обновляем Lambda
                # Удлиняем Lambda если нужно
                while len(Lambda) < len(B) + m:
                    Lambda.append(GF(0))
            
                for i in range(len(B)):
                    if i + m < len(Lambda):
                        Lambda[i + m] -= delta * B[i]
            
                if 2 * L <= r - 1:
                    L = r - L
                    B = T.copy()
                    m = 1
                else:
                    m += 1
    
        # Нормализация: делим на лямбда0 (должен быть 1)
        if Lambda[0] != 1:
            factor = Lambda[0]
            Lambda = [c / factor for c in Lambda]
    
        return [int(c) for c in Lambda]"""
        
    def _berlekamp_massey(self, syndromes):
        """
        Реализация алгоритма Берлекэмпа-Месси для нахождения полинома локаторов ошибок.
        Возвращает список коэффициентов Λ(x) = [λ0, λ1, ..., λv] (λ0 = 1).
        Работает в поле GF(2^m).
        """
        GF = self.GF
        t = self.t

        # Преобразуем синдромы в элементы поля GF
        S = [GF(s) if s != 0 else GF(0) for s in syndromes]

        # Инициализация
        Lambda = [GF(1)]      # Λ(x) = 1
        B = [GF(1)]          # B(x) = 1
        L = 0
        m = 1

        for r in range(1, len(S) + 1):
            # Вычисляем невязку Δ
            delta = S[r-1]
            for j in range(1, L+1):
                if j < len(Lambda):
                    delta += Lambda[j] * S[r-1-j]

            if delta == 0:
                m += 1
            else:
                # Сохраняем старый Λ
                T = Lambda.copy()

                # Удлиняем Λ, если нужно, до размера max(len(Lambda), len(B)+m)
                while len(Lambda) < len(B) + m:
                    Lambda.append(GF(0))
                for i in range(len(B)):
                    if i + m < len(Lambda):
                        # Lambda[i+m] -= delta * B[i]
                        Lambda[i+m] -= delta * B[i]

                if 2 * L <= r - 1:
                    L = r - L
                    B = T.copy()
                    m = 1
                else:
                    m += 1

        # Нормализация: делим все коэффициенты на λ0 (он должен быть 1, но на всякий случай)
        if Lambda[0] != 1:
            inv_l0 = 1 / Lambda[0]   # в поле GF
            Lambda = [c * inv_l0 for c in Lambda]
            
        # Обрезаем хвостовые нули (но λ0 всегда 1)
        while len(Lambda) > 1 and Lambda[-1] == 0:
            Lambda.pop()

        # Возвращаем список целых чисел
        return [int(c) for c in Lambda]

def get_bch_code(n, k):
    return BCHCode(n, k)

BCH_PRESETS = {
    "BCH(7,4) t=1": {"n": 7,  "k": 4, "t": 1},
    "BCH(15,7) t=2": {"n": 15, "k": 7, "t": 2},
    "BCH(15,5) t=3": {"n": 15, "k": 5, "t": 3},
    "BCH(31,21) t=2": {"n": 31, "k": 21, "t": 2},
    "BCH(31,16) t=3": {"n": 31, "k": 16, "t": 3},
    "BCH(31,11) t=5": {"n": 31, "k": 11, "t": 5},
    "BCH(63,51) t=2": {"n": 63, "k": 51, "t": 2},
    "BCH(63,45) t=3": {"n": 63, "k": 45, "t": 3},
    "BCH(63,39) t=4": {"n": 63, "k": 39, "t": 4},
    "BCH(63,36) t=5": {"n": 63, "k": 36, "t": 5},
    "BCH(63,30) t=6": {"n": 63, "k": 30, "t": 6},
    "BCH(63,24) t=7": {"n": 63, "k": 24, "t": 7},
    "BCH(63,18) t=10": {"n": 63, "k": 18, "t": 10},
    "BCH(63,16) t=11": {"n": 63, "k": 16, "t": 11},
    "BCH(63,10) t=13": {"n": 63, "k": 10, "t": 13},
    "BCH(63,7) t=15": {"n": 63, "k": 7, "t": 15},
}