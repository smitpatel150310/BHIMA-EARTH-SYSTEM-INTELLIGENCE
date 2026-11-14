import React, { HTMLAttributes } from 'react';

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'primary' | 'success' | 'warning' | 'danger' | 'outline';
  size?: 'sm' | 'md';
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'default',
  size = 'sm',
  className = '',
  ...props
}) => {
  const sizeClasses = {
    sm: 'text-[11px] font-medium px-2 py-0.5 rounded',
    md: 'text-xs font-medium px-2.5 py-1 rounded-md',
  };

  const variantClasses = {
    default: 'bg-bhima-subtle text-bhima-muted border border-bhima-border',
    primary: 'bg-bhima-primary/10 text-bhima-primary border border-bhima-primary/20',
    success: 'bg-[#EBF3ED] text-[#285741] border border-[#CDE3D5]',
    warning: 'bg-[#FBF6ED] text-[#8C5D1E] border border-[#F1E0C4]',
    danger: 'bg-[#FDF2F2] text-[#9E3634] border border-[#F6D0D0]',
    outline: 'bg-transparent text-bhima-muted border border-bhima-border',
  };

  return (
    <span
      className={`inline-flex items-center gap-1 leading-none tracking-tight select-none ${sizeClasses[size]} ${variantClasses[variant]} ${className}`}
      {...props}
    >
      {children}
    </span>
  );
};
