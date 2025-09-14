from pathlib import Path
import sys
import streamlit as st
import numpy as np
import pandas as pd
from io import BytesIO

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



st.set_page_config(page_title="Coding Playground", page_icon="🔧", layout="centered")
st.title("Кодирование и декодирование: учебное приложение")
st.caption("Хэмминг и Рида–Соломона • пошаговая визуализация")

# Инициализация session_state
if 'noisy' not in st.session_state:
    st.session_state.noisy = None
if 'code' not in st.session_state:
    st.session_state.code = None
if 'message' not in st.session_state:
    st.session_state.message = None
if 'error_introduced' not in st.session_state:
    st.session_state.error_introduced = False
if 'current_m' not in st.session_state:
    st.session_state.current_m = 3
if 'report_steps' not in st.session_state:
    st.session_state.report_steps = []
    
st.sidebar.header("Меню")
mode = st.sidebar.radio("Режим", ["Хэмминг", "Рида–Соломона"], index=0)

if mode == "Хэмминг":
    st.subheader("Обобщенный Хэмминг")
    
    m = st.sidebar.selectbox("Выберите m", [3, 4, 5, 6], index=0,
                           help="m=3: (7,4), m=4: (15,11), m=5: (31,26), m=6: (63,57)")
    st.session_state.current_m = m
    n = 2**m - 1
    k = n - m
    st.sidebar.info(f"Код ({n}, {k}): {n} бит всего, {k} информационных, {m} проверочных")
    
    st.header(f"Код Хэмминга ({n}, {k})")
    
    # Показ матриц
    if st.checkbox("Показать матрицы кода"):
        G, H, n, k = hamming_general_matrices(m)
        
        # нужны ли подписи?????
        st.subheader("Порождающая матрица G")
        st.latex(matrix_to_latex(G, "G"))
    
        st.subheader("Проверочная матрица H")
        st.latex(matrix_to_latex(H, "H"))

    # Ввод сообщения
    msg_str = st.text_input(f"Сообщение ({k} бит)", "1" * min(k, 57),
                          help=f"Введите {k} бит (0 и 1)")
    
    if len(msg_str) == k and set(msg_str) <= {"0","1"}:
        m_bits = np.array([int(b) for b in msg_str], dtype=int)
        code = encode_general(m_bits, m)
        st.session_state.code = code
        st.session_state.message = m_bits
        
        st.success(f"Кодовое слово ({n} бит): **{''.join(map(str, code.tolist()))}**")
    
        # Выбор режима ввода ошибки
        error_mode = st.radio("Режим ошибки", ["Ручной выбор", "Автоматическая ошибка"], index=0)
    
        if error_mode == "Ручной выбор":
            error_pos = st.slider("Испортить бит", 0, n-1, 0)
            if st.button("Ввести ошибку"):
                noisy = code.copy()
                noisy[error_pos] ^= 1
                st.session_state.noisy = noisy
                st.session_state.error_introduced = True
                st.session_state.error_position = error_pos
                st.rerun()
        else:
            if st.button("Сгенерировать случайную ошибку"):
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
            
            if st.button("Декодировать и показать шаги"):
                # Очищаем предыдущий отчет
                st.session_state.report_steps = []
                
                corr, info = decode_general(noisy, m)
                steps = explain_hamming_general(noisy, m)
                
                # Сохраняем шаги для отчета
                st.session_state.report_steps = steps
                st.session_state.decode_result = (corr, info)
                
                # Показываем шаги
                st.subheader("📋 Пошаговый разбор декодирования")
                for i, step in enumerate(steps, 1):
                    st.markdown(f"### Шаг {i}: {step.title}")
                    
                    if step.type == "matrix":
                        H = step.payload["H"]
                        st.write("Проверочная матрица H:")
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
                            st.code(" ".join(map(str, r)))
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
                                st.error("❌ Ошибка не может быть исправлена!")
                            else:
                                st.success(f"✅ Ошибка найдена в позиции: {pos}")
                                
                                bits_display = []
                                for j, bit in enumerate(st.session_state.noisy):
                                    if j == pos:
                                        bits_display.append(f"🔴**{bit}**")
                                    else:
                                        bits_display.append(str(bit))
                                
                                st.write("Принятое слово с выделенной ошибкой:")
                                st.markdown(" ".join(bits_display))
                                
                                # Для общего случая Хэмминга показываем двоичное представление
                                if m != 3:
                                    _, H_tmp, _, _ = hamming_general_matrices(st.session_state.current_m)
                                    st.write(f"Синдром {''.join(map(str, s))} соответствует {pos}-му столбцу матрицы H")
                        
                        else:
                            st.success("✅ Ошибок не обнаружено")
                    
                    elif step.type == "result":
                        corr = step.payload["corrected"]
                        pos = info_positions(st.session_state.current_m)
                        decoded_bits = corr[pos]
                        st.success(f"🎉 Исправленное слово: **{''.join(map(str, corr))}**")
                        
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
                            st.success("".join(map(str, corr)))
                        
                        # Финальный результат - декодированное сообщение
                        st.markdown("---")
                        st.success(f"**Декодированное сообщение: {''.join(map(str, decoded_bits))}**")
                    
                    st.markdown("---")
                
                # Кнопки экспорта
                col1, col2 = st.columns(2)
                with col1:
                    html_report = generate_html_report(
                        steps, m, n, k,
                        original_message=''.join(map(str, st.session_state.message)),
                        encoded_message=''.join(map(str, st.session_state.code)),
                        received_message=''.join(map(str, st.session_state.noisy)),
                        decoded_message=''.join(map(str, corr[:k]))
                    )
                    st.download_button(
                        "📥 Скачать HTML отчет", 
                        data=html_report, 
                        file_name="hamming_report.html", 
                        mime="text/html"
                    )
                
                with col2:
                    pdf_buffer = create_pdf_report(
                        steps, m, n, k,
                        original_message=''.join(map(str, st.session_state.message)),
                        encoded_message=''.join(map(str, st.session_state.code)),
                        received_message=''.join(map(str, st.session_state.noisy)),
                        decoded_message=''.join(map(str, corr[:k]))
                    )
                    st.download_button(
                        "📥 Скачать PDF отчет", 
                        data=pdf_buffer, 
                        file_name="hamming_report.pdf", 
                        mime="application/pdf"
                    )
                
    else:
        st.warning(f"Введите {k} бит (только 0 и 1)")
        
    # Кнопка сброса
    if st.button("Сбросить", key="reset"):
        st.session_state.error_introduced = False
        st.session_state.noisy = None
        st.session_state.report_steps = []
        st.rerun()

