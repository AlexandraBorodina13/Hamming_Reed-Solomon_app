import io
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import numpy as np
from datetime import datetime
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fonts import addMapping

from app.core.hamming import info_positions

# Регистрируем шрифты с поддержкой кириллицы
try:
    # Попробуем использовать стандартные шрифты
    pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))
    pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', 'DejaVuSans-Bold.ttf'))
except:
    # Если шрифты не найдены, используем встроенные
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        # Используем стандартный шрифт, который поддерживает кириллицу
        pdfmetrics.registerFont(TTFont('Arial', 'arial.ttf'))
    except:
        pass

def create_pdf_report(steps, m, n, k, original_message, encoded_message, received_message, decoded_message):
    """Создание PDF отчета с использованием ReportLab"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    styles = getSampleStyleSheet()
    FONT_NAME = "DejaVuSans"
    # Создаем custom стили с поддержкой кириллицы
    styles.add(ParagraphStyle(
        name='CustomTitle',
        parent=styles['Title'],
        fontSize=16,
        spaceAfter=30,
        alignment=1,  # center
        fontName=FONT_NAME + '-Bold'
    ))
    
    styles.add(ParagraphStyle(
        name='StepTitle',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=6,
        backColor=colors.lightgrey,
        fontName=FONT_NAME + '-Bold'
    ))
    
    # Стиль для нормального текста
    styles.add(ParagraphStyle(
        name='NormalText',
        parent=styles['Normal'],
        fontName=FONT_NAME
    ))
    
    
    story = []
    
    # Заголовок
    title = Paragraph(f"ОТЧЕТ ПО ДЕКОДИРОВАНИЮ КОДА ХЭММИНГА ({n},{k})", styles['CustomTitle'])
    story.append(title)
    
    # Информация о параметрах и дате
    params_text = f"""
    <b>Параметры кода:</b> m = {m}, n = {n}, k = {k}<br/>
    <b>Дата генерации:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>
    <b>Исходное сообщение:</b> {original_message}<br/>
    <b>Закодированное сообщение:</b> {encoded_message}<br/>
    <b>Принятое сообщение:</b> {received_message}<br/>
    <b>Декодированное сообщение:</b> {decoded_message}
    """
    
    params = Paragraph(params_text, styles['NormalText'])
    story.append(params)
    story.append(Spacer(1, 20))
    
    # Шаги декодирования
    step_title = Paragraph("ПОШАГОВЫЙ ПРОЦЕСС ДЕКОДИРОВАНИЯ", styles['StepTitle'])
    story.append(step_title)
    story.append(Spacer(1, 12))
    
    for i, step in enumerate(steps, 1):
        # Заголовок шага
        step_header = Paragraph(f"ШАГ {i}: {step.title.upper()}", styles['StepTitle'])
        story.append(step_header)
        
        if step.type == "matrix":
            H = step.payload["H"]
            # Создаем таблицу для матрицы H
            data = [[''] + [f'b{j}' for j in range(n)]]
            for row_idx, row in enumerate(H):
                data.append([f's{row_idx}'] + list(map(str, row)))
            
            t = Table(data)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('FONTSIZE', (0, 0), (-1, -1), 8)
            ]))
            story.append(t)
            
            # Описание матрицы
            desc = Paragraph("Проверочная матрица H используется для вычисления синдрома ошибки", styles['NormalText'])
            story.append(desc)
        
        elif step.type == "calc":
            r = step.payload["received"]
            s = step.payload["syndrome"]
            
            # Таблица с векторами
            data = [
                ['Вектор', 'Значение'],
                ['Принятый вектор (r)', ' '.join(map(str, r))],
                ['Синдром (s = r·Hᵀ)', ' '.join(map(str, s))]
            ]
            
            t = Table(data, colWidths=[2*inch, 4*inch])
            t.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'DejaVuSans'),        # <-- Явно указываем шрифт
                ('FONTSIZE', (0, 0), (-1, -1), 10),                  # размер шрифта
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgreen),
                ('FONTNAME', (0, 0), (-1, 0), 'DejaVuSans-Bold'),    # Заголовок жирным
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ]))
            story.append(t)
            
            # Формула
            formula = Paragraph("Формула: <i>s = r · Hᵀ mod 2</i>", styles['NormalText'])
            story.append(formula)
        
        elif step.type == "bit":
            error_pos = step.payload["error_pos"]
            if error_pos == "uncorrectable":
                error_text = Paragraph("<b><font color='red'>ОШИБКА: Неисправимая ошибка!</font></b>", styles['NormalText'])
                story.append(error_text)
            elif error_pos is None:
                success_text = Paragraph("<b><font color='green'>Ошибок не обнаружено</font></b>", styles['NormalText'])
                story.append(success_text)
            else:
                pos_text = Paragraph(f"<b>Обнаружена ошибка в позиции:</b> {error_pos}", styles['NormalText'])
                story.append(pos_text)
                
                # Визуализация позиции ошибки
                r = step.payload["received"]
                error_display = []
                for j, bit in enumerate(r):
                    if j == error_pos:
                        error_display.append(f"<b><font color='red'>{bit}</font></b>")
                    else:
                        error_display.append(str(bit))
                
                error_vis = Paragraph(f"Принятый вектор: {' '.join(error_display)}", styles['NormalText'])
                story.append(error_vis)
        
        elif step.type == "result":
            corrected = step.payload["corrected"]
            pos = info_positions(m)
            info_bits = step.payload.get("info_bits", corrected[pos])
            
            data = [
                ['Результат', 'Значение'],
                ['Исправленное слово', ' '.join(map(str, corrected[pos]))],
                ['Информационные биты', ' '.join(map(str, info_bits))]
            ]
            
            t = Table(data, colWidths=[2*inch, 4*inch])
            t.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'DejaVuSans'),        # <-- Явно указываем шрифт
                ('FONTSIZE', (0, 0), (-1, -1), 10),                  # размер шрифта
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgreen),
                ('FONTNAME', (0, 0), (-1, 0), 'DejaVuSans-Bold'),    # Заголовок жирным
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ]))
            story.append(t)
            
            success = Paragraph("<b><font color='green'>Декодирование завершено успешно!</font></b>", styles['NormalText'])
            story.append(success)
        
        story.append(Spacer(1, 15))
        
        # Добавляем разрыв страницы после каждых 3 шагов
        if i % 3 == 0 and i < len(steps):
            story.append(PageBreak())
    
    doc.build(story)
    buffer.seek(0)
    return buffer

def generate_html_report(steps, m, n, k, original_message, encoded_message, received_message, decoded_message):
    """Генерация HTML отчета"""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Отчет по декодированию Хэмминга ({n},{k})</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 40px;
                line-height: 1.6;
                color: #333;
            }}
            .header {{
                text-align: center;
                background: linear-gradient(135deg, #007bff, #0056b3);
                color: white;
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 30px;
            }}
            .info-box {{
                background: #f8f9fa;
                border-left: 4px solid #007bff;
                padding: 15px;
                margin: 20px 0;
                border-radius: 5px;
            }}
            .step {{
                margin: 25px 0;
                padding: 15px;
                border: 1px solid #ddd;
                border-radius: 8px;
                background: #fff;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .step-title {{
                background: #e9ecef;
                padding: 10px;
                border-radius: 5px;
                margin-bottom: 15px;
                font-weight: bold;
                color: #495057;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 15px 0;
                font-size: 14px;
            }}
            th, td {{
                border: 1px solid #dee2e6;
                padding: 8px;
                text-align: center;
            }}
            th {{
                background-color: #007bff;
                color: white;
            }}
            .matrix-table th {{
                background-color: #6c757d;
            }}
            .success {{
                color: #28a745;
                font-weight: bold;
            }}
            .error {{
                color: #dc3545;
                font-weight: bold;
            }}
            .highlight {{
                background-color: #fff3cd;
                padding: 2px 4px;
                border-radius: 3px;
            }}
            .footer {{
                text-align: center;
                margin-top: 40px;
                color: #6c757d;
                font-size: 12px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Отчет по декодированию кода Хэмминга ({n},{k})</h1>
        </div>
        
        <div class="info-box">
            <strong>Параметры кода:</strong> m = {m}, n = {n}, k = {k}<br>
            <strong>Дата генерации:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
            <strong>Исходное сообщение:</strong> {original_message}<br>
            <strong>Закодированное сообщение:</strong> {encoded_message}<br>
            <strong>Принятое сообщение:</strong> {received_message}<br>
            <strong>Декодированное сообщение:</strong> {decoded_message}
        </div>
        
        <h2>Пошаговый процесс декодирования</h2>
    """
    
    for i, step in enumerate(steps, 1):
        html += f'''
        <div class="step">
            <div class="step-title">Шаг {i}: {step.title}</div>
        '''
        
        if step.type == "matrix":
            H = step.payload["H"]
            html += '<h3>Проверочная матрица H:</h3>'
            html += '<table class="matrix-table">'
            html += '<tr><th></th>' + ''.join(f'<th>Бит {j}</th>' for j in range(n)) + '</tr>'
            for row_idx, row in enumerate(H):
                html += f'<tr><th>Строка {row_idx}</th>'
                html += ''.join(f'<td>{bit}</td>' for bit in row) + '</tr>'
            html += '</table>'
            html += '<p><em>Проверочная матрица H используется для вычисления синдрома ошибки</em></p>'
        
        elif step.type == "calc":
            r = step.payload["received"]
            s = step.payload["syndrome"]
            html += f'<p><strong>Принятый вектор (r):</strong> {" ".join(map(str, r))}</p>'
            html += f'<p><strong>Синдром (s = r·Hᵀ):</strong> <span class="highlight">{" ".join(map(str, s))}</span></p>'
            html += '<p><em>Формула: s = r · Hᵀ mod 2</em></p>'
        
        elif step.type == "bit":
            error_pos = step.payload["error_pos"]
            if error_pos == "uncorrectable":
                html += '<p class="error">Неисправимая ошибка!</p>'
            elif error_pos is None:
                html += '<p class="success">Ошибок не обнаружено</p>'
            else:
                html += f'<p class="success">Обнаружена ошибка в позиции: {error_pos}</p>'
                r = step.payload["received"]
                bits_display = []
                for j, bit in enumerate(r):
                    if j == error_pos:
                        bits_display.append(f'<span class="error">{bit}</span>')
                    else:
                        bits_display.append(str(bit))
                html += f'<p>Принятый вектор: {" ".join(bits_display)}</p>'
        
        elif step.type == "result":
            corrected = step.payload["corrected"]
            #/////////////////////////////////////////
            pos = info_positions(m)
            info_bits = step.payload.get("info_bits", corrected[pos])
            
            html += f'<p><strong>Исправленное слово:</strong> {" ".join(map(str, corrected[pos]))}</p>'
            html += f'<p><strong>Информационные биты:</strong> <span class="success">{" ".join(map(str, info_bits))}</span></p>'
            html += '<p class="success">Декодирование завершено успешно!</p>'
        
        html += '</div>'
    
    html += '''
        <div class="footer">
            <p>Отчет сгенерирован автоматически • Приложение для курсовой работы</p>
        </div>
    </body>
    </html>
    '''
    return html

