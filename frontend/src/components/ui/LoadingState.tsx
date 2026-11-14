import React, { useState, useEffect } from 'react';
import { LoadingSpinner } from './LoadingSpinner';
import { Database, Clock, Sparkles, XCircle } from 'lucide-react';

export interface LoadingStateProps {
  title?: string;
  message?: string;
  progressPct?: number | null;
  showElapsedTime?: boolean;
  startTime?: number | null;
  stage?: string;
  variant?: 'panel' | 'card' | 'inline' | 'compact';
  spinnerSize?: 'sm' | 'md' | 'lg' | 'xl';
  onCancel?: () => void;
  className?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  title = 'Retrieving Scientific Observations',
  message = 'Communicating with Microsoft Planetary Computer & Azure Blob Storage...',
  progressPct,
  showElapsedTime = true,
  startTime,
  stage,
  variant = 'panel',
  spinnerSize = 'lg',
  onCancel,
  className = '',
}) => {
  // Live elapsed time ticker
  const [elapsedSeconds, setElapsedSeconds] = useState<number>(0);

  useEffect(() => {
    const start = startTime || Date.now();
    // Immediate calculation
    setElapsedSeconds(Math.max(0, Math.floor((Date.now() - start) / 1000)));

    const interval = setInterval(() => {
      setElapsedSeconds(Math.max(0, Math.floor((Date.now() - start) / 1000)));
    }, 1000);

    return () => clearInterval(interval);
  }, [startTime]);

  const formatElapsed = (sec: number): string => {
    if (sec < 60) return `${sec}s`;
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m}m ${s < 10 ? '0' : ''}${s}s`;
  };

  const hasProgress = typeof progressPct === 'number' && progressPct >= 0 && progressPct <= 100;

  if (variant === 'compact') {
    return (
      <div className={`inline-flex items-center gap-2.5 py-1.5 px-3 rounded-md bg-sky-50 border border-sky-200 text-sky-950 text-xs ${className}`}>
        <LoadingSpinner size="sm" variant="accent" />
        <span className="font-medium">{message}</span>
        {hasProgress && <span className="font-mono font-bold text-sky-700">{progressPct}%</span>}
        {showElapsedTime && (
          <span className="font-mono text-[11px] text-sky-600">({formatElapsed(elapsedSeconds)})</span>
        )}
      </div>
    );
  }

  if (variant === 'inline') {
    return (
      <div className={`flex items-center gap-3 p-4 rounded-lg bg-white border border-bhima-border ${className}`}>
        <LoadingSpinner size="md" variant="accent" />
        <div className="flex-1 min-w-0">
          <p className="text-xs font-semibold text-bhima-text truncate">{title}</p>
          <p className="text-[11px] text-bhima-muted truncate">{message}</p>
        </div>
        {hasProgress && (
          <span className="text-xs font-bold font-mono text-sky-600">{progressPct}%</span>
        )}
        {showElapsedTime && (
          <span className="text-[11px] font-mono text-bhima-muted shrink-0">
            {formatElapsed(elapsedSeconds)}
          </span>
        )}
      </div>
    );
  }

  return (
    <div
      className={`relative flex flex-col items-center justify-center text-center p-8 sm:p-10 rounded-xl bg-white border border-bhima-border shadow-xs overflow-hidden ${className}`}
    >
      {/* Subtle top ambient indicator */}
      <div className="absolute top-0 inset-x-0 h-1 bg-gradient-to-r from-sky-400 via-[#31594B] to-sky-400 opacity-60 animate-pulse" />

      {/* Spinner & Glow */}
      <div className="relative mb-5">
        <div className="absolute -inset-3 rounded-full bg-sky-400/10 blur-md pointer-events-none" />
        <LoadingSpinner size={spinnerSize} variant="accent" />
      </div>

      {/* Title */}
      <h3 className="text-base font-bold text-bhima-text mb-1.5 tracking-tight flex items-center gap-2">
        <span>{title}</span>
      </h3>

      {/* Descriptive Message */}
      <p className="text-xs text-bhima-muted max-w-md mb-4 leading-relaxed font-sans">
        {message}
      </p>

      {/* Optional Progress Bar & Percentage */}
      {hasProgress && (
        <div className="w-full max-w-xs mb-4 space-y-1.5">
          <div className="flex items-center justify-between text-[11px] font-mono">
            <span className="text-bhima-muted">Observed Grid Progress</span>
            <span className="font-bold text-sky-600">{progressPct}%</span>
          </div>
          <div className="w-full h-1.5 bg-bhima-subtle rounded-full overflow-hidden">
            <div
              className="h-full bg-sky-500 rounded-full transition-all duration-300 ease-out"
              style={{ width: `${Math.max(5, progressPct)}%` }}
            />
          </div>
        </div>
      )}

      {/* Live Metadata Badges */}
      <div className="flex flex-wrap items-center justify-center gap-2 text-[11px] text-bhima-muted mb-2">
        {/* Source Badge */}
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-sky-50 border border-sky-200/80 text-sky-800 font-medium">
          <Database className="w-3 h-3 text-sky-600" />
          <span>Microsoft Planetary Computer</span>
        </span>

        {/* Stage Badge */}
        {stage && (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-bhima-subtle border border-bhima-border text-bhima-text font-medium">
            <Sparkles className="w-3 h-3 text-bhima-secondary" />
            <span>{stage}</span>
          </span>
        )}

        {/* Live Elapsed Time */}
        {showElapsedTime && (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-bhima-subtle border border-bhima-border text-bhima-muted font-mono">
            <Clock className="w-3 h-3 text-bhima-muted" />
            <span>Elapsed: {formatElapsed(elapsedSeconds)}</span>
          </span>
        )}
      </div>

      {/* Optional cancel action */}
      {onCancel && (
        <button
          type="button"
          onClick={onCancel}
          className="mt-4 inline-flex items-center gap-1 text-xs text-bhima-muted hover:text-bhima-danger transition-colors cursor-pointer"
        >
          <XCircle className="w-3.5 h-3.5" />
          <span>Cancel Request</span>
        </button>
      )}
    </div>
  );
};

export default LoadingState;
