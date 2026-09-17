'use client';

import React, { useState, useEffect, useCallback, use } from 'react';
import Link from 'next/link';
import {
  Play,
  Pause,
  StopCircle,
  QrCode,
  Radio,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Users,
  ShieldCheck,
  Search,
  RefreshCw,
  FileSpreadsheet,
  ArrowLeft,
  Lock,
  Building,
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
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  Alert,
  Dialog,
  Skeleton,
  ErrorState,
} from '@/components/ui';
import { LecturerQrDisplay } from '@/components/LecturerQrDisplay';

interface CheckpointData {
  id: string;
  type: 'START' | 'MIDDLE' | 'END' | string;
  status: 'NOT_OPENED' | 'OPEN' | 'CLOSED' | string;
  window_opened_at_utc?: string | null;
  window_closed_at_utc?: string | null;
  window_duration_seconds?: number | null;
}

interface SessionData {
  id: string;
  university_id: string;
  class_occurrence_id: string;
  attendance_policy_id?: string | null;
  policy_snapshot?: Record<string, any> | null;
  status: 'SCHEDULED' | 'ACTIVE' | 'PAUSED' | 'CLOSED' | string;
  host_type: string;
  opened_at_utc?: string | null;
  paused_at_utc?: string | null;
  resumed_at_utc?: string | null;
  closed_at_utc?: string | null;
  checkpoints: CheckpointData[];
  total_enrolled: number;
  total_present: number;
  total_late: number;
  total_absent: number;
  total_excused: number;
  total_leave: number;
  total_pending: number;
}

interface ClassOccurrenceData {
  id: string;
  course_code?: string | null;
  course_name?: string | null;
  section_name?: string | null;
  room_number?: string | null;
  building_name?: string | null;
  local_date: string;
  scheduled_start_utc: string;
  scheduled_end_utc: string;
  status: string;
}

interface AttendanceRecordItem {
  id: string;
  student_id: string;
  student_number?: string | null;
  student_name?: string | null;
  status: string; // PENDING, PRESENT, LATE, ABSENT, EXCUSED, LEAVE
  source_mode?: string | null;
  first_verified_at_utc?: string | null;
  last_verified_at_utc?: string | null;
  has_revision?: boolean;
}

interface BleAdvData {
  checkpoint_id: string;
  service_uuid: string;
  major: number;
  minor: number;
  payload_base64: string;
  rotation_seconds: number;
  expires_at_utc: string;
}

