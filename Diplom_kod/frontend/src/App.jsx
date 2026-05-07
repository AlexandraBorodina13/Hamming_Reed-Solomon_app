import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Hamming from './pages/Hamming';
import BCH from './pages/BCH';
import ReedSolomon from './pages/ReedSolomon';
import Convolutional from './pages/Convolutional';
import Comparison from './pages/Comparison';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Hamming />} />
          <Route path="hamming" element={<Hamming />} />
          <Route path="bch" element={<BCH />} />
          <Route path="rs" element={<ReedSolomon />} />
          <Route path="conv" element={<Convolutional />} />
          <Route path="compare" element={<Comparison />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}