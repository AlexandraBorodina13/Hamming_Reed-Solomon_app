import { useState, useEffect } from 'react';
import { encodeConvolutional, decodeConvolutional } from '../api/client';
import StepVisualizer from '../components/StepVisualizer';

const MAX_ERRORS_MAP = {
  "K=3, R=1/2 (7,5)": 2,
  "K=3, R=1/3 (7,5,3)": 3,
  "K=4, R=1/2 (13,17)": 2,
  "K=5, R=1/2 (23,35)": 3,
  "K=6, R=1/2 (53,75)": 3,
  "K=7, R=1/2 (133,171)": 4,
};

// Локальный словарь пресетов (оставлен для информации, но параметры кода уже есть в MAX_ERRORS_MAP)
const CONVOLUTIONAL_PRESETS = {
  "K=3, R=1/2 (7,5)":     { constraint_length: 3, rate_num: 1, rate_den: 2, generators: [7, 5] },
  "K=3, R=1/3 (7,5,3)":   { constraint_length: 3, rate_num: 1, rate_den: 3, generators: [7, 5, 3] },
  "K=4, R=1/2 (13,17)":   { constraint_length: 4, rate_num: 1, rate_den: 2, generators: [13, 17] },
  "K=5, R=1/2 (23,35)":   { constraint_length: 5, rate_num: 1, rate_den: 2, generators: [23, 35] },
  "K=6, R=1/2 (53,75)":   { constraint_length: 6, rate_num: 1, rate_den: 2, generators: [53, 75] },
  "K=7, R=1/2 (133,171)": { constraint_length: 7, rate_num: 1, rate_den: 2, generators: [133, 171] },
};

