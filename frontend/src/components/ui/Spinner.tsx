import React from 'react';
import { LoadingSpinner, LoadingSpinnerProps } from './LoadingSpinner';

export interface SpinnerProps extends LoadingSpinnerProps {
  label?: string;
}

export const Spinner: React.FC<SpinnerProps> = ({
  size = 'md',
  variant = 'accent',
  className = '',
  label,
  ...props
}) => {
  return (
    <div className={`inline-flex flex-col items-center justify-center gap-2 ${className}`}>
      <LoadingSpinner size={size} variant={variant} {...props} />
      {label && <span className="text-xs text-bhima-muted">{label}</span>}
    </div>
  );
};

export default Spinner;
