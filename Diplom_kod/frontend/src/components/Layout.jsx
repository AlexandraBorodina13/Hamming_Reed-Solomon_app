import { Link, Outlet } from 'react-router-dom';

export default function Layout() {
  return (
    <div>
      <nav style={{ background: '#f0f0f0', padding: '10px' }}>
        <Link to="/hamming">Хэмминг</Link>{' | '}
        <Link to="/bch">БЧХ</Link>{' | '}
        <Link to="/rs">Рид-Соломон</Link>{' | '}
        <Link to="/conv">Свёрточный</Link>{' | '}
        <Link to="/compare">Сравнение</Link>
      </nav>
      <hr />
      <main style={{ padding: '20px' }}>
        <Outlet />  {/* сюда будут рендериться дочерние страницы */}
      </main>
    </div>
  );
}