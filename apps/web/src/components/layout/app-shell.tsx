'use client';

import React, { useState, useEffect, useCallback, ReactNode } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuth } from '@/context/auth-context';
import { Sidebar } from './sidebar';
import { TopNav } from './top-nav';
import { Loader2 } from 'lucide-react';

export interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const { user, token, isLoading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [summaryCounts, setSummaryCounts] = useState<Record<string, number>>({});

  // Route guard
  useEffect(() => {
    if (!isLoading) {
      if (!user || !token) {
        router.push('/login');
      } else if (user.must_change_password && pathname !== '/change-password') {
        router.push('/change-password');
      }
    }
  }, [user, token, isLoading, pathname, router]);

  useEffect(() => {
    let ignore = false;
    const load = async () => {
      if (!token) return;
      try {
        const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';
        const res = await fetch(`${apiBase}/reports/attendance/dashboard/summary`, {
          headers: {
            Authorization: `Bearer ${token}`,
            Accept: 'application/json',
          },
        });
        if (res.ok && !ignore) {
          const json = await res.json();
          setSummaryCounts(json.data || {});
        }
      } catch {
        // Ignore background fetch error for sidebar
      }
    };

    load();
    const interval = setInterval(load, 30000);
    return () => {
      ignore = true;
      clearInterval(interval);
    };
  }, [token]);

  if (isLoading || !user) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-slate-50 text-slate-600 gap-3">
        <Loader2 className="w-8 h-8 animate-spin text-sky-600" />
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          Loading Institutional Session...
        </span>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* Sidebar (desktop fixed + mobile drawer) */}
      <Sidebar
        counts={summaryCounts}
        isOpen={isMobileMenuOpen}
        onClose={() => setIsMobileMenuOpen(false)}
      />

      {/* Main Container */}
      <div className="flex-1 flex flex-col md:pl-64 min-w-0">
        <TopNav onOpenMobileMenu={() => setIsMobileMenuOpen(true)} />

        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
