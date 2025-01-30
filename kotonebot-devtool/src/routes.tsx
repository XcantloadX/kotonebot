import { createBrowserRouter } from 'react-router-dom';
import { Home } from './pages/Home';
import Demo from './pages/Demo';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Home />,
  },
  {
    path: '/demo/*',
    element: <Demo />,
  },
]); 