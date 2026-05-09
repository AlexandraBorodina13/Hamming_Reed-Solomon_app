import { useState } from 'react';
import { encodeHamming, decodeHamming } from '../api/client';
import StepVisualizer from '../components/StepVisualizer';

export default function Hamming() {
  // === Параметры кода ===
  const [m, setM] = useState(3);
  const n = Math.pow(2, m) - 1;
  const k = n - m;

  // === Поля ввода ===
  const [message, setMessage] = useState('1011');
  const [errorPos, setErrorPos] = useState(0);        // для ручного режима
  const [errorMode, setErrorMode] = useState('manual'); // 'manual' | 'auto'

  // === Результаты с сервера ===
  const [codeword, setCodeword] = useState(null);     // закодированное слово
  const [noisy, setNoisy] = useState(null);           // слово с ошибкой
  const [decodeResult, setDecodeResult] = useState(null);
  const [steps, setSteps] = useState(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [positionError, setPositionError] = useState('');

  const [encodeSteps, setEncodeSteps] = useState(null);

  // === Фазы процесса ===
  // 'input' – только ввод сообщения (начало)
  // 'encoded' – сообщение закодировано, показываем кодовое слово и блок внесения ошибок
  // 'noisy' – ошибка внесена, показываем принятое слово и кнопку декодирования
  // 'decoded' – декодирование выполнено, показываем результат и шаги
  const [phase, setPhase] = useState('input');

  // === Обработчики ===

  const handleEncode = async () => {
    setErrorMsg('');
    setLoading(true);
    try {
      const res = await encodeHamming(m, message);
      setCodeword(res.data.codeword);
      setEncodeSteps(res.data.steps || null);     // сохраняем шаги
      setPhase('encoded');
    } catch (err) {
      setErrorMsg(extractError(err));
    }
    setLoading(false);
  };

  const handleIntroduceError = () => {
    if (!codeword) return;
    setPositionError('');
    if (errorMode === 'manual') {
        const pos = Number(errorPos);
        if (!Number.isInteger(pos) || pos < 0 || pos >= n){
            setPositionError(`Позиция должна быть целым числом от 0 до ${n - 1}`);
            return;
        }
        const arr = codeword.split('');
        arr[pos] = arr[pos] === '0' ? '1' : '0';
        setNoisy(arr.join(''));
    } else {
      // автоматический режим: случайная позиция
      const pos = Math.floor(Math.random() * n);
      const arr = codeword.split('');
      arr[pos] = arr[pos] === '0' ? '1' : '0';
      setNoisy(arr.join(''));
      setErrorPos(pos); // покажем, где ошибка
    }
    setPhase('noisy');
  };

  const handleDecode = async () => {
    setErrorMsg('');
    setLoading(true);
    try {
      const res = await decodeHamming(m, noisy);
      setDecodeResult(res.data);
      setSteps(res.data.steps);
      setPhase('decoded');
    } catch (err) {
      setErrorMsg(extractError(err));
    }
    setLoading(false);
  };

  const resetAll = () => {
    setPhase('input');
    setCodeword(null);
    setNoisy(null);
    setDecodeResult(null);
    setSteps(null);
    setErrorMsg('');
  };

  const extractError = (err) => {
    try {
      const detail = err.response?.data?.detail;
      if (Array.isArray(detail)) return detail.map(e => e.msg).join('; ');
      if (typeof detail === 'string') return detail;
    } catch {}
    return err.message || 'Неизвестная ошибка';
  };

  return (
    <div className="container mt-4">
      <div className="card shadow-sm">
        <div className="card-body">
          <h2 className="card-title text-center">Код Хэмминга ({n}, {k})</h2>

          {/* ВЫБОР m */}
          <div className="row mb-3 d-flex justify-content-center">
            <div className="col-md-3">
              <label className="form-label">Параметр m</label>
              <select
                className="form-select"
                value={m}
                onChange={e => { setM(Number(e.target.value)); resetAll(); }}
              >
                {[3,4,5,6].map(v => <option key={v} value={v}>{v}</option>)}
              </select>
              <div className="form-text">n = {n}, k = {k}</div>
            </div>
          </div>

          {/* Идея кодирования — статичное пояснение */}
          <div className="mb-4 p-3 border rounded bg-light text-start">
            <h5>Идея кодирования</h5>
            <p>Код Хэмминга – линейный блочный код. Из <strong>k</strong> информационных битов образуется <strong>n</strong> битов кодового слова. Добавляются <strong>m</strong> (n-k) проверочных бита так, чтобы для любого кодового слова <strong>c</strong> выполнялось равенство:</p>
            <p className="text-center"><strong>H·c<sup>T</sup> = 0 (mod 2)</strong>,</p>
            <p>где <strong>H</strong> – проверочная матрица m×n, столбцы которой – все ненулевые m-битные векторы.</p>
            <p>Проверочные биты размещаются на <strong>позициях, которые являются степенями двойки</strong> (при 1-индексации: 1,2,4). В 0-индексации это позиции 0,1,3. Информационные биты – на остальных позициях (2,4,5,6). Такое размещение делает код <strong>систематическим</strong>: первые проверочные, потом информационные, но с пропуском позиции 3 для третьего проверочного.</p>
          </div>

          {/* === ФАЗА 1: ВВОД И КОДИРОВАНИЕ === */}
            <div className="mb-4 p-3 border rounded bg-light">
              <h5>1. Кодирование</h5>
              <input
                className="form-control mb-2"
                placeholder="Введите сообщение"
                value={message}
                onChange={e => setMessage(e.target.value)}
              />
              <button
                className="btn btn-success"
                onClick={handleEncode}
                disabled={loading || message.length !== k}
                >
                {loading ? 'Кодируем...' : 'Закодировать'}
              </button>

              {/* Результат кодирования и шаги (появляются только после успешного кодирования) */}
              {codeword && (
                <>
                  <div className="alert alert-success mt-3">
                  Кодовое слово: <strong>{codeword}</strong>
                </div>
                  {encodeSteps && (
                    <div className="text-start mt-3">
                      <StepVisualizer steps={encodeSteps} />
                    </div>
                  )}
                </>
              )}
            </div>

          {/* === ФАЗА 2: ВНЕСЕНИЕ ОШИБОК === */}
          {phase !== 'input' && (
            <div className="mb-4 p-3 border rounded bg-light">
              <h5>2. Внесение ошибок</h5>
              <div className="mb-2">
                <div className="form-check form-check-inline">
                  <input
                    className="form-check-input"
                    type="radio"
                    checked={errorMode === 'manual'}
                    onChange={() => setErrorMode('manual')}
                  />
                  <label className="form-check-label">Ручная позиция</label>
                </div>
                <div className="form-check form-check-inline">
                  <input
                    className="form-check-input"
                    type="radio"
                    checked={errorMode === 'auto'}
                    onChange={() => setErrorMode('auto')}
                  />
                  <label className="form-check-label">Случайная ошибка</label>
                </div>
              </div>
              {errorMode === 'manual' && (
                <div className="row d-flex justify-content-center mb-2">
                    <div className="col-md-3">
                    <input
                        className="form-control mb-2"
                        type="number"
                        min="0"
                        max={n - 1}
                        value={errorPos}
                        onChange={e => {
                        setErrorPos(e.target.value);
                        setPositionError('');
                    }}
                    />
                    {positionError && <div className="text-danger mb-2">{positionError}</div>}
                    </div>
                </div>
              )}
              <button className="btn btn-warning" onClick={handleIntroduceError}>
                Внести ошибку
              </button>
              {noisy && (
                <div className="alert alert-info mt-2">
                  Принятое слово: <strong>{noisy}</strong>
                  {errorMode === 'auto' && <span> (ошибка в позиции {errorPos})</span>}
                </div>
              )}
            </div>
          )}

          {/* === ФАЗА 3: ДЕКОДИРОВАНИЕ === */}
          {phase === 'noisy' && (
            <div className="mb-4 p-3 border rounded bg-light">
              <h5>3. Декодирование</h5>
              <button
                className="btn btn-primary"
                onClick={handleDecode}
                disabled={loading}
              >
                {loading ? 'Декодируем...' : 'Декодировать и показать шаги'}
              </button>
            </div>
          )}

          {/* === ФАЗА 4: РЕЗУЛЬТАТ === */}
          {phase === 'decoded' && decodeResult && (
            <div className="mb-4 p-3 border rounded bg-light">
              <h5>4. Результат</h5>
              <div className="alert alert-success">
                Декодированное сообщение: <strong>{decodeResult.decoded}</strong>
              </div>
              {decodeResult.error_positions?.length > 0 && (
                <p>Ошибки исправлены в позициях: {decodeResult.error_positions.join(', ')}</p>
              )}
              <div className="text-start mt-3">
                <StepVisualizer steps={steps} />
              </div>
              {/* Кнопки экспорта можно добавить позже */}
              {/* <button className="btn btn-secondary">Скачать HTML-отчёт</button> */}
            </div>
          )}

          {/* Ошибки */}
          {errorMsg && <div className="alert alert-danger">{errorMsg}</div>}

          {/* Сброс */}
          {phase !== 'input' && (
            <button className="btn btn-outline-danger" onClick={resetAll}>
              Сбросить всё
            </button>
          )}
        </div>
      </div>
    </div>
  );
}