from pathlib import Path
import sys
import streamlit as st
import numpy as np
import pandas as pd
from functools import lru_cache
from datetime import datetime 
import time

# добавляем в sys.path корень проекта
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.core.hamming import (
    hamming_general_matrices, encode_general, decode_general, info_positions, matrix_to_latex
)
from app.explain.hamming_steps import explain_hamming_general 
from app.core.export_utils import generate_html_report, create_pdf_report, create_rs_pdf_report, generate_rs_html_report
from app.core.reed_solomon import (rs_make, rs_encode_bytes, rs_decode_symbols, 
                                   rs_syndromes, validate_rs_params, valid_n_for_m, 
                                   rs_add_errors)
from app.explain.rs_steps import explain_rs
from app.core.bch import BCHCode, get_bch_code
from app.explain.bch_steps import explain_bch
from app.core.convolutional import ConvolutionalCode, STANDARD_CONVOLUTIONAL_CODES


# Кэширование для тяжелых операций
@st.cache_data
def get_hamming_matrices_cached(m):
    """Кэширование матриц Хэмминга в Streamlit"""
    return hamming_general_matrices(m)


@st.cache_resource
def get_rs_code_cached(n, k, m):
    """Кэширование RS кода"""
    return rs_make(n, k, m)

"""@st.cache_resource
def get_bch_cached(n, k):
    return get_bch_code(n, k)"""

# Настройка страницы
st.set_page_config(
    page_title="Coding Playground", 
    layout="centered",
    initial_sidebar_state="expanded"
)

st.title("Кодирование и декодирование: учебное приложение")
st.caption("Хэмминг и Рида–Соломона • пошаговая визуализация")

