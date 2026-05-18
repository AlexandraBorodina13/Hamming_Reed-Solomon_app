import { useState, useEffect, useMemo } from 'react';
import { getComparisonInfo } from '../api/client';
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ZAxis
} from 'recharts';

// Сопоставление типов для цветов на графике
const TYPE_COLORS = {
  'Хэмминг': '#8884d8',
  'БЧХ': '#82ca9d',
  'Рид–Соломон': '#ffc658'
  //'Свёрточный': '#ff7300'
};

export default function Comparison() {
  const [data, setData] = useState([]);
  const [filterType, setFilterType] = useState('Все');
  const [sortKey, setSortKey] = useState(null);
  const [sortDir, setSortDir] = useState('asc');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Загрузка данных с бэкенда
  useEffect(() => {
    setLoading(true);
    getComparisonInfo()
      .then(res => setData(res.data.codes))
      .catch(err => setError('Ошибка загрузки данных: ' + (err.response?.data?.detail || err.message)))
      .finally(() => setLoading(false));
  }, []);

  // Фильтрация
  const filtered = useMemo(() => {
    if (filterType === 'Все') return data;
    return data.filter(c => c.type === filterType);
  }, [data, filterType]);

  // Сортировка
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

  // Уникальные типы для фильтра
  const types = useMemo(() => ['Все', ...new Set(data.map(c => c.type))], [data]);

  // Данные для scatter-plot (только те, где rate и error_capability можно нормализовать)
  const scatterData = useMemo(() => {
    return data
      .filter(c => c.type !== 'Свёрточный') // для свёрточных особая метрика, можно тоже добавить
      .map(c => {
        let y = 0;
        const match = c.error_capability.match(/t\s*=\s*(\d+)/);
        if (match) y = Number(match[1]) / c.n; // нормированная исправляющая способность
        return { ...c, y };
      });
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

  return (
    <div className="container mt-4">
      <h2 className="text-center mb-4">Сравнительный анализ кодов</h2>

      {/* Теоретическое введение */}
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

      {/* Фильтр */}
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

      {/* Таблица */}
      <div className="table-responsive">
        <table className="table table-bordered table-hover">
          <thead className="table-light">
            <tr>
              {['type', 'preset', 'n', 'k', 'rate', 'redundancy', 'error_capability', 'field_size'].map(key => (
                <th
                  key={key}
                  style={{ cursor: 'pointer', userSelect: 'none' }}
                  onClick={() => handleSort(key)}
                >
                  {{
                    type: 'Тип', preset: 'Конфигурация', n: 'n', k: 'k',
                    rate: 'Скорость R', redundancy: 'Избыточность',
                    error_capability: 'Исправление', field_size: 'Размер поля'
                  }[key]}
                  {sortKey === key && (sortDir === 'asc' ? ' ▲' : ' ▼')}
                </th>
              ))}
              <th>Примечание</th>
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
                <td style={{ fontSize: '0.9em' }}>{code.notes}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Визуализация: scatter-plot (опционально) */}
      {scatterData.length > 0 && (
        <div className="mt-5">
          <h5>Эффективность кодов (нормированная исправляющая способность vs скорость)</h5>
          <ResponsiveContainer width="100%" height={400}>
            <ScatterChart>
              <CartesianGrid />
              <XAxis
                type="number"
                dataKey="rate"
                name="Скорость R"
                domain={[0, 1]}
                label={{ value: 'Скорость R', position: 'bottom', offset: -5 }}
              />
              <YAxis
                type="number"
                dataKey="y"
                name="Исправление t/n"
                domain={[0, 'auto']}
                label={{ value: 't / n', angle: -90, position: 'insideLeft' }}
              />
              <Tooltip cursor={{ strokeDasharray: '3 3' }} />
              <Legend />
              {Object.keys(TYPE_COLORS).map(type => (
                <Scatter
                  key={type}
                  name={type}
                  data={scatterData.filter(d => d.type === type)}
                  fill={TYPE_COLORS[type]}
                />
              ))}
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Блок рекомендаций */}
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