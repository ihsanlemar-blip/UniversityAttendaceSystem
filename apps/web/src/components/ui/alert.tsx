import React, { HTMLAttributes } from 'react';
import { AlertCircle, CheckCircle2, AlertTriangle, Info, X } from 'lucide-react';

export interface AlertProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'info' | 'success' | 'warning' | 'destructive';
  title?: string;
  onDismiss?: () => void;
}

export function Alert({
  variant = 'info',
  title,
  onDismiss,
  className = '',
  children,
  ...props
}: AlertProps) {
  const iconMap = {
    info: <Info className="w-5 h-5 text-sky-600 shrink-0 mt-0.5" />,
    success: <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />,
    warning: <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />,
    destructive: <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />,
  };

  const styleMap = {
    info: 'bg-sky-50 border-sky-200 text-sky-900',
    success: 'bg-emerald-50 border-emerald-200 text-emerald-900',
    warning: 'bg-amber-50 border-amber-200 text-amber-900',
    destructive: 'bg-rose-50 border-rose-200 text-rose-900',
  };

  return (
    <div
      role="alert"
      className={`relative flex items-start gap-3 p-4 border rounded-xl shadow-xs ${styleMap[variant]} ${className}`}
      {...props}
    >
      {iconMap[variant]}
      <div className="flex-1 min-w-0">
        {title && <h5 className="font-semibold text-sm leading-snug mb-1">{title}</h5>}
        <div className="text-xs leading-relaxed opacity-90">{children}</div>
      </div>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          className="shrink-0 p-1 -mr-1 -mt-1 rounded-md opacity-60 hover:opacity-100 hover:bg-black/5 transition-opacity"
          aria-label="Dismiss alert"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}