export default function LecturerSessionControlPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id: occurrenceId } = use(params);
  const { user, token } = useAuth();

  const [occurrence, setOccurrence] = useState<ClassOccurrenceData | null>(null);
  const [session, setSession] = useState<SessionData | null>(null);
  const [records, setRecords] = useState<AttendanceRecordItem[]>([]);
  const [bleAdv, setBleAdv] = useState<BleAdvData | null>(null);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshingRoster, setIsRefreshingRoster] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [searchRoster, setSearchRoster] = useState('');

  // Modals state
  const [showCloseModal, setShowCloseModal] = useState(false);
  const [showManualModal, setShowManualModal] = useState(false);
  const [manualStudentId, setManualStudentId] = useState('');
  const [manualCheckpointType, setManualCheckpointType] = useState('START');
  const [manualReason, setManualReason] = useState('');
  const [isSubmittingManual, setIsSubmittingManual] = useState(false);

  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';

  // Load session and occurrence
  const loadData = useCallback(async () => {
    if (!token || !occurrenceId) return;
    setError(null);
    try {
      // 1. Fetch Occurrence
      const occRes = await fetch(`${apiBase}/scheduling/class-occurrences/${occurrenceId}`, {
        headers: { Authorization: `Bearer ${token}`, Accept: 'application/json' },
      });
      if (occRes.ok) {
        const occJson = await occRes.json();
        setOccurrence(occJson.data);
      }

      // 2. Fetch Session by Occurrence
      const sessRes = await fetch(`${apiBase}/attendance/sessions/by-occurrence/${occurrenceId}`, {
        headers: { Authorization: `Bearer ${token}`, Accept: 'application/json' },
      });

      if (sessRes.ok) {
        const sessJson = await sessRes.json();
        const sessData: SessionData = sessJson.data;
        setSession(sessData);

        // Fetch roster records
        const recRes = await fetch(`${apiBase}/attendance/sessions/${sessData.id}/records`, {
          headers: { Authorization: `Bearer ${token}`, Accept: 'application/json' },
        });
        if (recRes.ok) {
          const recJson = await recRes.json();
          setRecords(recJson.data || []);
        }

        // If a checkpoint is OPEN, fetch BLE ad info
        const openCp = sessData.checkpoints.find((c) => c.status === 'OPEN');
        if (openCp) {
          try {
            const bleRes = await fetch(`${apiBase}/attendance/checkpoints/${openCp.id}/ble-advertisement`, {
              headers: { Authorization: `Bearer ${token}`, Accept: 'application/json' },
            });
            if (bleRes.ok) {
              const bleJson = await bleRes.json();
              setBleAdv(bleJson.data);
            }
          } catch {
            // Non-fatal if BLE not enabled
          }
        } else {
          setBleAdv(null);
        }
      } else if (sessRes.status === 404) {
        setSession(null);
      } else {
        throw new Error(`Failed to load attendance session (HTTP ${sessRes.status})`);
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to initialize session view.');
    } finally {
      setIsLoading(false);
      setIsRefreshingRoster(false);
    }
  }, [token, occurrenceId, apiBase]);

  useEffect(() => {
    let ignore = false;
    async function init() {
      if (!token || !occurrenceId) return;
      try {
        const occRes = await fetch(`${apiBase}/scheduling/class-occurrences/${occurrenceId}`, {
          headers: { Authorization: `Bearer ${token}`, Accept: 'application/json' },
        });
        if (occRes.ok && !ignore) {
          const occJson = await occRes.json();
          setOccurrence(occJson.data);
        }

        const sessRes = await fetch(`${apiBase}/attendance/sessions/by-occurrence/${occurrenceId}`, {
          headers: { Authorization: `Bearer ${token}`, Accept: 'application/json' },
        });

        if (sessRes.ok && !ignore) {
          const sessJson = await sessRes.json();
          const sessData: SessionData = sessJson.data;
          setSession(sessData);

          const recRes = await fetch(`${apiBase}/attendance/sessions/${sessData.id}/records`, {
            headers: { Authorization: `Bearer ${token}`, Accept: 'application/json' },
          });
          if (recRes.ok && !ignore) {
            const recJson = await recRes.json();
            setRecords(recJson.data || []);
          }
        }
      } catch (err: any) {
        if (!ignore) {
          setError(err?.message || 'Error loading session.');
        }
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    }

    init();
    return () => {
      ignore = true;
    };
  }, [token, occurrenceId, apiBase]);

  // Periodic roster polling when session is ACTIVE
  useEffect(() => {
    if (!session || session.status !== 'ACTIVE' || !token) return;

    const interval = setInterval(async () => {
      try {
        const recRes = await fetch(`${apiBase}/attendance/sessions/${session.id}/records`, {
          headers: { Authorization: `Bearer ${token}`, Accept: 'application/json' },
        });
        if (recRes.ok) {
          const recJson = await recRes.json();
          setRecords(recJson.data || []);
        }
      } catch {
        // Ignore background polling errors
      }
    }, 10000);

    return () => clearInterval(interval);
  }, [session, token, apiBase]);

  // Action Handlers
  const handleStartSession = async () => {
    if (!token) return;
    setActionError(null);
    try {
      const res = await fetch(`${apiBase}/attendance/sessions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
          Accept: 'application/json',
        },
        body: JSON.stringify({
          class_occurrence_id: occurrenceId,
          activate_immediately: true,
        }),
      });

      if (!res.ok) {
        const errJson = await res.json();
        throw new Error(errJson?.detail || 'Failed to initialize session.');
      }

      await loadData();
    } catch (err: any) {
      setActionError(err?.message || 'Failed to start session.');
    }
  };

  const handleOpenCheckpoint = async (type: string) => {
    if (!token || !session) return;
    setActionError(null);
    try {
      const res = await fetch(`${apiBase}/attendance/sessions/${session.id}/checkpoints/${type}/open`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
          Accept: 'application/json',
        },
        body: JSON.stringify({ window_duration_seconds: 300 }),
      });

      if (!res.ok) {
        const errJson = await res.json();
        throw new Error(errJson?.detail || `Failed to open ${type} checkpoint.`);
      }

      await loadData();
    } catch (err: any) {
      setActionError(err?.message || `Failed to open ${type} checkpoint.`);
    }
  };

  const handleCloseCheckpoint = async (type: string) => {
    if (!token || !session) return;
    setActionError(null);
    try {
      const res = await fetch(`${apiBase}/attendance/sessions/${session.id}/checkpoints/${type}/close`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: 'application/json',
        },
      });

      if (!res.ok) {
        const errJson = await res.json();
        throw new Error(errJson?.detail || `Failed to close ${type} checkpoint.`);
      }

      await loadData();
    } catch (err: any) {
      setActionError(err?.message || `Failed to close ${type} checkpoint.`);
    }
  };

  const handlePauseResume = async () => {
    if (!token || !session) return;
    setActionError(null);
    const action = session.status === 'ACTIVE' ? 'pause' : 'resume';
    try {
      const res = await fetch(`${apiBase}/attendance/sessions/${session.id}/${action}`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: 'application/json',
        },
      });

      if (!res.ok) {
        const errJson = await res.json();
        throw new Error(errJson?.detail || `Failed to ${action} session.`);
      }

      await loadData();
    } catch (err: any) {
      setActionError(err?.message || `Failed to ${action} session.`);
    }
  };

  const handleCloseSession = async () => {
    if (!token || !session) return;
    setActionError(null);
    try {
      const res = await fetch(`${apiBase}/attendance/sessions/${session.id}/close`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: 'application/json',
        },
      });

      if (!res.ok) {
        const errJson = await res.json();
        throw new Error(errJson?.detail || 'Failed to finalize attendance session.');
      }

      setShowCloseModal(false);
      await loadData();
    } catch (err: any) {
      setActionError(err?.message || 'Failed to close session.');
    }
  };

  const handleManualCredit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !session || !manualStudentId || !manualReason.trim()) return;

    setIsSubmittingManual(true);
    setActionError(null);
    try {
      const res = await fetch(
        `${apiBase}/attendance/sessions/${session.id}/checkpoints/${manualCheckpointType}/manual-credit`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
            Accept: 'application/json',
          },
          body: JSON.stringify({
            student_id: manualStudentId,
            source_mode: 'MANUAL_OVERRIDE',
            reason: manualReason.trim(),
          }),
        }
      );

      if (!res.ok) {
        const errJson = await res.json();
        throw new Error(errJson?.detail || 'Failed to record manual credit.');
      }

      setShowManualModal(false);
      setManualReason('');
      setManualStudentId('');
      await loadData();
    } catch (err: any) {
      setActionError(err?.message || 'Failed to submit manual credit.');
    } finally {
      setIsSubmittingManual(false);
    }
  };

  const openCheckpoint = session?.checkpoints.find((c) => c.status === 'OPEN');

  const filteredRecords = records.filter((rec) => {
    const q = searchRoster.toLowerCase();
    return (
      (rec.student_name?.toLowerCase().includes(q) ?? false) ||
      (rec.student_number?.toLowerCase().includes(q) ?? false)
    );
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'PRESENT':
        return <Badge variant="success" size="sm">Present</Badge>;
      case 'LATE':
        return <Badge variant="warning" size="sm">Late</Badge>;
      case 'ABSENT':
        return <Badge variant="danger" size="sm">Absent</Badge>;
      case 'EXCUSED':
        return <Badge variant="info" size="sm">Excused</Badge>;
      case 'LEAVE':
        return <Badge variant="default" size="sm">Leave (0 Credit)</Badge>;
      case 'PENDING':
      default:
        return <Badge variant="default" size="sm">Pending</Badge>;
    }
  };

  return (
    <AppShell>
      <PageHeader
        title={`Session Control: ${occurrence?.course_code || 'Course'}`}
        description={`${occurrence?.course_name || 'Academic Class'} • Room ${occurrence?.room_number || 'TBA'} • Date ${occurrence?.local_date || ''}`}
        breadcrumbs={[
          { label: 'Lecturer Console', href: '/lecturer' },
          { label: 'Session Control' },
        ]}
        actions={
          <div className="flex items-center gap-2">
            <Link href="/lecturer">
              <Button variant="outline" size="sm" className="bg-white">
                <ArrowLeft className="w-3.5 h-3.5 mr-1" />
                Back to Schedule
              </Button>
            </Link>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setIsRefreshingRoster(true);
                loadData();
              }}
              isLoading={isRefreshingRoster}
              className="bg-white"
            >
              <RefreshCw className="w-3.5 h-3.5 mr-1" />
              Refresh
            </Button>
          </div>
        }
      />

      {actionError && (
        <Alert variant="destructive" className="mb-6" onDismiss={() => setActionError(null)}>
          {actionError}
        </Alert>
      )}

      {isLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      ) : error ? (
        <ErrorState title="Session Load Failed" message={error} onRetry={loadData} />
      ) : !session ? (
        /* Session Not Started Yet */
        <Card className="p-8 text-center max-w-2xl mx-auto my-8">
          <div className="w-14 h-14 rounded-2xl bg-sky-50 border border-sky-100 flex items-center justify-center mx-auto mb-4 text-sky-600">
            <Clock className="w-8 h-8" />
          </div>
          <h2 className="text-lg font-bold text-slate-900 mb-1">
            Ready to Begin Class Attendance?
          </h2>
          <p className="text-xs text-slate-500 max-w-md mx-auto mb-6 leading-relaxed">
            Starting the attendance session will freeze the authoritative student roster for this class occurrence and allow opening rotating QR / BLE verification windows.
          </p>

          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 mb-6 text-left max-w-md mx-auto space-y-2 text-xs">
            <div className="flex justify-between">
              <span className="text-slate-500 font-medium">Course:</span>
              <span className="font-semibold text-slate-800">{occurrence?.course_code} - {occurrence?.course_name}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500 font-medium">Room &amp; Hall:</span>
              <span className="font-semibold text-slate-800">{occurrence?.building_name} Room {occurrence?.room_number}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500 font-medium">Scheduled Date:</span>
              <span className="font-semibold text-slate-800">{occurrence?.local_date}</span>
            </div>
          </div>

          <Button
            variant="primary"
            size="lg"
            onClick={handleStartSession}
            className="bg-sky-600 hover:bg-sky-700 shadow-md"
          >
            <Play className="w-4 h-4 mr-2" />
            Initialize Attendance Session
          </Button>
        </Card>
      ) : (
        /* Active / Initialized Session Dashboard */
        <div className="space-y-6">
          {/* Top Status & Controls Banner */}
          <div className="p-5 bg-white border border-slate-200 rounded-xl shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-3.5">
              <div
                className={`p-3 rounded-xl shrink-0 ${
                  session.status === 'ACTIVE'
                    ? 'bg-emerald-100 text-emerald-700'
                    : session.status === 'PAUSED'
                    ? 'bg-amber-100 text-amber-700'
                    : 'bg-slate-100 text-slate-600'
                }`}
              >
                <Radio className="w-6 h-6" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-base font-bold text-slate-900">
                    {occurrence?.course_code}: Session Lifecycle
                  </h2>
                  <Badge
                    variant={
                      session.status === 'ACTIVE'
                        ? 'success'
                        : session.status === 'PAUSED'
                        ? 'warning'
                        : 'default'
                    }
                    size="sm"
                  >
                    {session.status}
                  </Badge>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  Host Mode: {session.host_type} &bull; Policy:{' '}
                  {session.policy_snapshot?.evidence_mode || 'STANDARD_DUAL'}
                </p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              {session.status !== 'CLOSED' && (
                <>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handlePauseResume}
                    className="bg-white"
                  >
                    {session.status === 'ACTIVE' ? (
                      <>
                        <Pause className="w-3.5 h-3.5 mr-1 text-amber-600" />
                        Pause Session
                      </>
                    ) : (
                      <>
                        <Play className="w-3.5 h-3.5 mr-1 text-emerald-600" />
                        Resume Session
                      </>
                    )}
                  </Button>

                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => setShowCloseModal(true)}
                  >
                    <StopCircle className="w-3.5 h-3.5 mr-1" />
                    Close &amp; Finalize
                  </Button>
                </>
              )}

              {session.status === 'CLOSED' && (
                <Link href={`/admin/reports/attendance?session_id=${session.id}`}>
                  <Button variant="primary" size="sm" className="bg-sky-600 hover:bg-sky-700">
                    <FileSpreadsheet className="w-3.5 h-3.5 mr-1.5" />
                    View Final Session Report
                  </Button>
                </Link>
              )}
            </div>
          </div>

          {/* Checkpoint Lifecycle Controller (START, MIDDLE, END) */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {(['START', 'MIDDLE', 'END'] as const).map((cpType) => {
              const cp = session.checkpoints.find((c) => c.type === cpType);
              const isOpen = cp?.status === 'OPEN';
              const isClosed = cp?.status === 'CLOSED';

              return (
                <div
                  key={cpType}
                  className={`p-5 rounded-xl border transition-all ${
                    isOpen
                      ? 'bg-emerald-50/50 border-emerald-300 ring-2 ring-emerald-500/20 shadow-sm'
                      : isClosed
                      ? 'bg-slate-50 border-slate-200 opacity-90'
                      : 'bg-white border-slate-200'
                  }`}
                >
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
                      {cpType} Checkpoint
                    </span>
                    <Badge
                      variant={isOpen ? 'success' : isClosed ? 'default' : 'outline'}
                      size="sm"
                    >
                      {cp?.status || 'NOT OPENED'}
                    </Badge>
                  </div>

                  <p className="text-xs text-slate-500 mb-4 leading-relaxed">
                    {cpType === 'START'
                      ? 'Opening verification window for class arrivals.'
                      : cpType === 'MIDDLE'
                      ? 'Mid-lecture verification checkpoint.'
                      : 'Final checkout window for course conclusion.'}
                  </p>

                  <div className="flex items-center justify-between pt-2 border-t border-slate-100">
                    {isOpen ? (
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => handleCloseCheckpoint(cpType)}
                        className="w-full"
                      >
                        Close Window
                      </Button>
                    ) : isClosed ? (
                      <span className="text-[11px] text-slate-400 font-medium">
                        Window Concluded
                      </span>
                    ) : (
                      <Button
                        variant="primary"
                        size="sm"
                        disabled={session.status !== 'ACTIVE'}
                        onClick={() => handleOpenCheckpoint(cpType)}
                        className="w-full bg-sky-600 hover:bg-sky-700"
                      >
                        Open Window (5 min)
                      </Button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Active Dynamic QR & BLE Broadcast Area */}
          {openCheckpoint && (
            <Card className="border-emerald-300 bg-white shadow-md overflow-hidden">
              <CardHeader className="bg-emerald-50 border-b border-emerald-100 flex flex-row items-center justify-between">
                <div>
                  <CardTitle className="text-emerald-950 flex items-center gap-2">
                    <QrCode className="w-5 h-5 text-emerald-700" />
                    Live Projector Broadcast: {openCheckpoint.type} Checkpoint
                  </CardTitle>
                  <CardDescription className="text-emerald-800">
                    Dynamic tokens rotate every 30 seconds. Point classroom projector here for students to scan.
                  </CardDescription>
                </div>
                {bleAdv && (
                  <Badge variant="success" size="sm">
                    BLE Dual-Factor Active
                  </Badge>
                )}
              </CardHeader>
              <CardContent className="p-6">
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-center">
                  <div className="lg:col-span-2">
                    <LecturerQrDisplay
                      checkpointId={openCheckpoint.id}
                      authToken={token || ''}
                      courseCode={occurrence?.course_code || 'CS-101'}
                      courseName={occurrence?.course_name || 'Academic Class'}
                    />
                  </div>

                  <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3 text-xs">
                    <h4 className="font-semibold text-slate-800 uppercase tracking-wider text-[11px]">
                      Broadcast Diagnostics
                    </h4>
                    <div>
                      <span className="text-slate-500 block">Checkpoint ID:</span>
                      <code className="text-slate-700 font-mono text-[11px] break-all">{openCheckpoint.id}</code>
                    </div>
                    {bleAdv && (
                      <>
                        <div>
                          <span className="text-slate-500 block">BLE Service UUID:</span>
                          <code className="text-slate-700 font-mono text-[11px] break-all">{bleAdv.service_uuid}</code>
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                          <div>
                            <span className="text-slate-500 block">Major:</span>
                            <span className="font-mono font-semibold">{bleAdv.major}</span>
                          </div>
                          <div>
                            <span className="text-slate-500 block">Minor:</span>
                            <span className="font-mono font-semibold">{bleAdv.minor}</span>
                          </div>
                        </div>
                      </>
                    )}
                    <div className="pt-2 border-t border-slate-200 text-[11px] text-slate-500">
                      Dual-factor verification validates dynamic QR timestamp + BLE proximity beacon.
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Live Progress KPIs */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <div className="p-4 bg-white border border-slate-200 rounded-xl">
              <span className="text-[11px] font-semibold uppercase text-slate-500 block">Enrolled</span>
              <span className="text-2xl font-bold text-slate-900">{session.total_enrolled}</span>
            </div>
            <div className="p-4 bg-white border border-slate-200 rounded-xl">
              <span className="text-[11px] font-semibold uppercase text-emerald-600 block">Present</span>
              <span className="text-2xl font-bold text-emerald-700">{session.total_present}</span>
            </div>
            <div className="p-4 bg-white border border-slate-200 rounded-xl">
              <span className="text-[11px] font-semibold uppercase text-amber-600 block">Late</span>
              <span className="text-2xl font-bold text-amber-700">{session.total_late}</span>
            </div>
            <div className="p-4 bg-white border border-slate-200 rounded-xl">
              <span className="text-[11px] font-semibold uppercase text-rose-600 block">Absent</span>
              <span className="text-2xl font-bold text-rose-700">{session.total_absent}</span>
            </div>
            <div className="p-4 bg-white border border-slate-200 rounded-xl">
              <span className="text-[11px] font-semibold uppercase text-sky-600 block">Excused</span>
              <span className="text-2xl font-bold text-sky-700">{session.total_excused}</span>
            </div>
            <div className="p-4 bg-white border border-slate-200 rounded-xl">
              <span className="text-[11px] font-semibold uppercase text-slate-400 block">Pending</span>
              <span className="text-2xl font-bold text-slate-600">{session.total_pending}</span>
            </div>
          </div>

          {/* Student Roster Table */}
          <Card>
            <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div>
                <CardTitle>Session Attendance Roster ({records.length})</CardTitle>
                <CardDescription>
                  Frozen class roster with real-time verification timestamps and check-in factors.
                </CardDescription>
              </div>
              <div className="flex items-center gap-2">
                <div className="relative w-48 sm:w-60">
                  <span className="absolute inset-y-0 left-0 pl-2.5 flex items-center pointer-events-none text-slate-400">
                    <Search className="w-3.5 h-3.5" />
                  </span>
                  <input
                    type="text"
                    placeholder="Search student..."
                    value={searchRoster}
                    onChange={(e) => setSearchRoster(e.target.value)}
                    className="w-full pl-8 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-sky-500"
                  />
                </div>
                {session.status === 'ACTIVE' && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowManualModal(true)}
                    className="bg-white"
                  >
                    Manual Credit
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Student ID</TableHead>
                    <TableHead>Student Name</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Verified Time (UTC)</TableHead>
                    <TableHead>Evidence Source</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredRecords.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center py-8 text-slate-400 text-xs">
                        No student records match search criteria.
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredRecords.map((r) => (
                      <TableRow key={r.id}>
                        <TableCell className="font-mono text-xs font-semibold text-slate-700">
                          {r.student_number || r.student_id.slice(0, 8)}
                        </TableCell>
                        <TableCell className="text-xs font-medium text-slate-900">
                          {r.student_name || 'Enrolled Student'}
                        </TableCell>
                        <TableCell>{getStatusBadge(r.status)}</TableCell>
                        <TableCell className="text-xs text-slate-500 font-mono">
                          {r.first_verified_at_utc
                            ? new Date(r.first_verified_at_utc).toUTCString().slice(17, 25)
                            : '—'}
                        </TableCell>
                        <TableCell className="text-xs text-slate-600">
                          {r.source_mode ? (
                            <span className="font-mono text-[11px] bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                              {r.source_mode}
                            </span>
                          ) : (
                            <span className="text-slate-400">—</span>
                          )}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Confirmation Modal to Close Session */}
      <Dialog
        isOpen={showCloseModal}
        onClose={() => setShowCloseModal(false)}
        title="Finalize & Close Attendance Session?"
        description="This will execute the combinatorial 8-pattern attendance rules and permanently finalize the student records for this class meeting."
        footer={
          <>
            <Button variant="outline" size="sm" onClick={() => setShowCloseModal(false)}>
              Cancel
            </Button>
            <Button variant="destructive" size="sm" onClick={handleCloseSession}>
              Yes, Finalize Session
            </Button>
          </>
        }
      >
        <div className="text-xs text-slate-600 space-y-2">
          <p>
            Closing the session transitions all remaining unverified students to their final evaluated status (`ABSENT`).
          </p>
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-800 text-[11px]">
            Future corrections after session closure require official student justification and dean review (INV-06).
          </div>
        </div>
      </Dialog>

      {/* Manual Checkpoint Credit Modal (INV-08) */}
      <Dialog
        isOpen={showManualModal}
        onClose={() => setShowManualModal(false)}
        title="Record Manual Checkpoint Credit"
        description="Manually credit a student with recorded administrative justification in the immutable audit ledger."
      >
        <form onSubmit={handleManualCredit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold uppercase text-slate-700 mb-1">
              Select Student
            </label>
            <select
              value={manualStudentId}
              onChange={(e) => setManualStudentId(e.target.value)}
              required
              className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg bg-white focus:outline-none focus:ring-1 focus:ring-sky-500"
            >
              <option value="">-- Choose enrolled student --</option>
              {records.map((r) => (
                <option key={r.student_id} value={r.student_id}>
                  {r.student_name || 'Student'} ({r.student_number || r.student_id.slice(0, 8)}) - Current: {r.status}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase text-slate-700 mb-1">
              Checkpoint Type
            </label>
            <select
              value={manualCheckpointType}
              onChange={(e) => setManualCheckpointType(e.target.value)}
              className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg bg-white focus:outline-none focus:ring-1 focus:ring-sky-500"
            >
              <option value="START">START Checkpoint</option>
              <option value="MIDDLE">MIDDLE Checkpoint</option>
              <option value="END">END Checkpoint</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase text-slate-700 mb-1">
              Mandatory Justification (INV-08)
            </label>
            <textarea
              required
              rows={3}
              value={manualReason}
              onChange={(e) => setManualReason(e.target.value)}
              placeholder="Provide explicit operational justification (e.g. verified physical arrival, battery depletion exception)..."
              className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg bg-white focus:outline-none focus:ring-1 focus:ring-sky-500"
            />
          </div>

          <div className="pt-2 flex justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setShowManualModal(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              isLoading={isSubmittingManual}
              disabled={!manualStudentId || !manualReason.trim()}
              className="bg-sky-600 hover:bg-sky-700"
            >
              Confirm Manual Credit
            </Button>
          </div>
        </form>
      </Dialog>
    </AppShell>
  );
}
