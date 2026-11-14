import React from 'react';
import { AlertCircle, RotateCcw } from 'lucide-react';
import { Button } from './Button';

export interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  className?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Unable to Load Data',
  message = 'An unexpected error occurred while communicating with the BHIMA services.',
  onRetry,
  className = '',
}) => {
  return (
    <div
      className={`flex flex-col items-center justify-center text-center p-6 border border-red-200 rounded-lg bg-red-50/50 ${className}`}
    >
      <div className="w-9 h-9 rounded-full bg-red-100 flex items-center justify-center text-bhima-danger mb-3">
        <AlertCircle className="w-5 h-5 text-bhima-danger" />
      </div>
      <h3 className="text-sm font-semibold text-bhima-text mb-1">{title}</h3>
      <p className="text-xs text-bhima-muted max-w-md mb-4 leading-relaxed font-mono">
        {message}
      </p>
      {onRetry && (
        <Button
          variant="secondary"
          size="sm"
          onClick={onRetry}
          leftIcon={<RotateCcw className="w-3.5 h-3.5" />}
        >
          Try Again
        </Button>
      )}
    </div>
  );
};
