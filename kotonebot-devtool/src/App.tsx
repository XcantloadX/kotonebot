import React from 'react';
import { RouterProvider } from 'react-router-dom';
import { router } from './routes';
import { ErrorBoundary } from './components/Common/ErrorBoundary';
import { Global } from '@emotion/react';
import { globalStyles } from './styles/globalStyles';

export const App: React.FC = () => {
  return (
    <ErrorBoundary>
      <Global styles={globalStyles} />
      <RouterProvider router={router} />
    </ErrorBoundary>
  );
};
