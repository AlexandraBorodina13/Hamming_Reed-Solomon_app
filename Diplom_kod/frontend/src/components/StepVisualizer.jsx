import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import { useState } from 'react';



// ── Таблица трассировки регистра (кодирование) ──────────────────────────────
function ConvEncodeTrace({ payload }) {
  const { trace, memory, rate_den, message_len, codeword_pairs, description } = payload;
  if (!trace) return null;
  return (
    <div>
      <div style={{ marginBottom: 10 }}>
        <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
          {description}
        </ReactMarkdown>
      </div>
      <div style={{ overflowX: 'auto' }}>
        <table border="1" cellPadding="5"
               style={{ borderCollapse: 'collapse', fontSize: 13, width: '100%' }}>
          <thead>
            <tr style={{ background: '#e9f5ff', textAlign: 'center' }}>
              <th>Такт</th>
              <th>Вход</th>
              <th>Регистр до</th>
              {Array.from({ length: rate_den }, (_, i) => (
                <th key={i}>c{i} (формула)</th>
              ))}
              <th>Выход</th>
              <th>Регистр после</th>
            </tr>
          </thead>
          <tbody>
            {trace.map((row) => (
              <tr key={row.step}
                  style={{
                    background: row.is_tail ? '#fff3cd' : 'white',
                    textAlign: 'center',
                  }}>
                <td>{row.step}{row.is_tail ? ' 🔚' : ''}</td>
                <td><strong>{row.input}</strong></td>
                <td><code>{row.reg_before}</code></td>
                {row.formulas.map((f, i) => (
                  <td key={i} style={{ fontFamily: 'monospace', fontSize: 12 }}>{f}</td>
                ))}
                <td><strong>{row.output_str}</strong></td>
                <td><code>{row.reg_after}</code></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div style={{ marginTop: 10 }}>
        <strong>Кодовое слово парами:</strong>{' '}
        {codeword_pairs.slice(0, message_len).join(' ')}
        {' | '}
        <span style={{ color: '#856404' }}>
          {codeword_pairs.slice(message_len).join(' ')} (хвост)
        </span>
      </div>
    </div>
  );
}

// ── Интерактивная таблица Витерби ───────────────────────────────────────────
function ConvViterbiTable({ payload }) {
  const { num_steps, state_labels, viterbi_steps, description } = payload;
  const [selectedT, setSelectedT] = useState(0);
  const [showAll, setShowAll] = useState(false);

  if (!viterbi_steps || viterbi_steps.length === 0) return null;

  const stepData = viterbi_steps[selectedT];
  const displayTrans = showAll
    ? stepData.transitions
    : stepData.transitions.filter(tr => tr.survived);

  const INF_DISPLAY = '∞';

  return (
    <div>
      <div style={{ marginBottom: 10 }}>
        <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
          {description}
        </ReactMarkdown>
      </div>

      {/* Сводная матрица метрик: состояния × такты */}
      <div style={{ overflowX: 'auto', marginBottom: 16 }}>
        <strong>Метрики состояний по тактам:</strong>
        <table border="1" cellPadding="4"
               style={{ borderCollapse: 'collapse', fontSize: 12, marginTop: 6 }}>
          <thead>
            <tr style={{ background: '#e9f5ff', textAlign: 'center' }}>
              <th>Состояние</th>
              <th>Старт</th>
              {viterbi_steps.map((s, t) => (
                <th key={t}
                    style={{
                      cursor: 'pointer',
                      background: selectedT === t ? '#0066cc' : '#e9f5ff',
                      color: selectedT === t ? 'white' : 'inherit',
                    }}
                    onClick={() => setSelectedT(t)}>
                  t={t + 1}<br />[{s.received_str}]
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {state_labels.map((label, s) => (
              <tr key={s} style={{ textAlign: 'center' }}>
                <td><code><strong>{label}</strong></code></td>
                <td style={{ color: s === 0 ? '#155724' : '#6c757d' }}>
                  {s === 0 ? '0' : INF_DISPLAY}
                </td>
                {viterbi_steps.map((step, t) => {
                  const m = step.metrics_after[s];
                  const isPath = step.transitions.some(
                    tr => tr.survived && tr.to_state === s
                  );
                  return (
                    <td key={t}
                        style={{
                          background: selectedT === t
                            ? (m === null ? '#f8d7da' : isPath ? '#d4edda' : '#fff')
                            : m === null ? '#f8f9fa' : 'white',
                          fontWeight: isPath ? 'bold' : 'normal',
                          color: m === null ? '#6c757d' : 'inherit',
                        }}>
                      {m === null ? INF_DISPLAY : m}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
        <small className="text-muted">
          Нажмите на заголовок такта для просмотра переходов.
          Зелёный — выживший путь.
        </small>
      </div>

      {/* Детальная таблица переходов для выбранного такта */}
      <div>
        <div className="d-flex justify-content-between align-items-center mb-2">
          <strong>
            Такт t={selectedT + 1} — принятые биты: [{stepData.received_str}]
          </strong>
          <button
            className="btn btn-sm btn-outline-secondary"
            onClick={() => setShowAll(v => !v)}>
            {showAll ? 'Только выжившие' : 'Все переходы'}
          </button>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table border="1" cellPadding="4"
                 style={{ borderCollapse: 'collapse', fontSize: 12, width: '100%' }}>
            <thead>
              <tr style={{ background: '#e9f5ff', textAlign: 'center' }}>
                <th>Из</th>
                <th>Вход</th>
                <th>В</th>
                <th>Ожидаемый выход</th>
                <th>HD</th>
                <th>Стар. метрика</th>
                <th>Кандидат</th>
                <th>Выжил?</th>
              </tr>
            </thead>
            <tbody>
              {displayTrans.map((tr, i) => (
                <tr key={i}
                    style={{
                      background: tr.survived ? '#d4edda' : 'white',
                      textAlign: 'center',
                      fontWeight: tr.survived ? 'bold' : 'normal',
                    }}>
                  <td><code>{tr.from_label}</code></td>
                  <td>{tr.input}</td>
                  <td><code>{tr.to_label}</code></td>
                  <td><code>{tr.expected_str}</code></td>
                  <td style={{ color: tr.hd > 0 ? '#dc3545' : '#155724' }}>{tr.hd}</td>
                  <td>{tr.old_metric}</td>
                  <td><strong>{tr.candidate}</strong></td>
                  <td>{tr.survived ? '✓' : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div style={{ marginTop: 6 }}>
          <button disabled={selectedT === 0}
                  className="btn btn-sm btn-outline-primary me-2"
                  onClick={() => setSelectedT(v => v - 1)}>← Пред.</button>
          <button disabled={selectedT === num_steps - 1}
                  className="btn btn-sm btn-outline-primary"
                  onClick={() => setSelectedT(v => v + 1)}>След. →</button>
        </div>
      </div>
    </div>
  );
}

// ── Обратный проход (трассировка) ───────────────────────────────────────────
function ConvTraceback({ payload }) {
  const { description, traceback_rows, decoded_bits, final_metrics, best_state, best_metric } = payload;
  if (!traceback_rows) return null;
  return (
    <div>
      <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
        {description}
      </ReactMarkdown>
      <div style={{ marginTop: 10, overflowX: 'auto' }}>
        <table border="1" cellPadding="5"
               style={{ borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ background: '#e9f5ff', textAlign: 'center' }}>
              <th>Такт t</th>
              <th>Состояние</th>
              <th>Входной бит</th>
              <th>Следующее состояние</th>
              <th>Тип</th>
            </tr>
          </thead>
          <tbody>
            {traceback_rows.map((row) => (
              <tr key={row.t}
                  style={{
                    background: row.is_tail ? '#fff3cd' : 'white',
                    textAlign: 'center',
                  }}>
                <td>{row.t}</td>
                <td><code>{row.state_label}</code></td>
                <td><strong>{row.input}</strong></td>
                <td><code>{row.next_state_label}</code></td>
                <td style={{ color: row.is_tail ? '#856404' : '#155724', fontSize: 12 }}>
                  {row.is_tail ? 'хвост' : 'данные'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {decoded_bits && (
        <div className="alert alert-success mt-3">
          <strong>Декодированное сообщение:</strong>{' '}
          <code>{decoded_bits.join('')}</code>
          {' | '}Финальная метрика: <strong>{best_metric}</strong>
        </div>
      )}
    </div>
  );
}




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
              <div style={{
                background: step.payload.success === false ? '#fee' : '#efe',
                padding: 10,
                borderRadius: 5
              }}>
                {step.payload.success === false ? (
                  <div>
                    {step.payload.description && (
                      <ReactMarkdown
                        remarkPlugins={[remarkMath]}
                        rehypePlugins={[rehypeKatex]}
                      >
                        {step.payload.description}
                      </ReactMarkdown>
                    )}
                  </div>
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

          {/* ── Трассировка кодирования ── */}
          {step.type === 'conv_encode_trace' && (
          <ConvEncodeTrace payload={step.payload} />
          )}

          {/* ── Таблица Витерби ── */}
          {step.type === 'conv_viterbi_table' && (
          <ConvViterbiTable payload={step.payload} />
          )}

          {/* ── Обратный проход ── */}
          {step.type === 'conv_traceback' && (
          <ConvTraceback payload={step.payload} />
          )}



            {/* Неизвестный тип */}
            {!['text','matrix','calc','bit','bm','chien','viterbi','result',
                'rs_syndromes','rs_bm','rs_chien','rs_forney',
                'conv_encode_trace','conv_viterbi_table','conv_traceback'].includes(step.type) && (
              <pre>{JSON.stringify(step.payload, null, 2)}</pre>
            )}
          </div>
        </details>
      ))}
    </div>
  );
}