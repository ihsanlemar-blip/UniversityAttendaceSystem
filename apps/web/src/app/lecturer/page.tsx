'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import {
  GraduationCap,
  Calendar,
  Clock,
  QrCode,
  Users,
  Building,
  ArrowRight,
  RefreshCw,
  Search,
  AlertCircle,
  Play,
  CheckCircle2,
  XCircle,
} from 'lucide-react';
import { useAuth } from '@/context/auth-context';
import { AppShell, PageHeader } from '@/components/layout';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  Button,
  Badge,
  Input,
  Skeleton,
  ErrorState,
  EmptyState,
} from '@/components/ui';

interface ClassOccurrenceItem {
  id: string;
  course_code?: string | null;
  course_name?: string | null;
  section_name?: string | null;
  room_number?: string | null;
  building_name?: string | null;
  local_date: string;
  scheduled_start_utc: string;
  scheduled_end_utc: string;
  status: string; // SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED
}

export default function LecturerPortalPage() {
  const { user, token } = useAuth();
  const [occurrences, setOccurrences] = useState<ClassOccurrenceItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [manualOccurrenceId, setManualOccurrenceId] = useState('');

  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';

  const fetchSchedule = useCallback(async () => {
    if (!token) return;
    setIsLoading(true);
    setError(null);
    try {
      // First try to fetch instructor's personal schedule
      const res = await fetch(`${apiBase}/scheduling/lecturers/me/class-occurrences`, {
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: 'application/json',
        },
      });

      if (res.ok) {
        const json = await res.json();
        const items: ClassOccurrenceItem[] = json.data || [];
        setOccurrences(items);
      } else {
        // If 403 or empty, fallback to today's occurrences list
        const today = new Date().toISOString().split('T')[0];
        const res2 = await fetch(`${apiBase}/scheduling/class-occurrences?date=${today}`, {
          headers: {
            Authorization: `Bearer ${token}`,
            Accept: 'application/json',
          },
        });
        if (res2.ok) {
          const json2 = await res2.json();
          setOccurrences(json2.data || []);
        } else {
          setOccurrences([]);
        }
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to load teaching schedule.');
    } finally {
      setIsLoading(false);
    }
  }, [token, apiBase]);

  useEffect(() => {
    let ignore = false;
    async function load() {
      if (!token) return;
      try {
        const res = await fetch(`${apiBase}/scheduling/lecturers/me/class-occurrences`, {
          headers: {
            Authorization: `Bearer ${token}`,
            Accept: 'application/json',
          },
        });
        if (res.ok && !ignore) {
          const json = await res.json();
          setOccurrences(json.data || []);
        }
      } catch (err: any) {
        if (!ignore) {
          setError(err?.message || 'Failed to load schedule.');
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

  const filteredOccurrences = occurrences.filter((occ) => {
    const q = searchQuery.toLowerCase();
    return (
      (occ.course_code?.toLowerCase().includes(q) ?? false) ||
      (occ.course_name?.toLowerCase().includes(q) ?? false) ||
      (occ.room_number?.toLowerCase().includes(q) ?? false) ||
      (occ.section_name?.toLowerCase().includes(q) ?? false)
    );
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'SCHEDULED':
        return <Badge variant="info" size="sm">Scheduled</Badge>;
      case 'ACTIVE':
      case 'IN_PROGRESS':
        return <Badge variant="success" size="sm">Active Session</Badge>;
      case 'COMPLETED':
        return <Badge variant="default" size="sm">Completed</Badge>;
      case 'CANCELLED':
        return <Badge variant="danger" size="sm">Cancelled</Badge>;
      default:
        return <Badge variant="default" size="sm">{status}</Badge>;
    }
  };

  const formatTimeRange = (startUtc: string, endUtc: string) => {
    try {
      const s = new Date(startUtc);
      const e = new Date(endUtc);
      return `${s.toUTCString().slice(17, 22)} – ${e.toUTCString().slice(17, 22)} UTC`;
    } catch {
      return `${startUtc} – ${endUtc}`;
    }
  };

  return (
    <AppShell>
      <PageHeader
        title="Lecturer Academic Console"
        description="Review assigned class meetings, launch live attendance sessions, and broadcast cryptographic verification checkpoints."
        breadcrumbs={[{ label: 'Lecturer Console' }]}
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={fetchSchedule}
              isLoading={isLoading}
              className="bg-white"
            >
              <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
              Refresh
            </Button>
            <Link href="/admin/reports/attendance">
              <Button variant="outline" size="sm" className="bg-white">
                View Reports
              </Button>
            </Link>
          </div>
        }
      />

      {/* Instructor Profile Card */}
      <div className="p-5 bg-gradient-to-r from-sky-900 via-sky-800 to-indigo-950 text-white rounded-xl shadow-xs mb-8 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-white/10 backdrop-blur-sm border border-white/20 flex items-center justify-center text-sky-300 shrink-0">
            <GraduationCap className="w-7 h-7" />
          </div>
          <div>
            <h2 className="text-base font-bold text-white">
              {user?.username || 'Faculty Instructor'}
            </h2>
            <p className="text-xs text-sky-200 mt-0.5">
              Authorized Teaching Faculty &bull; University Attendance Trust Domain
            </p>
            <div className="flex items-center gap-2 mt-2">
              <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                ACTIVE FACULTY
              </span>
              <span className="text-[11px] text-sky-300">
                Tenant ID: {user?.university_id ? `${user.university_id.slice(0, 8)}...` : 'Default'}
              </span>
            </div>
          </div>
        </div>

        {/* Quick Launch by Occurrence ID */}
        <div className="bg-white/10 backdrop-blur-xs p-3 rounded-lg border border-white/15 max-w-xs w-full">
          <label className="block text-[11px] font-semibold text-sky-200 mb-1">
            Direct Occurrence Jump
          </label>
          <div className="flex gap-1.5">
            <input
              type="text"
              placeholder="Paste Occurrence UUID"
              value={manualOccurrenceId}
              onChange={(e) => setManualOccurrenceId(e.target.value.trim())}
              className="px-2.5 py-1 text-xs rounded bg-white text-slate-900 placeholder:text-slate-400 focus:outline-none w-full"
            />
            {manualOccurrenceId && (
              <Link href={`/lecturer/session/${manualOccurrenceId}`}>
                <Button variant="primary" size="sm" className="bg-sky-500 hover:bg-sky-400 text-white h-7 px-2">
                  <ArrowRight className="w-3.5 h-3.5" />
                </Button>
              </Link>
            )}
          </div>
        </div>
      </div>

      {/* Class Meetings Section */}
      <Card>
        <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <CardTitle>Teaching Schedule &amp; Class Occurrences</CardTitle>
            <CardDescription>
              Select a scheduled class meeting to initialize attendance or open session control.
            </CardDescription>
          </div>
          <div className="w-full sm:w-64">
            <div className="relative">
              <span className="absolute inset-y-0 left-0 pl-2.5 flex items-center pointer-events-none text-slate-400">
                <Search className="w-3.5 h-3.5" />
              </span>
              <input
                type="text"
                placeholder="Search course or room..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-sky-500"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6 space-y-3">
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
            </div>
          ) : error ? (
            <div className="p-6">
              <ErrorState title="Failed to Load Schedule" message={error} onRetry={fetchSchedule} />
            </div>
          ) : filteredOccurrences.length === 0 ? (
            <div className="p-8 text-center">
              <EmptyState
                icon={<Calendar className="w-8 h-8 text-slate-400" />}
                title="No Scheduled Occurrences Found"
                description="There are currently no active calendar class meetings assigned for this academic term. You can paste an occurrence ID above or view semester timetables."
                action={
                  <Button variant="outline" size="sm" onClick={fetchSchedule}>
                    <RefreshCw className="w-3.5 h-3.5 mr-1" />
                    Check Again
                  </Button>
                }
              />
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {filteredOccurrences.map((occ) => (
                <div
                  key={occ.id}
                  className="p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-slate-50/80 transition-colors"
                >
                  <div className="flex items-start gap-4">
                    <div className="p-3 rounded-xl bg-sky-50 text-sky-700 border border-sky-100 shrink-0">
                      <QrCode className="w-6 h-6" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-800 border border-slate-200">
                          {occ.course_code || 'COURSE'}
                        </span>
                        <h3 className="text-sm font-semibold text-slate-900">
                          {occ.course_name || 'Academic Course Occurrence'}
                        </h3>
                        {getStatusBadge(occ.status)}
                      </div>

                      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500 mt-1.5">
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3.5 h-3.5 text-slate-400" />
                          {occ.local_date}
                        </span>
                        <span className="flex items-center gap-1">
                          <Clock className="w-3.5 h-3.5 text-slate-400" />
                          {formatTimeRange(occ.scheduled_start_utc, occ.scheduled_end_utc)}
                        </span>
                        <span className="flex items-center gap-1">
                          <Building className="w-3.5 h-3.5 text-slate-400" />
                          {occ.room_number ? `${occ.building_name || 'Building'} - Room ${occ.room_number}` : 'Room TBA'}
                        </span>
                        {occ.section_name && (
                          <span className="flex items-center gap-1">
                            <Users className="w-3.5 h-3.5 text-slate-400" />
                            Section: {occ.section_name}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 shrink-0 self-end md:self-center">
                    <Link href={`/lecturer/session/${occ.id}`}>
                      <Button
                        variant="primary"
                        size="sm"
                        className="bg-sky-600 hover:bg-sky-700 active:bg-sky-800 focus:ring-sky-500 shadow-sm"
                      >
                        <Play className="w-3.5 h-3.5 mr-1.5" />
                        Manage Session
                        <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
                      </Button>
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </AppShell>
  );
}
