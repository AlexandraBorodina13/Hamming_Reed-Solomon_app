# backend/app/core/channels.py
import numpy as np

def awgn_channel(bits: np.ndarray, snr_db: float, k: int = None, n: int = None) -> np.ndarray:
    """
    bits: массив 0/1 (кодовое слово)
    snr_db: SNR в дБ, интерпретируемое как Es/N0 (энергия на кодовый бит)
    k, n: параметры кода; если не None, то шум пересчитывается к Eb/N0 с понижением на 10*log10(k/n)
    Возвращает биты после жёсткого решения.
    """
    symbols = 2 * bits - 1

    # Линейное отношение Es/N0
    es_n0 = 10 ** (snr_db / 10.0)

    # Если заданы k и n, пересчитываем к Eb/N0 (Eb = Es / R, R = k/n)
    if k is not None and n is not None:
        rate = k / n
        eb_n0 = es_n0 * rate          # Eb/N0 = (Es/N0) * R   (меньше -> шум сильнее)
    else:
        eb_n0 = es_n0                 # для совместимости, если параметры не переданы

    # Дисперсия шума: для BPSK σ² = 1/(2 * Eb/N0)
    noise_std = np.sqrt(1.0 / (2 * eb_n0))
    noise = np.random.normal(0, noise_std, size=symbols.shape)
    received = symbols + noise
    return (received > 0).astype(int)


def ber_channel(bits: np.ndarray, ber: float) -> np.ndarray:
    """
    Инвертирует каждый бит с вероятностью ber (независимо).
    bits: массив 0/1
    ber: вероятность ошибки на бит (0..1)
    возвращает массив принятых битов
    """
    flip = np.random.rand(len(bits)) < ber
    return bits ^ flip.astype(int)