"""
Простой тестовый скрипт для проверки БЧХ и сверточных кодов
Запустите: python test_codes.py
"""

import numpy as np
from app.core.bch import BCHCode
from app.core.convolutional import ConvolutionalCode

def test_bch():
    print("=" * 50)
    print("Тестирование БЧХ кода")
    print("=" * 50)
    
    # Создаем код (15, 11)
    bch = BCHCode(15, 11, m=4)
    print(f"Параметры: n={bch.n}, k={bch.k}, m={bch.m}, t={bch.t}")
    
    # Исходное сообщение
    message = np.array([1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1], dtype=int)
    print(f"Исходное сообщение: {message}")
    
    # Кодируем
    codeword = bch.encode(message)
    print(f"Кодовое слово: {codeword}")
    
    # Вносим ошибку
    received = codeword.copy()
    received[3] ^= 1  # Инвертируем 4-й бит
    print(f"Принятое слово (с ошибкой): {received}")
    
    # Декодируем
    decoded, info = bch.decode(received)
    print(f"Декодированное сообщение: {decoded}")
    print(f"Синдромы: {info['syndromes'][:5]}...")
    print(f"Позиции ошибок: {info['error_positions']}")
    
    if np.array_equal(decoded, message):
        print("Тест БЧХ пройден!")
    else:
        print("Тест БЧХ не пройден!")
    
    print()

def test_convolutional():
    print("=" * 50)
    print("Тестирование сверточного кода")
    print("=" * 50)
    
    # Создаем код K=3, rate=1/2
    conv = ConvolutionalCode(constraint_length=3, rate=(1, 2), generators=[7, 5])
    print(f"Параметры: K={conv.constraint_length}, скорость={conv.rate_num}/{conv.rate_den}")
    print(f"Порождающие полиномы: {conv.generators}")
    
    # Исходное сообщение
    message = np.array([1, 0, 1, 1, 0, 1], dtype=int)
    print(f"Исходное сообщение: {message}")
    
    # Кодируем
    encoded = conv.encode(message)
    print(f"Закодированная последовательность: {encoded}")
    print(f"Длина сообщения: {len(message)}, длина закодированного: {len(encoded)}")
    
    # Вносим ошибку
    received = encoded.copy()
    if len(received) > 2:
        received[2] ^= 1
    print(f"Принятая последовательность (с ошибкой): {received}")
    
    # Декодируем
    decoded, info = conv.decode(received)
    print(f"Декодированное сообщение: {decoded}")
    
    # Сравниваем (обрезаем до одинаковой длины)
    min_len = min(len(decoded), len(message))
    if np.array_equal(decoded[:min_len], message[:min_len]):
        print("Тест сверточного кода пройден!")
    else:
        print("Тест сверточного кода не пройден!")
    
    print()

if __name__ == "__main__":
    test_bch()
    test_convolutional()