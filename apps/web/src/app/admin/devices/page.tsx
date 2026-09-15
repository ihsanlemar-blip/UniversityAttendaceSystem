'use client';

import React, { useState, useEffect } from 'react';
import {
  Smartphone,
  ShieldCheck,
  ShieldAlert,
  History,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Search,
  Filter,
} from 'lucide-react';

interface ReplacementRequest {
  id: string;
  student_id: string;
  student_name?: string;
  student_number?: string;
  current_device_id: string;
  current_device_short_fingerprint?: string;
  candidate_device_short_fingerprint: string;
  candidate_device_label?: string;
  candidate_platform?: string;
  reason: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
  requested_at: string;
  reviewed_at?: string;
  reviewer_name?: string;
}

interface TrustedDevice {
  id: string;
  student_id: string;
  student_name?: string;
  student_number?: string;
  device_label?: string;
  platform?: string;
  short_fingerprint: string;
  status: 'ACTIVE' | 'PENDING_REGISTRATION' | 'SUSPENDED' | 'REPLACED' | 'REVOKED';
  activated_at?: string;
  created_at: string;
}

interface DeviceTrustEvent {
  id: string;
  event_type: string;
  student_id: string;
  trusted_device_id?: string;
  reason?: string;
  created_at: string;
}

export default function AdminDeviceManagementPage() {
  const [activeTab, setActiveTab] = useState<'replacements' | 'devices' | 'audit'>('replacements');
  const [replacements, setReplacements] = useState<ReplacementRequest[]>([]);
  const [devices, setDevices] = useState<TrustedDevice[]>([]);
  const [auditEvents, setAuditEvents] = useState<DeviceTrustEvent[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedRequest, setSelectedRequest] = useState<ReplacementRequest | null>(null);
  const [reviewAction, setReviewAction] = useState<'APPROVE' | 'REJECT'>('APPROVE');
  const [reviewReason, setReviewReason] = useState<string>('');
  const [isSubmittingReview, setIsSubmittingReview] = useState<boolean>(false);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';

  const loadData = React.useCallback(async () => {
    setIsLoading(true);
    setActionError(null);
    try {
      const replRes = await fetch(`${apiBaseUrl}/devices/replacement-requests`, {
        headers: { Accept: 'application/json' },
      });
      if (replRes.ok) {
        const data = await replRes.json();
        setReplacements(data.data || []);
      }

      const devRes = await fetch(`${apiBaseUrl}/devices`, {
        headers: { Accept: 'application/json' },
      });
      if (devRes.ok) {
        const data = await devRes.json();
        setDevices(data.data || []);
      }
    } catch {
      setActionError('Could not reach backend API server. Showing cached or demo state.');
    } finally {
      setIsLoading(false);
    }
  }, [apiBaseUrl]);

  useEffect(() => {
    let ignore = false;
    async function initFetch() {
      try {
        const replRes = await fetch(`${apiBaseUrl}/devices/replacement-requests`, {
          headers: { Accept: 'application/json' },
        });
        if (replRes.ok && !ignore) {
          const data = await replRes.json();
          setReplacements(data.data || []);
        }

        const devRes = await fetch(`${apiBaseUrl}/devices`, {
          headers: { Accept: 'application/json' },
        });
        if (devRes.ok && !ignore) {
          const data = await devRes.json();
          setDevices(data.data || []);
        }
      } catch {
        if (!ignore) {
          setActionError('Could not reach backend API server. Showing cached or demo state.');
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

  const handleReviewSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRequest) return;
    setIsSubmittingReview(true);
    setActionError(null);
    setActionSuccess(null);

    try {
      const res = await fetch(
        `${apiBaseUrl}/devices/replacement-requests/${selectedRequest.id}/review`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Accept: 'application/json',
          },
          body: jsonEncode({
            action: reviewAction,
            justification: reviewReason || undefined,
          }),
        }
      );

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to submit replacement decision.');
      }

      setActionSuccess(
        `Replacement request successfully ${reviewAction === 'APPROVE' ? 'approved' : 'rejected'}.`
      );
      setSelectedRequest(null);
      setReviewReason('');
      await loadData();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : 'Error submitting review.');
    } finally {
      setIsSubmittingReview(false);
    }
  };

  function jsonEncode(obj: Record<string, unknown>): string {
    return JSON.stringify(obj);
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'ACTIVE':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="w-3 h-3" /> ACTIVE
          </span>
        );
      case 'PENDING':
      case 'PENDING_REGISTRATION':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-700 border border-amber-200">
            <AlertTriangle className="w-3 h-3" /> PENDING
          </span>
        );
      case 'SUSPENDED':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2.5 py-1 text-xs font-semibold text-rose-700 border border-rose-200">
            <ShieldAlert className="w-3 h-3" /> SUSPENDED
          </span>
        );
      case 'REPLACED':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-slate-50 px-2.5 py-1 text-xs font-semibold text-slate-600 border border-slate-200">
            <History className="w-3 h-3" /> REPLACED
          </span>
        );
      case 'REVOKED':
      case 'REJECTED':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2.5 py-1 text-xs font-semibold text-rose-700 border border-rose-200">
            <XCircle className="w-3 h-3" /> {status}
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-gray-50 px-2.5 py-1 text-xs font-semibold text-gray-600 border border-gray-200">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <div>
            <div className="flex items-center gap-3">
              <div className="p-2 bg-indigo-50 rounded-lg text-indigo-600">
                <Smartphone className="w-6 h-6" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-slate-900">
                  Device Registration & Trust Governance
                </h1>
                <p className="text-sm text-slate-500">
                  Manage primary mobile device authorizations, replacement workflows, and cryptographic integrity.
                </p>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={loadData}
              disabled={isLoading}
              className="inline-flex items-center gap-2 px-4 py-2 border border-slate-300 rounded-lg text-sm font-medium text-slate-700 bg-white hover:bg-slate-50 transition-colors shadow-sm"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>

        {/* Notifications */}
        {actionSuccess && (
          <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-sm flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              <span>{actionSuccess}</span>
            </div>
            <button
              onClick={() => setActionSuccess(null)}
              className="text-emerald-600 hover:text-emerald-900 font-bold"
            >
              &times;
            </button>
          </div>
        )}
        {actionError && (
          <div className="p-4 bg-rose-50 border border-rose-200 text-rose-800 rounded-lg text-sm flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-600" />
              <span>{actionError}</span>
            </div>
            <button
              onClick={() => setActionError(null)}
              className="text-rose-600 hover:text-rose-900 font-bold"
            >
              &times;
            </button>
          </div>
        )}

        {/* Tabs */}
        <div className="flex border-b border-slate-200 bg-white px-4 rounded-t-xl">
          <button
            onClick={() => setActiveTab('replacements')}
            className={`flex items-center gap-2 py-4 px-4 font-semibold text-sm border-b-2 transition-colors ${
              activeTab === 'replacements'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            <AlertTriangle className="w-4 h-4" />
            Replacement Requests
            {replacements.filter((r) => r.status === 'PENDING').length > 0 && (
              <span className="ml-1 px-2 py-0.5 text-xs bg-amber-100 text-amber-800 rounded-full font-bold">
                {replacements.filter((r) => r.status === 'PENDING').length}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('devices')}
            className={`flex items-center gap-2 py-4 px-4 font-semibold text-sm border-b-2 transition-colors ${
              activeTab === 'devices'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            <ShieldCheck className="w-4 h-4" />
            Active Trusted Devices
            <span className="ml-1 px-2 py-0.5 text-xs bg-slate-100 text-slate-600 rounded-full">
              {devices.length}
            </span>
          </button>
          <button
            onClick={() => setActiveTab('audit')}
            className={`flex items-center gap-2 py-4 px-4 font-semibold text-sm border-b-2 transition-colors ${
              activeTab === 'audit'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            <History className="w-4 h-4" />
            Trust Audit Trail
          </button>
        </div>

        {/* Tab 1: Replacement Requests */}
        {activeTab === 'replacements' && (
          <div className="bg-white rounded-b-xl border border-slate-200 shadow-sm p-6 space-y-4">
            <div className="flex flex-col sm:flex-row justify-between items-center gap-4">
              <h2 className="text-lg font-bold text-slate-800">
                Pending Primary Device Replacements
              </h2>
              <div className="relative w-full sm:w-64">
                <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search by student or reason..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-4 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>

            {replacements.length === 0 ? (
              <div className="text-center py-12 text-slate-400">
                <Smartphone className="w-12 h-12 mx-auto mb-3 opacity-40" />
                <p>No pending replacement requests found.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-200">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">
                        Student
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">
                        Status
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">
                        Candidate Fingerprint
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">
                        Reason
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">
                        Requested At
                      </th>
                      <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 uppercase">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {replacements
                      .filter(
                        (r) =>
                          r.reason.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          r.candidate_device_short_fingerprint.toLowerCase().includes(searchQuery.toLowerCase())
                      )
                      .map((req) => (
                        <tr key={req.id} className="hover:bg-slate-50/50">
                          <td className="px-4 py-3 text-sm text-slate-900 font-medium">
                            {req.student_number || req.student_id.substring(0, 8)}
                          </td>
                          <td className="px-4 py-3 text-sm">{getStatusBadge(req.status)}</td>
                          <td className="px-4 py-3 text-sm font-mono text-slate-600">
                            {req.candidate_device_short_fingerprint}
                          </td>
                          <td className="px-4 py-3 text-sm text-slate-600 max-w-xs truncate">
                            {req.reason}
                          </td>
                          <td className="px-4 py-3 text-sm text-slate-500">
                            {new Date(req.requested_at).toLocaleString()}
                          </td>
                          <td className="px-4 py-3 text-sm text-right space-x-2">
                            {req.status === 'PENDING' ? (
                              <button
                                onClick={() => {
                                  setSelectedRequest(req);
                                  setReviewAction('APPROVE');
                                }}
                                className="inline-flex items-center gap-1 px-3 py-1 bg-indigo-600 text-white rounded text-xs font-medium hover:bg-indigo-700 transition"
                              >
                                Review Request
                              </button>
                            ) : (
                              <span className="text-xs text-slate-400">Decision Recorded</span>
                            )}
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Registered Devices */}
        {activeTab === 'devices' && (
          <div className="bg-white rounded-b-xl border border-slate-200 shadow-sm p-6 space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-lg font-bold text-slate-800">Enrolled Student Devices</h2>
            </div>
            {devices.length === 0 ? (
              <div className="text-center py-12 text-slate-400">
                <ShieldCheck className="w-12 h-12 mx-auto mb-3 opacity-40" />
                <p>No active registered devices in database.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-200">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">
                        Device
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">
                        Status
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">
                        Fingerprint
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">
                        Platform
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">
                        Activated
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {devices.map((dev) => (
                      <tr key={dev.id} className="hover:bg-slate-50/50">
                        <td className="px-4 py-3 text-sm text-slate-900 font-medium">
                          {dev.device_label || 'Mobile Device'}
                        </td>
                        <td className="px-4 py-3 text-sm">{getStatusBadge(dev.status)}</td>
                        <td className="px-4 py-3 text-sm font-mono text-slate-700">
                          {dev.short_fingerprint}
                        </td>
                        <td className="px-4 py-3 text-sm text-slate-500 capitalize">
                          {dev.platform || 'Unknown'}
                        </td>
                        <td className="px-4 py-3 text-sm text-slate-500">
                          {dev.activated_at ? new Date(dev.activated_at).toLocaleDateString() : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Tab 3: Trust Audit Trail */}
        {activeTab === 'audit' && (
          <div className="bg-white rounded-b-xl border border-slate-200 shadow-sm p-6">
            <h2 className="text-lg font-bold text-slate-800 mb-4">Device Trust Security Ledger</h2>
            <p className="text-sm text-slate-500 mb-6">
              Append-only audit logs for all device authorizations, replacements, suspensions, and cryptographic events.
            </p>
            <div className="p-8 border border-dashed border-slate-300 rounded-lg text-center text-slate-400">
              <History className="w-10 h-10 mx-auto mb-2 opacity-40" />
              <p>Audit trail entries are recorded securely in the PostgreSQL audit ledger.</p>
            </div>
          </div>
        )}

        {/* Review Modal Dialog */}
        {selectedRequest && (
          <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-xl max-w-lg w-full p-6 space-y-4 shadow-xl">
              <div className="flex justify-between items-center border-b border-slate-100 pb-3">
                <h3 className="text-lg font-bold text-slate-900">
                  Review Device Replacement Request
                </h3>
                <button
                  onClick={() => setSelectedRequest(null)}
                  className="text-slate-400 hover:text-slate-600"
                >
                  &times;
                </button>
              </div>

              <div className="space-y-3 text-sm">
                <div>
                  <span className="font-semibold text-slate-700">Student: </span>
                  <span className="text-slate-900">{selectedRequest.student_number || selectedRequest.student_id}</span>
                </div>
                <div>
                  <span className="font-semibold text-slate-700">Stated Justification: </span>
                  <p className="mt-1 p-2.5 bg-slate-50 rounded border border-slate-200 text-slate-800">
                    {selectedRequest.reason}
                  </p>
                </div>
                <div>
                  <span className="font-semibold text-slate-700">New Device Fingerprint: </span>
                  <span className="font-mono text-indigo-700">
                    {selectedRequest.candidate_device_short_fingerprint}
                  </span>
                </div>
              </div>

              <form onSubmit={handleReviewSubmit} className="space-y-4 pt-2">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                    Administrative Decision
                  </label>
                  <div className="flex gap-3">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name="reviewAction"
                        value="APPROVE"
                        checked={reviewAction === 'APPROVE'}
                        onChange={() => setReviewAction('APPROVE')}
                        className="text-indigo-600 focus:ring-indigo-500"
                      />
                      <span className="text-sm font-medium text-slate-800">Approve Replacement</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name="reviewAction"
                        value="REJECT"
                        checked={reviewAction === 'REJECT'}
                        onChange={() => setReviewAction('REJECT')}
                        className="text-rose-600 focus:ring-rose-500"
                      />
                      <span className="text-sm font-medium text-slate-800">Reject</span>
                    </label>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                    Auditor Justification (Mandatory for rejection)
                  </label>
                  <textarea
                    rows={2}
                    value={reviewReason}
                    onChange={(e) => setReviewReason(e.target.value)}
                    placeholder="Enter review notes for immutable audit record..."
                    className="w-full p-2 border border-slate-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div className="flex justify-end gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setSelectedRequest(null)}
                    disabled={isSubmittingReview}
                    className="px-4 py-2 border border-slate-300 rounded-lg text-sm text-slate-700 hover:bg-slate-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmittingReview}
                    className={`px-4 py-2 rounded-lg text-sm font-medium text-white shadow-sm ${
                      reviewAction === 'APPROVE'
                        ? 'bg-indigo-600 hover:bg-indigo-700'
                        : 'bg-rose-600 hover:bg-rose-700'
                    }`}
                  >
                    {isSubmittingReview ? 'Processing...' : `Confirm ${reviewAction}`}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
