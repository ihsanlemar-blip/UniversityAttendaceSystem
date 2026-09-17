'use client';

import React, { useState, useEffect } from 'react';
import { Menu, Clock, Shield, LogOut } from 'lucide-react';
import { useAuth } from '@/context/auth-context';
import { ConnectivityIndicator, Badge } from '@/components/ui';
import { LanguageSelector } from './language-selector';

export interface TopNavProps {
  onOpenMobileMenu: () => void;
}

export function TopNav({ onOpenMobileMenu }: TopNavProps) {
  const { user, logout } = useAuth();
  const [utcTime, setUtcTime] = useState<string>('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setUtcTime(now.toUTCString().slice(17, 25) + ' UTC');
    };
    updateTime();
    const timer = setInterval(updateTime, 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <header className="h-16 bg-white border-b border-slate-200 sticky top-0 z-20 flex items-center justify-between px-4 sm:px-6 lg:px-8 shadow-xs">
      {/* Left: Mobile Toggle & Context */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onOpenMobileMenu}
          className="md:hidden p-2 text-slate-600 hover:text-slate-900 rounded-lg hover:bg-slate-100 transition-colors"
          aria-label="Open navigation menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="hidden sm:flex items-center gap-2 text-xs text-slate-600">
          <span className="font-semibold text-slate-900">University Attendance Governance</span>
          <span className="text-slate-300">|</span>
          <span className="text-slate-500">Milestone 17 MVP</span>
        </div>
      </div>

      {/* Right: Telemetry & Actions */}
      <div className="flex items-center gap-3 sm:gap-4">
        {/* UTC Clock pill enforcing INV-03 (Server Clock Authority) */}
        <div
          title="Authoritative Server UTC Time"
          className="hidden md:flex items-center gap-1.5 px-2.5 py-1 bg-slate-100 rounded-lg text-xs font-mono font-medium text-slate-700 border border-slate-200"
        >
          <Clock className="w-3.5 h-3.5 text-slate-500" />
          <span>{utcTime || 'UTC --:--:--'}</span>
        </div>

        {/* Language Selector */}
        <LanguageSelector />

        {/* Connectivity Status */}
        <ConnectivityIndicator />

        {/* User Role Tag */}
        {user?.roles?.[0] && (
          <Badge variant="info" size="sm" className="hidden lg:inline-flex uppercase">
            {user.roles[0].replace('_', ' ')}
          </Badge>
        )}

        {/* Quick Sign Out */}
        <button
          type="button"
          onClick={logout}
          className="p-1.5 text-slate-500 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
          title="Sign Out"
          aria-label="Sign Out"
        >
          <LogOut className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
}
