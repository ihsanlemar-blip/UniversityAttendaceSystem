'use client';

import React, { Suspense } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { ShieldX, ArrowLeft, LogOut } from 'lucide-react';
import { useAuth } from '@/context/auth-context';
import { Button } from '@/components/ui';

function UnauthorizedContent() {
  const searchParams = useSearchParams();
  const requiredPermission = searchParams.get('required');
  const { user, logout } = useAuth();

  const isLecturer = user?.roles.includes('LECTURER');
  const homeHref = isLecturer ? '/lecturer' : '/admin';

  return (
    <div className="min-h-screen flex flex-col justify-center items-center bg-slate-100/70 p-4 sm:p-6 lg:p-8">
      <div className="w-full max-w-md bg-white border border-slate-200 rounded-2xl shadow-xl p-8 text-center">
        <div className="w-16 h-16 rounded-2xl bg-rose-50 border border-rose-200 flex items-center justify-center mx-auto mb-4 text-rose-600">
          <ShieldX className="w-9 h-9" />
        </div>

        <h1 className="text-xl font-bold text-slate-900 mb-2">Access Denied (403)</h1>
        <p className="text-sm text-slate-600 mb-6 leading-relaxed">
          Your account does not possess the institutional permissions required to view or modify this resource.
        </p>

        {requiredPermission && (
          <div className="mb-6 p-3 bg-slate-50 border border-slate-200 rounded-lg text-left">
            <span className="block text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-1">
              Required Permission Code
            </span>
            <code className="text-xs font-mono text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-200">
              {requiredPermission}
            </code>
          </div>
        )}

        {user && (
          <div className="mb-6 text-xs text-slate-500 bg-slate-50 p-2.5 rounded-lg border border-slate-100">
            Signed in as <span className="font-semibold text-slate-800">{user.username}</span> ({user.roles.join(', ')})
          </div>
        )}

        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link href={homeHref} className="w-full sm:w-auto">
            <Button variant="primary" className="w-full">
              <ArrowLeft className="w-4 h-4 mr-1.5" />
              Return to Dashboard
            </Button>
          </Link>
          <Button variant="outline" onClick={logout} className="w-full sm:w-auto">
            <LogOut className="w-4 h-4 mr-1.5 text-slate-400" />
            Sign Out
          </Button>
        </div>
      </div>
    </div>
  );
}

export default function UnauthorizedPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center bg-slate-100 text-sm text-slate-500">Loading...</div>}>
      <UnauthorizedContent />
    </Suspense>
  );
}
