import React, { ButtonHTMLAttributes } from 'react';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  leftIcon,
  rightIcon,
  className = '',
  disabled,
  ...props
}) => {
  const baseClasses =
    'inline-flex items-center justify-center font-medium transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-bhima-primary/20 disabled:opacity-50 disabled:cursor-not-allowed select-none';

  const sizeClasses = {
    sm: 'text-xs px-2.5 py-1.5 rounded gap-1.5',
    md: 'text-sm px-3.5 py-2 rounded-md gap-2',
    lg: 'text-base px-5 py-2.5 rounded-md gap-2.5',
  };

  const variantClasses = {
    primary:
      'bg-bhima-primary text-white hover:bg-bhima-primary-hover active:bg-[#1E372E] border border-bhima-primary shadow-none',
    secondary:
      'bg-bhima-subtle text-bhima-text hover:bg-[#E5E9E4] active:bg-[#DCE1DB] border border-bhima-border',
    outline:
      'bg-white text-bhima-text hover:bg-bhima-subtle active:bg-[#E5E9E4] border border-bhima-border',
    ghost:
      'bg-transparent text-bhima-muted hover:text-bhima-text hover:bg-bhima-subtle active:bg-[#E5E9E4]',
    danger:
      'bg-red-50 text-bhima-danger border border-red-200 hover:bg-red-100 active:bg-red-200',
  };

  return (
    <button
      className={`${baseClasses} ${sizeClasses[size]} ${variantClasses[variant]} ${className}`}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? (
        <svg
          className="animate-spin -ml-0.5 h-4 w-4 text-current"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="3"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
      ) : (
        leftIcon
      )}
      <span>{children}</span>
      {!isLoading && rightIcon}
    </button>
  );
};
