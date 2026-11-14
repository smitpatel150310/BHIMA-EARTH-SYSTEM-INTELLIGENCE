import React from 'react';

export interface LoadingSpinnerProps {
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  variant?: 'primary' | 'accent' | 'white' | 'muted';
  className?: string;
  label?: string;
}

const sizeMap = {
  xs: {
    container: 'w-3.5 h-3.5',
    stroke: 2.5,
  },
  sm: {
    container: 'w-4 h-4',
    stroke: 2.5,
  },
  md: {
    container: 'w-6 h-6',
    stroke: 2.5,
  },
  lg: {
    container: 'w-9 h-9',
    stroke: 2.75,
  },
  xl: {
    container: 'w-12 h-12',
    stroke: 3,
  },
};

const variantMap = {
  // BHIMA's core brand green
  primary: {
    track: 'stroke-[#31594B]/20',
    arc: 'stroke-[#31594B]',
  },
  // Cyan / Blue accent consistent with modern scientific Earth data UI
  accent: {
    track: 'stroke-sky-500/20',
    arc: 'stroke-sky-500',
  },
  // White for dark surfaces / primary buttons
  white: {
    track: 'stroke-white/25',
    arc: 'stroke-white',
  },
  // Subtle muted secondary
  muted: {
    track: 'stroke-[#84978B]/20',
    arc: 'stroke-[#84978B]',
  },
};

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'md',
  variant = 'accent',
  className = '',
  label = 'Loading...',
}) => {
  const { container, stroke } = sizeMap[size] || sizeMap.md;
  const colors = variantMap[variant] || variantMap.accent;

  return (
    <div
      className={`inline-flex items-center justify-center shrink-0 ${container} ${className}`}
      role="status"
      aria-label={label}
    >
      <svg
        className="w-full h-full animate-spin"
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* Background track circle */}
        <circle
          cx="12"
          cy="12"
          r="9.5"
          className={colors.track}
          strokeWidth={stroke}
        />
        {/* Animated foreground arc */}
        <path
          d="M12 2.5C17.2467 2.5 21.5 6.75329 21.5 12C21.5 14.1206 20.8068 16.0792 19.6384 17.6583"
          className={colors.arc}
          strokeWidth={stroke}
          strokeLinecap="round"
        />
      </svg>
      <span className="sr-only">{label}</span>
    </div>
  );
};

export default LoadingSpinner;
