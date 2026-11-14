import React, { HTMLAttributes } from 'react';

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'subtle' | 'flat';
  padding?: 'none' | 'sm' | 'md' | 'lg';
}

export const Card: React.FC<CardProps> = ({
  children,
  variant = 'default',
  padding = 'md',
  className = '',
  ...props
}) => {
  const variantClasses = {
    default: 'bg-white border border-bhima-border shadow-[0_1px_3px_rgba(0,0,0,0.02)]',
    subtle: 'bg-bhima-subtle border border-bhima-border',
    flat: 'bg-white border-0',
  };

  const paddingClasses = {
    none: 'p-0',
    sm: 'p-3',
    md: 'p-5',
    lg: 'p-6 sm:p-7',
  };

  return (
    <div
      className={`rounded-lg transition-all duration-150 ${variantClasses[variant]} ${paddingClasses[padding]} ${className}`}
      {...props}
    >
      {children}
    </div>
  );
};