elif mode == "Рида–Соломона":
    st.header("Код Рида–Соломона")

    # Параметры
    m = st.sidebar.number_input(
        "Поле m (GF(2^m))", 
        min_value=1, max_value=16, value=8
    )

    n_options = valid_n_for_m(m)
    n_default = max(n_options)  # обычно выбираем максимальное
    n = st.sidebar.selectbox(
        "Длина кодового слова n",
        options=n_options,
        index=n_options.index(n_default)
    )

    k_min = 1
    k_max = max(1, n-1)  # всегда >=1
    k_default = min(k_max, n-2 if n>2 else 1)  # разумное значение по умолчанию

    k = st.sidebar.number_input(
        "Информационные символы k",
        min_value=k_min,
        max_value=k_max,
        value=k_default
    )

    n, k, m, errs = validate_rs_params(n, k, m)

    if errs:
        for e in errs:
            st.sidebar.error(e)
    else:
        st.sidebar.success(f"Используемые параметры: n={n}, k={k}, m={m}")
        t = (n - k) // 2
        redundancy = n - k
        correction_capability = f"до {t} ошибок"
    
        st.sidebar.success(f"**Параметры кода:** RS({n}, {k}) в GF(2^{m})")
        st.sidebar.info(f"**Избыточность:** {redundancy} символов")
        st.sidebar.info(f"**Исправляет:** {correction_capability}")
    
    try:
        GF, RS = rs_make(n, k, m)
        t = (n - k) // 2
        st.write(f"Макс. число исправляемых ошибок t = {t}")
        
        msg_input = st.text_area(f"Введите сообщение (длина k={k} байт)", "Hello RS!", max_chars=k)
        # Приведение к длине k
        msg_bytes = msg_input.encode("utf-8")[:k]
        msg_bytes = msg_bytes.ljust(k, b'\0')  # дополнение нулями

        if st.button("Кодировать"):
            codeword = rs_encode_bytes(msg_bytes, RS)
            st.success(f"Кодовое слово (длина {n}): {codeword}")
            st.session_state.rs_codeword = codeword

        # Искусственные ошибки
        if "rs_codeword" in st.session_state:
            codeword = st.session_state.rs_codeword.copy()
            st.write("Добавить ошибки:")
    
            # Выбор режима ввода ошибок
            error_mode = st.radio("Режим ввода ошибок", ["Автоматический", "Ручной"], index=0)
    
            if error_mode == "Автоматический":
                max_errors = min(t, n)  # Максимальное количество ошибок, которое можно исправить
                num_errors = st.slider("Количество ошибок", 0, max_errors, 1)
    
                if st.button("Сгенерировать случайные ошибки"):
                    error_positions = np.random.choice(n, size=num_errors, replace=False)
                    noisy = rs_add_errors(codeword, RS, error_positions)
        
                    st.session_state.rs_noisy = noisy
                    st.session_state.error_positions = error_positions
                    st.info(f"Принятое кодовое слово с ошибками: {noisy}")
                    st.info(f"Позиции ошибок: {error_positions}")
                    st.info(f"Количество ошибок: {num_errors} (максимум исправимых: {t})")
    
            else:  # Ручной режим
                st.write("Введите позиции ошибок через запятую (0-based индексы):")
                error_input = st.text_input("Позиции ошибок", "0, 5, 10")
    
                st.write("Опционально: величины ошибок через запятую (1-255):")
                magnitude_input = st.text_input("Величины ошибок", "1, 128, 255")
    
                if st.button("Применить ошибки"):
                    try:
                        # Парсим введенные позиции
                        error_positions = [int(pos.strip()) for pos in error_input.split(",") if pos.strip()]
            
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
                            noisy = rs_add_errors(codeword, RS, error_positions, error_magnitudes)
                
                            st.session_state.rs_noisy = noisy
                            st.session_state.error_positions = error_positions
                            st.success(f"Ошибки применены в позициях: {error_positions}")
                            if error_magnitudes:
                                st.success(f"Величины ошибок: {error_magnitudes}")
                            st.info(f"Принятое кодовое слово: {noisy}")
        
                    except ValueError:
                        st.error("Введите корректные числа через запятую")
            
                 
                 
                        
        # Декодирование и пошаговый вывод
        if "rs_noisy" in st.session_state:
            noisy = st.session_state.rs_noisy
            steps = explain_rs(noisy, RS)
            st.subheader("Пошаговый разбор декодирования RS")

            for i, step in enumerate(steps, 1):
                st.markdown(f"### Шаг {i}: {step.title}")

                if step.type == "text":
                    st.write(step.payload["description"])
                elif step.type == "matrix":
                    word = step.payload["codeword"]
                    st.write("Кодовое слово (вектор символов):")
    
                    # Компактное отображение - показываем только первые и последние символы
                    if len(word) > 20:
                        preview = word[:10].tolist() + ["..."] + word[-10:].tolist()
                        indices = list(range(10)) + ["..."] + list(range(len(word)-10, len(word)))
        
                        df_preview = pd.DataFrame({
                            'Позиция': indices,
                            'Значение': preview
                        })
                        st.table(df_preview)
        
                        # Полная таблица в расширяемом блоке
                        with st.expander("Показать полное кодовое слово"):
                            df_full = pd.DataFrame({
                                'Позиция': range(len(word)),
                                'Значение': word,
                                'Символ': [f"'{chr(val)}'" if 32 <= val < 127 else 'N/A' for val in word]
                            })
                            st.table(df_full)
                    else:
                        # Для коротких слов показываем полностью
                        df = pd.DataFrame({
                            'Позиция': range(len(word)),
                            'Значение': word,
                            'Символ': [f"'{chr(val)}'" if 32 <= val < 127 else 'N/A' for val in word]
                        })
                        st.table(df)
    
                    # Дополнительная информация
                    st.info(f"Длина кодового слова: {len(word)} символов")
                    st.write("Символы отображаются только для печатных ASCII символов (32-126)")
                elif step.type == "calc":
                    synd = step.payload["syndromes"]
                    st.write("Синдромы S_i:", synd)
                    st.latex(step.payload["formula"])
                elif step.type == "result":
                    if step.payload.get("success", True):
                        decoded_msg = step.payload["decoded"]
                        st.success("✅ Декодирование завершено успешно!")
                        st.markdown(f"**Восстановленное сообщение:** `{decoded_msg}`")
        
                        # Показываем исходное сообщение для сравнения
                        if "msg_bytes" in locals():
                            original_msg = msg_bytes.decode("utf-8", errors="replace").rstrip("\x00")
                            st.markdown(f"**Исходное сообщение:** `{original_msg}`")
            
                            # Сравнение
                            if decoded_msg == original_msg:
                                st.success("✅ Сообщение восстановлено корректно!")
                            else:
                                st.warning("⚠️ Сообщение восстановлено с различиями")
                    else:
                        st.error("❌ Ошибка декодирования!")
                        st.write(step.payload["description"])
                        
                        
        if "rs_noisy" in st.session_state and "rs_codeword" in st.session_state:
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
                st.error("❌ Слишком много ошибок для исправления!")
            else:
                st.success("✅ Количество ошибок в пределах исправимой способности кода")
    
            # Таблица ошибок
            if error_positions:
                error_data = []
                for pos, val in zip(error_positions, error_values):
                    error_data.append({
                        'Позиция': pos,
                        'Исходное значение': original[pos],
                        'Ошибочное значение': noisy[pos],
                        'Величина ошибки': val
                    })
        
                st.table(pd.DataFrame(error_data))
            col1, col2 = st.columns(2)
            with col1:
                html_report = generate_rs_html_report(
                    steps, n, k, m,
                    original_message=msg_bytes.decode("utf-8", errors="replace").rstrip("\x00"),
                    encoded_message=' '.join(map(str, st.session_state.rs_codeword)),
                    received_message=' '.join(map(str, st.session_state.rs_noisy)),
                    decoded_message=decoded_msg if step.payload.get("success", True) else "Ошибка декодирования"
                )
                st.download_button(
                    "📥 Скачать HTML отчет", 
                    data=html_report, 
                    file_name="rs_report.html", 
                    mime="text/html"
                )
    
            with col2:
                pdf_buffer = create_rs_pdf_report(
                    steps, n, k, m,
                    original_message=msg_bytes.decode("utf-8", errors="replace").rstrip("\x00"),
                    encoded_message=' '.join(map(str, st.session_state.rs_codeword)),
                    received_message=' '.join(map(str, st.session_state.rs_noisy)),
                    decoded_message=decoded_msg if step.payload.get("success", True) else "Ошибка декодирования"
                )
                st.download_button(
                    "📥 Скачать PDF отчет", 
                    data=pdf_buffer, 
                    file_name="rs_report.pdf", 
                    mime="application/pdf"
                )
                
    except ValueError as e:
        st.error(f"Невозможно создать RS({n},{k}) в GF(2^{m}): {e}")
        RS = None
        
    if st.button("Сбросить RS", key="reset_rs"):
        if 'rs_noisy' in st.session_state:
            del st.session_state.rs_noisy
        if 'rs_codeword' in st.session_state:
            del st.session_state.rs_codeword
        if 'error_positions' in st.session_state:
            del st.session_state.error_positions
        st.rerun()
    

    
    
    
    
    
    
    