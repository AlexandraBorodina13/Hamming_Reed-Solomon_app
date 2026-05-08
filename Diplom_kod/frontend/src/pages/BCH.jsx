import { useState, useEffect } from 'react';
import { encodeBCH, decodeBCH } from '../api/client';
import StepVisualizer from '../components/StepVisualizer';

const BCH_PRESETS = {
  "BCH(7,4) t=1":    { n: 7,  k: 4,  t: 1 },
  "BCH(15,7) t=2":   { n: 15, k: 7,  t: 2 },
  "BCH(15,5) t=3":   { n: 15, k: 5,  t: 3 },
  "BCH(31,21) t=2":  { n: 31, k: 21, t: 2 },
  "BCH(31,16) t=3":  { n: 31, k: 16, t: 3 },
  "BCH(31,11) t=5":  { n: 31, k: 11, t: 5 },
  "BCH(63,51) t=2":  { n: 63, k: 51, t: 2 },
  "BCH(63,45) t=3":  { n: 63, k: 45, t: 3 },
  "BCH(63,39) t=4":  { n: 63, k: 39, t: 4 },
  "BCH(63,36) t=5":  { n: 63, k: 36, t: 5 },
  "BCH(63,30) t=6":  { n: 63, k: 30, t: 6 },
  "BCH(63,24) t=7":  { n: 63, k: 24, t: 7 },
  "BCH(63,18) t=10": { n: 63, k: 18, t: 10 },
  "BCH(63,16) t=11": { n: 63, k: 16, t: 11 },
  "BCH(63,10) t=13": { n: 63, k: 10, t: 13 },
  "BCH(63,7) t=15":  { n: 63, k: 7,  t: 15 },
};

export default function BCH() {
  const [preset, setPreset] = useState("BCH(15,7) t=2");
  const params = BCH_PRESETS[preset];
  const { n, k, t } = params;

  const [message, setMessage] = useState('1110110'); // длина 7
  const [errorMode, setErrorMode] = useState('manual');
  //const [errorPos, setErrorPos] = useState(0);
  const [manualPositions, setManualPositions] = useState('');  // для ручного ввода нескольких позиций
  const [autoErrorPos, setAutoErrorPos] = useState([]);        // для отображения позиций автогенерации (опционально)
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
    setLoading(true);
    try {
      const res = await encodeBCH(preset, message);
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
    // --- обработка списка позиций ---
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
    if (posArray.length > t) {
      setPositionError(`Слишком много ошибок! Код может исправить не более ${t}.`);
      return;
    }
    const arr = codeword.split('');
    for (const pos of posArray) {
      arr[pos] = arr[pos] === '0' ? '1' : '0';
    }
    setNoisy(arr.join(''));
    setAutoErrorPos(posArray); // сохраняем для информации, если нужно
  } else {
    // автоматический режим остаётся без изменений
    if (numAutoErrors > t) {
      setPositionError(`Слишком много ошибок! Максимум: ${t}`);
      return;
    }
    const count = Math.min(numAutoErrors, n);
    const positions = [];
    const used = new Set();
    while (positions.length < count) {
      const p = Math.floor(Math.random() * n);
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
    setAutoErrorPos(positions);
  }
  setPhase('noisy');
};

  const handleDecode = async () => {
    setErrorMsg('');
    setLoading(true);
    try {
      const res = await decodeBCH(preset, noisy);
      setDecodeResult({ decoded: res.data.decoded, error_positions: res.data.error_positions });
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
          <h2 className="card-title text-center">Код БЧХ</h2>

          {/* Выбор пресета */}
          <div className="row mb-3 d-flex justify-content-center">
            <div className="col-md-4">
              <label className="form-label">Конфигурация кода</label>
              <select className="form-select" value={preset} onChange={e => setPreset(e.target.value)}>
                {Object.keys(BCH_PRESETS).map(key => (
                  <option key={key} value={key}>{key}</option>
                ))}
              </select>
              <div className="form-text">
                n = {n}, k = {k}, исправляет до {t} ошибок
              </div>
            </div>
          </div>

          {/* 1. Кодирование */}
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
          </div>

          {/* 2. Внесение ошибок */}
          {phase !== 'input' && (
            <div className="mb-4 p-3 border rounded bg-light">
              <h5>2. Внесение ошибок</h5>
              <div className="alert alert-success">
                Кодовое слово: <strong>{codeword}</strong>
              </div>
              <div className="mb-2">
                <div className="form-check form-check-inline">
                  <input className="form-check-input" type="radio" checked={errorMode === 'manual'} onChange={() => setErrorMode('manual')} />
                  <label className="form-check-label">Ручная позиция</label>
                </div>
                <div className="form-check form-check-inline">
                  <input className="form-check-input" type="radio" checked={errorMode === 'auto'} onChange={() => setErrorMode('auto')} />
                  <label className="form-check-label">Случайные ошибки</label>
                </div>
              </div>
              {errorMode === 'manual' && (
                <>
                <div className="row d-flex justify-content-center mb-2">
                  <div className="col-md-4">
                    <label className="form-label">Позиция ошибки (через запятую)</label>
                    <input 
                      className="form-control" 
                      placeholder="0, 5, 10"
                      value={manualPositions} 
                      onChange={e => { 
                        setManualPositions(e.target.value); 
                        setPositionError(''); }} />
                    
                  </div>
                </div>
                {positionError && <div className="text-danger mt-1">{positionError}</div>}
                </>
              )}
              {errorMode === 'auto' && (
                <div className="row d-flex justify-content-center mb-2">
                  <div className="col-md-2">
                    <label className="form-label">Количество ошибок</label>
                    <input className="form-control" type="number" min="0" max={t} value={numAutoErrors} onChange={e => setNumAutoErrors(Number(e.target.value))} />
                    <div className="form-text">Максимум: {t}</div>
                  </div>
                </div>
              )}
              <button className="btn btn-warning" onClick={handleIntroduceError}>Внести ошибки</button>
              {noisy && (
                  <div className="alert alert-info mt-2">
                  Принятое слово: <strong>{noisy}</strong>
                  {autoErrorPos.length > 0 && (
                  <div>Ошибки внесены в позициях: {autoErrorPos.join(', ')}</div>
                )}
            </div>
          )}
            </div>
          )}

          {/* 3. Декодирование */}
          {phase === 'noisy' && (
            <div className="mb-4 p-3 border rounded bg-light">
              <h5>3. Декодирование</h5>
              <button className="btn btn-primary" onClick={handleDecode} disabled={loading}>
                {loading ? 'Декодируем...' : 'Декодировать и показать шаги'}
              </button>
            </div>
          )}

          {/* 4. Результат */}
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
            </div>
          )}

          {errorMsg && <div className="alert alert-danger">{errorMsg}</div>}

          {phase !== 'input' && (
            <button className="btn btn-outline-danger mt-2" onClick={resetAll}>Сбросить всё</button>
          )}
        </div>
      </div>
    </div>
  );
}