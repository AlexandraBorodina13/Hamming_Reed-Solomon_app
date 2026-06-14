import { useState, useEffect, useMemo } from 'react';
import { getComparisonInfo } from '../api/client';
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ZAxis,
  BarChart, Bar, LineChart, Line
} from 'recharts';

const TYPE_COLORS = {
  'Хэмминг': '#8884d8',
  'БЧХ': '#82ca9d',
  'Рид–Соломон': '#ffc658',
  'Свёрточный': '#ff7300'   // для линий можно использовать тот же цвет
};

export default function Comparison() {
  const [data, setData] = useState([]);
  const [filterType, setFilterType] = useState('Все');
  const [sortKey, setSortKey] = useState(null);
  const [sortDir, setSortDir] = useState('asc');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    setLoading(true);
    getComparisonInfo()
      .then(res => setData(res.data.codes))
      .catch(err => setError('Ошибка загрузки данных: ' + (err.response?.data?.detail || err.message)))
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    if (filterType === 'Все') return data;
    return data.filter(c => c.type === filterType);
  }, [data, filterType]);

  const sorted = useMemo(() => {
    if (!sortKey) return filtered;
    const dir = sortDir === 'asc' ? 1 : -1;
    return [...filtered].sort((a, b) => {
      const valA = typeof a[sortKey] === 'string' ? a[sortKey] : Number(a[sortKey]);
      const valB = typeof b[sortKey] === 'string' ? b[sortKey] : Number(b[sortKey]);
      if (valA < valB) return -1 * dir;
      if (valA > valB) return 1 * dir;
      return 0;
    });
  }, [filtered, sortKey, sortDir]);

  const types = useMemo(() => ['Все', ...new Set(data.map(c => c.type))], [data]);

  // Scatter-plot: только блоковые коды (как раньше)
  const scatterData = useMemo(() => {
    return data
      .filter(c => c.type !== 'Свёрточный')
      .map(c => {
        let y = 0;
        const match = c.error_capability.match(/t\s*=\s*(\d+)/);
        if (match) y = Number(match[1]) / c.n;
        return { ...c, y };
      });
  }, [data]);

  // Данные для свёрточных кодов (как раньше)
  const convData = useMemo(() => {
    return data
      .filter(c => c.type === 'Свёрточный')
      .map(c => {
        const match = c.error_capability.match(/d_free\s*=\s*(\d+)/);
        const d_free = match ? Number(match[1]) : 0;
        let K = 3;
        if (typeof c.n === 'string') {
          const kmatch = c.n.match(/K=(\d+)/);
          if (kmatch) K = Number(kmatch[1]);
        }
        const shortName = c.preset.replace(/,?\s*R=/, ', ');
        return { ...c, d_free, K, shortName };
      });
  }, [data]);

  // Данные для графика BER
  const berChartData = useMemo(() => {
    // Собираем все уникальные SNR из всех кодов
    const snrSet = new Set();
    data.forEach(code => {
      code.ber_samples?.forEach(p => snrSet.add(p.snr));
    });
    const snrList = Array.from(snrSet).sort((a, b) => a - b);
    const result = [];
    // Для каждого SNR создаём точку с полями-именами пресетов
    snrList.forEach(snr => {
      const point = { snr };
      data.forEach(code => {
        const sample = code.ber_samples?.find(s => s.snr === snr);
        if (sample) point[code.preset] = sample.ber;
      });
      result.push(point);
    });
    return result;
  }, [data]);

  const handleSort = (key) => {
    if (sortKey === key) {
      setSortDir(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  if (loading) return <p>Загрузка...</p>;
  if (error) return <div className="alert alert-danger">{error}</div>;

  // Таблица со столбцами сложности
  const columns = [
    'type', 'preset', 'n', 'k', 'rate', 'redundancy',
    'error_capability', 'field_size', 'complexity_time', 'complexity_memory', 'notes'
  ];

  return (
    <div className="container-xxl mt-4">
      <h2 className="text-center mb-4">Сравнительный анализ кодов</h2>

      <div className="card mb-4">
        <div className="card-body">
          <h5>Компромисс между скоростью, избыточностью и исправляющей способностью</h5>
          <p>
            Скорость кода <em>R = k/n</em> показывает долю полезной информации.
            Чем выше скорость, тем меньше избыточных символов, но и слабее защита от ошибок.
            БЧХ и РС позволяют гибко настраивать число исправляемых ошибок <em>t</em> ценой снижения скорости.
            Свёрточные коды работают с потоком данных и характеризуются длиной кодового ограничения <em>K</em>
            и скоростью, а их исправляющая способность определяется свободным расстоянием <em>d<sub>free</sub></em>.
          </p>
        </div>
      </div>

      <div className="mb-3">
        <label className="me-2">Тип кода:</label>
        <select
          className="form-select w-auto d-inline-block"
          value={filterType}
          onChange={e => setFilterType(e.target.value)}
        >
          {types.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
      </div>

      <div className="table-responsive">
        <table className="table table-bordered table-hover">
          <thead className="table-light">
            <tr>
              {columns.map(key => (
                <th
                  key={key}
                  style={{ cursor: 'pointer', userSelect: 'none' }}
                  onClick={() => handleSort(key)}
                >
                  {{
                    type: 'Тип', preset: 'Конфигурация', n: 'n', k: 'k',
                    rate: 'Скорость R', redundancy: 'Избыточность',
                    error_capability: 'Исправление', field_size: 'Размер поля',
                    complexity_time: 'Врем. сложность', complexity_memory: 'Память',
                    notes: 'Примечание'
                  }[key]}
                  {sortKey === key && (sortDir === 'asc' ? ' ▲' : ' ▼')}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((code, idx) => (
              <tr key={idx}>
                <td>{code.type}</td>
                <td><code>{code.preset}</code></td>
                <td>{code.n}</td>
                <td>{code.k}</td>
                <td>{code.rate}</td>
                <td>{code.redundancy}</td>
                <td>{code.error_capability}</td>
                <td>{code.field_size}</td>
                <td>{code.complexity_time || '—'}</td>
                <td>{code.complexity_memory || '—'}</td>
                <td style={{ fontSize: '0.9em' }}>{code.notes}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* График эффективности блоковых кодов (t/n vs R) */}
      {scatterData.length > 0 && (
        <div className="mt-5">
          <h5>Эффективность блоковых кодов (нормированная исправляющая способность vs скорость)</h5>
          <ResponsiveContainer width="100%" height={400}>
            <ScatterChart>
              <CartesianGrid />
              <XAxis type="number" dataKey="rate" name="Скорость R" domain={[0, 1]}
                     label={{ value: 'Скорость R', position: 'bottom', offset: -5 }} />
              <YAxis type="number" dataKey="y" name="Исправление t/n" domain={[0, 'auto']}
                     label={{ value: 't / n', angle: -90, position: 'insideLeft' }} />
              <Tooltip cursor={{ strokeDasharray: '3 3' }} />
              <Legend />
              {Object.keys(TYPE_COLORS).filter(t => t !== 'Свёрточный').map(type => (
                <Scatter key={type} name={type} data={scatterData.filter(d => d.type === type)}
                         fill={TYPE_COLORS[type]} />
              ))}
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* График свёрточных кодов (d_free) */}
      {convData.length > 0 && (
        <div className="mt-5">
          <div className="card mb-3">
            <div className="card-body">
              <h5>Почему свёрточные коды вынесены отдельно?</h5>
              <p>
                Для блоковых кодов исправляющая способность выражается числом гарантированно исправляемых ошибок <em>t</em>,
                которое напрямую связано с минимальным расстоянием <em>d = 2t+1</em>.
                У свёрточных кодов нет фиксированной длины блока; их способность противостоять ошибкам характеризуется
                <strong>свободным расстоянием</strong> <em>d<sub>free</sub></em> — минимальным весом Хэмминга между любыми двумя путями на решётке.
                Поэтому прямое сравнение <em>t</em> и <em>d<sub>free</sub></em> на одном графике было бы некорректным.
                Ниже показано свободное расстояние для каждой конфигурации свёрточного кода в зависимости от длины ограничения <em>K</em>.
              </p>
            </div>
          </div>

          <h5>Свёрточные коды: свободное расстояние d<sub>free</sub></h5>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={convData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="shortName"
                     label={{ value: 'Конфигурация', position: 'insideBottom', offset: -5 }} />
              <YAxis label={{ value: 'd_free', angle: -90, position: 'insideLeft' }} />
              <Tooltip />
              <Bar dataKey="d_free" fill="#ff7300" name="Свободное расстояние" />
            </BarChart>
          </ResponsiveContainer>

          <table className="table table-sm mt-3" style={{ maxWidth: 500 }}>
            <thead>
              <tr>
                <th>Конфигурация</th>
                <th>K</th>
                <th>R</th>
                <th>d<sub>free</sub></th>
              </tr>
            </thead>
            <tbody>
              {convData.map((c, idx) => (
                <tr key={idx}>
                  <td><code>{c.preset}</code></td>
                  <td>{c.K}</td>
                  <td>{c.rate}</td>
                  <td>{c.d_free}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* График BER(SNR) для всех кодов */}
      {berChartData.length > 0 && (
        <div className="mt-5">
          <h5>Аналитическая оценка BER в зависимости от SNR</h5>
          <ResponsiveContainer width="100%" height={450}>
            <LineChart data={berChartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="snr"
                domain={['auto', 'auto']}
                label={{ value: 'SNR (dB)', position: 'insideBottom', offset: -5 }}
              />
              <YAxis
                scale="log"
                domain={[0.0001, 1]}
                label={{ value: 'BER', angle: -90, position: 'insideLeft' }}
              />
              <Tooltip />
              <Legend />
              {data.map(code => (
                <Line
                  key={code.preset}
                  type="monotone"
                  dataKey={code.preset}
                  stroke={TYPE_COLORS[code.type] || '#000'}
                  dot={false}
                  connectNulls
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="card mt-4">
        <div className="card-body">
          <h5>Рекомендации по выбору кода</h5>
          <ul>
            <li><strong>Одиночные ошибки, низкая избыточность:</strong> Код Хэмминга.</li>
            <li><strong>Многократные независимые битовые ошибки:</strong> БЧХ с нужным <em>t</em>.</li>
            <li><strong>Пакетные ошибки (стирания, группы битов):</strong> Коды Рида–Соломона.</li>
            <li><strong>Потоковые данные, мягкое декодирование:</strong> Свёрточный код с алгоритмом Витерби.</li>
          </ul>
        </div>
      </div>
    </div>
  );
}