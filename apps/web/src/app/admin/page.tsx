'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import {
  Activity,
  Calendar,
  ClipboardCheck,
  ShieldAlert,
  Users,
  BookOpen,
  ArrowRight,
  RefreshCw,
  UploadCloud,
  Smartphone,
  Sliders,
  AlertTriangle,
  FileSpreadsheet,
} from 'lucide-react';
import { useAuth } from '@/context/auth-context';
import { PageHeader } from '@/components/layout';
import {
  KpiCard,
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  Button,
  Badge,
  Skeleton,
  ErrorState,
  EmptyState,
} from '@/components/ui';

interface DashboardSummary {
  total_students: number;
  total_lecturers: number;
  total_course_offerings: number;
  today_occurrences_count: number;
  active_attendance_sessions_count: number;
  pending_corrections_count: number;
  pending_excuses_count: number;
  pending_leaves_count: number;
  open_risk_signals_count: number;
  pending_devices_count: number;
  generated_at_utc: string;
}

export default function AdminDashboardPage() {
  const { token } = useAuth();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());

  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';

  const fetchSummary = useCallback(async () => {
    if (!token) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(`${apiBase}/reports/attendance/dashboard/summary`, {
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: 'application/json',
        },
      });

      if (!res.ok) {
        throw new Error(`Failed to load dashboard summary (HTTP ${res.status})`);
      }

      const json = await res.json();
      setSummary(json.data);
      setLastRefreshed(new Date());
    } catch (err: any) {
      setError(err?.message || 'Failed to load dashboard data. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }, [token, apiBase]);

  useEffect(() => {
    let ignore = false;
    async function load() {
      if (!token) return;
      try {
        const res = await fetch(`${apiBase}/reports/attendance/dashboard/summary`, {
          headers: {
            Authorization: `Bearer ${token}`,
            Accept: 'application/json',
          },
        });

        if (!res.ok) {
          throw new Error(`Failed to load dashboard summary (HTTP ${res.status})`);
        }

        const json = await res.json();
        if (!ignore) {
          setSummary(json.data);
          setLastRefreshed(new Date());
        }
      } catch (err: any) {
        if (!ignore) {
          setError(err?.message || 'Failed to load dashboard data. Please try again.');
        }
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    }

    load();
    return () => {
      ignore = true;
    };
  }, [token, apiBase]);

  const totalPendingReviews =
    (summary?.pending_corrections_count || 0) +
    (summary?.pending_excuses_count || 0) +
    (summary?.pending_leaves_count || 0);

  return (
    <div>
      <PageHeader
        title="Institutional Operations Dashboard"
        description="High-assurance academic session governance, attendance verification, and operational queue oversight."
        breadcrumbs={[{ label: 'Dashboard' }]}
        actions={
          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-400 hidden sm:inline">
              Refreshed: {lastRefreshed.toLocaleTimeString()}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={fetchSummary}
              isLoading={isLoading}
              className="bg-white"
            >
              <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
              Refresh
            </Button>
          </div>
        }
      />

      {error ? (
        <ErrorState
          title="Dashboard Unavailable"
          message={error}
          onRetry={fetchSummary}
          className="my-8"
        />
      ) : (
        <>
          {/* KPI Metrics Grid */}
          <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-8">
            <KpiCard
              title="Active Sessions"
              value={summary?.active_attendance_sessions_count ?? 0}
              subtitle="Open or paused in campus"
              icon={<Activity className="w-5 h-5 text-emerald-600" />}
              variant="success"
              href="/admin/reports/attendance"
              isLoading={isLoading}
            />
            <KpiCard
              title="Today's Classes"
              value={summary?.today_occurrences_count ?? 0}
              subtitle="Scheduled occurrences"
              icon={<Calendar className="w-5 h-5 text-sky-600" />}
              variant="info"
              href="/admin/reports/attendance"
              isLoading={isLoading}
            />
            <KpiCard
              title="Pending Reviews"
              value={totalPendingReviews}
              subtitle="Corrections & excuses"
              icon={<ClipboardCheck className="w-5 h-5 text-amber-600" />}
              variant={totalPendingReviews > 0 ? 'warning' : 'default'}
              href="/admin/attendance/reviews"
              isLoading={isLoading}
            />
            <KpiCard
              title="Open Risk Signals"
              value={summary?.open_risk_signals_count ?? 0}
              subtitle="Flagged anomalies"
              icon={<ShieldAlert className="w-5 h-5 text-rose-600" />}
              variant={(summary?.open_risk_signals_count ?? 0) > 0 ? 'danger' : 'default'}
              href="/admin/security"
              isLoading={isLoading}
            />
            <KpiCard
              title="Enrolled Students"
              value={summary?.total_students ?? 0}
              subtitle="Active university students"
              icon={<Users className="w-5 h-5 text-slate-700" />}
              variant="default"
              isLoading={isLoading}
            />
            <KpiCard
              title="Active Offerings"
              value={summary?.total_course_offerings ?? 0}
              subtitle="Active semester courses"
              icon={<BookOpen className="w-5 h-5 text-slate-700" />}
              variant="default"
              isLoading={isLoading}
            />
          </section>

          {/* Operational Sections */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
            {/* Action Queues Panel */}
            <Card className="lg:col-span-2">
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle>Attendance Operations & Review Queues</CardTitle>
                  <CardDescription>
                    Pending verification and authorization requests requiring academic decision.
                  </CardDescription>
                </div>
                <Link href="/admin/attendance/reviews">
                  <Button variant="ghost" size="sm" className="text-sky-600 hover:text-sky-800">
                    Open Queue
                    <ArrowRight className="w-3.5 h-3.5 ml-1" />
                  </Button>
                </Link>
              </CardHeader>
              <CardContent>
                {isLoading ? (
                  <div className="space-y-3">
                    <Skeleton className="h-16 w-full" />
                    <Skeleton className="h-16 w-full" />
                    <Skeleton className="h-16 w-full" />
                  </div>
                ) : (
                  <div className="space-y-3">
                    {/* Corrections item */}
                    <div className="flex items-center justify-between p-3.5 bg-slate-50 border border-slate-200 rounded-xl hover:bg-slate-100/60 transition-colors">
                      <div className="flex items-center gap-3">
                        <div className="p-2.5 rounded-lg bg-amber-100 text-amber-800">
                          <ClipboardCheck className="w-4 h-4" />
                        </div>
                        <div>
                          <h4 className="text-xs font-semibold text-slate-900">
                            Attendance Corrections
                          </h4>
                          <p className="text-[11px] text-slate-500">
                            Student claims for post-session attendance amendments
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <Badge
                          variant={summary?.pending_corrections_count ? 'warning' : 'default'}
                          size="sm"
                        >
                          {summary?.pending_corrections_count ?? 0} Pending
                        </Badge>
                        <Link href="/admin/attendance/reviews">
                          <Button variant="outline" size="sm" className="bg-white">
                            Review
                          </Button>
                        </Link>
                      </div>
                    </div>

                    {/* Excuses item */}
                    <div className="flex items-center justify-between p-3.5 bg-slate-50 border border-slate-200 rounded-xl hover:bg-slate-100/60 transition-colors">
                      <div className="flex items-center gap-3">
                        <div className="p-2.5 rounded-lg bg-sky-100 text-sky-800">
                          <ClipboardCheck className="w-4 h-4" />
                        </div>
                        <div>
                          <h4 className="text-xs font-semibold text-slate-900">
                            Absence Excuse Requests
                          </h4>
                          <p className="text-[11px] text-slate-500">
                            Medical certificates and administrative excuse documentation
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <Badge
                          variant={summary?.pending_excuses_count ? 'info' : 'default'}
                          size="sm"
                        >
                          {summary?.pending_excuses_count ?? 0} Pending
                        </Badge>
                        <Link href="/admin/attendance/reviews">
                          <Button variant="outline" size="sm" className="bg-white">
                            Review
                          </Button>
                        </Link>
                      </div>
                    </div>

                    {/* Leaves item */}
                    <div className="flex items-center justify-between p-3.5 bg-slate-50 border border-slate-200 rounded-xl hover:bg-slate-100/60 transition-colors">
                      <div className="flex items-center gap-3">
                        <div className="p-2.5 rounded-lg bg-emerald-100 text-emerald-800">
                          <ClipboardCheck className="w-4 h-4" />
                        </div>
                        <div>
                          <h4 className="text-xs font-semibold text-slate-900">
                            Leave Requests
                          </h4>
                          <p className="text-[11px] text-slate-500">
                            Anticipated student academic leaves awaiting dean endorsement
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <Badge
                          variant={summary?.pending_leaves_count ? 'success' : 'default'}
                          size="sm"
                        >
                          {summary?.pending_leaves_count ?? 0} Pending
                        </Badge>
                        <Link href="/admin/attendance/reviews">
                          <Button variant="outline" size="sm" className="bg-white">
                            Review
                          </Button>
                        </Link>
                      </div>
                    </div>

                    {/* Pending Devices item */}
                    <div className="flex items-center justify-between p-3.5 bg-slate-50 border border-slate-200 rounded-xl hover:bg-slate-100/60 transition-colors">
                      <div className="flex items-center gap-3">
                        <div className="p-2.5 rounded-lg bg-purple-100 text-purple-800">
                          <Smartphone className="w-4 h-4" />
                        </div>
                        <div>
                          <h4 className="text-xs font-semibold text-slate-900">
                            Device Trust Authorizations
                          </h4>
                          <p className="text-[11px] text-slate-500">
                            Hardware binding and device replacement verifications
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <Badge
                          variant={summary?.pending_devices_count ? 'default' : 'default'}
                          size="sm"
                        >
                          {summary?.pending_devices_count ?? 0} Pending
                        </Badge>
                        <Link href="/admin/devices">
                          <Button variant="outline" size="sm" className="bg-white">
                            Manage
                          </Button>
                        </Link>
                      </div>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Quick Actions & Short Cuts */}
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>Administrative Shortcuts</CardTitle>
                  <CardDescription>Direct navigation to operational management hubs.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-2">
                  <Link
                    href="/admin/reports/attendance"
                    className="flex items-center justify-between p-3 rounded-lg border border-slate-200 hover:border-sky-300 hover:bg-sky-50/50 transition-all group"
                  >
                    <div className="flex items-center gap-3">
                      <FileSpreadsheet className="w-4 h-4 text-sky-600" />
                      <div>
                        <span className="text-xs font-semibold text-slate-800 block">Attendance Reports</span>
                        <span className="text-[11px] text-slate-500">Audit ledgers, thresholds & CSV exports</span>
                      </div>
                    </div>
                    <ArrowRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-sky-600 transition-colors" />
                  </Link>

                  <Link
                    href="/admin/imports"
                    className="flex items-center justify-between p-3 rounded-lg border border-slate-200 hover:border-sky-300 hover:bg-sky-50/50 transition-all group"
                  >
                    <div className="flex items-center gap-3">
                      <UploadCloud className="w-4 h-4 text-sky-600" />
                      <div>
                        <span className="text-xs font-semibold text-slate-800 block">Data Import Center</span>
                        <span className="text-[11px] text-slate-500">Staging, preview & commit rosters</span>
                      </div>
                    </div>
                    <ArrowRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-sky-600 transition-colors" />
                  </Link>

                  <Link
                    href="/admin/security"
                    className="flex items-center justify-between p-3 rounded-lg border border-slate-200 hover:border-rose-300 hover:bg-rose-50/50 transition-all group"
                  >
                    <div className="flex items-center gap-3">
                      <ShieldAlert className="w-4 h-4 text-rose-600" />
                      <div>
                        <span className="text-xs font-semibold text-slate-800 block">Risk Signals & Defense</span>
                        <span className="text-[11px] text-slate-500">Anomaly flags & tamper monitoring</span>
                      </div>
                    </div>
                    <ArrowRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-rose-600 transition-colors" />
                  </Link>

                  <Link
                    href="/admin/settings/attendance"
                    className="flex items-center justify-between p-3 rounded-lg border border-slate-200 hover:border-slate-300 hover:bg-slate-50 transition-all group"
                  >
                    <div className="flex items-center gap-3">
                      <Sliders className="w-4 h-4 text-slate-600" />
                      <div>
                        <span className="text-xs font-semibold text-slate-800 block">Attendance Policy</span>
                        <span className="text-[11px] text-slate-500">Configure windows, thresholds & rules</span>
                      </div>
                    </div>
                    <ArrowRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-slate-600 transition-colors" />
                  </Link>
                </CardContent>
              </Card>

              {/* Institutional Notice Card */}
              <div className="p-4 bg-sky-900 text-white rounded-xl shadow-xs">
                <div className="flex items-center gap-2 mb-1.5">
                  <AlertTriangle className="w-4 h-4 text-sky-300" />
                  <span className="text-xs font-bold uppercase tracking-wider text-sky-200">
                    Institutional Governance Invariant
                  </span>
                </div>
                <p className="text-xs text-sky-100 leading-relaxed">
                  All attendance evaluations depend strictly on university server UTC timestamps. Client devices cannot mark themselves present.
                </p>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
