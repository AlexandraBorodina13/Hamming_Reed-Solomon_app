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
          <summary>
            <strong>
              Шаг {index + 1}:{' '}
              <ReactMarkdown
                remarkPlugins={[remarkMath]}
                rehypePlugins={[rehypeKatex]}
                components={{ p: ({ children }) => <>{children}</> }}
              >
                {step.title}
              </ReactMarkdown>
            </strong>
          </summary>
          <div style={{ marginLeft: 20, marginTop: 10 }}>

            {/* Текст */}
            {step.type === 'text' && (
              <div style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', overflowWrap: 'anywhere'}}>
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
                {step.payload.H ? (
                  // Проверочная матрица Хэмминга
                  <table border="1" cellPadding="4" style={{ borderCollapse: 'collapse' }}>
                    <thead>
                      <tr>
                        <th></th>
                        {Array.from({ length: step.payload.n || step.payload.H[0].length }, (_, j) => (
                          <th key={j}>b{j}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {step.payload.H.map((row, i) => (
                        <tr key={i}>
                          <td><strong>s{i}</strong></td>
                          {row.map((bit, j) => (
                            <td key={j}>{bit}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : step.payload.codeword ? (
                  <p>Кодовое слово: [{step.payload.codeword.join(', ')}]</p>
                ) : step.payload.transitions ? (
                  <table border="1">
                    <thead>
                      <tr>
                        <th>Из</th><th>Вход</th><th>Выход</th><th>В</th>
                      </tr>
                    </thead>
                    <tbody>
                      {step.payload.transitions.map((t, i) => (
                        <tr key={i}>
                          <td>{t.from || t["Текущее состояние"]}</td>
                          <td>{t.input || t["Вход"]}</td>
                          <td>{Array.isArray(t.output) ? t.output.join('') : t["Выход"]}</td>
                          <td>{t.to || t["След. состояние"]}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <pre>{JSON.stringify(step.payload, null, 2)}</pre>
                )}
              </div>
            )}

            {/* Вычисления (синдром, синдромы) */}
            {step.type === 'calc' && (
              <div>
                {step.payload.syndromes != null && (
                  <div>
                    <strong>Синдромы:</strong>
                    {step.payload.syndrome_indices ? (
                      <ul>
                        {step.payload.syndrome_indices.map((j, idx) => (
                          <li key={idx}>S{j} = {step.payload.syndromes[idx]}</li>
                        ))}
                      </ul>
                    ) : (
                      <p>{step.payload.syndromes.join(', ')}</p>
                    )}
                  </div>
                )}
                {step.payload.received != null && (
                  <p style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
                  <p><strong>Принятый вектор:</strong> {step.payload.received.join(' ')}</p>
                  </p>
                )}
                {step.payload.formula && (
                  <ReactMarkdown
                    remarkPlugins={[remarkMath]}
                    rehypePlugins={[rehypeKatex]}
                  >
                    {step.payload.formula}
                  </ReactMarkdown>
                )}
                {step.payload.description && (
                  <div style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
                  <ReactMarkdown
                    remarkPlugins={[remarkMath]}
                    rehypePlugins={[rehypeKatex]}
                  >
                    {step.payload.description}
                  </ReactMarkdown>
                  </div>
                )}
              </div>
            )}

            {/* Поиск ошибки (для Хэмминга и БЧХ) */}
            {step.type === 'bit' && (
              <div>
                {step.payload.description && (
                  <ReactMarkdown
                    remarkPlugins={[remarkMath]}
                    rehypePlugins={[rehypeKatex]}
                  >
                    {step.payload.description}
                  </ReactMarkdown>
                )}
                {step.payload.error_pos === 'uncorrectable' ? (
                  <p style={{ color: 'red' }}>Ошибка не может быть исправлена!</p>
                ) : step.payload.error_pos != null ? (
                  <p>Ошибка найдена в позиции: <strong>{step.payload.error_pos}</strong></p>
                ) : (
                  <p>Ошибок не обнаружено</p>
                )}
                {step.payload.received && (
                  <p>
                    Принятое слово:{' '}
                    {step.payload.received.map((bit, idx) =>
                      idx === step.payload.error_pos ? <b key={idx}>{bit}</b> : bit
                    ).reduce((prev, curr) => [prev, ' ', curr])}
                  </p>
                )}
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

            {/* Витерби (свёрточный код) */}
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
              <div style={{ background: '#efe', padding: 10, borderRadius: 5, wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
                {step.payload.success === false ? (
                  <p style={{ color: 'red' }}>Ошибка декодирования: {step.payload.description}</p>
                ) : (
                  <>
                    <p style={{ color: 'green', fontWeight: 'bold' }}>Декодирование завершено успешно.</p>
                    {step.payload.description && (
                      <ReactMarkdown
                        remarkPlugins={[remarkMath]}
                        rehypePlugins={[rehypeKatex]}
                      >
                        {step.payload.description}
                      </ReactMarkdown>
                    )}
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


            {/* ── Синдромы RS ── */}
            {step.type === 'rs_syndromes' && (
            <div>
            <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
              {step.payload.description}
            </ReactMarkdown>
            <details style={{ marginTop: 8 }}>
              <summary style={{ cursor: 'pointer', color: '#0066cc' }}>
                Таблица синдромов ({step.payload.syndromes?.length} значений)
              </summary>
              <table border="1" cellPadding="4"
                      style={{ borderCollapse: 'collapse', marginTop: 8, fontSize: 13 }}>
                <thead>
                  <tr style={{ background: '#e9f5ff' }}>
                    <th>j</th><th>S<sub>j</sub></th><th>= 0?</th>
                  </tr>
                </thead>
                <tbody>
                  {step.payload.syndromes?.map((val, idx) => (
                    <tr key={idx}
                        style={{ background: val !== 0 ? '#fff3cd' : 'white' }}>
                      <td>{idx + 1}</td>
                      <td>{val}</td>
                      <td>{val === 0 ? '✓' : '✗'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </details>
          </div>
          )}

          {/* ── Берлекэмп–Месси RS ── */}
          {step.type === 'rs_bm' && (
          <div>
            <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
              {step.payload.description}
            </ReactMarkdown>
            {step.payload.locator_poly && (
              <p><strong>Λ(x) коэффициенты [λ₀, λ₁, …]:</strong>{' '}
                [{step.payload.locator_poly.join(', ')}]
              </p>
            )}
            {step.payload.iterations?.length > 0 && (
              <details style={{ marginTop: 8 }}>
                <summary style={{ cursor: 'pointer', color: '#0066cc' }}>
                  Итерации алгоритма (первые {step.payload.iterations.length})
                </summary>
                <table border="1" cellPadding="4"
                        style={{ borderCollapse: 'collapse', marginTop: 8, fontSize: 12 }}>
                  <thead>
                    <tr style={{ background: '#e9f5ff' }}>
                      <th>r</th><th>S_r</th><th>Δ</th><th>L</th><th>Λ(x) после</th>
                    </tr>
                  </thead>
                  <tbody>
                    {step.payload.iterations.map((it, i) => (
                      <tr key={i} style={{ background: it.delta !== 0 ? '#fff3cd' : 'white' }}>
                        <td>{it.r}</td>
                        <td>{it.S_r}</td>
                        <td>{it.delta}</td>
                        <td>{it.L_after}</td>
                        <td>[{it.C_after?.join(', ')}]</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </details>
            )}
          </div>
          )}

          {/* ── Поиск Ченя RS ── */}
          {step.type === 'rs_chien' && (
          <div>
            <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
              {step.payload.description}
            </ReactMarkdown>
            {step.payload.chien_preview?.length > 0 && (
              <details style={{ marginTop: 8 }}>
                <summary style={{ cursor: 'pointer', color: '#0066cc' }}>
                  Результаты подстановки (показаны первые 8 + ошибочные)
                </summary>
                <table border="1" cellPadding="4"
                        style={{ borderCollapse: 'collapse', marginTop: 8, fontSize: 12 }}>
                  <thead>
                    <tr style={{ background: '#e9f5ff' }}>
                      <th>i</th><th>Λ(α<sup>−i</sup>)</th><th>Корень?</th>
                    </tr>
                  </thead>
                  <tbody>
                    {step.payload.chien_preview.map((row, idx) => (
                      <tr key={idx}
                          style={{ background: row.is_root ? '#d4edda' : 'white',
                                    fontWeight: row.is_root ? 'bold' : 'normal' }}>
                        <td>{row.i}</td>
                        <td>{row.val}</td>
                        <td>{row.is_root ? '✓ ошибка' : '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p><em>… всего проверено {step.payload.n} позиций</em></p>
              </details>
            )}
            {step.payload.error_positions?.length > 0 && (
              <p style={{ color: '#155724', fontWeight: 'bold' }}>
                Позиции ошибок: [{step.payload.error_positions.join(', ')}]
              </p>
            )}
          </div>
          )}

          {/* ── Форни RS ── */}
          {step.type === 'rs_forney' && (
          <div>
            <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
              {step.payload.description}
            </ReactMarkdown>
            {step.payload.forney_rows?.length > 0 && (
              <table border="1" cellPadding="4"
                      style={{ borderCollapse: 'collapse', marginTop: 8, fontSize: 13 }}>
                <thead>
                  <tr style={{ background: '#e9f5ff' }}>
                    <th>Позиция i</th><th>Величина ошибки e<sub>i</sub></th>
                  </tr>
                </thead>
                <tbody>
                  {step.payload.forney_rows.map((row, idx) => (
                    <tr key={idx}>
                      <td>{row.pos}</td>
                      <td><strong>{row.magnitude}</strong></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
          )}



            {/* Неизвестный тип */}
            {!['text','matrix','calc','bit','bm','chien','viterbi','result',
                'rs_syndromes','rs_bm','rs_chien','rs_forney'].includes(step.type) && (
              <pre>{JSON.stringify(step.payload, null, 2)}</pre>
            )}
          </div>
        </details>
      ))}
    </div>
  );
}