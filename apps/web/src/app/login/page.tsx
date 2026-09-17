'use client';

import React, { useState, useEffect, FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { ShieldCheck, Lock, User, Eye, EyeOff, Building2 } from 'lucide-react';
import { useAuth } from '@/context/auth-context';
import { useLanguage } from '@/context/language-context';
import { Button, Alert, ConnectivityIndicator } from '@/components/ui';
import { LanguageSelector } from '@/components/layout/language-selector';

export default function LoginPage() {
  const { user, login } = useAuth();
  const { t } = useLanguage();
  const router = useRouter();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // If already logged in, redirect appropriately
    if (user) {
      if (user.must_change_password) {
        router.push('/change-password');
      } else if (user.roles.includes('LECTURER')) {
        router.push('/lecturer');
      } else {
        router.push('/admin');
      }
    }
  }, [user, router]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) {
      setError('Please enter both username and password.');
      return;
    }

    setError(null);
    setIsLoading(true);

    try {
      const result = await login(username.trim(), password);
      if (!result.success) {
        setError(result.error || 'Authentication failed. Please verify your credentials.');
      }
    } catch {
      setError('An unexpected error occurred during sign-in.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col justify-between bg-slate-100/70 p-4 sm:p-6 lg:p-8">
      {/* Top Bar with Campus Status & Language Selector */}
      <header className="w-full max-w-6xl mx-auto flex items-center justify-between py-2">
        <div className="flex items-center gap-2 text-slate-800 font-semibold text-sm">
          <Building2 className="w-4 h-4 text-sky-600" />
          <span>{t('app.title')}</span>
        </div>
        <div className="flex items-center gap-3">
          <LanguageSelector />
          <ConnectivityIndicator />
        </div>
      </header>

      {/* Main Login Card */}
      <main className="w-full max-w-md mx-auto my-auto py-8">
        <div className="bg-white border border-slate-200 rounded-2xl shadow-xl overflow-hidden">
          {/* Header Banner */}
          <div className="bg-gradient-to-r from-sky-900 via-sky-800 to-indigo-950 p-6 text-white text-center">
            <div className="w-12 h-12 rounded-xl bg-white/10 backdrop-blur-sm border border-white/20 flex items-center justify-center mx-auto mb-3 shadow-inner">
              <ShieldCheck className="w-7 h-7 text-sky-300" />
            </div>
            <h1 className="text-xl font-bold tracking-tight">{t('app.title')}</h1>
            <p className="text-xs text-sky-200 mt-1 font-medium">{t('app.subtitle')}</p>
          </div>

          {/* Form Area */}
          <div className="p-6 sm:p-8">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-700 mb-1">
              {t('auth.signIn')}
            </h2>
            <p className="text-xs text-slate-500 mb-6">
              {t('auth.credentialsPrompt')}
            </p>

            {error && (
              <Alert variant="destructive" className="mb-6" onDismiss={() => setError(null)}>
                {error}
              </Alert>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5">
                  {t('auth.username')}
                </label>
                <div className="relative">
                  <span className="absolute inset-y-0 start-0 ps-3 flex items-center pointer-events-none text-slate-400">
                    <User className="w-4 h-4" />
                  </span>
                  <input
                    type="text"
                    required
                    autoComplete="username"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="e.g. admin, lecturer@uni.edu"
                    className="w-full ps-9 pe-3 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent transition-all"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5">
                  {t('auth.password')}
                </label>
                <div className="relative">
                  <span className="absolute inset-y-0 start-0 ps-3 flex items-center pointer-events-none text-slate-400">
                    <Lock className="w-4 h-4" />
                  </span>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full ps-9 pe-10 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent transition-all"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 end-0 pe-3 flex items-center text-slate-400 hover:text-slate-600 focus:outline-none"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div className="pt-2">
                <Button
                  type="submit"
                  variant="primary"
                  size="lg"
                  className="w-full"
                  isLoading={isLoading}
                >
                  {t('auth.signIn')}
                </Button>
              </div>
            </form>

            <div className="mt-6 pt-4 border-t border-slate-100 text-center">
              <p className="text-[11px] text-slate-400">
                Institutional single sign-on & token rotation compliant. Unauthorized access attempts are monitored and recorded.
              </p>
            </div>
          </div>
        </div>
      </main>

      {/* Institutional Footer */}
      <footer className="w-full max-w-6xl mx-auto py-4 text-center text-xs text-slate-500">
        <p>© {new Date().getFullYear()} Digital Student Attendance System. Strict server authority enforced.</p>
      </footer>
    </div>
  );
}
