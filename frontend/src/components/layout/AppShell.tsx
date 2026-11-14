import React, { useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';

const TITLE_MAP: Record<string, string> = {
  '/app/overview': 'System Overview',
  '/app/explorer': 'Earth Explorer & Regional Investigation',
  '/app/investigation': 'Trend & Statistical Analysis',
  '/app/compare': 'Comparative Regional Analysis',
  '/app/ask': 'Ask BHIMA Intelligent Copilot',
  '/app/data-sources': 'Scientific Data Sources & Specifications',
  '/app/methodology': 'Statistical Methodology & Rigor',
};

export const AppShell: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();

  const title = TITLE_MAP[location.pathname] || 'BHIMA Platform';

  return (
    <div className="min-h-screen bg-bhima-bg flex flex-col">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <div className="lg:pl-60 flex flex-col flex-1 min-w-0">
        <Header onMenuToggle={() => setSidebarOpen(!sidebarOpen)} title={title} />

        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
