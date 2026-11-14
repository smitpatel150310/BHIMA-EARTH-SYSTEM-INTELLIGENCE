import React from 'react';
import { Menu, Wifi, WifiOff } from 'lucide-react';
import { useHealthCheck } from '../../api/queries';

export interface HeaderProps {
  onMenuToggle?: () => void;
  title?: string;
}

export const Header: React.FC<HeaderProps> = ({ onMenuToggle, title }) => {
  const { data: health, isSuccess, isError, isLoading } = useHealthCheck();

  const isOnline = isSuccess && health?.status === 'ok';

  return (
    <header className="h-14 bg-white border-b border-bhima-border px-4 sm:px-6 flex items-center justify-between sticky top-0 z-20">
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuToggle}
          className="lg:hidden p-1.5 text-bhima-muted hover:text-bhima-text rounded hover:bg-bhima-subtle"
          aria-label="Toggle navigation menu"
        >
          <Menu className="w-5 h-5" />
        </button>
        {title && (
          <h1 className="text-sm font-semibold text-bhima-text tracking-tight hidden sm:block">
            {title}
          </h1>
        )}
      </div>

      <div className="flex items-center gap-4">
        {/* Health status badge */}
        <div
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium bg-bhima-subtle border border-bhima-border text-bhima-muted"
          title={isOnline ? 'BHIMA Engine Connected' : isLoading ? 'Connecting to backend...' : 'Backend service unreachable'}
        >
          {isOnline ? (
            <>
              <span className="w-2 h-2 rounded-full bg-emerald-600 animate-pulse" />
              <span className="hidden md:inline text-bhima-text">Engine Online</span>
              <Wifi className="w-3 h-3 text-bhima-primary ml-0.5" />
            </>
          ) : isLoading ? (
            <>
              <span className="w-2 h-2 rounded-full bg-amber-500 animate-ping" />
              <span className="hidden md:inline">Connecting...</span>
            </>
          ) : (
            <>
              <span className="w-2 h-2 rounded-full bg-red-400" />
              <span className="hidden md:inline text-red-600">Offline</span>
              <WifiOff className="w-3 h-3 text-red-500 ml-0.5" />
            </>
          )}
        </div>

        {/* Space Apps badge */}
        <div className="hidden sm:flex items-center gap-1.5 text-xs text-bhima-muted border-l border-bhima-border pl-4">
          <span className="font-medium text-bhima-text">NASA Space Apps</span>
          <span className="text-[10px] bg-bhima-subtle px-1.5 py-0.5 rounded border border-bhima-border font-mono">
            2024
          </span>
        </div>
      </div>
    </header>
  );
};
