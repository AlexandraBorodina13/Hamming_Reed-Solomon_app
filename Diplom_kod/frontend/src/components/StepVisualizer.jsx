import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';

export default function StepVisualizer({ steps }) {
  if (!steps || steps.length === 0) return <p>Нет шагов для отображения.</p>;

  return (
    <div>
      {steps.map((step, index) => (
        <details key={index} open>
          <summary><strong>Шаг {index + 1}: {step.title}</strong></summary>
          <div style={{ marginLeft: 20, marginTop: 10 }}>

            {/* Текст */}
            {step.type === 'text' && (
              <div style={{ whiteSpace: 'pre-wrap' }}>
                <ReactMarkdown
                  remarkPlugins={[remarkMath]}
                  rehypePlugins={[rehypeKatex]}
                >
                  {step.payload.description}
                </ReactMarkdown>
              </div>
            )}

            {/* Матрица */}
            {step.type === 'matrix' && (
              <div>
                {/* ... (как раньше, без изменений) ... */}
              </div>
            )}

            {/* Вычисления, синдромы и т.п. — часто содержат формулы */}
            {step.type === 'calc' && (
              <div>
                {step.payload.syndromes != null && (
                  <div>
                    <strong>Синдромы:</strong>
                    {step.payload.syndrome_indices ? (
                      <ul>
                        {step.payload.syndrome_indices.map((j, idx) => (
                          <li key={idx}>
                            S{j} = {step.payload.syndromes[idx]}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p>{step.payload.syndromes.join(', ')}</p>
                    )}
                  </div>
                )}
                {step.payload.received != null && (
                  <p><strong>Принятый вектор:</strong> {step.payload.received.join(' ')}</p>
                )}
                {step.payload.formula && (
                  <ReactMarkdown
                    remarkPlugins={[remarkMath]}
                    rehypePlugins={[rehypeKatex]}
                  >
                    {`**Формула:** ${step.payload.formula}`}
                  </ReactMarkdown>
                )}
                {step.payload.description && (
                  <ReactMarkdown
                    remarkPlugins={[remarkMath]}
                    rehypePlugins={[rehypeKatex]}
                  >
                    {step.payload.description}
                  </ReactMarkdown>
                )}
              </div>
            )}

            {/* Поиск ошибки (для Хэмминга и БЧХ) */}
            {step.type === 'bit' && (
              <div>
                {/* ... без LaTeX, можно оставить как есть ... */}
              </div>
            )}

            {/* Алгоритм Берлекэмпа–Месси (БЧХ) */}
            {step.type === 'bm' && (
              <div>
                <ReactMarkdown
                  remarkPlugins={[remarkMath]}
                  rehypePlugins={[rehypeKatex]}
                >
                  {step.payload.description}
                </ReactMarkdown>
                {step.payload.locator_poly && (
                  <p>Полином локаторов: [{step.payload.locator_poly.join(', ')}]</p>
                )}
              </div>
            )}

            {/* Поиск Ченя (БЧХ) */}
            {step.type === 'chien' && (
              <div>
                <ReactMarkdown
                  remarkPlugins={[remarkMath]}
                  rehypePlugins={[rehypeKatex]}
                >
                  {step.payload.description}
                </ReactMarkdown>
                {step.payload.error_positions && (
                  <p>Позиции ошибок: {step.payload.error_positions.join(', ')}</p>
                )}
              </div>
            )}

            {/* Витерби (свёрточный код) — тоже может содержать формулы */}
            {step.type === 'viterbi' && (
              <div>
                <ReactMarkdown
                  remarkPlugins={[remarkMath]}
                  rehypePlugins={[rehypeKatex]}
                >
                  {step.payload.description}
                </ReactMarkdown>
                <p>Состояний: {step.payload.num_states}, размер блока: {step.payload.block_size}</p>
              </div>
            )}

            {/* Результат */}
            {step.type === 'result' && (
              <div style={{ background: '#efe', padding: 10, borderRadius: 5 }}>
              {step.payload.success === false ? (
                <p style={{ color: 'red' }}>Ошибка декодирования: {step.payload.description}</p>
              ) : (
            <>
               <p style={{ color: 'green', fontWeight: 'bold' }}>Декодирование завершено успешно.</p>
                {step.payload.corrected && (
                <p>Исправленное кодовое слово: {step.payload.corrected.join(' ')}</p>
              )}
              {step.payload.decoded_str ? (
                <p>Декодированное сообщение: <strong>{step.payload.decoded_str}</strong></p>
              ) : step.payload.decoded ? (
                <p>Декодированное сообщение: <strong>{step.payload.decoded}</strong></p>
              ) : null}
              {step.payload.info_bits && (
              <p>Информационные биты: {step.payload.info_bits.join(' ')}</p>
              )}
              {step.payload.final_metric != null && (
            <p>Финальная метрика: {step.payload.final_metric}</p>
            )}
            </>
              )}
            </div>
          )}

            {/* Неизвестный тип */}
            {!['text','matrix','calc','bit','bm','chien','viterbi','result'].includes(step.type) && (
              <pre>{JSON.stringify(step.payload, null, 2)}</pre>
            )}
          </div>
        </details>
      ))}
    </div>
  );
}