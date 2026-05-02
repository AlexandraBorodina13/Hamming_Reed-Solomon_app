import numpy as np


class ConvolutionalCode:
    """Сверточный код с корректным алгоритмом Витерби."""

    def __init__(self, constraint_length=3, rate=(1, 2), generators=None):
        self.constraint_length = constraint_length
        self.rate_num, self.rate_den = rate
        self.memory = constraint_length - 1
        self.num_states = 2 ** self.memory

        if generators is None:
            generators = self._get_standard_generators()
        self.generators = generators

        # Бинарные маски порождающих полиномов
        self.gen_masks = [
            self._octal_to_binary_poly(g, constraint_length)
            for g in self.generators
        ]

        self._precompute_outputs()

    # ------------------------------------------------------------------
    # Служебные методы
    # ------------------------------------------------------------------

    def _get_standard_generators(self):
        standard = {
            (2, 2): [5, 7],
            (3, 2): [7, 5],
            (3, 3): [7, 5, 3],
            (4, 2): [13, 17],
            (5, 2): [23, 35],
            (6, 2): [53, 75],
            (7, 2): [133, 171],
        }
        return standard.get((self.constraint_length, self.rate_den), [7, 5])

    def _octal_to_binary_poly(self, octal, length):
        """Восьмеричное число → бинарный вектор длины length (MSB first)."""
        binary = [int(b) for b in bin(octal)[2:]]
        while len(binary) < length:
            binary.insert(0, 0)
        return binary[-length:]

    def _precompute_outputs(self):
        """
        Предвычисляет таблицы переходов и выходов.

        Соглашение о состоянии:
          Состояние state — это (memory) бит регистра.
          Бит (state >> (memory-1-i)) & 1 соответствует i-й ячейке регистра,
          где i=0 — самая «свежая» (последний вошедший бит), i=memory-1 — самая старая.

        Регистр при вычислении выхода: [inp, s[0], s[1], ..., s[memory-1]]
          то есть [текущий вход, самый свежий бит памяти, ..., самый старый].
        """
        self.outputs = {}     # (state, inp) -> tuple of output bits
        self.next_states = {} # (state, inp) -> next_state

        for state in range(self.num_states):
            # Распаковываем состояние: s[0] — самый свежий бит (MSB)
            state_bits = [(state >> (self.memory - 1 - i)) & 1
                          for i in range(self.memory)]

            for inp in [0, 1]:
                # Регистр: вход + биты памяти
                reg = [inp] + state_bits  # длина = constraint_length

                # Вычисляем выходные биты через каждый порождающий полином
                output = []
                for mask in self.gen_masks:
                    out_bit = 0
                    for i in range(self.constraint_length):
                        out_bit ^= reg[i] & mask[i]
                    output.append(out_bit)

                self.outputs[(state, inp)] = tuple(output)

                # Новое состояние: вход становится самым свежим битом
                # new_state_bits = [inp, s[0], s[1], ..., s[memory-2]]
                new_state = inp
                for i in range(self.memory - 1):
                    new_state = (new_state << 1) | state_bits[i]

                # Если memory == 0, new_state = 0 (один возможный)
                if self.memory == 0:
                    new_state = 0

                self.next_states[(state, inp)] = new_state

    # ------------------------------------------------------------------
    # Кодирование
    # ------------------------------------------------------------------

    def encode(self, message):
        """Кодирует сообщение. Добавляет memory нулевых хвостовых бит."""
        tail = [0] * self.memory
        message_with_tail = list(message) + tail

        encoded = []
        state = 0

        for bit in message_with_tail:
            output = self.outputs[(state, bit)]
            encoded.extend(output)
            state = self.next_states[(state, bit)]

        return np.array(encoded, dtype=int)

    # ------------------------------------------------------------------
    # Декодирование
    # ------------------------------------------------------------------

    def decode(self, received, method="viterbi"):
        return self._viterbi_decode(received)

    def _viterbi_decode(self, received):
        """
        Полный алгоритм Витерби с обратным трассированием.
        """
        received = np.asarray(received, dtype=int)

        # Выравниваем длину по размеру блока
        remainder = len(received) % self.rate_den
        if remainder:
            # Дополняем нулями до кратной длины
            received = np.append(received, [0] * (self.rate_den - remainder))

        num_steps = len(received) // self.rate_den

        INF = 10 ** 9

        # metrics[state] — лучшая накопленная метрика для состояния state
        metrics = [INF] * self.num_states
        metrics[0] = 0  # всегда стартуем из состояния 0

        # Для обратного трассирования
        # prev_state[step][next_state] — из какого состояния пришли
        # input_bit[step][next_state]  — каким битом пришли
        prev_state = [[-1] * self.num_states for _ in range(num_steps)]
        input_bit  = [[ 0] * self.num_states for _ in range(num_steps)]

        # Прямой проход
        for step in range(num_steps):
            block = received[step * self.rate_den : (step + 1) * self.rate_den]
            new_metrics = [INF] * self.num_states

            for state in range(self.num_states):
                if metrics[state] == INF:
                    continue

                for inp in [0, 1]:
                    nxt = self.next_states[(state, inp)]
                    out = self.outputs[(state, inp)]

                    # Расстояние Хэмминга между принятым блоком и ожидаемым выходом
                    dist = sum(int(out[i]) != int(block[i])
                               for i in range(min(len(block), self.rate_den)))

                    candidate = metrics[state] + dist

                    if candidate < new_metrics[nxt]:
                        new_metrics[nxt] = candidate
                        prev_state[step][nxt] = state
                        input_bit[step][nxt]  = inp

            metrics = new_metrics

        # Выбираем лучшее конечное состояние (предпочтительно 0 — из-за хвостовых бит)
        best_state = 0
        best_metric = metrics[0]
        for s in range(self.num_states):
            if metrics[s] < best_metric:
                best_metric = metrics[s]
                best_state = s

        # Обратное трассирование
        path_bits = []
        cur = best_state
        for step in range(num_steps - 1, -1, -1):
            path_bits.append(input_bit[step][cur])
            cur = prev_state[step][cur]

        path_bits.reverse()

        # Убираем хвостовые биты (если memory > 0)
        if self.memory > 0:
            decoded = path_bits[: -self.memory]
        else:
            decoded = path_bits

        return np.array(decoded, dtype=int), {
            "method": "viterbi",
            "final_metric": best_metric,
            "num_states": self.num_states,
            "success": True,
        }

    # ------------------------------------------------------------------
    # Выкалывание
    # ------------------------------------------------------------------

    def puncture(self, encoded, pattern):
        pattern_len = len(pattern)
        return np.array(
            [bit for i, bit in enumerate(encoded) if pattern[i % pattern_len] == 1],
            dtype=int,
        )

    def depuncture(self, received, pattern, original_length):
        depunctured = []
        pattern_len = len(pattern)
        rx_idx = 0
        for i in range(original_length):
            if pattern[i % pattern_len] == 1:
                depunctured.append(received[rx_idx] if rx_idx < len(received) else 0)
                rx_idx += 1
            else:
                depunctured.append(0)
        return np.array(depunctured, dtype=int)