def create_rs_pdf_report(steps, n, k, m, original_message, encoded_message, received_message, decoded_message):
    """Создание PDF отчета для Рида-Соломона"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    styles = getSampleStyleSheet()
    FONT_NAME = "DejaVuSans"
    
    # Создаем custom стили с поддержкой кириллицы
    styles.add(ParagraphStyle(
        name='CustomTitle',
        parent=styles['Title'],
        fontSize=16,
        spaceAfter=30,
        alignment=1,
        fontName=FONT_NAME + '-Bold'
    ))
    
    styles.add(ParagraphStyle(
        name='StepTitle',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=6,
        backColor=colors.lightgrey,
        fontName=FONT_NAME + '-Bold'
    ))
    
    styles.add(ParagraphStyle(
        name='NormalText',
        parent=styles['Normal'],
        fontName=FONT_NAME
    ))
    
    # Стиль для длинного текста с переносом
    styles.add(ParagraphStyle(
        name='WrappedText',
        parent=styles['Normal'],
        fontName=FONT_NAME,
        fontSize=8,  # Уменьшаем шрифт для длинного текста
        wordWrap='CJK'  # Включаем перенос слов
    ))
    
    story = []
    
    # Заголовок
    title = Paragraph(f"ОТЧЕТ ПО ДЕКОДИРОВАНИЮ КОДА РИДА-СОЛОМОНА ({n},{k})", styles['CustomTitle'])
    story.append(title)
    
    # Информация о параметрах и дате
    params_text = f"""
    <b>Параметры кода:</b> n = {n}, k = {k}, m = {m}<br/>
    <b>Поле:</b> GF(2^{m})<br/>
    <b>Исправляет ошибок:</b> t = {(n - k) // 2}<br/>
    <b>Дата генерации:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>
    <b>Исходное сообщение:</b> {original_message}<br/>
    <b>Закодированное сообщение:</b> {encoded_message}<br/>
    <b>Принятое сообщение:</b> {received_message}<br/>
    <b>Декодированное сообщение:</b> {decoded_message}
    """
    
    params = Paragraph(params_text, styles['NormalText'])
    story.append(params)
    story.append(Spacer(1, 20))
    
    # Шаги декодирования
    step_title = Paragraph("ПОШАГОВЫЙ ПРОЦЕСС ДЕКОДИРОВАНИЯ", styles['StepTitle'])
    story.append(step_title)
    story.append(Spacer(1, 12))
    
    for i, step in enumerate(steps, 1):
        # Заголовок шага
        step_header = Paragraph(f"ШАГ {i}: {step.title.upper()}", styles['StepTitle'])
        story.append(step_header)
        
        if step.type == "text":
            desc = Paragraph(step.payload["description"], styles['NormalText'])
            story.append(desc)
        
        elif step.type == "matrix":
            codeword = step.payload["codeword"]
            # Создаем таблицу для кодового слова (только первые 10 и последние 10 символов для экономии места)
            data = [['Позиция', 'Значение', 'Символ']]
            
            # Показываем только первые 10 и последние 10 символов
            if len(codeword) > 20:
                for pos in range(10):
                    val = codeword[pos]
                    symbol = f"'{chr(val)}'" if 32 <= val < 127 else 'N/A'
                    data.append([str(pos), str(val), symbol])
                data.append(['...', '...', '...'])
                for pos in range(len(codeword)-10, len(codeword)):
                    val = codeword[pos]
                    symbol = f"'{chr(val)}'" if 32 <= val < 127 else 'N/A'
                    data.append([str(pos), str(val), symbol])
            else:
                for pos, val in enumerate(codeword):
                    symbol = f"'{chr(val)}'" if 32 <= val < 127 else 'N/A'
                    data.append([str(pos), str(val), symbol])
            
            t = Table(data, colWidths=[0.5*inch, 0.8*inch, 0.8*inch])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'DejaVuSans-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('FONTSIZE', (0, 0), (-1, -1), 7)
            ]))
            story.append(t)
            
            desc = Paragraph(f"Кодовое слово длины {len(codeword)} символов (показаны первые и последние 10)", styles['NormalText'])
            story.append(desc)
        
        elif step.type == "calc":
            syndromes = step.payload["syndromes"]
            formula = step.payload["formula"]
            
            # Таблица с синдромами
            data = [['Синдром', 'Значение']]
            for idx, s in enumerate(syndromes):
                data.append([f'S{idx}', str(s)])
            
            t = Table(data, colWidths=[1*inch, 1*inch])
            t.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'DejaVuSans'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgreen),
                ('FONTNAME', (0, 0), (-1, 0), 'DejaVuSans-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ]))
            story.append(t)
            
            # Формула
            formula_text = Paragraph(f"Формула: <i>{formula}</i>", styles['NormalText'])
            story.append(formula_text)
        
        elif step.type == "result":
            if step.payload.get("success", True):
                corrected = step.payload["corrected"]
                decoded = step.payload["decoded"]
                
                # Форматируем длинные строки с переносами
                corrected_str = ' '.join(map(str, corrected))
                # Разбиваем на несколько строк если слишком длинное
                if len(corrected_str) > 50:
                    corrected_parts = [corrected_str[i:i+50] for i in range(0, len(corrected_str), 50)]
                    corrected_display = '<br/>'.join(corrected_parts)
                else:
                    corrected_display = corrected_str
                
                # Разбиваем декодированное сообщение если слишком длинное
                if len(decoded) > 30:
                    decoded_parts = [decoded[i:i+30] for i in range(0, len(decoded), 30)]
                    decoded_display = '<br/>'.join(decoded_parts)
                else:
                    decoded_display = decoded
                
                data = [
                    ['Результат', 'Значение'],
                    ['Исправленное \nкодовое слово', Paragraph(corrected_display, styles['WrappedText'])],
                    ['Декодированное \nсообщение', Paragraph(decoded_display, styles['WrappedText'])]
                ]
                
                t = Table(data, colWidths=[1.5*inch, 4.5*inch])
                t.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, -1), 'DejaVuSans'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgreen),
                    ('FONTNAME', (0, 0), (-1, 0), 'DejaVuSans-Bold'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                    ('LEFTPADDING', (0, 0), (-1, -1), 3),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                ]))
                story.append(t)
                
                success = Paragraph("<b><font color='green'>Декодирование завершено успешно!</font></b>", styles['NormalText'])
                story.append(success)
            else:
                error_desc = Paragraph(f"<b><font color='red'>Ошибка декодирования:</font></b> {step.payload['description']}", styles['NormalText'])
                story.append(error_desc)
        
        story.append(Spacer(1, 15))
        
        # Добавляем разрыв страницы после каждых 2 шагов (из-за больших таблиц)
        if i % 2 == 0 and i < len(steps):
            story.append(PageBreak())
    
    doc.build(story)
    buffer.seek(0)
    return buffer

def generate_rs_html_report(steps, n, k, m, original_message, encoded_message, received_message, decoded_message):
    """Генерация HTML отчета для Рида-Соломона"""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Отчет по декодированию Рида-Соломона ({n},{k})</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 40px;
                line-height: 1.6;
                color: #333;
            }}
            .header {{
                text-align: center;
                background: linear-gradient(135deg, #28a745, #1e7e34);
                color: white;
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 30px;
            }}
            .info-box {{
                background: #f8f9fa;
                border-left: 4px solid #28a745;
                padding: 15px;
                margin: 20px 0;
                border-radius: 5px;
            }}
            .step {{
                margin: 25px 0;
                padding: 15px;
                border: 1px solid #ddd;
                border-radius: 8px;
                background: #fff;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .step-title {{
                background: #e9ecef;
                padding: 10px;
                border-radius: 5px;
                margin-bottom: 15px;
                font-weight: bold;
                color: #495057;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 15px 0;
                font-size: 14px;
            }}
            th, td {{
                border: 1px solid #dee2e6;
                padding: 8px;
                text-align: center;
            }}
            th {{
                background-color: #28a745;
                color: white;
            }}
            .matrix-table th {{
                background-color: #6c757d;
            }}
            .success {{
                color: #28a745;
                font-weight: bold;
            }}
            .error {{
                color: #dc3545;
                font-weight: bold;
            }}
            .highlight {{
                background-color: #fff3cd;
                padding: 2px 4px;
                border-radius: 3px;
            }}
            .footer {{
                text-align: center;
                margin-top: 40px;
                color: #6c757d;
                font-size: 12px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Отчет по декодированию кода Рида-Соломона ({n},{k})</h1>
        </div>
        
        <div class="info-box">
            <strong>Параметры кода:</strong> n = {n}, k = {k}, m = {m}<br>
            <strong>Поле:</strong> GF(2^{m})<br>
            <strong>Исправляет ошибок:</strong> t = {(n - k) // 2}<br>
            <strong>Дата генерации:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
            <strong>Исходное сообщение:</strong> {original_message}<br>
            <strong>Закодированное сообщение:</strong> {encoded_message}<br>
            <strong>Принятое сообщение:</strong> {received_message}<br>
            <strong>Декодированное сообщение:</strong> {decoded_message}
        </div>
        
        <h2>Пошаговый процесс декодирования</h2>
    """
    
    for i, step in enumerate(steps, 1):
        html += f'''
        <div class="step">
            <div class="step-title">Шаг {i}: {step.title}</div>
        '''
        
        if step.type == "text":
            html += f'<p>{step.payload["description"]}</p>'
        
        elif step.type == "matrix":
            codeword = step.payload["codeword"]
            html += '<h3>Кодовое слово:</h3>'
            html += '<table class="matrix-table">'
            html += '<tr><th>Позиция</th><th>Значение</th><th>Символ</th></tr>'
            for pos, val in enumerate(codeword):
                symbol = f"'{chr(val)}'" if 32 <= val < 127 else 'N/A'
                html += f'<tr><td>{pos}</td><td>{val}</td><td>{symbol}</td></tr>'
            html += '</table>'
            html += f'<p><em>Длина кодового слова: {len(codeword)} символов</em></p>'
        
        elif step.type == "calc":
            syndromes = step.payload["syndromes"]
            formula = step.payload["formula"]
            html += '<h3>Синдромы:</h3>'
            html += '<table>'
            html += '<tr><th>Синдром</th><th>Значение</th></tr>'
            for idx, s in enumerate(syndromes):
                html += f'<tr><td>S{idx}</td><td>{s}</td></tr>'
            html += '</table>'
            html += f'<p><em>Формула: {formula}</em></p>'
        
        elif step.type == "result":
            if step.payload.get("success", True):
                corrected = step.payload["corrected"]
                decoded = step.payload["decoded"]
                html += f'<p><strong>Исправленное кодовое слово:</strong> {" ".join(map(str, corrected))}</p>'
                html += f'<p><strong>Декодированное сообщение:</strong> <span class="success">{decoded}</span></p>'
                html += '<p class="success">Декодирование завершено успешно!</p>'
            else:
                html += f'<p class="error">Ошибка декодирования: {step.payload["description"]}</p>'
        
        html += '</div>'
    
    html += '''
        <div class="footer">
            <p>Отчет сгенерирован автоматически • Приложение для курсовой работы</p>
        </div>
    </body>
    </html>
    '''
    return html

