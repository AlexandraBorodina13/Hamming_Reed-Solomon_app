import axios from 'axios';

// Создаём экземпляр axios с базовым URL сервера
const api = axios.create({
  baseURL: 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
});

// ===================== Хэмминг =====================
export const encodeHamming = (m, message) =>
  api.post('/hamming/encode', { m, message });

export const decodeHamming = (m, received) =>
  api.post('/hamming/decode', { m, received });

// ===================== БЧХ =====================
export const encodeBCH = (n, k, message) =>
  api.post('/bch/encode', { n, k, message });

export const decodeBCH = (n, k, received) =>
  api.post('/bch/decode', { n, k, received });

// ===================== Рид-Соломон =====================
export const encodeRS = (preset, message) =>
  api.post('/rs/encode', { preset, message });

export const decodeRSAsync = (preset, received) =>
  api.post('/rs/decode/async', { preset, received });

// Проверка статуса задачи RS – без изменений
export const getRSTaskStatus = (taskId) =>
  api.get(`/rs/task/${taskId}`);

// ===================== Свёрточный код =====================
export const encodeConvolutional = (preset, message) =>
  api.post('/conv/encode', { preset, message });

export const decodeConvolutional = (preset, received) =>
  api.post('/conv/decode', { preset, received });

// ===================== Сравнение кодов (заглушка) =====================
export const compareCodes = (params) =>
  api.post('/comparison', params);

// ===================== Экспорт отчётов =====================
export const exportPDF = (payload) =>
  api.post('/export/pdf', payload, { responseType: 'blob' });

export const exportHTML = (payload) =>
  api.post('/export/html', payload, { responseType: 'blob' });

export default api;