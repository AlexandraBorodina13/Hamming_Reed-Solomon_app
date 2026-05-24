import math
import numpy as np
import math

def comb(n, k):
    return math.comb(n, k) 

def Q(x):
    """Гауссов Q-функция"""
    return 0.5 * math.erfc(x / math.sqrt(2))

def channel_bit_error_prob(snr_db, rate=1.0):
    """Вероятность ошибки на бит канала BPSK"""
    eb_n0 = 10 ** (snr_db / 10) * rate   # для некодированной передачи rate=1
    return Q(math.sqrt(2 * eb_n0))

def block_code_ber_union_bound(n, k, t, snr_db):
    """
    Оценка BER для блочного кода с жёстким декодированием (исправление t ошибок).
    Возвращает приближённую вероятность битовой ошибки после декодирования.
    """
    p = channel_bit_error_prob(snr_db, rate=k/n)  # вероятность ошибки в канальном бите
    ber = 0.0
    for i in range(t+1, n+1):
        # количество информационных битов, затронутых ошибками, в среднем i * (k/n)
        # но здесь суммируем i * C(n,i) * p^i * (1-p)^{n-i} / k
        ber += i * comb(n, i) * (p ** i) * ((1 - p) ** (n - i))
    ber /= k
    return min(ber, 0.5)   # ограничиваем 0.5

def conv_code_ber_bound(d_free, rate, snr_db):
    """
    Верхняя граница BER для свёрточного кода (жёсткое декодирование).
    """
    eb_n0 = 10 ** (snr_db / 10)
    return Q(math.sqrt(2 * d_free * rate * eb_n0))