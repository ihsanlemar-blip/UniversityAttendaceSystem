'use client';

import React, { useState, useMemo, FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { ShieldAlert, Check, X, Lock, LogOut } from 'lucide-react';
import { useAuth } from '@/context/auth-context';
import { Button, Alert } from '@/components/ui';

export default function ChangePasswordPage() {
  const { user, changePassword, logout } = useAuth();
  const router = useRouter();

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Policy validation checks
  const checks = useMemo(() => {
    return {
      minLength: newPassword.length >= 8,
      hasUpper: /[A-Z]/.test(newPassword),
      hasLower: /[a-z]/.test(newPassword),
      hasDigit: /[0-9]/.test(newPassword),
      hasSpecial: /[^A-Za-z0-9]/.test(newPassword),
      matches: newPassword.length > 0 && newPassword === confirmPassword,
      differs: newPassword.length > 0 && currentPassword.length > 0 && newPassword !== currentPassword,
    };
  }, [newPassword, confirmPassword, currentPassword]);

  const allValid =
    checks.minLength &&
    checks.hasUpper &&
    checks.hasLower &&
    checks.hasDigit &&
    checks.hasSpecial &&
    checks.matches &&
    checks.differs;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!allValid) {
      setError('Please satisfy all password policy criteria below before submitting.');
      return;
    }

    setError(null);
    setIsLoading(true);

    try {
      const res = await changePassword(currentPassword, newPassword);
      if (res.success) {
        setSuccess(true);
        setTimeout(() => {
          if (user?.roles.includes('LECTURER')) {
            router.push('/lecturer');
          } else {
            router.push('/admin');
          }
        }, 1500);
      } else {
        setError(res.error || 'Failed to update password. Please verify your current password.');
      }
    } catch {
      setError('An unexpected error occurred while updating your password.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col justify-center items-center bg-slate-100/70 p-4 sm:p-6 lg:p-8">
      <main className="w-full max-w-lg">
        <div className="bg-white border border-slate-200 rounded-2xl shadow-xl overflow-hidden">
          {/* Warning Header */}
          <div className="bg-amber-600 p-6 text-white text-center">
            <div className="w-12 h-12 rounded-xl bg-white/15 backdrop-blur-sm border border-white/20 flex items-center justify-center mx-auto mb-3">
              <ShieldAlert className="w-7 h-7 text-amber-100" />
            </div>
            <h1 className="text-xl font-bold tracking-tight">Security Action Required</h1>
            <p className="text-xs text-amber-100 mt-1">
              You must update your institutional password to continue accessing the system.
            </p>
          </div>

          <div className="p-6 sm:p-8">
            {error && (
              <Alert variant="destructive" className="mb-6" onDismiss={() => setError(null)}>
                {error}
              </Alert>
            )}

            {success && (
              <Alert variant="success" className="mb-6">
                Password changed successfully! Redirecting to your dashboard...
              </Alert>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5">
                  Current Password
                </label>
                <div className="relative">
                  <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                    <Lock className="w-4 h-4" />
                  </span>
                  <input
                    type="password"
                    required
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    placeholder="Enter current password"
                    className="w-full pl-9 pr-3 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent transition-all"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5">
                  New Password
                </label>
                <div className="relative">
                  <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                    <Lock className="w-4 h-4" />
                  </span>
                  <input
                    type="password"
                    required
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="Enter new strong password"
                    className="w-full pl-9 pr-3 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent transition-all"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5">
                  Confirm New Password
                </label>
                <div className="relative">
                  <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                    <Lock className="w-4 h-4" />
                  </span>
                  <input
                    type="password"
                    required
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Confirm new strong password"
                    className="w-full pl-9 pr-3 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent transition-all"
                  />
                </div>
              </div>

              {/* Password Policy Checklist */}
              <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2 mt-4">
                <span className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-2">
                  Institutional Password Policy Checklist
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                  <PolicyItem passed={checks.minLength} label="At least 8 characters" />
                  <PolicyItem passed={checks.hasUpper} label="Uppercase letter (A-Z)" />
                  <PolicyItem passed={checks.hasLower} label="Lowercase letter (a-z)" />
                  <PolicyItem passed={checks.hasDigit} label="Number digit (0-9)" />
                  <PolicyItem passed={checks.hasSpecial} label="Special character (!@#...)" />
                  <PolicyItem passed={checks.differs} label="Different from current" />
                  <PolicyItem passed={checks.matches} label="Passwords match" />
                </div>
              </div>

              <div className="pt-3 flex items-center justify-between gap-3">
                <button
                  type="button"
                  onClick={logout}
                  className="inline-flex items-center text-xs font-medium text-slate-600 hover:text-slate-900 px-3 py-2 rounded-lg hover:bg-slate-100 transition-colors"
                >
                  <LogOut className="w-4 h-4 mr-1.5 text-slate-400" />
                  Sign Out
                </button>
                <Button
                  type="submit"
                  variant="primary"
                  size="md"
                  disabled={!allValid || isLoading}
                  isLoading={isLoading}
                  className="bg-amber-600 hover:bg-amber-700 active:bg-amber-800 focus:ring-amber-500"
                >
                  Update Password & Proceed
                </Button>
              </div>
            </form>
          </div>
        </div>
      </main>
    </div>
  );
}

function PolicyItem({ passed, label }: { passed: boolean; label: string }) {
  return (
    <div className="flex items-center gap-1.5">
      {passed ? (
        <span className="w-4 h-4 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center shrink-0">
          <Check className="w-3 h-3" />
        </span>
      ) : (
        <span className="w-4 h-4 rounded-full bg-slate-200 text-slate-400 flex items-center justify-center shrink-0">
          <X className="w-3 h-3" />
        </span>
      )}
      <span className={passed ? 'text-emerald-800 font-medium' : 'text-slate-500'}>
        {label}
      </span>
    </div>
  );
}
