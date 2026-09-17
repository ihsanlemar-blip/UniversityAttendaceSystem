'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import {
  ClipboardCheck,
  FileQuestion,
  CalendarOff,
  UserCheck,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  RefreshCw,
  Search,
  Filter,
  History,
  Shield,
  Check,
  X,
  Smartphone,
  BarChart3,
} from 'lucide-react';

interface CorrectionRequest {
  id: string;
  university_id: string;
  attendance_record_id: string;
  attendance_session_id: string;
  student_id: string;
  student_name?: string;
  student_number?: string;
  course_code?: string;
  course_title?: string;
  request_type: string;
  requested_status: string;
  reason: string;
  supporting_note?: string | null;
  status: 'PENDING' | 'UNDER_REVIEW' | 'APPROVED' | 'REJECTED' | 'CANCELLED';
  review_note?: string | null;
  reviewed_at_utc?: string | null;
  created_at: string;
}

interface ExcuseRequest {
  id: string;
  university_id: string;
  student_id: string;
  student_name?: string;
  student_number?: string;
  course_code?: string;
  attendance_record_id?: string | null;
  attendance_session_id?: string | null;
  class_occurrence_id?: string | null;
  category: string;
  description: string;
  document_reference?: string | null;
  status: 'PENDING' | 'UNDER_REVIEW' | 'APPROVED' | 'REJECTED';
  review_note?: string | null;
  reviewed_at_utc?: string | null;
  created_at: string;
}

interface LeaveRequest {
  id: string;
  university_id: string;
  student_id: string;
  student_name?: string;
  student_number?: string;
  course_code?: string;
  class_occurrence_id: string;
  reason: string;
  status: 'PENDING' | 'UNDER_REVIEW' | 'APPROVED' | 'REJECTED';
  review_note?: string | null;
  reviewed_at_utc?: string | null;
  created_at: string;
}

interface ManualReviewItem {
  record_id: string;
  session_id: string;
  student_id: string;
  student_name?: string | null;
  student_number?: string | null;
  course_code?: string | null;
  course_title?: string | null;
  status: string;
  attendance_credit: number;
  verification_method?: string | null;
  is_flagged: boolean;
  flag_reasons: string[];
  is_manual: boolean;
  created_at: string;
}

interface RevisionItem {
  id: string;
  attendance_session_id: string;
  attendance_record_id?: string | null;
  actor_user_id: string;
  event_type: string;
  previous_status?: string | null;
  new_status?: string | null;
  previous_credit?: number | null;
  new_credit?: number | null;
  reason?: string | null;
  occurred_at_utc: string;
  created_at: string;
}

interface RecordTimeline {
  record_id: string;
  session_id: string;
  student_id: string;
  current_status: string;
  current_credit: number;
  version_no: number;
  is_manual: boolean;
  manual_reason?: string | null;
  revisions: RevisionItem[];
}

interface OperationsCounts {
  pending_corrections: number;
  pending_excuses: number;
  pending_leaves: number;
  manual_reviews: number;
}

