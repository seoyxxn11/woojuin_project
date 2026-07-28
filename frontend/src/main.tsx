import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Provider as JotaiProvider } from 'jotai';
import { RouterProvider } from 'react-router-dom';
import { router } from './routes/router';
import { jotaiStore } from './stores/jotaiStore';
import './styles/index.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // 저장 항목 상태(PROCESSING → DONE) 폴링은 각 쿼리에서 refetchInterval로 제어
      staleTime: 30_000,
      retry: 1,
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <JotaiProvider store={jotaiStore}>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </JotaiProvider>
  </React.StrictMode>,
);
