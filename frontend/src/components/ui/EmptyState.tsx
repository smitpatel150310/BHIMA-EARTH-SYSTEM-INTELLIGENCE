import React from 'react';
import { LucideIcon } from 'lucide-react';

export interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon: Icon,
  title,
  description,
  action,
  className = '',
}) => {
  return (
    <div
      className={`flex flex-col items-center justify-center text-center p-8 border border-dashed border-bhima-border rounded-lg bg-white/50 ${className}`}
    >
      {Icon && (
        <div className="w-10 h-10 rounded-full bg-bhima-subtle flex items-center justify-center text-bhima-muted mb-3">
          <Icon className="w-5 h-5 text-bhima-secondary" />
        </div>
      )}
      <h3 className="text-sm font-semibold text-bhima-text mb-1">{title}</h3>
      {description && <p className="text-xs text-bhima-muted max-w-sm mb-4 leading-relaxed">{description}</p>}
      {action && <div className="mt-1">{action}</div>}
    </div>
  );
};
