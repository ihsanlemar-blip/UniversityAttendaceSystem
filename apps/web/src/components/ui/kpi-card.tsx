import React, { ReactNode } from 'react';
import Link from 'next/link';
import { ArrowUpRight } from 'lucide-react';

export interface KpiCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: ReactNode;
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info';
  href?: string;
  trend?: string;
  isLoading?: boolean;
}

export function KpiCard({
  title,
  value,
  subtitle,
  icon,
  variant = 'default',
  href,
  trend,
  isLoading = false,
}: KpiCardProps) {
  const iconColorMap = {
    default: 'bg-slate-100 text-slate-700',
    success: 'bg-emerald-100 text-emerald-700',
    warning: 'bg-amber-100 text-amber-700',
    danger: 'bg-rose-100 text-rose-700',
    info: 'bg-sky-100 text-sky-700',
  };

  const content = (
    <div className="p-5 flex flex-col justify-between h-full bg-white border border-slate-200 rounded-xl shadow-xs transition-all duration-200 hover:shadow-md hover:border-slate-300">
      <div className="flex items-start justify-between gap-2 mb-3">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 leading-tight">
          {title}
        </span>
        <div className={`p-2.5 rounded-lg shrink-0 ${iconColorMap[variant]}`}>
          {icon}
        </div>
      </div>
      <div>
        {isLoading ? (
          <div className="h-8 w-20 bg-slate-200 animate-pulse rounded my-1" />
        ) : (
          <div className="text-2xl font-bold text-slate-900 tracking-tight">
            {value}
          </div>
        )}
        {(subtitle || trend) && (
          <div className="flex items-center gap-1.5 mt-1 text-xs text-slate-500">
            {trend && <span className="font-semibold text-slate-700">{trend}</span>}
            {subtitle && <span>{subtitle}</span>}
            {href && <ArrowUpRight className="w-3 h-3 text-slate-400 ml-auto" />}
          </div>
        )}
      </div>
    </div>
  );

  if (href) {
    return (
      <Link href={href} className="block group focus:outline-none focus:ring-2 focus:ring-sky-500 rounded-xl">
        {content}
      </Link>
    );
  }

  return content;
}
