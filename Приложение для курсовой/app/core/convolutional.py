import numpy as np
from functools import lru_cache

class ConvolutionalCode:
    """Класс для работы со сверточными кодами"""
    
    def __init__(self, constraint_length=3, rate=(1, 2), generators=None):
        """
        Инициализация сверточного кода.
        
        Параметры:
        - constraint_length: длина кодового ограничения (K)
        - rate: скорость кода (k/n) - количество входных бит на выходные
        - generators: порождающие полиномы в восьмеричном формате
        """
        self.constraint_length = constraint_length
        self.rate_num, self.rate_den = rate
        self.memory = constraint_length - 1
        
        # Стандартные порождающие полиномы для разных кодов
        if generators is None:
            generators = self._get_standard_generators()
        self.generators = generators
        
        # Количество состояний
        self.num_states = 2**self.memory
        
    def _get_standard_generators(self):
        """Возвращает стандартные порождающие полиномы"""
        standard_configs = {
            (2, 2): [5, 7],      # K=2, rate=1/2: полиномы 5 и 7 (восьмеричные)
            (3, 2): [7, 5],      # K=3, rate=1/2: полиномы 7 и 5
            (3, 3): [7, 5, 3],   # K=3, rate=1/3: полиномы 7, 5, 3
            (4, 2): [13, 17],    # K=4, rate=1/2: полиномы 13 и 17
            (5, 2): [23, 35],    # K=5, rate=1/2: полиномы 23 и 35
            (6, 2): [53, 75],    # K=6, rate=1/2: полиномы 53 и 75
        }
        
        key = (self.constraint_length, self.rate_den)
        return standard_configs.get(key, [5, 7])  # По умолчанию (3,2)
    
    def _octal_to_binary_poly(self, octal, length):
        """Преобразует восьмеричный полином в бинарный вектор"""
        binary = [int(b) for b in bin(octal)[2:]]
        # Дополняем до нужной длины
        while len(binary) < length:
            binary.insert(0, 0)
        return binary[-length:]
    
    def encode(self, message):
        """
        Кодирование сверточным кодом.
        
        Параметры:
        - message: бинарное сообщение (массив бит)
        
        Возвращает:
        - закодированная последовательность
        """
        # Добавляем хвостовые биты для возврата в нулевое состояние
        tail = [0] * self.memory
        message_with_tail = list(message) + tail
        
        encoded = []
        state = [0] * self.memory
        
        for bit in message_with_tail:
            # Сдвигаем состояние
            state = [bit] + state[:-1]
            
            # Вычисляем выходные биты
            for gen in self.generators:
                # Преобразуем полином в бинарную маску
                gen_bits = self._octal_to_binary_poly(gen, self.constraint_length)
                # Вычисляем свертку
                output_bit = 0
                for i in range(self.constraint_length):
                    if i < len(state):
                        output_bit ^= (state[i] & gen_bits[i])
                    else:
                        output_bit ^= (0 & gen_bits[i])
                encoded.append(output_bit)
        
        return np.array(encoded, dtype=int)
    
    def decode(self, received, method="viterbi"):
        """
        Декодирование сверточного кода.
        
        Параметры:
        - received: принятая последовательность
        - method: метод декодирования ("viterbi" или "simplified")
        
        Возвращает:
        - декодированное сообщение
        - словарь с информацией
        """
        if method == "viterbi":
            return self._viterbi_decode(received)
        else:
            return self._simplified_decode(received)
    
    def _viterbi_decode(self, received):
        """
        Декодирование алгоритмом Витерби.
        
        Это упрощенная версия для демонстрации.
        В реальном приложении здесь был бы полный алгоритм Витерби.
        """
        # Проверяем, что длина принятой последовательности кратна скорости
        if len(received) % self.rate_den != 0:
            raise ValueError("Длина принятой последовательности должна быть кратна скорости")
        
        num_outputs = len(received) // self.rate_den
        num_inputs = num_outputs - self.memory
        
        # Упрощенное декодирование (для демонстрации)
        decoded = []
        
        # Группируем принятые биты в блоки
        for i in range(num_inputs):
            # Берем блок из rate_den бит
            block_start = i * self.rate_den
            block = received[block_start:block_start + self.rate_den]
            
            # Упрощенное решение: выбираем бит, который дает минимальное расстояние
            # В реальном Витерби используется динамическое программирование
            best_bit = 0
            min_distance = float('inf')
            
            for test_bit in [0, 1]:
                # Кодируем тестовый бит в текущем состоянии (упрощенно)
                test_encoded = self._encode_single_bit(test_bit)
                # Вычисляем расстояние Хэмминга
                distance = sum(1 for j in range(self.rate_den) 
                              if j < len(block) and j < len(test_encoded) 
                              and block[j] != test_encoded[j])
                if distance < min_distance:
                    min_distance = distance
                    best_bit = test_bit
            
            decoded.append(best_bit)
        
        return np.array(decoded[:num_inputs - self.memory], dtype=int), {
            "method": "viterbi_simplified",
            "num_states": self.num_states,
            "success": True
        }
    
    def _encode_single_bit(self, bit):
        """Кодирует один бит для демонстрации"""
        # Упрощенная версия для одного бита
        encoded = []
        for gen in self.generators:
            gen_bits = self._octal_to_binary_poly(gen, self.constraint_length)
            # Для упрощения используем только младший бит
            encoded.append(bit & gen_bits[0])
        return encoded
    
    def _simplified_decode(self, received):
        """Максимально упрощенное декодирование для тестирования"""
        # Простое пороговое декодирование
        decoded = []
        
        for i in range(0, len(received), self.rate_den):
            block = received[i:i+self.rate_den]
            # Голосование: если больше единиц, то 1, иначе 0
            if sum(block) > self.rate_den / 2:
                decoded.append(1)
            else:
                decoded.append(0)
        
        return np.array(decoded, dtype=int), {
            "method": "simplified",
            "success": True
        }
    
    def puncture(self, encoded, pattern):
        """
        Выкалывание (puncturing) для увеличения скорости.
        
        Параметры:
        - encoded: закодированная последовательность
        - pattern: шаблон выкалывания (1 - оставить, 0 - удалить)
        
        Возвращает:
        - выколотая последовательность
        """
        punctured = []
        pattern_len = len(pattern)
        
        for i, bit in enumerate(encoded):
            if pattern[i % pattern_len] == 1:
                punctured.append(bit)
        
        return np.array(punctured, dtype=int)
    
    def depuncture(self, received, pattern, original_length):
        """
        Восстановление выколотой последовательности.
        
        Параметры:
        - received: принятая выколотая последовательность
        - pattern: шаблон выкалывания
        - original_length: исходная длина
        
        Возвращает:
        - восстановленная последовательность с вставленными нулями
        """
        depunctured = []
        pattern_len = len(pattern)
        received_idx = 0
        
        for i in range(original_length):
            if pattern[i % pattern_len] == 1:
                if received_idx < len(received):
                    depunctured.append(received[received_idx])
                    received_idx += 1
                else:
                    depunctured.append(0)
            else:
                depunctured.append(0)
        
        return np.array(depunctured, dtype=int)

# Простые функции для удобного использования
def convolutional_encode(message, constraint_length=3, rate=(1, 2)):
    """Быстрое кодирование сверточным кодом"""
    conv = ConvolutionalCode(constraint_length, rate)
    return conv.encode(message)

def convolutional_decode(received, constraint_length=3, rate=(1, 2)):
    """Быстрое декодирование сверточного кода"""
    conv = ConvolutionalCode(constraint_length, rate)
    return conv.decode(received)

# Предопределенные конфигурации сверточных кодов
STANDARD_CONVOLUTIONAL_CODES = {
    "K3_R12": {"constraint_length": 3, "rate": (1, 2), "generators": [7, 5]},
    "K3_R13": {"constraint_length": 3, "rate": (1, 3), "generators": [7, 5, 3]},
    "K4_R12": {"constraint_length": 4, "rate": (1, 2), "generators": [13, 17]},
    "K5_R12": {"constraint_length": 5, "rate": (1, 2), "generators": [23, 35]},
    "K6_R12": {"constraint_length": 6, "rate": (1, 2), "generators": [53, 75]},
    "K7_R12": {"constraint_length": 7, "rate": (1, 2), "generators": [133, 171]},
}