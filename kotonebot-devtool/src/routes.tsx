import { createBrowserRouter } from 'react-router-dom';
import { Home } from './pages/Home';
import Demo from './pages/Demo';
import ImageAnnotation from './pages/ImageAnnotation/ImageAnnotation';
import ScriptRecorder from './pages/ScriptRecorder/ScriptRecorder';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Home />,
  },
  {
    path: '/demo/*',
    element: <Demo />,
  },
  {
    path: '/image-annotation',
    element: <ImageAnnotation />,
  },
  {
    path: '/script-recorder',
    element: <ScriptRecorder />,
  },
]); 