export default function AttendanceOperationsConsolePage() {
  const [activeTab, setActiveTab] = useState<'corrections' | 'excuses' | 'leave' | 'manual'>('corrections');
  const [counts, setCounts] = useState<OperationsCounts>({
    pending_corrections: 0,
    pending_excuses: 0,
    pending_leaves: 0,
    manual_reviews: 0,
  });

  const [corrections, setCorrections] = useState<CorrectionRequest[]>([]);
  const [excuses, setExcuses] = useState<ExcuseRequest[]>([]);
  const [leaves, setLeaves] = useState<LeaveRequest[]>([]);
  const [manualReviews, setManualReviews] = useState<ManualReviewItem[]>([]);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  // Modals state
  const [approveItem, setApproveItem] = useState<{ id: string; type: string; label: string } | null>(null);
  const [approveNote, setApproveNote] = useState<string>('');
  const [approvedStatus, setApprovedStatus] = useState<string>('PRESENT');
  const [deliberateConfirmation, setDeliberateConfirmation] = useState<boolean>(false);

  const [rejectItem, setRejectItem] = useState<{ id: string; type: string; label: string } | null>(null);
  const [rejectNote, setRejectNote] = useState<string>('');

  const [overrideItem, setOverrideItem] = useState<{ record_id: string; current_status: string } | null>(null);
  const [overrideTargetStatus, setOverrideTargetStatus] = useState<string>('PRESENT');
  const [overrideTargetCredit, setOverrideTargetCredit] = useState<string>('');
  const [overrideReason, setOverrideReason] = useState<string>('');
  const [overrideConfirmed, setOverrideConfirmed] = useState<boolean>(false);

  const [showReversalModal, setShowReversalModal] = useState<boolean>(false);
  const [reversalRevisionId, setReversalRevisionId] = useState<string>('');
  const [reversalReason, setReversalReason] = useState<string>('');

  const [bulkModalOpen, setBulkModalOpen] = useState<boolean>(false);
  const [bulkAction, setBulkAction] = useState<'APPROVED' | 'REJECTED'>('APPROVED');
  const [bulkNote, setBulkNote] = useState<string>('');
  const [bulkApprovedStatus, setBulkApprovedStatus] = useState<string>('PRESENT');

  const [timelineModalOpen, setTimelineModalOpen] = useState<boolean>(false);
  const [timelineLoading, setTimelineLoading] = useState<boolean>(false);
  const [timelineData, setTimelineData] = useState<RecordTimeline | null>(null);

  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setActionError(null);
    setSelectedIds(new Set());
    try {
      // 1. Fetch Counts
      const countsRes = await fetch(`${apiBaseUrl}/attendance/operations/counts`, {
        headers: { Accept: 'application/json' },
      });
      if (countsRes.ok) {
        const countsJson = await countsRes.json();
        setCounts(countsJson.data);
      }

      // 2. Fetch Queues
      const [corrRes, excRes, leaveRes, manRes] = await Promise.all([
        fetch(`${apiBaseUrl}/attendance/operations/corrections/queue`, { headers: { Accept: 'application/json' } }),
        fetch(`${apiBaseUrl}/attendance/operations/excuses/queue`, { headers: { Accept: 'application/json' } }),
        fetch(`${apiBaseUrl}/attendance/operations/leave/queue`, { headers: { Accept: 'application/json' } }),
        fetch(`${apiBaseUrl}/attendance/operations/manual-reviews`, { headers: { Accept: 'application/json' } }),
      ]);

      if (corrRes.ok) {
        const data = await corrRes.json();
        setCorrections(data.data || []);
      }
      if (excRes.ok) {
        const data = await excRes.json();
        setExcuses(data.data || []);
      }
      if (leaveRes.ok) {
        const data = await leaveRes.json();
        setLeaves(data.data || []);
      }
      if (manRes.ok) {
        const data = await manRes.json();
        setManualReviews(data.data || []);
      }
    } catch {
      setActionError('Could not reach backend API server. Check connectivity.');
    } finally {
      setIsLoading(false);
    }
  }, [apiBaseUrl]);

  useEffect(() => {
    let ignore = false;
    async function initFetch() {
      try {
        const countsRes = await fetch(`${apiBaseUrl}/attendance/operations/counts`, {
          headers: { Accept: 'application/json' },
        });
        if (countsRes.ok && !ignore) {
          const countsJson = await countsRes.json();
          setCounts(countsJson.data);
        }

        const [corrRes, excRes, leaveRes, manRes] = await Promise.all([
          fetch(`${apiBaseUrl}/attendance/operations/corrections/queue`, { headers: { Accept: 'application/json' } }),
          fetch(`${apiBaseUrl}/attendance/operations/excuses/queue`, { headers: { Accept: 'application/json' } }),
          fetch(`${apiBaseUrl}/attendance/operations/leave/queue`, { headers: { Accept: 'application/json' } }),
          fetch(`${apiBaseUrl}/attendance/operations/manual-reviews`, { headers: { Accept: 'application/json' } }),
        ]);

        if (corrRes.ok && !ignore) {
          const data = await corrRes.json();
          setCorrections(data.data || []);
        }
        if (excRes.ok && !ignore) {
          const data = await excRes.json();
          setExcuses(data.data || []);
        }
        if (leaveRes.ok && !ignore) {
          const data = await leaveRes.json();
          setLeaves(data.data || []);
        }
        if (manRes.ok && !ignore) {
          const data = await manRes.json();
          setManualReviews(data.data || []);
        }
      } catch {
        if (!ignore) {
          setActionError('Could not reach backend API server. Check connectivity.');
        }
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    }
    initFetch();
    return () => {
      ignore = true;
    };
  }, [apiBaseUrl]);


  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const selectAllInActiveTab = () => {
    let currentList: string[] = [];
    if (activeTab === 'corrections') currentList = corrections.filter(c => c.status === 'PENDING').map(c => c.id);
    else if (activeTab === 'excuses') currentList = excuses.filter(e => e.status === 'PENDING').map(e => e.id);
    else if (activeTab === 'leave') currentList = leaves.filter(l => l.status === 'PENDING').map(l => l.id);

    if (selectedIds.size === currentList.length && currentList.length > 0) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(currentList));
    }
  };

  const handleOpenTimeline = async (recordId: string) => {
    setTimelineModalOpen(true);
    setTimelineLoading(true);
    setTimelineData(null);
    try {
      const res = await fetch(`${apiBaseUrl}/attendance/operations/records/${recordId}/timeline`, {
        headers: { Accept: 'application/json' },
      });
      if (res.ok) {
        const json = await res.json();
        setTimelineData(json.data);
      } else {
        setActionError('Failed to load record revision timeline.');
      }
    } catch {
      setActionError('Error connecting to timeline API.');
    } finally {
      setTimelineLoading(false);
    }
  };

  const handleApproveSubmit = async () => {
    if (!approveItem) return;
    if (!deliberateConfirmation) {
      setActionError('Please confirm the verification statement before approving.');
      return;
    }
    setIsSubmitting(true);
    setActionError(null);

    try {
      let endpoint = '';
      let body: Record<string, unknown> = {
        status: 'APPROVED',
        review_note: approveNote.trim() || 'Verified and approved by attendance reviewer.',
      };

      if (approveItem.type === 'correction') {
        endpoint = `${apiBaseUrl}/attendance/operations/corrections/${approveItem.id}/review`;
        body.approved_status = approvedStatus;
      } else if (approveItem.type === 'excuse') {
        endpoint = `${apiBaseUrl}/attendance/operations/excuses/${approveItem.id}/review`;
      } else if (approveItem.type === 'leave') {
        endpoint = `${apiBaseUrl}/attendance/operations/leave/${approveItem.id}/review`;
      }

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify(body),
      });

      if (res.status === 409) {
        setActionError('409 Conflict: This request was already resolved or modified by another actor. Queue refreshed.');
        setApproveItem(null);
        await loadData();
        return;
      }

      if (!res.ok) {
        const errJson = await res.json().catch(() => null);
        throw new Error(errJson?.error?.message || `Approval failed [HTTP ${res.status}]`);
      }

      setActionSuccess(`Request ${approveItem.id.slice(0, 8)} successfully approved.`);
      setApproveItem(null);
      setApproveNote('');
      setDeliberateConfirmation(false);
      await loadData();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : 'Approval failed.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRejectSubmit = async () => {
    if (!rejectItem) return;
    if (!rejectNote.trim() || rejectNote.trim().length < 3) {
      setActionError('A mandatory rejection note (at least 3 characters) is required.');
      return;
    }
    setIsSubmitting(true);
    setActionError(null);

    try {
      let endpoint = '';
      const body = {
        status: 'REJECTED',
        review_note: rejectNote.trim(),
      };

      if (rejectItem.type === 'correction') {
        endpoint = `${apiBaseUrl}/attendance/operations/corrections/${rejectItem.id}/review`;
      } else if (rejectItem.type === 'excuse') {
        endpoint = `${apiBaseUrl}/attendance/operations/excuses/${rejectItem.id}/review`;
      } else if (rejectItem.type === 'leave') {
        endpoint = `${apiBaseUrl}/attendance/operations/leave/${rejectItem.id}/review`;
      }

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify(body),
      });

      if (res.status === 409) {
        setActionError('409 Conflict: This request was already resolved or modified. Queue refreshed.');
        setRejectItem(null);
        await loadData();
        return;
      }

      if (!res.ok) {
        const errJson = await res.json().catch(() => null);
        throw new Error(errJson?.error?.message || `Rejection failed [HTTP ${res.status}]`);
      }

      setActionSuccess(`Request ${rejectItem.id.slice(0, 8)} rejected.`);
      setRejectItem(null);
      setRejectNote('');
      await loadData();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : 'Rejection failed.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleOverrideSubmit = async () => {
    if (!overrideItem) return;
    if (!overrideConfirmed) {
      setActionError('You must acknowledge the immutable audit warning before overriding.');
      return;
    }
    if (!overrideReason.trim() || overrideReason.trim().length < 5) {
      setActionError('A clear justification (minimum 5 characters) is mandatory for overrides.');
      return;
    }

    setIsSubmitting(true);
    setActionError(null);

    try {
      const body: Record<string, unknown> = {
        attendance_record_id: overrideItem.record_id,
        target_status: overrideTargetStatus,
        reason: overrideReason.trim(),
      };
      if (overrideTargetCredit) {
        body.target_credit = parseFloat(overrideTargetCredit);
      }

      const res = await fetch(`${apiBaseUrl}/attendance/operations/overrides`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => null);
        throw new Error(errJson?.error?.message || `Override failed [HTTP ${res.status}]`);
      }

      setActionSuccess('Attendance record override applied and immutable revision logged.');
      setOverrideItem(null);
      setOverrideReason('');
      setOverrideConfirmed(false);
      await loadData();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : 'Override failed.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReversalSubmit = async () => {
    if (!reversalRevisionId.trim()) {
      setActionError('Revision UUID is required.');
      return;
    }
    if (!reversalReason.trim() || reversalReason.trim().length < 5) {
      setActionError('A minimum 5-character reason is required for reversal.');
      return;
    }

    setIsSubmitting(true);
    setActionError(null);

    try {
      const res = await fetch(`${apiBaseUrl}/attendance/operations/reversals`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({
          revision_id: reversalRevisionId.trim(),
          reason: reversalReason.trim(),
        }),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => null);
        throw new Error(errJson?.error?.message || `Reversal failed [HTTP ${res.status}]`);
      }

      setActionSuccess('Compensating revision logged; prior revision reversed without history loss.');
      setShowReversalModal(false);
      setReversalRevisionId('');
      setReversalReason('');
      await loadData();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : 'Reversal failed.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleBulkSubmit = async () => {
    if (selectedIds.size === 0) return;
    if (!bulkNote.trim() || bulkNote.trim().length < 3) {
      setActionError('A bulk review note (at least 3 characters) is required.');
      return;
    }

    setIsSubmitting(true);
    setActionError(null);

    try {
      let requestType = 'correction';
      if (activeTab === 'excuses') requestType = 'excuse';
      else if (activeTab === 'leave') requestType = 'leave';

      const body: Record<string, unknown> = {
        request_type: requestType,
        request_ids: Array.from(selectedIds),
        status: bulkAction,
        review_note: bulkNote.trim(),
      };
      if (bulkAction === 'APPROVED' && requestType === 'correction') {
        body.approved_status = bulkApprovedStatus;
      }

      const res = await fetch(`${apiBaseUrl}/attendance/operations/bulk-review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => null);
        throw new Error(errJson?.error?.message || `Bulk review failed [HTTP ${res.status}]`);
      }

      const json = await res.json();
      const summary = json.data;
      setActionSuccess(`Bulk operation completed: ${summary.succeeded} succeeded, ${summary.failed} failed.`);
      setBulkModalOpen(false);
      setBulkNote('');
      setSelectedIds(new Set());
      await loadData();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : 'Bulk review failed.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Filter items
  const filteredCorrections = corrections.filter((c) => {
    if (statusFilter !== 'ALL' && c.status !== statusFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        c.reason.toLowerCase().includes(q) ||
        (c.student_name && c.student_name.toLowerCase().includes(q)) ||
        (c.student_number && c.student_number.toLowerCase().includes(q)) ||
        c.requested_status.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const filteredExcuses = excuses.filter((e) => {
    if (statusFilter !== 'ALL' && e.status !== statusFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        e.description.toLowerCase().includes(q) ||
        e.category.toLowerCase().includes(q) ||
        (e.student_name && e.student_name.toLowerCase().includes(q))
      );
    }
    return true;
  });

  const filteredLeaves = leaves.filter((l) => {
    if (statusFilter !== 'ALL' && l.status !== statusFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        l.reason.toLowerCase().includes(q) ||
        (l.student_name && l.student_name.toLowerCase().includes(q))
      );
    }
    return true;
  });

  const filteredManuals = manualReviews.filter((m) => {
    if (statusFilter !== 'ALL' && m.status !== statusFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        (m.student_name && m.student_name.toLowerCase().includes(q)) ||
        (m.course_code && m.course_code.toLowerCase().includes(q)) ||
        m.status.toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 p-6 md:p-8">
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-8 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-indigo-600 text-white rounded-xl shadow-sm">
              <ClipboardCheck className="w-7 h-7" />
            </div>
            <div>
              <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-slate-900">
                Attendance Operations & Reviews
              </h1>
              <p className="text-sm text-slate-500 mt-0.5">
                Authoritative review console for corrections, excuses, leave, and immutable revisions
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowReversalModal(true)}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition"
          >
            <History className="w-4 h-4 text-slate-500" />
            Revision Reversal
          </button>
          <button
            onClick={loadData}
            disabled={isLoading}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition shadow-sm"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      <div className="max-w-7xl mx-auto space-y-6">
        {/* KPI Summary Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Corrections Queue</p>
              <h3 className="text-2xl font-bold text-slate-900 mt-1">{counts.pending_corrections}</h3>
              <p className="text-xs text-slate-400 mt-0.5">Pending review</p>
            </div>
            <div className="p-3 bg-amber-50 text-amber-600 rounded-xl">
              <FileQuestion className="w-6 h-6" />
            </div>
          </div>

          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Absence Excuses</p>
              <h3 className="text-2xl font-bold text-slate-900 mt-1">{counts.pending_excuses}</h3>
              <p className="text-xs text-slate-400 mt-0.5">Medical / official</p>
            </div>
            <div className="p-3 bg-blue-50 text-blue-600 rounded-xl">
              <CalendarOff className="w-6 h-6" />
            </div>
          </div>

          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Pre-Class Leave</p>
              <h3 className="text-2xl font-bold text-slate-900 mt-1">{counts.pending_leaves}</h3>
              <p className="text-xs text-slate-400 mt-0.5">0-credit approved</p>
            </div>
            <div className="p-3 bg-purple-50 text-purple-600 rounded-xl">
              <Clock className="w-6 h-6" />
            </div>
          </div>

          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Manual & Overrides</p>
              <h3 className="text-2xl font-bold text-slate-900 mt-1">{counts.manual_reviews}</h3>
              <p className="text-xs text-slate-400 mt-0.5">Flagged / adjusted</p>
            </div>
            <div className="p-3 bg-emerald-50 text-emerald-600 rounded-xl">
              <UserCheck className="w-6 h-6" />
            </div>
          </div>
        </div>

        {/* Global Notifications */}
        {actionSuccess && (
          <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center justify-between text-emerald-800 text-sm">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
              <span>{actionSuccess}</span>
            </div>
            <button onClick={() => setActionSuccess(null)} className="text-emerald-700 hover:text-emerald-900">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {actionError && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-xl flex items-center justify-between text-red-800 text-sm">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-red-600 shrink-0" />
              <span>{actionError}</span>
            </div>
            <button onClick={() => setActionError(null)} className="text-red-700 hover:text-red-900">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Console Body */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          {/* Navigation Tabs */}
          <div className="flex border-b border-slate-200 px-6 pt-4 gap-6 bg-slate-50/50">
            <button
              onClick={() => { setActiveTab('corrections'); setSelectedIds(new Set()); }}
              className={`pb-3 text-sm font-semibold border-b-2 flex items-center gap-2 transition ${
                activeTab === 'corrections'
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              <FileQuestion className="w-4 h-4" />
              Corrections Queue
              {counts.pending_corrections > 0 && (
                <span className="px-2 py-0.5 text-xs font-bold bg-amber-100 text-amber-800 rounded-full">
                  {counts.pending_corrections}
                </span>
              )}
            </button>

            <button
              onClick={() => { setActiveTab('excuses'); setSelectedIds(new Set()); }}
              className={`pb-3 text-sm font-semibold border-b-2 flex items-center gap-2 transition ${
                activeTab === 'excuses'
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              <CalendarOff className="w-4 h-4" />
              Absence Excuses
              {counts.pending_excuses > 0 && (
                <span className="px-2 py-0.5 text-xs font-bold bg-blue-100 text-blue-800 rounded-full">
                  {counts.pending_excuses}
                </span>
              )}
            </button>

            <button
              onClick={() => { setActiveTab('leave'); setSelectedIds(new Set()); }}
              className={`pb-3 text-sm font-semibold border-b-2 flex items-center gap-2 transition ${
                activeTab === 'leave'
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              <Clock className="w-4 h-4" />
              Pre-Class Leave
              {counts.pending_leaves > 0 && (
                <span className="px-2 py-0.5 text-xs font-bold bg-purple-100 text-purple-800 rounded-full">
                  {counts.pending_leaves}
                </span>
              )}
            </button>

            <button
              onClick={() => { setActiveTab('manual'); setSelectedIds(new Set()); }}
              className={`pb-3 text-sm font-semibold border-b-2 flex items-center gap-2 transition ${
                activeTab === 'manual'
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              <UserCheck className="w-4 h-4" />
              Manual & Overrides
              {counts.manual_reviews > 0 && (
                <span className="px-2 py-0.5 text-xs font-bold bg-emerald-100 text-emerald-800 rounded-full">
                  {counts.manual_reviews}
                </span>
              )}
            </button>
          </div>

          {/* Action & Filter Toolbar */}
          <div className="p-4 border-b border-slate-200 bg-white flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-3 flex-1 max-w-md">
              <div className="relative w-full">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Filter by student, reason, status..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-4 py-2 text-sm bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div className="flex items-center gap-2">
                <Filter className="w-4 h-4 text-slate-400 shrink-0" />
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="text-sm bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="ALL">All Statuses</option>
                  <option value="PENDING">Pending</option>
                  <option value="APPROVED">Approved</option>
                  <option value="REJECTED">Rejected</option>
                </select>
              </div>
            </div>

            {/* Bulk Selection Actions Bar */}
            {activeTab !== 'manual' && (
              <div className="flex items-center gap-2">
                <button
                  onClick={selectAllInActiveTab}
                  className="text-xs font-medium text-indigo-600 hover:text-indigo-800 px-3 py-1.5 rounded-md hover:bg-indigo-50 transition"
                >
                  {selectedIds.size > 0 ? 'Deselect All' : 'Select All Pending'}
                </button>

                {selectedIds.size > 0 && (
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-slate-600 bg-slate-100 px-2 py-1 rounded">
                      {selectedIds.size} selected
                    </span>
                    <button
                      onClick={() => { setBulkAction('APPROVED'); setBulkModalOpen(true); }}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-emerald-600 rounded-lg hover:bg-emerald-700 transition"
                    >
                      <Check className="w-3.5 h-3.5" />
                      Bulk Approve
                    </button>
                    <button
                      onClick={() => { setBulkAction('REJECTED'); setBulkModalOpen(true); }}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-red-600 rounded-lg hover:bg-red-700 transition"
                    >
                      <X className="w-3.5 h-3.5" />
                      Bulk Reject
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Table / Queue Content */}
          <div className="overflow-x-auto">
            {isLoading ? (
              <div className="py-16 text-center text-slate-400">
                <RefreshCw className="w-8 h-8 mx-auto animate-spin mb-3 text-indigo-500" />
                <p className="text-sm">Loading attendance operations queue...</p>
              </div>
            ) : (
              <>
                {/* 1. CORRECTIONS QUEUE */}
                {activeTab === 'corrections' && (
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="bg-slate-50/75 border-b border-slate-200 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                        <th className="p-4 w-10 text-center">
                          <input
                            type="checkbox"
                            checked={selectedIds.size > 0 && selectedIds.size === filteredCorrections.filter(c => c.status === 'PENDING').length}
                            onChange={selectAllInActiveTab}
                            className="rounded text-indigo-600 focus:ring-indigo-500"
                          />
                        </th>
                        <th className="p-4">Student & Record</th>
                        <th className="p-4">Requested Change</th>
                        <th className="p-4">Justification & Notes</th>
                        <th className="p-4">Trust & Signals</th>
                        <th className="p-4">Status</th>
                        <th className="p-4 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200 text-sm">
                      {filteredCorrections.length === 0 ? (
                        <tr>
                          <td colSpan={7} className="py-12 text-center text-slate-400">
                            No attendance correction requests matching filters.
                          </td>
                        </tr>
                      ) : (
                        filteredCorrections.map((corr) => (
                          <tr key={corr.id} className="hover:bg-slate-50/80 transition">
                            <td className="p-4 text-center">
                              {corr.status === 'PENDING' && (
                                <input
                                  type="checkbox"
                                  checked={selectedIds.has(corr.id)}
                                  onChange={() => toggleSelect(corr.id)}
                                  className="rounded text-indigo-600 focus:ring-indigo-500"
                                />
                              )}
                            </td>
                            <td className="p-4">
                              <div className="font-semibold text-slate-900">
                                {corr.student_name || 'Enrolled Student'}
                              </div>
                              <div className="text-xs text-slate-500">
                                ID: {corr.student_number || corr.student_id.slice(0, 8)}
                              </div>
                              <div className="text-xs text-slate-400 font-mono mt-0.5">
                                Rec: {corr.attendance_record_id.slice(0, 8)}
                              </div>
                            </td>
                            <td className="p-4">
                              <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-bold bg-indigo-50 text-indigo-700">
                                Target: {corr.requested_status}
                              </div>
                              <div className="text-xs text-slate-500 mt-1 capitalize">
                                Type: {corr.request_type.toLowerCase()}
                              </div>
                            </td>
                            <td className="p-4 max-w-xs">
                              <div className="text-slate-800 line-clamp-2">{corr.reason}</div>
                              {corr.supporting_note && (
                                <div className="text-xs text-slate-500 italic mt-1 line-clamp-1">
                                  Note: {corr.supporting_note}
                                </div>
                              )}
                              <div className="text-xs text-slate-400 mt-1">
                                Submitted {new Date(corr.created_at).toLocaleString()}
                              </div>
                            </td>
                            <td className="p-4">
                              <div className="flex flex-wrap gap-1.5">
                                <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded bg-slate-100 text-slate-700">
                                  <Smartphone className="w-3 h-3 text-slate-500" />
                                  App
                                </span>
                                <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded bg-emerald-50 text-emerald-700">
                                  <Shield className="w-3 h-3 text-emerald-600" />
                                  M14 Verified
                                </span>
                              </div>
                            </td>
                            <td className="p-4">
                              <span
                                className={`px-2.5 py-1 text-xs font-bold rounded-full ${
                                  corr.status === 'PENDING'
                                    ? 'bg-amber-100 text-amber-800'
                                    : corr.status === 'APPROVED'
                                    ? 'bg-emerald-100 text-emerald-800'
                                    : corr.status === 'REJECTED'
                                    ? 'bg-red-100 text-red-800'
                                    : 'bg-slate-100 text-slate-700'
                                }`}
                              >
                                {corr.status}
                              </span>
                            </td>
                            <td className="p-4 text-right space-x-2">
                              {corr.status === 'PENDING' ? (
                                <>
                                  <button
                                    onClick={() => {
                                      setApproveItem({ id: corr.id, type: 'correction', label: `Correction for ${corr.student_name || 'Student'}` });
                                      setApprovedStatus(corr.requested_status);
                                      setDeliberateConfirmation(false);
                                    }}
                                    className="px-2.5 py-1 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-md transition"
                                  >
                                    Approve
                                  </button>
                                  <button
                                    onClick={() => setRejectItem({ id: corr.id, type: 'correction', label: `Correction for ${corr.student_name || 'Student'}` })}
                                    className="px-2.5 py-1 text-xs font-semibold text-white bg-red-600 hover:bg-red-700 rounded-md transition"
                                  >
                                    Reject
                                  </button>
                                </>
                              ) : (
                                <span className="text-xs text-slate-400 italic">Resolved</span>
                              )}
                              <button
                                onClick={() => handleOpenTimeline(corr.attendance_record_id)}
                                title="View Revision Audit Timeline"
                                className="p-1 text-slate-400 hover:text-indigo-600 transition"
                              >
                                <History className="w-4 h-4 inline" />
                              </button>
                              <Link
                                href={`/admin/reports/attendance?tab=session&session_id=${corr.attendance_session_id}`}
                                title="View Session Attendance Report"
                                className="p-1 text-slate-400 hover:text-indigo-600 transition inline-flex items-center"
                              >
                                <BarChart3 className="w-4 h-4" />
                              </Link>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                )}

                {/* 2. EXCUSES QUEUE */}
                {activeTab === 'excuses' && (
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="bg-slate-50/75 border-b border-slate-200 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                        <th className="p-4 w-10 text-center">
                          <input
                            type="checkbox"
                            checked={selectedIds.size > 0 && selectedIds.size === filteredExcuses.filter(e => e.status === 'PENDING').length}
                            onChange={selectAllInActiveTab}
                            className="rounded text-indigo-600 focus:ring-indigo-500"
                          />
                        </th>
                        <th className="p-4">Student & Target</th>
                        <th className="p-4">Category</th>
                        <th className="p-4">Description & Document</th>
                        <th className="p-4">Credit Policy</th>
                        <th className="p-4">Status</th>
                        <th className="p-4 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200 text-sm">
                      {filteredExcuses.length === 0 ? (
                        <tr>
                          <td colSpan={7} className="py-12 text-center text-slate-400">
                            No absence excuse requests matching filters.
                          </td>
                        </tr>
                      ) : (
                        filteredExcuses.map((exc) => (
                          <tr key={exc.id} className="hover:bg-slate-50/80 transition">
                            <td className="p-4 text-center">
                              {exc.status === 'PENDING' && (
                                <input
                                  type="checkbox"
                                  checked={selectedIds.has(exc.id)}
                                  onChange={() => toggleSelect(exc.id)}
                                  className="rounded text-indigo-600 focus:ring-indigo-500"
                                />
                              )}
                            </td>
                            <td className="p-4">
                              <div className="font-semibold text-slate-900">
                                {exc.student_name || 'Enrolled Student'}
                              </div>
                              <div className="text-xs text-slate-500">
                                ID: {exc.student_number || exc.student_id.slice(0, 8)}
                              </div>
                            </td>
                            <td className="p-4">
                              <span className="px-2.5 py-1 text-xs font-bold rounded-md bg-blue-50 text-blue-700">
                                {exc.category}
                              </span>
                            </td>
                            <td className="p-4 max-w-xs">
                              <div className="text-slate-800 line-clamp-2">{exc.description}</div>
                              {exc.document_reference && (
                                <div className="text-xs text-indigo-600 font-mono mt-1">
                                  Doc Ref: {exc.document_reference}
                                </div>
                              )}
                              <div className="text-xs text-slate-400 mt-1">
                                Submitted {new Date(exc.created_at).toLocaleString()}
                              </div>
                            </td>
                            <td className="p-4">
                              <div className="text-xs text-slate-600">
                                <span className="font-bold">EXCUSED</span> (Policy Credit)
                              </div>
                            </td>
                            <td className="p-4">
                              <span
                                className={`px-2.5 py-1 text-xs font-bold rounded-full ${
                                  exc.status === 'PENDING'
                                    ? 'bg-amber-100 text-amber-800'
                                    : exc.status === 'APPROVED'
                                    ? 'bg-emerald-100 text-emerald-800'
                                    : 'bg-red-100 text-red-800'
                                }`}
                              >
                                {exc.status}
                              </span>
                            </td>
                            <td className="p-4 text-right space-x-2">
                              {exc.status === 'PENDING' ? (
                                <>
                                  <button
                                    onClick={() => {
                                      setApproveItem({ id: exc.id, type: 'excuse', label: `Excuse for ${exc.student_name || 'Student'}` });
                                      setDeliberateConfirmation(false);
                                    }}
                                    className="px-2.5 py-1 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-md transition"
                                  >
                                    Approve
                                  </button>
                                  <button
                                    onClick={() => setRejectItem({ id: exc.id, type: 'excuse', label: `Excuse for ${exc.student_name || 'Student'}` })}
                                    className="px-2.5 py-1 text-xs font-semibold text-white bg-red-600 hover:bg-red-700 rounded-md transition"
                                  >
                                    Reject
                                  </button>
                                </>
                              ) : (
                                <span className="text-xs text-slate-400 italic">Resolved</span>
                              )}
                              {exc.attendance_session_id && (
                                <Link
                                  href={`/admin/reports/attendance?tab=session&session_id=${exc.attendance_session_id}`}
                                  title="View Session Attendance Report"
                                  className="p-1 text-slate-400 hover:text-indigo-600 transition inline-flex items-center"
                                >
                                  <BarChart3 className="w-4 h-4" />
                                </Link>
                              )}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                )}

                {/* 3. PRE-CLASS LEAVE QUEUE */}
                {activeTab === 'leave' && (
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="bg-slate-50/75 border-b border-slate-200 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                        <th className="p-4 w-10 text-center">
                          <input
                            type="checkbox"
                            checked={selectedIds.size > 0 && selectedIds.size === filteredLeaves.filter(l => l.status === 'PENDING').length}
                            onChange={selectAllInActiveTab}
                            className="rounded text-indigo-600 focus:ring-indigo-500"
                          />
                        </th>
                        <th className="p-4">Student</th>
                        <th className="p-4">Occurrence ID</th>
                        <th className="p-4">Reason</th>
                        <th className="p-4">Credit Rule</th>
                        <th className="p-4">Status</th>
                        <th className="p-4 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200 text-sm">
                      {filteredLeaves.length === 0 ? (
                        <tr>
                          <td colSpan={7} className="py-12 text-center text-slate-400">
                            No pre-class leave requests matching filters.
                          </td>
                        </tr>
                      ) : (
                        filteredLeaves.map((l) => (
                          <tr key={l.id} className="hover:bg-slate-50/80 transition">
                            <td className="p-4 text-center">
                              {l.status === 'PENDING' && (
                                <input
                                  type="checkbox"
                                  checked={selectedIds.has(l.id)}
                                  onChange={() => toggleSelect(l.id)}
                                  className="rounded text-indigo-600 focus:ring-indigo-500"
                                />
                              )}
                            </td>
                            <td className="p-4">
                              <div className="font-semibold text-slate-900">
                                {l.student_name || 'Enrolled Student'}
                              </div>
                              <div className="text-xs text-slate-500">
                                ID: {l.student_number || l.student_id.slice(0, 8)}
                              </div>
                            </td>
                            <td className="p-4 font-mono text-xs text-slate-600">
                              {l.class_occurrence_id.slice(0, 8)}...
                            </td>
                            <td className="p-4 max-w-xs text-slate-800">
                              <div className="line-clamp-2">{l.reason}</div>
                              <div className="text-xs text-slate-400 mt-1">
                                {new Date(l.created_at).toLocaleString()}
                              </div>
                            </td>
                            <td className="p-4">
                              <span className="px-2 py-0.5 text-xs font-bold bg-amber-50 text-amber-700 rounded">
                                0.00 Credit (Section 38)
                              </span>
                            </td>
                            <td className="p-4">
                              <span
                                className={`px-2.5 py-1 text-xs font-bold rounded-full ${
                                  l.status === 'PENDING'
                                    ? 'bg-amber-100 text-amber-800'
                                    : l.status === 'APPROVED'
                                    ? 'bg-emerald-100 text-emerald-800'
                                    : 'bg-red-100 text-red-800'
                                }`}
                              >
                                {l.status}
                              </span>
                            </td>
                            <td className="p-4 text-right space-x-2">
                              {l.status === 'PENDING' ? (
                                <>
                                  <button
                                    onClick={() => {
                                      setApproveItem({ id: l.id, type: 'leave', label: `Leave for ${l.student_name || 'Student'}` });
                                      setDeliberateConfirmation(false);
                                    }}
                                    className="px-2.5 py-1 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-md transition"
                                  >
                                    Approve
                                  </button>
                                  <button
                                    onClick={() => setRejectItem({ id: l.id, type: 'leave', label: `Leave for ${l.student_name || 'Student'}` })}
                                    className="px-2.5 py-1 text-xs font-semibold text-white bg-red-600 hover:bg-red-700 rounded-md transition"
                                  >
                                    Reject
                                  </button>
                                </>
                              ) : (
                                <span className="text-xs text-slate-400 italic">Resolved</span>
                              )}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                )}

                {/* 4. MANUAL & OVERRIDES QUEUE */}
                {activeTab === 'manual' && (
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="bg-slate-50/75 border-b border-slate-200 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                        <th className="p-4">Student</th>
                        <th className="p-4">Course & Session</th>
                        <th className="p-4">Current Status & Credit</th>
                        <th className="p-4">Verification Signal / Reason</th>
                        <th className="p-4">Method</th>
                        <th className="p-4 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200 text-sm">
                      {filteredManuals.length === 0 ? (
                        <tr>
                          <td colSpan={6} className="py-12 text-center text-slate-400">
                            No manual review records found.
                          </td>
                        </tr>
                      ) : (
                        filteredManuals.map((man) => (
                          <tr key={man.record_id} className="hover:bg-slate-50/80 transition">
                            <td className="p-4">
                              <div className="font-semibold text-slate-900">
                                {man.student_name || 'Enrolled Student'}
                              </div>
                              <div className="text-xs text-slate-500">
                                ID: {man.student_number || man.student_id.slice(0, 8)}
                              </div>
                            </td>
                            <td className="p-4">
                              <div className="font-medium text-slate-800">
                                {man.course_code || 'General Course'}
                              </div>
                              <div className="text-xs text-slate-400 font-mono">
                                Sess: {man.session_id.slice(0, 8)}
                              </div>
                            </td>
                            <td className="p-4">
                              <span className="px-2.5 py-1 text-xs font-bold rounded-full bg-slate-100 text-slate-800">
                                {man.status}
                              </span>
                              <span className="ml-2 text-xs font-mono text-slate-500">
                                ({man.attendance_credit.toFixed(2)} cr)
                              </span>
                            </td>
                            <td className="p-4 max-w-xs">
                              {man.flag_reasons.length > 0 ? (
                                man.flag_reasons.map((r, i) => (
                                  <div key={i} className="text-xs text-amber-700 bg-amber-50 rounded px-2 py-0.5 mb-1 inline-block">
                                    {r}
                                  </div>
                                ))
                              ) : (
                                <span className="text-xs text-slate-400 italic">None flagged</span>
                              )}
                            </td>
                            <td className="p-4">
                              <span className="px-2 py-0.5 text-xs font-medium rounded bg-slate-100 text-slate-600">
                                {man.verification_method || 'MANUAL'}
                              </span>
                            </td>
                            <td className="p-4 text-right space-x-2">
                              <button
                                onClick={() => {
                                  setOverrideItem({ record_id: man.record_id, current_status: man.status });
                                  setOverrideTargetStatus(man.status);
                                  setOverrideConfirmed(false);
                                }}
                                className="px-2.5 py-1 text-xs font-semibold text-indigo-600 hover:text-white hover:bg-indigo-600 border border-indigo-300 rounded-md transition"
                              >
                                Override Status
                              </button>
                              <button
                                onClick={() => handleOpenTimeline(man.record_id)}
                                title="View Revision Audit Timeline"
                                className="p-1 text-slate-400 hover:text-indigo-600 transition"
                              >
                                <History className="w-4 h-4 inline" />
                              </button>
                              <Link
                                href={`/admin/reports/attendance?tab=session&session_id=${man.session_id}`}
                                title="View Session Attendance Report"
                                className="p-1 text-slate-400 hover:text-indigo-600 transition inline-flex items-center"
                              >
                                <BarChart3 className="w-4 h-4" />
                              </Link>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                )}
              </>
            )}
          </div>
        </div>
      </div>

      {/* APPROVE CONFIRMATION MODAL */}
      {approveItem && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl border border-slate-100 space-y-4">
            <div className="flex items-center gap-3 text-emerald-600">
              <div className="p-2 bg-emerald-100 rounded-lg">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-slate-900">Deliberate Approval Confirmation</h3>
            </div>

            <p className="text-sm text-slate-600">
              You are approving: <span className="font-semibold text-slate-800">{approveItem.label}</span>.
              This action will append an immutable audit revision in the institutional ledger.
            </p>

            {approveItem.type === 'correction' && (
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase mb-1">Approved Target Status</label>
                <select
                  value={approvedStatus}
                  onChange={(e) => setApprovedStatus(e.target.value)}
                  className="w-full text-sm bg-slate-50 border border-slate-300 rounded-lg px-3 py-2"
                >
                  <option value="PRESENT">PRESENT (1.00 credit)</option>
                  <option value="LATE">LATE (0.50 credit)</option>
                  <option value="EXCUSED">EXCUSED (Policy credit)</option>
                </select>
              </div>
            )}

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-1">Review Note (Optional)</label>
              <textarea
                value={approveNote}
                onChange={(e) => setApproveNote(e.target.value)}
                placeholder="Verified supporting documents / physical attendance..."
                rows={2}
                className="w-full text-sm bg-slate-50 border border-slate-300 rounded-lg p-3"
              />
            </div>

            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-2.5">
              <input
                type="checkbox"
                id="deliberateCheck"
                checked={deliberateConfirmation}
                onChange={(e) => setDeliberateConfirmation(e.target.checked)}
                className="mt-0.5 rounded text-indigo-600 focus:ring-indigo-500"
              />
              <label htmlFor="deliberateCheck" className="text-xs text-amber-900 leading-relaxed font-medium cursor-pointer">
                I confirm that I have verified the academic or medical evidence for this adjustment and take authoritative responsibility for this status change.
              </label>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setApproveItem(null)}
                className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg transition"
              >
                Cancel
              </button>
              <button
                onClick={handleApproveSubmit}
                disabled={isSubmitting || !deliberateConfirmation}
                className="px-4 py-2 text-sm font-semibold text-white bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 rounded-lg transition shadow-sm"
              >
                {isSubmitting ? 'Approving...' : 'Confirm Approval'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* REJECT MODAL */}
      {rejectItem && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl border border-slate-100 space-y-4">
            <div className="flex items-center gap-3 text-red-600">
              <div className="p-2 bg-red-100 rounded-lg">
                <XCircle className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-slate-900">Reject Attendance Request</h3>
            </div>

            <p className="text-sm text-slate-600">
              Rejecting: <span className="font-semibold text-slate-800">{rejectItem.label}</span>.
              The original attendance record and credit remain unchanged.
            </p>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-1">
                Mandatory Rejection Rationale <span className="text-red-500">*</span>
              </label>
              <textarea
                value={rejectNote}
                onChange={(e) => setRejectNote(e.target.value)}
                placeholder="State the reason for rejection (e.g. invalid document, insufficient justification)..."
                rows={3}
                className="w-full text-sm bg-slate-50 border border-slate-300 rounded-lg p-3"
              />
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setRejectItem(null)}
                className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg transition"
              >
                Cancel
              </button>
              <button
                onClick={handleRejectSubmit}
                disabled={isSubmitting || !rejectNote.trim()}
                className="px-4 py-2 text-sm font-semibold text-white bg-red-600 hover:bg-red-700 disabled:opacity-50 rounded-lg transition shadow-sm"
              >
                {isSubmitting ? 'Rejecting...' : 'Reject Request'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* OUT-OF-WINDOW OVERRIDE MODAL */}
      {overrideItem && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl border border-slate-100 space-y-4">
            <div className="flex items-center gap-3 text-amber-600">
              <div className="p-2 bg-amber-100 rounded-lg">
                <AlertTriangle className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-slate-900">Direct / Out-of-Window Override</h3>
            </div>

            <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-900 space-y-1">
              <div className="font-bold">Authoritative Ledger Warning:</div>
              <div>
                Direct overrides bypass standard student correction windows. A permanent revision is appended to the audit ledger tagged with your administrator identity.
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-1">Target Status</label>
              <select
                value={overrideTargetStatus}
                onChange={(e) => setOverrideTargetStatus(e.target.value)}
                className="w-full text-sm bg-slate-50 border border-slate-300 rounded-lg px-3 py-2"
              >
                <option value="PRESENT">PRESENT (1.00 credit)</option>
                <option value="LATE">LATE (0.50 credit)</option>
                <option value="EXCUSED">EXCUSED (Policy credit)</option>
                <option value="ABSENT">ABSENT (0.00 credit)</option>
                <option value="LEAVE">LEAVE (0.00 credit)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-1">Target Credit Override (Optional)</label>
              <input
                type="number"
                step="0.01"
                min="0.0"
                max="1.0"
                placeholder="Leave blank to use default status credit"
                value={overrideTargetCredit}
                onChange={(e) => setOverrideTargetCredit(e.target.value)}
                className="w-full text-sm bg-slate-50 border border-slate-300 rounded-lg px-3 py-2"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-1">
                Mandatory Override Justification <span className="text-red-500">*</span>
              </label>
              <textarea
                value={overrideReason}
                onChange={(e) => setOverrideReason(e.target.value)}
                placeholder="Official justification for administrative override..."
                rows={3}
                className="w-full text-sm bg-slate-50 border border-slate-300 rounded-lg p-3"
              />
            </div>

            <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg flex items-start gap-2.5">
              <input
                type="checkbox"
                id="overrideAck"
                checked={overrideConfirmed}
                onChange={(e) => setOverrideConfirmed(e.target.checked)}
                className="mt-0.5 rounded text-indigo-600 focus:ring-indigo-500"
              />
              <label htmlFor="overrideAck" className="text-xs text-slate-700 font-medium cursor-pointer">
                I acknowledge that this override will be permanently attributed to my user identity in the audit trail.
              </label>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setOverrideItem(null)}
                className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg transition"
              >
                Cancel
              </button>
              <button
                onClick={handleOverrideSubmit}
                disabled={isSubmitting || !overrideConfirmed || !overrideReason.trim()}
                className="px-4 py-2 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 rounded-lg transition shadow-sm"
              >
                {isSubmitting ? 'Applying...' : 'Apply Override'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* REVERSAL MODAL */}
      {showReversalModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl border border-slate-100 space-y-4">
            <div className="flex items-center gap-3 text-slate-800">
              <div className="p-2 bg-slate-100 rounded-lg">
                <History className="w-6 h-6 text-indigo-600" />
              </div>
              <h3 className="text-lg font-bold text-slate-900">Compensating Revision Reversal</h3>
            </div>

            <p className="text-xs text-slate-600">
              In accordance with INV-06, revisions cannot erase history. A compensating revision will be appended to reverse a prior erroneous revision.
            </p>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-1">Target Revision UUID</label>
              <input
                type="text"
                placeholder="0192323e-..."
                value={reversalRevisionId}
                onChange={(e) => setReversalRevisionId(e.target.value)}
                className="w-full text-sm font-mono bg-slate-50 border border-slate-300 rounded-lg px-3 py-2"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-1">Reversal Rationale</label>
              <textarea
                value={reversalReason}
                onChange={(e) => setReversalReason(e.target.value)}
                placeholder="Reason why this prior revision is being reversed..."
                rows={3}
                className="w-full text-sm bg-slate-50 border border-slate-300 rounded-lg p-3"
              />
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setShowReversalModal(false)}
                className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg transition"
              >
                Cancel
              </button>
              <button
                onClick={handleReversalSubmit}
                disabled={isSubmitting || !reversalRevisionId.trim() || !reversalReason.trim()}
                className="px-4 py-2 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 rounded-lg transition shadow-sm"
              >
                {isSubmitting ? 'Processing...' : 'Apply Compensating Reversal'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* BULK REVIEW MODAL */}
      {bulkModalOpen && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl border border-slate-100 space-y-4">
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-lg ${bulkAction === 'APPROVED' ? 'bg-emerald-100 text-emerald-600' : 'bg-red-100 text-red-600'}`}>
                {bulkAction === 'APPROVED' ? <Check className="w-6 h-6" /> : <X className="w-6 h-6" />}
              </div>
              <h3 className="text-lg font-bold text-slate-900">
                Bulk {bulkAction === 'APPROVED' ? 'Approve' : 'Reject'} ({selectedIds.size} items)
              </h3>
            </div>

            <p className="text-xs text-slate-600">
              Each selected item will be processed individually with itemized transaction safety.
            </p>

            {bulkAction === 'APPROVED' && activeTab === 'corrections' && (
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase mb-1">Approved Status</label>
                <select
                  value={bulkApprovedStatus}
                  onChange={(e) => setBulkApprovedStatus(e.target.value)}
                  className="w-full text-sm bg-slate-50 border border-slate-300 rounded-lg px-3 py-2"
                >
                  <option value="PRESENT">PRESENT (1.00 credit)</option>
                  <option value="LATE">LATE (0.50 credit)</option>
                  <option value="EXCUSED">EXCUSED (Policy credit)</option>
                </select>
              </div>
            )}

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-1">Batch Review Note</label>
              <textarea
                value={bulkNote}
                onChange={(e) => setBulkNote(e.target.value)}
                placeholder="State standard batch justification note..."
                rows={3}
                className="w-full text-sm bg-slate-50 border border-slate-300 rounded-lg p-3"
              />
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setBulkModalOpen(false)}
                className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg transition"
              >
                Cancel
              </button>
              <button
                onClick={handleBulkSubmit}
                disabled={isSubmitting || !bulkNote.trim()}
                className={`px-4 py-2 text-sm font-semibold text-white rounded-lg transition shadow-sm ${
                  bulkAction === 'APPROVED'
                    ? 'bg-emerald-600 hover:bg-emerald-700'
                    : 'bg-red-600 hover:bg-red-700'
                }`}
              >
                {isSubmitting ? 'Processing Batch...' : `Execute Bulk ${bulkAction}`}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* AUDIT TIMELINE MODAL */}
      {timelineModalOpen && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-xl border border-slate-100 max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between pb-4 border-b border-slate-200">
              <div className="flex items-center gap-2.5">
                <History className="w-5 h-5 text-indigo-600" />
                <h3 className="text-lg font-bold text-slate-900">Immutable Revision Audit Timeline</h3>
              </div>
              <button
                onClick={() => setTimelineModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-md"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto py-4 space-y-4">
              {timelineLoading ? (
                <div className="py-12 text-center text-slate-400">
                  <RefreshCw className="w-6 h-6 mx-auto animate-spin mb-2 text-indigo-500" />
                  <p className="text-xs">Loading record revision history...</p>
                </div>
              ) : timelineData ? (
                <div>
                  <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 grid grid-cols-2 gap-2 text-xs mb-4">
                    <div>
                      <span className="text-slate-500">Record ID:</span>{' '}
                      <span className="font-mono font-bold text-slate-800">{timelineData.record_id.slice(0, 8)}</span>
                    </div>
                    <div>
                      <span className="text-slate-500">Current Status:</span>{' '}
                      <span className="font-bold text-slate-900">{timelineData.current_status}</span>{' '}
                      ({timelineData.current_credit.toFixed(2)} cr)
                    </div>
                    <div>
                      <span className="text-slate-500">Version:</span>{' '}
                      <span className="font-bold text-slate-800">v{timelineData.version_no}</span>
                    </div>
                    <div>
                      <span className="text-slate-500">Manual Flag:</span>{' '}
                      <span className="font-semibold text-slate-800">{timelineData.is_manual ? 'Yes' : 'No'}</span>
                    </div>
                  </div>

                  {timelineData.revisions.length === 0 ? (
                    <div className="py-8 text-center text-slate-400 text-xs">
                      No revisions recorded yet for this record.
                    </div>
                  ) : (
                    <div className="relative pl-6 border-l-2 border-slate-200 space-y-6">
                      {timelineData.revisions.map((rev) => (
                        <div key={rev.id} className="relative group">
                          <div className="absolute -left-[31px] top-1 w-3.5 h-3.5 rounded-full border-2 border-white bg-indigo-600 shadow-xs" />
                          <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs">
                            <div className="flex items-center justify-between text-xs mb-1">
                              <span className="font-bold text-indigo-600">{rev.event_type}</span>
                              <span className="text-slate-400">
                                {new Date(rev.occurred_at_utc).toUTCString()}
                              </span>
                            </div>
                            <div className="text-xs text-slate-700 font-medium">
                              Status: {rev.previous_status || 'NONE'} &rarr;{' '}
                              <span className="font-bold text-slate-900">{rev.new_status || 'UNCHANGED'}</span>
                              <span className="text-slate-400 ml-2">
                                (credit: {rev.previous_credit?.toFixed(2) ?? '-'} &rarr;{' '}
                                {rev.new_credit?.toFixed(2) ?? '-'})
                              </span>
                            </div>
                            {rev.reason && (
                              <div className="text-xs text-slate-600 mt-1.5 italic bg-slate-50 p-2 rounded">
                                &ldquo;{rev.reason}&rdquo;
                              </div>
                            )}
                            <div className="text-[10px] text-slate-400 font-mono mt-1.5">
                              Actor: {rev.actor_user_id.slice(0, 8)}... | Rev ID: {rev.id.slice(0, 8)}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <div className="py-8 text-center text-slate-400 text-xs">Failed to load timeline.</div>
              )}
            </div>

            <div className="pt-3 border-t border-slate-200 flex justify-end">
              <button
                onClick={() => setTimelineModalOpen(false)}
                className="px-4 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