# Инициализация session_state с проверкой на существование
defaults = {
    'noisy': None,
    'code': None,
    'message': None,
    'error_introduced': False,
    'current_m': 3,
    'report_steps': [],
    'rs_codeword': None,
    'rs_noisy': None,
    'error_positions': None,
    'decode_result': None,
    'bch_codeword': None,
    'bch_message': None,
    'bch_noisy': None,
    'bch_error_introduced': False,
    'bch_error_positions': None,
    'conv_encoded': None,
    'conv_message': None
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

st.sidebar.header("Меню")
mode = st.sidebar.radio("Режим", ["Хэмминг", "Рида–Соломона", "БЧХ", "Сверточные коды"], index=0)

# ==================== ХЭММИНГ ====================
if mode == "Хэмминг":
    st.subheader("Обобщенный Хэмминг")
    
    m = st.sidebar.selectbox(
        "Выберите m", 
        [3, 4, 5, 6], 
        index=[3, 4, 5, 6].index(st.session_state.current_m) if st.session_state.current_m in [3,4,5,6] else 0,
        help="m=3: (7,4), m=4: (15,11), m=5: (31,26), m=6: (63,57)"
    )
    
    if m != st.session_state.current_m:
        st.session_state.current_m = m
        st.session_state.error_introduced = False
        st.session_state.noisy = None
        st.rerun()
    
    n = 2**m - 1
    k = n - m
    st.sidebar.info(f"Код ({n}, {k}): {n} бит всего, {k} информационных, {m} проверочных")
    st.header(f"Код Хэмминга ({n}, {k})")
    
    # Показ матриц
    if st.checkbox("Показать матрицы кода"):
        with st.spinner("Загрузка матриц..."):
            G, H, n_calc, k_calc = get_hamming_matrices_cached(m)
            
            st.subheader("Порождающая матрица G")
            # Показываем только часть матрицы если она большая
            if G.shape[0] > 10 or G.shape[1] > 20:
                st.info(f"Матрица G имеет размер {G.shape[0]}×{G.shape[1]}, показаны первые 10 строк и 20 столбцов")
                st.latex(matrix_to_latex(G[:10, :20], "G_{truncated}"))
            else:
                st.latex(matrix_to_latex(G, "G"))
        
            st.subheader("Проверочная матрица H")
            if H.shape[0] > 10 or H.shape[1] > 20:
                st.info(f"Матрица H имеет размер {H.shape[0]}×{H.shape[1]}, показаны первые 10 строк и 20 столбцов")
                st.latex(matrix_to_latex(H[:10, :20], "H_{truncated}"))
            else:
                st.latex(matrix_to_latex(H, "H"))

    # Ввод сообщения
    default_msg = "1" * min(k, 57)
    msg_str = st.text_input(
        f"Сообщение ({k} бит)", 
        default_msg,
        help=f"Введите {k} бит (0 и 1)",
        key="hamming_message_input"
    )
    
    # Проверка длины сообщения
    if len(msg_str) != k:
        st.warning(f"Введите {k} бит (сейчас {len(msg_str)})")
    elif not set(msg_str).issubset({"0", "1"}):
        st.warning("Используйте только 0 и 1")
    else:
        m_bits = np.array([int(b) for b in msg_str], dtype=int)
        
        # Кодирование с кэшированием
        code = encode_general(tuple(m_bits), m)
        st.session_state.code = code
        st.session_state.message = m_bits
        
        st.success(f"Кодовое слово ({n} бит): **{''.join(map(str, code.tolist()))}**")
    
        # Выбор режима ввода ошибки
        error_mode = st.radio("Режим ошибки", ["Ручной выбор", "Автоматическая ошибка"], index=0)
    
        if error_mode == "Ручной выбор":
            error_pos = st.slider("Испортить бит", 0, n-1, 0)
            if st.button("Ввести ошибку", key="manual_error_btn"):
                with st.spinner("Внесение ошибки..."):
                    noisy = code.copy()
                    noisy[error_pos] ^= 1
                    st.session_state.noisy = noisy
                    st.session_state.error_introduced = True
                    st.session_state.error_position = error_pos
                    st.rerun()
        else:
            if st.button("Сгенерировать случайную ошибку", key="random_error_btn"):
                with st.spinner("Генерация случайной ошибки..."):
                    noisy = code.copy()
                    error_pos = np.random.randint(0, n)
                    noisy[error_pos] ^= 1
                    st.session_state.noisy = noisy
                    st.session_state.error_introduced = True
                    st.session_state.error_position = error_pos
                    st.rerun()
        
        if st.session_state.error_introduced and st.session_state.noisy is not None:
            noisy = st.session_state.noisy
            st.info(f"Принятое слово: **{''.join(map(str, noisy.tolist()))}**")
            
            if st.button("Декодировать и показать шаги", key="decode_btn"):
                with st.spinner("Декодирование..."):
                    # Очищаем предыдущий отчет
                    st.session_state.report_steps = []
                    
                    # Декодирование
                    start_time = time.time()
                    corr, info = decode_general(noisy, m)
                    steps = explain_hamming_general(noisy, m)
                    decode_time = time.time() - start_time
                    
                    # Сохраняем шаги для отчета
                    st.session_state.report_steps = steps
                    st.session_state.decode_result = (corr, info)
                    
                    st.success(f"Декодирование завершено за {decode_time:.3f} секунд")
                    
                    # Показываем шаги
                    st.subheader("Пошаговый разбор декодирования")
                    
                    # Используем expander для длинных шагов
                    for i, step in enumerate(steps, 1):
                        with st.expander(f"Шаг {i}: {step.title}", expanded=i==1):
                            
                            if step.type == "matrix":
                                H = step.payload["H"]
                                st.write("Проверочная матрица H:")
                                # Ограничиваем отображение большой матрицы
                                if H.shape[0] > 10 or H.shape[1] > 20:
                                    st.info(f"Матрица имеет размер {H.shape[0]}×{H.shape[1]}")
                                    df = pd.DataFrame(H[:10, :20], 
                                                    columns=[f'Бит {i}' for i in range(min(H.shape[1], 20))],
                                                    index=[f'Синдром {i}' for i in range(min(H.shape[0], 10))])
                                    st.table(df)
                                else:
                                    df = pd.DataFrame(H, 
                                                    columns=[f'Бит {i}' for i in range(H.shape[1])],
                                                    index=[f'Синдром {i}' for i in range(H.shape[0])])
                                    st.table(df)
                            
                            elif step.type == "calc":
                                r = step.payload["received"]
                                s = step.payload["syndrome"]
                                
                                st.write("Вычисляем синдром s = r · Hᵀ:")
                                
                                col1, col2, col3 = st.columns([2,1,2])
                                with col1:
                                    st.write("Принятый вектор r:")
                                    r_str = " ".join(map(str, r[:50]))
                                    if len(r) > 50:
                                        r_str += "..."
                                    st.code(r_str)
                                with col2:
                                    st.write(" ")
                                with col3:
                                    st.write("Синдром s:")
                                    st.code(" ".join(map(str, s)))
                                
                                st.latex(r"s = r \cdot H^T \mod 2")
                            
                            elif step.type == "bit":
                                pos = step.payload["error_pos"]
                                if pos is not None:
                                    if pos == "uncorrectable":
                                        st.error("Ошибка не может быть исправлена!")
                                    else:
                                        st.success(f"Ошибка найдена в позиции: {pos}")
                                        
                                        bits_display = []
                                        for j, bit in enumerate(st.session_state.noisy):
                                            if j == pos:
                                                bits_display.append(f"**{bit}**")
                                            else:
                                                bits_display.append(str(bit))
                                        
                                        st.write("Принятое слово с выделенной ошибкой:")
                                        st.markdown(" ".join(bits_display))
                                        
                                        # Для общего случая Хэмминга показываем двоичное представление
                                        if m != 3:
                                            _, H_tmp, _, _ = get_hamming_matrices_cached(st.session_state.current_m)
                                            st.write(f"Синдром {''.join(map(str, s))} соответствует {pos}-му столбцу матрицы H")
                                
                                else:
                                    st.success("Ошибок не обнаружено")
                            
                            elif step.type == "result":
                                corr_step = step.payload["corrected"]
                                pos = info_positions(st.session_state.current_m)
                                decoded_bits = corr_step[pos]
                                st.success(f"Исправленное слово: **{''.join(map(str, corr_step))}**")
                                
                                # Сравнение с исходным кодовым словом
                                st.write("Сравнение с исходным кодовым словом:")
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.write("Исходное:")
                                    st.success("".join(map(str, st.session_state.code)))
                                with col2:
                                    st.write("→")
                                with col3:
                                    st.write("Исправленное:")
                                    st.success("".join(map(str, corr_step)))
                                
                                # Финальный результат - декодированное сообщение
                                st.markdown("---")
                                st.success(f"**Декодированное сообщение: {''.join(map(str, decoded_bits))}**")
                    
                    # Кнопки экспорта
                    col1, col2 = st.columns(2)
                    with col1:
                        try:
                            html_report = generate_html_report(
                                steps, m, n, k,
                                original_message=''.join(map(str, st.session_state.message)),
                                encoded_message=''.join(map(str, st.session_state.code)),
                                received_message=''.join(map(str, st.session_state.noisy)),
                                decoded_message=''.join(map(str, corr[:k]))
                            )
                            st.download_button(
                                "Скачать HTML отчет", 
                                data=html_report, 
                                file_name=f"hamming_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html", 
                                mime="text/html",
                                key="html_download"
                            )
                        except Exception as e:
                            st.error(f"Ошибка создания HTML отчета: {e}")
                    
                    with col2:
                        try:
                            pdf_buffer = create_pdf_report(
                                steps, m, n, k,
                                original_message=''.join(map(str, st.session_state.message)),
                                encoded_message=''.join(map(str, st.session_state.code)),
                                received_message=''.join(map(str, st.session_state.noisy)),
                                decoded_message=''.join(map(str, corr[:k]))
                            )
                            st.download_button(
                                "Скачать PDF отчет", 
                                data=pdf_buffer, 
                                file_name=f"hamming_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf", 
                                mime="application/pdf",
                                key="pdf_download"
                            )
                        except Exception as e:
                            st.error(f"Ошибка создания PDF отчета: {e}")
    
    # Кнопка сброса
    if st.button("Сбросить", key="reset_hamming"):
        st.session_state.error_introduced = False
        st.session_state.noisy = None
        st.session_state.report_steps = []
        st.session_state.decode_result = None
        st.cache_data.clear()
        st.rerun()

# ==================== РИДА-СОЛОМОНА ====================
elif mode == "Рида–Соломона":
    st.header("Код Рида–Соломона")

    # Параметры
    col1, col2 = st.sidebar.columns(2)
    with col1:
        m = st.number_input(
            "m (GF(2^m))", 
            min_value=1, max_value=8, value=8,  # Ограничиваем до 8 для производительности
            help="Размер поля GF(2^m)"
        )
    
    n_options = valid_n_for_m(m)
    n_default = max(n_options)
    
    with col2:
        n = st.selectbox(
            "Длина n",
            options=n_options,
            index=n_options.index(n_default) if n_default in n_options else 0
        )

    k_max = max(1, n-1)
    k_default = min(k_max, n-2 if n>2 else 1)
    
    k = st.sidebar.number_input(
        "Информационных символов k",
        min_value=1,
        max_value=k_max,
        value=k_default
    )

    # Валидация параметров
    n, k, m, errs = validate_rs_params(n, k, m)

    if errs:
        for e in errs:
            st.sidebar.error(e)
    else:
        t = (n - k) // 2
        st.sidebar.success(f"**RS({n}, {k})** в GF(2^{m})")
        st.sidebar.info(f"Избыточность: {n - k} символов")
        st.sidebar.info(f"Исправляет: до {t} ошибок")
    
    try:
        # Используем кэшированный RS код
        GF, RS = get_rs_code_cached(n, k, m)
        t = (n - k) // 2
        st.info(f"Макс. число исправляемых ошибок t = {t}")
        
        msg_input = st.text_area(
            f"Введите сообщение (до {k} байт)", 
            "Hello RS!", 
            max_chars=k,
            help=f"Сообщение будет обрезано или дополнено до {k} байт"
        )
        
        # Приведение к длине k
        msg_bytes = msg_input.encode("utf-8")[:k]
        msg_bytes = msg_bytes.ljust(k, b'\0')

        if st.button("Кодировать", key="rs_encode_btn"):
            with st.spinner("Кодирование..."):
                codeword = rs_encode_bytes(msg_bytes, RS)
                st.success(f"Кодовое слово (длина {n}):")
                # Показываем только часть длинного кодового слова
                codeword_str = str(codeword.tolist())
                if len(codeword_str) > 500:
                    st.text(codeword_str[:500] + "...")
                else:
                    st.text(codeword_str)
                st.session_state.rs_codeword = codeword

        # Искусственные ошибки
        if st.session_state.rs_codeword is not None:
            codeword = st.session_state.rs_codeword.copy()
            st.markdown("---")
            st.subheader("Внесение ошибок")
    
            # Выбор режима ввода ошибок
            error_mode = st.radio("Режим ввода ошибок", ["Автоматический", "Ручной"], index=0)
    
            if error_mode == "Автоматический":
                max_errors = min(t, n, 10)  # Ограничиваем до 10 ошибок для производительности
                num_errors = st.slider("Количество ошибок", 0, max_errors, min(1, max_errors))
    
                if st.button("Сгенерировать случайные ошибки", key="random_rs_errors"):
                    with st.spinner("Генерация ошибок..."):
                        error_positions = np.random.choice(n, size=num_errors, replace=False)
                        noisy = rs_add_errors(codeword, RS, error_positions)
        
                        st.session_state.rs_noisy = noisy
                        st.session_state.error_positions = error_positions
                        st.info(f"Принятое слово: {noisy.tolist()[:20]}..." if len(noisy) > 20 else f"Принятое слово: {noisy.tolist()}")
                        st.info(f"Позиции ошибок: {error_positions}")
                        st.info(f"Количество ошибок: {num_errors} (максимум исправимых: {t})")
    
            else:  # Ручной режим
                st.write("Введите позиции ошибок через запятую (0-based индексы):")
                error_input = st.text_input("Позиции ошибок", "0, 5, 10", key="manual_positions")
    
                st.write("Опционально: величины ошибок через запятую (1-255):")
                magnitude_input = st.text_input("Величины ошибок", "1, 128, 255", key="manual_magnitudes")
    
                if st.button("Применить ошибки", key="apply_manual_errors"):
                    try:
                        # Парсим введенные позиции
                        error_positions = [int(pos.strip()) for pos in error_input.split(",") if pos.strip()]
                        
                        if len(error_positions) > t:
                            st.warning(f"Количество ошибок ({len(error_positions)}) превышает исправимую способность кода ({t})")
                        
                        # Парсим величины ошибок (если указаны)
                        error_magnitudes = None
                        if magnitude_input.strip():
                            error_magnitudes = [int(mag.strip()) for mag in magnitude_input.split(",") if mag.strip()]
                            # Проверяем величины ошибок
                            invalid_mags = [mag for mag in error_magnitudes if mag < 1 or mag > 255]
                            if invalid_mags:
                                st.error(f"Некорректные величины ошибок: {invalid_mags}. Допустимый диапазон: 1-255")
                                error_magnitudes = None
            
                        # Проверяем корректность позиций
                        invalid_positions = [pos for pos in error_positions if pos < 0 or pos >= n]
                        if invalid_positions:
                            st.error(f"Некорректные позиции: {invalid_positions}. Допустимый диапазон: 0-{n-1}")
                        else:
                            with st.spinner("Применение ошибок..."):
                                noisy = rs_add_errors(codeword, RS, error_positions, error_magnitudes)
                
                                st.session_state.rs_noisy = noisy
                                st.session_state.error_positions = error_positions
                                st.success(f"Ошибки применены в позициях: {error_positions}")
                                if error_magnitudes:
                                    st.success(f"Величины ошибок: {error_magnitudes}")
                                st.info(f"Принятое кодовое слово: {noisy.tolist()[:20]}..." if len(noisy) > 20 else f"Принятое кодовое слово: {noisy.tolist()}")
        
                    except ValueError as e:
                        st.error(f"Ошибка ввода: {e}. Введите корректные числа через запятую")
            
        # Декодирование и пошаговый вывод
        if st.session_state.rs_noisy is not None:
            noisy = st.session_state.rs_noisy
            st.markdown("---")
            st.subheader("Декодирование")
            
            if st.button("Декодировать", key="rs_decode_btn"):
                with st.spinner("Декодирование..."):
                    steps = explain_rs(noisy, RS)
                    st.session_state.rs_steps = steps
                    
                    # Показываем пошаговый разбор
                    st.subheader("Пошаговый разбор декодирования RS")

                    for i, step in enumerate(steps, 1):
                        with st.expander(f"Шаг {i}: {step.title}", expanded=i==1):
                            if step.type == "text":
                                st.write(step.payload["description"])
                            
                            elif step.type == "matrix":
                                word = step.payload["codeword"]
                                st.write("Кодовое слово (вектор символов):")
                                
                                # Компактное отображение для длинных слов
                                if len(word) > 50:
                                    st.info(f"Длина слова: {len(word)} символов")
                                    preview = word[:20].tolist() + ["..."] + word[-20:].tolist()
                                    indices = list(range(20)) + ["..."] + list(range(len(word)-20, len(word)))
                                    
                                    df_preview = pd.DataFrame({
                                        'Позиция': indices,
                                        'Значение': preview
                                    })
                                    st.table(df_preview)
                                else:
                                    df = pd.DataFrame({
                                        'Позиция': range(len(word)),
                                        'Значение': word,
                                    })
                                    st.table(df)
                            
                            elif step.type == "calc":
                                synd = step.payload["syndromes"]
                                st.write("Синдромы S_i:")
                                st.write(synd[:20] if len(synd) > 20 else synd)
                                if len(synd) > 20:
                                    st.caption(f"... и еще {len(synd) - 20} синдромов")
                            
                            elif step.type == "result":
                                if step.payload.get("success", True):
                                    decoded_msg = step.payload["decoded"]
                                    st.success("Декодирование завершено успешно!")
                                    st.markdown(f"**Восстановленное сообщение:** `{decoded_msg}`")
                                    
                                    # Показываем исходное сообщение для сравнения
                                    original_msg = msg_bytes.decode("utf-8", errors="replace").rstrip("\x00")
                                    st.markdown(f"**Исходное сообщение:** `{original_msg}`")
                                    
                                    # Сравнение
                                    if decoded_msg == original_msg:
                                        st.success("Сообщение восстановлено корректно!")
                                    else:
                                        st.warning("Сообщение восстановлено с различиями")
                                else:
                                    st.error("Ошибка декодирования!")
                                    st.write(step.payload["description"])
                                    
                                    # Сохраняем decoded_msg для отчета
                                    decoded_msg = "Ошибка декодирования"
                    
                    # Анализ ошибок
                    if st.session_state.rs_codeword is not None:
                        st.subheader("Анализ ошибок")
                        
                        original = st.session_state.rs_codeword
                        noisy = st.session_state.rs_noisy
                        
                        # Находим все позиции с ошибками
                        error_positions = []
                        error_values = []
                        for i in range(len(original)):
                            if original[i] != noisy[i]:
                                error_positions.append(i)
                                error_values.append((noisy[i] - original[i]) % 256)
                        
                        error_count = len(error_positions)
                        
                        st.write(f"**Общее количество ошибок:** {error_count}")
                        st.write(f"**Максимально исправимое количество ошибок (t):** {t}")
                        
                        if error_count > t:
                            st.error("Слишком много ошибок для исправления!")
                        else:
                            st.success("Количество ошибок в пределах исправимой способности кода")
                        
                        # Таблица ошибок
                        if error_positions and error_count <= 20:  # Показываем только до 20 ошибок
                            error_data = []
                            for pos, val in zip(error_positions, error_values):
                                error_data.append({
                                    'Позиция': pos,
                                    'Исходное значение': original[pos],
                                    'Ошибочное значение': noisy[pos],
                                    'Величина ошибки': val
                                })
                            st.table(pd.DataFrame(error_data))
                        elif error_count > 20:
                            st.info(f"Слишком много ошибок ({error_count}) для отображения таблицы")
                    
                    # Кнопки экспорта
                    if 'steps' in locals():
                        col1, col2 = st.columns(2)
                        with col1:
                            try:
                                html_report = generate_rs_html_report(
                                    steps, n, k, m,
                                    original_message=msg_bytes.decode("utf-8", errors="replace").rstrip("\x00"),
                                    encoded_message=' '.join(map(str, st.session_state.rs_codeword)),
                                    received_message=' '.join(map(str, st.session_state.rs_noisy)),
                                    decoded_message=decoded_msg if 'decoded_msg' in locals() else "Ошибка"
                                )
                                st.download_button(
                                    "Скачать HTML отчет", 
                                    data=html_report, 
                                    file_name=f"rs_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html", 
                                    mime="text/html",
                                    key="rs_html_download"
                                )
                            except Exception as e:
                                st.error(f"Ошибка создания HTML отчета: {e}")
                        
                        with col2:
                            try:
                                pdf_buffer = create_rs_pdf_report(
                                    steps, n, k, m,
                                    original_message=msg_bytes.decode("utf-8", errors="replace").rstrip("\x00"),
                                    encoded_message=' '.join(map(str, st.session_state.rs_codeword)),
                                    received_message=' '.join(map(str, st.session_state.rs_noisy)),
                                    decoded_message=decoded_msg if 'decoded_msg' in locals() else "Ошибка"
                                )
                                st.download_button(
                                    "Скачать PDF отчет", 
                                    data=pdf_buffer, 
                                    file_name=f"rs_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf", 
                                    mime="application/pdf",
                                    key="rs_pdf_download"
                                )
                            except Exception as e:
                                st.error(f"Ошибка создания PDF отчета: {e}")
                
    except ValueError as e:
        st.error(f"Невозможно создать RS({n},{k}) в GF(2^{m}): {e}")
        
    # Кнопка сброса RS
    if st.button("Сбросить RS", key="reset_rs"):
        st.session_state.rs_noisy = None
        st.session_state.rs_codeword = None
        st.session_state.error_positions = None
        st.session_state.rs_steps = None
        st.cache_data.clear()
        st.rerun()

# ==================== БЧХ ====================
elif mode == "Сверточные коды":
    st.header("Сверточный код")
    
    st.info("""
    **Сверточные коды** - коды с памятью, использующие скользящее окно.
    Декодирование выполняется **алгоритмом Витерби**, который находит наиболее вероятный путь на решетчатой диаграмме.
    """)
    
    # Настройки в sidebar - только готовые конфигурации
    st.sidebar.subheader("Параметры сверточного кода")
    
    # Выбор конфигурации из стандартных
    conv_preset = st.sidebar.selectbox(
        "Выберите конфигурацию кода",
        list(STANDARD_CONVOLUTIONAL_CODES.keys())
    )
    
    # Получаем параметры выбранной конфигурации
    config = STANDARD_CONVOLUTIONAL_CODES[conv_preset]
    constraint_length = config["constraint_length"]
    rate = config["rate"]
    generators = config["generators"]
    
    # Создаем код
    conv = ConvolutionalCode(constraint_length, rate, generators)
    
    # Информация о коде в основной области
    memory = constraint_length - 1
    num_states = 2 ** memory
    
    # Словарь максимальных исправляемых ошибок для стандартных кодов
    max_errors_map = {
        "K=3, R=1/2 (7,5)": 2,
        "K=3, R=1/3 (7,5,3)": 3,
        "K=4, R=1/2 (13,17)": 2,
        "K=5, R=1/2 (23,35)": 3,
        "K=6, R=1/2 (53,75)": 3,
        "K=7, R=1/2 (133,171)": 4,
    }
    
    max_errors_limit = max_errors_map.get(conv_preset, 3)
    
    st.subheader(f"Код: {conv_preset}")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Скорость", f"{rate[0]}/{rate[1]}")
    with col2:
        st.metric("Длина ограничения K", constraint_length)
    with col3:
        st.metric("Память (m)", memory)
    with col4:
        st.metric("Состояний", num_states)
    with col5:
        st.metric("Исправляет ошибок", f"до {max_errors_limit}")
    
    # Показываем порождающие полиномы
    st.write("**Порождающие полиномы (восьмеричные):**", generators)
    for i, gen in enumerate(generators):
        mask = conv._octal_to_binary_poly(gen, constraint_length)
        st.write(f"  g{i}(x) = {gen} (восьм.) → бинарная маска: {mask}")
    
    # Ввод сообщения (любой длины)
    msg_str = st.text_input(
        "Сообщение (биты, только 0 и 1)", 
        "101010",
        help="Введите последовательность битов (0 и 1) любой длины"
    )
    
    # Валидация ввода
    if msg_str and not set(msg_str).issubset({"0", "1"}):
        st.warning("Используйте только 0 и 1")
    elif msg_str:
        message = np.array([int(b) for b in msg_str], dtype=int)
        
        # Показываем длину сообщения
        st.caption(f"Длина сообщения: {len(message)} бит")
        
        # Кодирование
        if st.button("Кодировать", key="conv_encode_btn"):
            with st.spinner("Кодирование..."):
                encoded = conv.encode(message)
                st.success(f"**Закодированная последовательность:**")
                st.code(''.join(map(str, encoded.tolist())))
                st.info(f"Длина сообщения: {len(message)} бит → длина кодового слова: {len(encoded)} бит")
                st.session_state.conv_encoded = encoded
                st.session_state.conv_message = message
        
        # Если есть закодированное слово
        if st.session_state.get('conv_encoded') is not None:
            encoded = st.session_state.conv_encoded
            
            st.markdown("---")
            st.subheader("Внесение ошибок")
            
            # Выбор режима ввода ошибок (как в RS коде)
            error_mode = st.radio("Режим ввода ошибок", ["Автоматический", "Ручной"], index=0)
            
            if error_mode == "Автоматический":
                max_errors = min(max_errors_limit, len(encoded))
                num_errors = st.slider("Количество ошибок", 0, max_errors, min(1, max_errors))
                
                if st.button("Сгенерировать случайные ошибки", key="random_conv_errors"):
                    with st.spinner("Генерация ошибок..."):
                        noisy = encoded.copy()
                        if num_errors > 0:
                            error_positions = np.random.choice(len(noisy), size=num_errors, replace=False).tolist()
                            for pos in error_positions:
                                noisy[pos] ^= 1
                        else:
                            error_positions = []
                        
                        st.session_state.conv_noisy = noisy
                        st.session_state.conv_error_positions = error_positions
                        st.rerun()
            
            else:  # Ручной режим
                st.write("Введите позиции ошибок через запятую (0-based индексы):")
                error_input = st.text_input("Позиции ошибок", "0, 5", key="conv_manual_positions")
                
                if st.button("Применить ошибки", key="apply_conv_manual_errors"):
                    try:
                        error_positions = [int(pos.strip()) for pos in error_input.split(",") if pos.strip()]
                        
                        # Проверяем количество ошибок
                        if len(error_positions) > max_errors_limit:
                            st.error(f"Слишком много ошибок! Код может исправить только {max_errors_limit} ошибок.")
                        else:
                            # Проверяем корректность позиций
                            invalid_positions = [pos for pos in error_positions if pos < 0 or pos >= len(encoded)]
                            if invalid_positions:
                                st.error(f"Некорректные позиции: {invalid_positions}. Допустимый диапазон: 0-{len(encoded)-1}")
                            else:
                                with st.spinner("Применение ошибок..."):
                                    noisy = encoded.copy()
                                    for pos in error_positions:
                                        noisy[pos] ^= 1
                                    
                                    st.session_state.conv_noisy = noisy
                                    st.session_state.conv_error_positions = error_positions
                                    st.success(f"Ошибки применены в позициях: {error_positions}")
                                    st.rerun()
                    except ValueError as e:
                        st.error(f"Ошибка ввода: {e}. Введите корректные числа через запятую")
            
            # Показываем искаженное слово
            if st.session_state.get('conv_noisy') is not None:
                noisy = st.session_state.conv_noisy
                error_positions = st.session_state.get('conv_error_positions', [])
                
                st.info(f"**Принятое слово:**")
                
                # Визуализация с выделением ошибок
                noisy_list = noisy.tolist()
                if error_positions:
                    bits_display = []
                    for j, bit in enumerate(noisy_list):
                        if j in error_positions:
                            bits_display.append(f"**{bit}**")
                        else:
                            bits_display.append(str(bit))
                    st.markdown(" ".join(bits_display))
                    st.warning(f"Внесены ошибки в позициях: {error_positions}")
                    st.caption(f"Количество ошибок: {len(error_positions)}")
                else:
                    st.code(''.join(map(str, noisy_list)))
                    st.info("Ошибки не внесены")
                
                # Декодирование
                st.markdown("---")
                st.subheader("Декодирование")
                
                if st.button("Декодировать и показать шаги", key="conv_decode_btn"):
                    with st.spinner("Декодирование..."):
                        from app.explain.convolutional_steps import explain_convolutional
                        
                        steps, decoded, info = explain_convolutional(noisy, conv)
                        st.session_state.conv_steps = steps
                        st.session_state.conv_decoded = decoded
                        
                        
                    
                        
                        
                        
                        
                        
                        
                        
                        
                        st.subheader("Пошаговый разбор декодирования")
                        
                        for i, step in enumerate(steps):
                            with st.expander(f"Шаг {i+1}: {step.title}", expanded=(i==0)):
                                if step.type == "text":
                                    st.write(step.payload["description"])
                                
                                elif step.type == "matrix":
                                    codeword = step.payload["codeword"]
                                    if step.payload.get("type") == "received":
                                        st.write("Принятая последовательность (по блокам):")
                                    else:
                                        st.write("Последовательность:")
                                    
                                    block_size = conv.rate_den
                                    blocks = [codeword[j:j+block_size] for j in range(0, min(len(codeword), 100), block_size)]
                                    
                                    block_data = []
                                    for idx, block in enumerate(blocks[:20]):
                                        block_str = ' '.join(map(str, block))
                                        block_data.append({"Блок": idx, "Биты": block_str})
                                    
                                    if block_data:
                                        st.table(pd.DataFrame(block_data))
                                        if len(blocks) > 20:
                                            st.caption(f"... и еще {len(blocks)-20} блоков")
                                
                                elif step.type == "viterbi":
                                    st.write(step.payload["description"])
                                    st.info(f"Количество состояний: {step.payload['num_states']}")
                                    st.info(f"Размер блока: {step.payload['block_size']} бит")
                                
                                elif step.type == "result":
                                    decoded_bits = step.payload["decoded"]
                                    decoded_str = step.payload["decoded_str"]
                                    
                                    st.success(f"**Декодированное сообщение:** {decoded_str}")
                                    
                                    # Сравнение с исходным
                                    original_str = ''.join(map(str, st.session_state.conv_message))
                                    st.write(f"**Исходное сообщение:** {original_str}")
                                    
                                    if decoded_str == original_str:
                                        st.success("Сообщение восстановлено корректно!")
                                    else:
                                        st.error("Ошибка декодирования!")
                                        
                                        # Показываем сравнение по битам
                                        st.write("**Сравнение бит:**")
                                        comp_parts = []
                                        max_len = max(len(decoded_str), len(original_str))
                                        for j in range(max_len):
                                            if j < len(original_str) and j < len(decoded_str):
                                                if decoded_str[j] == original_str[j]:
                                                    comp_parts.append(decoded_str[j])
                                                else:
                                                    comp_parts.append(f"**{original_str[j]}→{decoded_str[j]}**")
                                            elif j < len(original_str):
                                                comp_parts.append(f"**{original_str[j]}→?**")
                                            else:
                                                comp_parts.append(f"**?→{decoded_str[j]}**")
                                        
                                        for j in range(0, len(comp_parts), 20):
                                            st.text(" ".join(comp_parts[j:j+20]))
                                    
                                    st.info(f"Финальная метрика пути: {step.payload.get('final_metric', 0)}")
                        
                        st.success("Декодирование завершено!")
    
    # Кнопка сброса
    if st.button("Сбросить", key="conv_reset_btn"):
        st.session_state.conv_encoded = None
        st.session_state.conv_noisy = None
        st.session_state.conv_message = None
        st.session_state.conv_error_positions = None
        st.session_state.conv_steps = None
        st.session_state.conv_decoded = None
        st.cache_data.clear()
        st.rerun()