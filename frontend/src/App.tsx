import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { AppShell } from './components/layout/AppShell';
import { LandingPage } from './pages/LandingPage';
import { OverviewPage } from './pages/OverviewPage';
import { ExplorerPage } from './pages/ExplorerPage';
import { InvestigationPage } from './pages/InvestigationPage';
import { ComparePage } from './pages/ComparePage';
import { AgentPage } from './pages/AgentPage';
import { DataSourcesPage } from './pages/DataSourcesPage';
import { MethodologyPage } from './pages/MethodologyPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      staleTime: 1000 * 60 * 5,
    },
  },
});

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {/* Public Landing Page */}
          <Route path="/" element={<LandingPage />} />

          {/* App Workspace Shell */}
          <Route path="/app" element={<AppShell />}>
            <Route index element={<Navigate to="/app/overview" replace />} />
            <Route path="overview" element={<OverviewPage />} />
            <Route path="explorer" element={<ExplorerPage />} />
            <Route path="investigation" element={<InvestigationPage />} />
            <Route path="compare" element={<ComparePage />} />
            <Route path="ask" element={<AgentPage />} />
            <Route path="data-sources" element={<DataSourcesPage />} />
            <Route path="methodology" element={<MethodologyPage />} />
          </Route>

          {/* Catch-all redirect */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
};

export default App;