export default function Convolutional() {
  const [preset, setPreset] = useState("K=3, R=1/2 (7,5)");
  const params = CONVOLUTIONAL_PRESETS[preset];
  const maxErrors = MAX_ERRORS_MAP[preset];
  const { constraint_length, rate_num, rate_den, generators } = params;
  const memory = constraint_length - 1;
  const numStates = Math.pow(2, memory);
  const rateStr = `${rate_num}/${rate_den}`;

  const [message, setMessage] = useState('101010');
  const [errorMode, setErrorMode] = useState('manual');
  const [manualPositions, setManualPositions] = useState('');
  const [numAutoErrors, setNumAutoErrors] = useState(1);

  const [codeword, setCodeword] = useState(null);
  const [noisy, setNoisy] = useState(null);
  const [decodeResult, setDecodeResult] = useState(null);
  const [steps, setSteps] = useState(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [positionError, setPositionError] = useState('');

  const [phase, setPhase] = useState('input');

  useEffect(() => {
    resetAll();
  }, [preset]);

  const resetAll = () => {
    setPhase('input');
    setCodeword(null);
    setNoisy(null);
    setDecodeResult(null);
    setSteps(null);
    setErrorMsg('');
    setPositionError('');
    setManualPositions('');
    setNumAutoErrors(1);
  };

  const extractError = (err) => {
    try {
      const detail = err.response?.data?.detail;
      if (Array.isArray(detail)) return detail.map(e => e.msg).join('; ');
      if (typeof detail === 'string') return detail;
    } catch {}
    return err.message || 'Неизвестная ошибка';
  };

  const handleEncode = async () => {
    setErrorMsg('');
    if (!/^[01]+$/.test(message)) {
      setErrorMsg('Сообщение должно содержать только 0 и 1');
      return;
    }
    setLoading(true);
    try {
      const res = await encodeConvolutional(preset, message);
      setCodeword(res.data.codeword);
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
      if (posArray.some(p => p < 0 || p >= codeword.length)) {
        setPositionError(`Позиции должны быть от 0 до ${codeword.length - 1}`);
        return;
      }
      if (posArray.length > maxErrors) {
        setPositionError(`Слишком много ошибок! Код может исправить не более ${maxErrors}.`);
        return;
      }
      const arr = codeword.split('');
      for (const pos of posArray) {
        arr[pos] = arr[pos] === '0' ? '1' : '0';
      }
      setNoisy(arr.join(''));
    } else {
      if (numAutoErrors < 0 || numAutoErrors > maxErrors) {
        setPositionError(`Количество ошибок должно быть от 0 до ${maxErrors}.`);
        return;
      }
      const count = Math.min(numAutoErrors, codeword.length); // на случай, если длина меньше
      const positions = [];
      const used = new Set();
      while (positions.length < count) {
        const p = Math.floor(Math.random() * codeword.length);
        if (!used.has(p)) {
          used.add(p);
          positions.push(p);
        }
      }
      const arr = codeword.split('');
      for (const p of positions) {
        arr[p] = arr[p] === '0' ? '1' : '0';
      }
      setNoisy(arr.join(''));
    }
    setPhase('noisy');
  };

  const handleDecode = async () => {
    setErrorMsg('');
    setLoading(true);
    try {
      const res = await decodeConvolutional(preset, noisy);
      setDecodeResult(res.data);
      setSteps(res.data.steps);
      setPhase('decoded');
    } catch (err) {
      setErrorMsg(extractError(err));
    }
    setLoading(false);
  };

  return (
    <div className="container mt-4">
      <div className="card shadow-sm">
        <div className="card-body">
          <h2 className="card-title text-center">Свёрточный код</h2>

          <div className="row mb-3 d-flex justify-content-center">
            <div className="col-md-4">
              <label className="form-label">Конфигурация кода</label>
              <select
                className="form-select"
                value={preset}
                onChange={e => setPreset(e.target.value)}
              >
                {Object.keys(CONVOLUTIONAL_PRESETS).map(key => (
                  <option key={key} value={key}>{key}</option>
                ))}
              </select>
              <div className="form-text">
                K = {constraint_length}, R = {rateStr}, память m = {memory}, состояний = {numStates}<br />
                Порождающие полиномы (восьм.): {generators.join(', ')}
                <br />
                Исправляет ошибок: до {maxErrors}
              </div>
            </div>
          </div>

          <div className="mb-4 p-3 border rounded bg-light">
            <h5>1. Кодирование</h5>
            <input
              className="form-control mb-2"
              placeholder="Введите сообщение (только 0 и 1)"
              value={message}
              onChange={e => setMessage(e.target.value)}
            />
            <button
              className="btn btn-success"
              onClick={handleEncode}
              disabled={loading}
            >
              {loading ? 'Кодируем...' : 'Закодировать'}
            </button>
          </div>

          {phase !== 'input' && (
            <div className="mb-4 p-3 border rounded bg-light">
              <h5>2. Внесение ошибок</h5>
              <div className="alert alert-success">
                <strong>Кодовое слово:</strong> {codeword}<br />
                <small>Длина: {codeword?.length} бит</small>
              </div>

              <div className="mb-2">
                <div className="form-check form-check-inline">
                  <input
                    className="form-check-input"
                    type="radio"
                    checked={errorMode === 'manual'}
                    onChange={() => setErrorMode('manual')}
                  />
                  <label className="form-check-label">Ручной ввод позиций</label>
                </div>
                <div className="form-check form-check-inline">
                  <input
                    className="form-check-input"
                    type="radio"
                    checked={errorMode === 'auto'}
                    onChange={() => setErrorMode('auto')}
                  />
                  <label className="form-check-label">Случайные ошибки</label>
                </div>
              </div>

              {errorMode === 'manual' && (
                <>
                  <div className="row d-flex justify-content-center mb-2">
                    <div className="col-md-4">
                      <label className="form-label">Позиции ошибок (через запятую, макс. {maxErrors})</label>
                      <input
                        className="form-control"
                        placeholder="0, 3, 5"
                        value={manualPositions}
                        onChange={e => {
                          setManualPositions(e.target.value);
                          setPositionError('');
                        }}
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
                      max={maxErrors}
                      value={numAutoErrors}
                      onChange={e => setNumAutoErrors(Number(e.target.value))}
                    />
                    <div className="form-text">Макс. {maxErrors}</div>
                  </div>
                </div>
              )}

              <button className="btn btn-warning" onClick={handleIntroduceError}>
                Внести ошибки
              </button>

              {noisy && (
                <div className="alert alert-info mt-2">
                  <strong>Принятое слово:</strong> {noisy}<br />
                  <small>Длина: {noisy.length} бит</small>
                </div>
              )}
            </div>
          )}

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

          {phase === 'decoded' && decodeResult && (
            <div className="mb-4 p-3 border rounded bg-light">
              <h5>4. Результат</h5>
              <div className="alert alert-success">
                Декодированное сообщение: <strong>{decodeResult.decoded}</strong>
                {decodeResult.final_metric !== undefined && (
                  <span> &nbsp; (финальная метрика: {decodeResult.final_metric})</span>
                )}
              </div>
              <div className="text-start mt-3">
                <StepVisualizer steps={steps} />
              </div>
            </div>
          )}

          {errorMsg && <div className="alert alert-danger">{errorMsg}</div>}

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