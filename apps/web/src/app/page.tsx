'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ShieldCheck, ArrowRight, BookOpen, Clock, Users, Building } from 'lucide-react';
import { useAuth } from '@/context/auth-context';
import { Button, ConnectivityIndicator } from '@/components/ui';

interface HealthStatus {
  status: string;
  service: string;
  version?: string;
}

export default function HomePage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [isLive, setIsLive] = useState<boolean | null>(null);

  useEffect(() => {
    if (!isLoading && user) {
      if (user.must_change_password) {
        router.push('/change-password');
      } else if (user.roles.includes('LECTURER')) {
        router.push('/lecturer');
      } else {
        router.push('/admin');
      }
    }
  }, [user, isLoading, router]);

  useEffect(() => {
    const checkLive = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';
        const healthUrl = apiUrl.replace(/\/api\/v1\/?$/, '/health/live');
        const res = await fetch(healthUrl, { cache: 'no-store' });
        if (res.ok) {
          const data: HealthStatus = await res.json();
          setHealth(data);
          setIsLive(true);
        } else {
          setIsLive(false);
        }
      } catch {
        setIsLive(false);
      }
    };
    checkLive();
  }, []);

  return (
    <div className="min-h-screen flex flex-col justify-between bg-slate-50">
      {/* Top Navbar */}
      <header className="border-b border-slate-200 bg-white sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-sky-900 flex items-center justify-center text-white shadow-sm">
              <ShieldCheck className="w-5 h-5 text-sky-400" />
            </div>
            <div>
              <span className="font-bold text-slate-900 text-sm tracking-tight block">
                Digital Attendance System
              </span>
              <span className="text-[11px] text-slate-500 block">
                Academic Operations & Session Governance
              </span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <ConnectivityIndicator />
            <Link href="/login">
              <Button variant="primary" size="sm">
                Sign In
                <ArrowRight className="w-3.5 h-3.5 ml-1" />
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 lg:py-20 flex-1 flex flex-col items-center justify-center text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-sky-50 border border-sky-200 text-sky-700 text-xs font-medium mb-6">
          <span className="w-2 h-2 rounded-full bg-sky-500 animate-pulse" />
          Enterprise University Academic Infrastructure
        </div>

        <h1 className="text-3xl sm:text-5xl font-extrabold text-slate-900 tracking-tight max-w-3xl leading-tight">
          Authoritative Attendance Verification & Governance
        </h1>
        <p className="mt-4 text-base sm:text-lg text-slate-600 max-w-2xl leading-relaxed">
          High-assurance academic session tracking with cryptographic rotating tokens, campus network fencing, and transparent administrative audit trails.
        </p>

        <div className="mt-8 flex flex-col sm:flex-row gap-4 justify-center">
          <Link href="/login">
            <Button variant="primary" size="lg" className="w-full sm:w-auto shadow-md">
              Enter Academic Portal
              <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          </Link>
          <Link href="/admin">
            <Button variant="outline" size="lg" className="w-full sm:w-auto bg-white">
              Administrative Console
            </Button>
          </Link>
        </div>

        {/* Feature Highlights Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mt-16 w-full max-w-5xl text-left">
          <div className="p-5 bg-white border border-slate-200 rounded-xl shadow-xs">
            <div className="w-10 h-10 rounded-lg bg-sky-50 text-sky-700 flex items-center justify-center mb-3">
              <Clock className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-semibold text-slate-900 mb-1">Rotating Tokens</h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              Dynamic cryptographic QR codes rotating every 20-30 seconds prevent replay fraud and proxy check-ins.
            </p>
          </div>

          <div className="p-5 bg-white border border-slate-200 rounded-xl shadow-xs">
            <div className="w-10 h-10 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center mb-3">
              <Building className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-semibold text-slate-900 mb-1">Campus-Fenced Trust</h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              Strict network zone validation ensures attendance claims originate from designated physical classrooms.
            </p>
          </div>

          <div className="p-5 bg-white border border-slate-200 rounded-xl shadow-xs">
            <div className="w-10 h-10 rounded-lg bg-indigo-50 text-indigo-700 flex items-center justify-center mb-3">
              <Users className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-semibold text-slate-900 mb-1">Multi-Role Governance</h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              Dedicated interfaces tailored for faculty instructors, students, department heads, and compliance auditors.
            </p>
          </div>

          <div className="p-5 bg-white border border-slate-200 rounded-xl shadow-xs">
            <div className="w-10 h-10 rounded-lg bg-amber-50 text-amber-700 flex items-center justify-center mb-3">
              <BookOpen className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-semibold text-slate-900 mb-1">Immutable Audit Trail</h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              Every status revision, excuse approval, and manual override maintains an unalterable historical ledger.
            </p>
          </div>
        </div>

        {/* System Health Status Pill */}
        <div className="mt-12 inline-flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 rounded-xl shadow-xs text-xs">
          <span
            className={`w-2.5 h-2.5 rounded-full ${
              isLive === true ? 'bg-emerald-500' : isLive === false ? 'bg-rose-500' : 'bg-amber-400'
            }`}
          />
          <span className="font-medium text-slate-700">Platform Health:</span>
          <span className="text-slate-500">
            {isLive === true
              ? `Connected (${health?.service || 'API'} v${health?.version || '1.0.0'})`
              : isLive === false
              ? 'Backend Offline'
              : 'Verifying connection...'}
          </span>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500">
          <div>
            © {new Date().getFullYear()} Digital Student Attendance System. Institutional Core Engine.
          </div>
          <div className="flex gap-6">
            <span>Server Clock: Authoritative UTC</span>
            <span>Security Standard: Defense-in-Depth</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
