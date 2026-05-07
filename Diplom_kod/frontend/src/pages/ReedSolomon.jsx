import { useState, useEffect, useRef } from 'react';
import { encodeRS, decodeRSAsync, getRSTaskStatus } from '../api/client';
import StepVisualizer from '../components/StepVisualizer';

// Локальный словарь пресетов (синхронизирован с RS_PRESETS)
const RS_PRESETS = {
  "RS(255,223) – GF(2^8), t=16": { n: 255, k: 223, m: 8, t: 16 },
  "RS(255,239) – GF(2^8), t=8":  { n: 255, k: 239, m: 8, t: 8 },
  "RS(255,191) – GF(2^8), t=32": { n: 255, k: 191, m: 8, t: 32 },
  "RS(255,127) – GF(2^8), t=64": { n: 255, k: 127, m: 8, t: 64 }
};

export default function ReedSolomon() {
  // === Параметры ===
  const [preset, setPreset] = useState("RS(255,223) – GF(2^8), t=16");
  const params = RS_PRESETS[preset];
  const { n, k, t } = params;

  // === Поля ввода ===
  const [message, setMessage] = useState('Hello RS!');
  const [errorMode, setErrorMode] = useState('manual');
  const [manualPositions, setManualPositions] = useState('');
  const [manualMagnitudes, setManualMagnitudes] = useState('');
  const [numAutoErrors, setNumAutoErrors] = useState(1);

  // === Состояния процесса ===
  const [codeword, setCodeword] = useState(null);   // массив чисел
  const [noisy, setNoisy] = useState(null);
  const [errorPositions, setErrorPositions] = useState([]);
  const [decodeResult, setDecodeResult] = useState(null);
  const [steps, setSteps] = useState(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [positionError, setPositionError] = useState('');

  const [phase, setPhase] = useState('input');  // input|encoded|noisy|decoding|decoded
  const pollRef = useRef(null);

  // Сброс всего, кроме параметров
  const resetAll = () => {
    if (pollRef.current) clearTimeout(pollRef.current);
    setPhase('input');
    setCodeword(null);
    setNoisy(null);
    setErrorPositions([]);
    setDecodeResult(null);
    setSteps(null);
    setErrorMsg('');
    setPositionError('');
  };

  // При смене пресета сбрасываем процесс
  useEffect(() => {
    resetAll();
  }, [preset]);

  const extractError = (err) => {
    try {
      const detail = err.response?.data?.detail;
      if (Array.isArray(detail)) return detail.map(e => e.msg).join('; ');
      if (typeof detail === 'string') return detail;
    } catch {}
    return err.message || 'Неизвестная ошибка';
  };

  // ============ ОБРАБОТЧИКИ ============
  const handleEncode = async () => {
    setErrorMsg('');
    setLoading(true);
    try {
      const res = await encodeRS(preset, message);
      // ответ: { codeword: "числа,через,запятую", params: ... }
      setCodeword(res.data.codeword.split(',').map(Number));
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
      const posStr = manualPositions.trim();
      if (!posStr) {
        setPositionError('Введите хотя бы одну позицию');
        return;
      }
      const posArray = posStr.split(',').map(s => parseInt(s.trim()));
      if (posArray.some(isNaN)) {
        setPositionError('Все позиции должны быть целыми числами');
        return;
      }
      if (posArray.some(p => p < 0 || p >= n)) {
        setPositionError(`Позиции должны быть от 0 до ${n - 1}`);
        return;
      }

      let magArray = null;
      if (manualMagnitudes.trim()) {
        const magStr = manualMagnitudes.trim();
        magArray = magStr.split(',').map(s => parseInt(s.trim()));
        if (magArray.some(isNaN) || magArray.some(v => v < 1 || v > 255)) {
          setPositionError('Величины ошибок должны быть целыми числами от 1 до 255');
          return;
        }
        if (magArray.length !== posArray.length) {
          setPositionError('Количество величин ошибок должно совпадать с количеством позиций');
          return;
        }
      }

      const noisyArr = [...codeword];
      for (let i = 0; i < posArray.length; i++) {
        const pos = posArray[i];
        const errVal = magArray ? magArray[i] : Math.floor(Math.random() * 255) + 1;
        noisyArr[pos] = (noisyArr[pos] + errVal) % 256;
      }
      setNoisy(noisyArr);
      setErrorPositions(posArray);
    } else {
      // Автоматический режим
      const count = Math.min(numAutoErrors, n);
      const positions = [];
      const used = new Set();
      while (positions.length < count) {
        const pos = Math.floor(Math.random() * n);
        if (!used.has(pos)) {
          used.add(pos);
          positions.push(pos);
        }
      }
      const noisyArr = [...codeword];
      for (const pos of positions) {
        const errVal = Math.floor(Math.random() * 255) + 1;
        noisyArr[pos] = (noisyArr[pos] + errVal) % 256;
      }
      setNoisy(noisyArr);
      setErrorPositions(positions);
    }
    setPhase('noisy');
  };

  const handleDecode = async () => {
    setErrorMsg('');
    setLoading(true);
    try {
      const res = await decodeRSAsync(preset, noisy.join(','));
      const taskId = res.data.task_id;
      setPhase('decoding');
      pollTask(taskId);
    } catch (err) {
      setErrorMsg(extractError(err));
      setLoading(false);
    }
  };

  const pollTask = async (taskId) => {
    try {
      const res = await getRSTaskStatus(taskId);
      const { status, result, steps } = res.data;
      if (status === 'done') {
        setDecodeResult(result);
        setSteps(steps);
        setPhase('decoded');
        setLoading(false);
      } else if (status === 'error') {
        setErrorMsg('Ошибка декодирования: ' + (res.data.detail || 'неизвестно'));
        setPhase('noisy');
        setLoading(false);
      } else {
        pollRef.current = setTimeout(() => pollTask(taskId), 1000);
      }
    } catch (err) {
      setErrorMsg('Ошибка при опросе статуса: ' + extractError(err));
      setPhase('noisy');
      setLoading(false);
    }
  };

  // ============ РЕНДЕР ============
  return (
    <div className="container mt-4">
      <div className="card shadow-sm">
        <div className="card-body">
          <h2 className="card-title text-center">Код Рида–Соломона</h2>

          {/* БЛОК ВЫБОРА ПРЕСЕТА */}
          <div className="row mb-3 d-flex justify-content-center">
            <div className="col-md-4">
              <label className="form-label">Конфигурация кода</label>
              <select
                className="form-select"
                value={preset}
                onChange={e => setPreset(e.target.value)}
              >
                {Object.keys(RS_PRESETS).map(key => (
                  <option key={key} value={key}>{key}</option>
                ))}
              </select>
              <div className="form-text">
                n = {n}, k = {k}, исправляет до {t} ошибок
              </div>
            </div>
          </div>

          {/* === ФАЗА 1: КОДИРОВАНИЕ === */}
          <div className="mb-4 p-3 border rounded bg-light">
            <h5>1. Кодирование</h5>
            <textarea
              className="form-control mb-2"
              rows="2"
              placeholder="Введите текст сообщения"
              value={message}
              onChange={e => setMessage(e.target.value)}
              maxLength={k}
            />
            <small className="text-muted">
              Сообщение будет обрезано или дополнено до {k} байт
            </small>
            <br />
            <button
              className="btn btn-success mt-2"
              onClick={handleEncode}
              disabled={loading}
            >
              {loading ? 'Кодируем...' : 'Закодировать'}
            </button>
          </div>

          {/* === ФАЗА 2: ВНЕСЕНИЕ ОШИБОК === */}
          {phase !== 'input' && (
            <div className="mb-4 p-3 border rounded bg-light">
              <h5>2. Внесение ошибок</h5>
              <div className="alert alert-success">
                <strong>Кодовое слово:</strong> [{codeword?.join(', ')}]
              </div>

              <div className="mb-2">
                <div className="form-check form-check-inline">
                  <input
                    className="form-check-input"
                    type="radio"
                    checked={errorMode === 'manual'}
                    onChange={() => setErrorMode('manual')}
                  />
                  <label className="form-check-label">Ручной ввод</label>
                </div>
                <div className="form-check form-check-inline">
                  <input
                    className="form-check-input"
                    type="radio"
                    checked={errorMode === 'auto'}
                    onChange={() => setErrorMode('auto')}
                  />
                  <label className="form-check-label">Автоматически</label>
                </div>
              </div>

              {errorMode === 'manual' && (
                <>
                  <div className="row d-flex justify-content-center mb-2">
                    <div className="col-md-4">
                      <label className="form-label">Позиции ошибок (через запятую)</label>
                      <input
                        className="form-control"
                        placeholder="0, 5, 10"
                        value={manualPositions}
                        onChange={e => { setManualPositions(e.target.value); setPositionError(''); }}
                      />
                    </div>
                  </div>
                  <div className="row d-flex justify-content-center mb-2">
                    <div className="col-md-4">
                      <label className="form-label">Величины ошибок (1-255, опционально)</label>
                      <input
                        className="form-control"
                        placeholder="1, 128, 255"
                        value={manualMagnitudes}
                        onChange={e => { setManualMagnitudes(e.target.value); setPositionError(''); }}
                      />
                    </div>
                  </div>
                  {positionError && <div className="text-danger mb-2">{positionError}</div>}
                </>
              )}

              {errorMode === 'auto' && (
                <div className="row d-flex justify-content-center mb-2">
                  <div className="col-md-2">
                    <label className="form-label">Количество ошибок</label>
                    <input
                      className="form-control"
                      type="number"
                      min="0"
                      max={Math.floor((n - k) / 2)}
                      value={numAutoErrors}
                      onChange={e => setNumAutoErrors(Number(e.target.value))}
                    />
                  </div>
                </div>
              )}

              <button className="btn btn-warning" onClick={handleIntroduceError}>
                Внести ошибки
              </button>

              {noisy && (
                <div className="alert alert-info mt-2">
                  <strong>Принятое слово:</strong> [{noisy.join(', ')}]
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

          {/* ФАЗА ОЖИДАНИЯ */}
          {phase === 'decoding' && (
            <div className="mb-4 p-3 border rounded bg-light text-center">
              <div className="spinner-border text-primary" role="status">
                <span className="visually-hidden">Идёт декодирование...</span>
              </div>
              <p className="mt-2">Идёт декодирование, пожалуйста, подождите...</p>
            </div>
          )}

          {/* === ФАЗА 4: РЕЗУЛЬТАТ === */}
          {phase === 'decoded' && decodeResult && (
            <div className="mb-4 p-3 border rounded bg-light">
              <h5>4. Результат</h5>
              <div className="alert alert-success">
                Декодированное сообщение: <strong>{decodeResult.decoded}</strong>
              </div>
              <div className="text-start mt-3">
                {steps ? (
                  <StepVisualizer steps={steps} />
                ) : (
                  <p>Шаги декодирования отсутствуют.</p>
                )}
              </div>
            </div>
          )}

          {/* ОШИБКИ */}
          {errorMsg && <div className="alert alert-danger">{errorMsg}</div>}

          {/* КНОПКА СБРОСА */}
          {phase !== 'input' && (
            <button className="btn btn-outline-danger mt-2" onClick={resetAll}>
              Сбросить всё
            </button>
          )}
        </div>
      </div>
    </div>
  );
}