# ------------------------------------------------------------------
# Удобные функции-обёртки
# ------------------------------------------------------------------

def convolutional_encode(message, constraint_length=3, rate=(1, 2), generators=None):
    return ConvolutionalCode(constraint_length, rate, generators).encode(message)


def convolutional_decode(received, constraint_length=3, rate=(1, 2), generators=None):
    return ConvolutionalCode(constraint_length, rate, generators).decode(received)


# Стандартные конфигурации (ключи совпадают с max_errors_map в UI)
STANDARD_CONVOLUTIONAL_CODES = {
    "K=3, R=1/2 (7,5)":    {"constraint_length": 3, "rate": (1, 2), "generators": [7, 5]},
    "K=3, R=1/3 (7,5,3)":  {"constraint_length": 3, "rate": (1, 3), "generators": [7, 5, 3]},
    "K=4, R=1/2 (13,17)":  {"constraint_length": 4, "rate": (1, 2), "generators": [13, 17]},
    "K=5, R=1/2 (23,35)":  {"constraint_length": 5, "rate": (1, 2), "generators": [23, 35]},
    "K=6, R=1/2 (53,75)":  {"constraint_length": 6, "rate": (1, 2), "generators": [53, 75]},
    "K=7, R=1/2 (133,171)":{"constraint_length": 7, "rate": (1, 2), "generators": [133, 171]},
}