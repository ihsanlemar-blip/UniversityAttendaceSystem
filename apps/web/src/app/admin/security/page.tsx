'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  Wifi,
  Radio,
  Network,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  Filter,
  RefreshCw,
  Plus,
  Info,
  Eye,
  Check,
  X,
  Building,
  Activity,
  Layers,
} from 'lucide-react';

interface CampusNetworkZone {
  id: string;
  university_id: string;
  building_id?: string | null;
  name: string;
  code: string;
  network_cidr: string;
  ip_version: number;
  zone_type: string;
  status: 'ACTIVE' | 'INACTIVE' | 'DEPRECATED';
  priority: number;
  allow_student_presence: boolean;
  created_at: string;
}

interface AttendanceRiskSignal {
  id: string;
  university_id: string;
  signal_type: string;
  severity: 'INFO' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  risk_points?: number | null;
  subject_type: 'STUDENT' | 'LECTURER' | 'SYSTEM';
  subject_user_id?: string | null;
  trusted_device_id?: string | null;
  attendance_session_id?: string | null;
  class_occurrence_id?: string | null;
  context?: Record<string, unknown> | null;
  rule_version: string;
  status: 'OPEN' | 'ACKNOWLEDGED' | 'RESOLVED' | 'DISMISSED';
  detected_at: string;
  reviewed_at?: string | null;
  reviewed_by_user_id?: string | null;
  review_note?: string | null;
}

interface RadioAnalysisSummary {
  observation_count: number;
  median_rssi?: number | null;
  p10_rssi?: number | null;
  p25_rssi?: number | null;
  p75_rssi?: number | null;
  p90_rssi?: number | null;
  min_rssi?: number | null;
  max_rssi?: number | null;
  computed_at: string;
}

export default function AdminSecurityPage() {
  const [activeTab, setActiveTab] = useState<'networks' | 'risks' | 'radio'>('networks');
  const [zones, setZones] = useState<CampusNetworkZone[]>([]);
  const [riskSignals, setRiskSignals] = useState<AttendanceRiskSignal[]>([]);
  const [radioSummary, setRadioSummary] = useState<RadioAnalysisSummary | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Filters for Risk Signals
  const [riskStatusFilter, setRiskStatusFilter] = useState<string>('');
  const [riskSeverityFilter, setRiskSeverityFilter] = useState<string>('');

  // Modals
  const [showCreateZoneModal, setShowCreateZoneModal] = useState<boolean>(false);
  const [selectedSignal, setSelectedSignal] = useState<AttendanceRiskSignal | null>(null);
  const [reviewModalSignal, setReviewModalSignal] = useState<AttendanceRiskSignal | null>(null);
  const [reviewModalAction, setReviewModalAction] = useState<'RESOLVE' | 'DISMISS'>('RESOLVE');
  const [reviewNote, setReviewNote] = useState<string>('');
  const [isSubmittingReview, setIsSubmittingReview] = useState<boolean>(false);

  // Zone Form State
  const [newZoneName, setNewZoneName] = useState<string>('');
  const [newZoneCode, setNewZoneCode] = useState<string>('');
  const [newZoneCidr, setNewZoneCidr] = useState<string>('');
  const [newZoneType, setNewZoneType] = useState<string>('CAMPUS_TRUSTED');
  const [newZonePriority, setNewZonePriority] = useState<number>(50);
  const [newZoneAllowStudents, setNewZoneAllowStudents] = useState<boolean>(true);
  const [isSubmittingZone, setIsSubmittingZone] = useState<boolean>(false);

  // Radio diagnostics query parameters
  const [radioSessionId, setRadioSessionId] = useState<string>('');

  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setActionError(null);
    try {
      // 1. Fetch network zones
      const zonesRes = await fetch(`${apiBaseUrl}/security/network-zones`, {
        headers: { Accept: 'application/json' },
      });
      if (zonesRes.ok) {
        const d = await zonesRes.json();
        setZones(d.data || []);
      }

      // 2. Fetch risk signals
      const queryParams = new URLSearchParams();
      if (riskStatusFilter) queryParams.set('status', riskStatusFilter);
      if (riskSeverityFilter) queryParams.set('severity', riskSeverityFilter);

      const risksRes = await fetch(`${apiBaseUrl}/security/risk-signals?${queryParams.toString()}`, {
        headers: { Accept: 'application/json' },
      });
      if (risksRes.ok) {
        const d = await risksRes.json();
        setRiskSignals(d.data || []);
      }

      // 3. Fetch radio diagnostics
      const radioUrl = radioSessionId
        ? `${apiBaseUrl}/security/radio-analysis?session_id=${encodeURIComponent(radioSessionId)}`
        : `${apiBaseUrl}/security/radio-analysis`;
      const radioRes = await fetch(radioUrl, {
        headers: { Accept: 'application/json' },
      });
      if (radioRes.ok) {
        const d = await radioRes.json();
        setRadioSummary(d.data || null);
      }
    } catch {
      setActionError('Could not reach backend API server. Displaying live or fallback view.');
    } finally {
      setIsLoading(false);
    }
  }, [apiBaseUrl, riskStatusFilter, riskSeverityFilter, radioSessionId]);

  useEffect(() => {
    let ignore = false;

    async function initFetch() {
      try {
        const zonesRes = await fetch(`${apiBaseUrl}/security/network-zones`, {
          headers: { Accept: 'application/json' },
        });
        if (zonesRes.ok && !ignore) {
          const d = await zonesRes.json();
          setZones(d.data || []);
        }

        const queryParams = new URLSearchParams();
        if (riskStatusFilter) queryParams.set('status', riskStatusFilter);
        if (riskSeverityFilter) queryParams.set('severity', riskSeverityFilter);

        const risksRes = await fetch(
          `${apiBaseUrl}/security/risk-signals?${queryParams.toString()}`,
          {
            headers: { Accept: 'application/json' },
          }
        );
        if (risksRes.ok && !ignore) {
          const d = await risksRes.json();
          setRiskSignals(d.data || []);
        }

        const radioUrl = radioSessionId
          ? `${apiBaseUrl}/security/radio-analysis?session_id=${encodeURIComponent(radioSessionId)}`
          : `${apiBaseUrl}/security/radio-analysis`;
        const radioRes = await fetch(radioUrl, {
          headers: { Accept: 'application/json' },
        });
        if (radioRes.ok && !ignore) {
          const d = await radioRes.json();
          setRadioSummary(d.data || null);
        }
      } catch {
        if (!ignore) {
          setActionError('Could not reach backend API server. Displaying live or fallback view.');
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
  }, [apiBaseUrl, riskStatusFilter, riskSeverityFilter, radioSessionId]);

  // Handle Zone Creation
  const handleCreateZone = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmittingZone(true);
    setActionError(null);
    setActionSuccess(null);

    try {
      const res = await fetch(`${apiBaseUrl}/security/network-zones`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({
          name: newZoneName,
          code: newZoneCode.toUpperCase(),
          network_cidr: newZoneCidr,
          zone_type: newZoneType,
          priority: Number(newZonePriority),
          allow_student_presence: newZoneAllowStudents,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.message || 'Failed to create campus network zone.');
      }

      setActionSuccess(`Campus network zone '${newZoneName}' created successfully.`);
      setShowCreateZoneModal(false);
      setNewZoneName('');
      setNewZoneCode('');
      setNewZoneCidr('');
      setNewZonePriority(50);
      setNewZoneAllowStudents(true);
      await loadData();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : 'Error creating network zone.');
    } finally {
      setIsSubmittingZone(false);
    }
  };

  // Handle Zone Status Toggle
  const handleToggleZoneStatus = async (zone: CampusNetworkZone) => {
    const nextStatus = zone.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE';
    try {
      const res = await fetch(`${apiBaseUrl}/security/network-zones/${zone.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({ status: nextStatus }),
      });
      if (!res.ok) {
        throw new Error('Failed to update zone status.');
      }
      setActionSuccess(`Zone ${zone.code} updated to ${nextStatus}.`);
      await loadData();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : 'Failed to update zone.');
    }
  };

  // Handle Acknowledge Signal
  const handleAcknowledgeSignal = async (sigId: string) => {
    try {
      const res = await fetch(`${apiBaseUrl}/security/risk-signals/${sigId}/acknowledge`, {
        method: 'POST',
        headers: { Accept: 'application/json' },
      });
      if (!res.ok) throw new Error('Failed to acknowledge risk signal.');
      setActionSuccess('Risk signal marked as Acknowledged.');
      await loadData();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : 'Error acknowledging signal.');
    }
  };

  // Handle Review (Resolve or Dismiss) Submit
  const handleReviewSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reviewModalSignal) return;
    if (!reviewNote.trim()) {
      setActionError('A review note explanation is required by governance policy.');
      return;
    }

    setIsSubmittingReview(true);
    setActionError(null);
    setActionSuccess(null);

    const endpoint = reviewModalAction === 'RESOLVE' ? 'resolve' : 'dismiss';
    try {
      const res = await fetch(
        `${apiBaseUrl}/security/risk-signals/${reviewModalSignal.id}/${endpoint}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
          body: JSON.stringify({ review_note: reviewNote }),
        }
      );
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.message || `Failed to ${endpoint} signal.`);
      }
      setActionSuccess(
        `Risk signal successfully ${reviewModalAction === 'RESOLVE' ? 'resolved' : 'dismissed'}.`
      );
      setReviewModalSignal(null);
      setReviewNote('');
      await loadData();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : 'Error processing review action.');
    } finally {
      setIsSubmittingReview(false);
    }
  };

  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case 'CRITICAL':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-rose-100 px-2.5 py-0.5 text-xs font-bold text-rose-800 border border-rose-300">
            <XCircle className="w-3 h-3" /> CRITICAL
          </span>
        );
      case 'HIGH':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-orange-100 px-2.5 py-0.5 text-xs font-semibold text-orange-800 border border-orange-300">
            <AlertTriangle className="w-3 h-3" /> HIGH
          </span>
        );
      case 'MEDIUM':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-800 border border-amber-300">
            <AlertTriangle className="w-3 h-3" /> MEDIUM
          </span>
        );
      case 'LOW':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800 border border-blue-200">
            <Info className="w-3 h-3" /> LOW
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700 border border-slate-200">
            <Info className="w-3 h-3" /> INFO
          </span>
        );
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'OPEN':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2.5 py-0.5 text-xs font-bold text-rose-700 border border-rose-200">
            <Clock className="w-3 h-3" /> OPEN
          </span>
        );
      case 'ACKNOWLEDGED':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-semibold text-amber-700 border border-amber-200">
            <Eye className="w-3 h-3" /> ACKNOWLEDGED
          </span>
        );
      case 'RESOLVED':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="w-3 h-3" /> RESOLVED
          </span>
        );
      case 'DISMISSED':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600 border border-slate-300">
            <X className="w-3 h-3" /> DISMISSED
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-gray-50 px-2.5 py-0.5 text-xs font-medium text-gray-600">
            {status}
          </span>
        );
    }
  };

  const openRiskCount = riskSignals.filter((s) => s.status === 'OPEN').length;

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 p-6 md:p-8">
      {/* Page Header */}
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 pb-5">
          <div>
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-indigo-600 text-white rounded-xl shadow-sm">
                <ShieldAlert className="w-6 h-6" />
              </div>
              <div>
                <h1 className="text-2xl font-bold tracking-tight text-slate-900">
                  Campus Security & Anti-Cheat Operations
                </h1>
                <p className="text-sm text-slate-500">
                  Milestone 14 Campus Network Presence, Radio Diagnostics, and Human Review Ledger
                </p>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={loadData}
              disabled={isLoading}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50 disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
            {activeTab === 'networks' && (
              <button
                onClick={() => setShowCreateZoneModal(true)}
                className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-3.5 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-700"
              >
                <Plus className="w-4 h-4" />
                New Network Zone
              </button>
            )}
          </div>
        </div>

        {/* Action Alerts */}
        {actionSuccess && (
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-emerald-800 flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-medium">
              <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
              {actionSuccess}
            </div>
            <button
              onClick={() => setActionSuccess(null)}
              className="text-emerald-600 hover:text-emerald-800"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}
        {actionError && (
          <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-rose-800 flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-medium">
              <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0" />
              {actionError}
            </div>
            <button
              onClick={() => setActionError(null)}
              className="text-rose-600 hover:text-rose-800"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Tab Navigation */}
        <div className="flex items-center gap-2 border-b border-slate-200">
          <button
            onClick={() => setActiveTab('networks')}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-semibold border-b-2 transition-colors ${
              activeTab === 'networks'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-600 hover:text-slate-900 hover:border-slate-300'
            }`}
          >
            <Network className="w-4 h-4" />
            Campus Networks
            <span className="ml-1 rounded-full bg-slate-200 px-2 py-0.5 text-xs font-medium text-slate-700">
              {zones.length}
            </span>
          </button>
          <button
            onClick={() => setActiveTab('risks')}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-semibold border-b-2 transition-colors ${
              activeTab === 'risks'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-600 hover:text-slate-900 hover:border-slate-300'
            }`}
          >
            <ShieldAlert className="w-4 h-4" />
            Risk Review Queue
            {openRiskCount > 0 && (
              <span className="ml-1 rounded-full bg-rose-600 px-2 py-0.5 text-xs font-bold text-white">
                {openRiskCount}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('radio')}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-semibold border-b-2 transition-colors ${
              activeTab === 'radio'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-600 hover:text-slate-900 hover:border-slate-300'
            }`}
          >
            <Radio className="w-4 h-4" />
            Radio Diagnostics
          </button>
        </div>

        {/* ===================================================================== */}
        {/* TAB 1: CAMPUS NETWORKS                                                */}
        {/* ===================================================================== */}
        {activeTab === 'networks' && (
          <div className="space-y-6">
            {/* KPI Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    Total Zones
                  </span>
                  <Network className="w-5 h-5 text-slate-400" />
                </div>
                <p className="mt-2 text-3xl font-bold text-slate-900">{zones.length}</p>
                <p className="mt-1 text-xs text-slate-500">Configured CIDR subnets</p>
              </div>

              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    Active Zones
                  </span>
                  <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                </div>
                <p className="mt-2 text-3xl font-bold text-emerald-600">
                  {zones.filter((z) => z.status === 'ACTIVE').length}
                </p>
                <p className="mt-1 text-xs text-slate-500">Evaluating client IPs</p>
              </div>

              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    Student Presence Allowed
                  </span>
                  <Wifi className="w-5 h-5 text-indigo-500" />
                </div>
                <p className="mt-2 text-3xl font-bold text-indigo-600">
                  {zones.filter((z) => z.allow_student_presence).length}
                </p>
                <p className="mt-1 text-xs text-slate-500">Permitted for student check-in</p>
              </div>

              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    Highest Priority
                  </span>
                  <Layers className="w-5 h-5 text-amber-500" />
                </div>
                <p className="mt-2 text-3xl font-bold text-amber-600">
                  {zones.length > 0 ? Math.max(...zones.map((z) => z.priority)) : 0}
                </p>
                <p className="mt-1 text-xs text-slate-500">Priority prefix resolution</p>
              </div>
            </div>

            {/* Network Zones Table */}
            <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
              <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-slate-900">Campus Network Subnets</h3>
                  <p className="text-xs text-slate-500">
                    Zones verified against server-observed source IPs via longest-prefix matching.
                  </p>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-slate-600">
                  <thead className="bg-slate-50 text-xs font-semibold uppercase text-slate-500 border-b border-slate-200">
                    <tr>
                      <th className="px-6 py-3">Zone Details</th>
                      <th className="px-6 py-3">CIDR Subnet</th>
                      <th className="px-6 py-3">Type</th>
                      <th className="px-6 py-3 text-center">Priority</th>
                      <th className="px-6 py-3 text-center">Student Presence</th>
                      <th className="px-6 py-3 text-center">Status</th>
                      <th className="px-6 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {zones.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="px-6 py-12 text-center text-slate-400">
                          <Network className="w-10 h-10 mx-auto mb-2 opacity-40" />
                          No campus network zones configured. Click &quot;New Network Zone&quot; to add one.
                        </td>
                      </tr>
                    ) : (
                      zones.map((zone) => (
                        <tr key={zone.id} className="hover:bg-slate-50/75 transition-colors">
                          <td className="px-6 py-4">
                            <div className="font-semibold text-slate-900">{zone.name}</div>
                            <div className="text-xs text-slate-400 font-mono">{zone.code}</div>
                          </td>
                          <td className="px-6 py-4">
                            <div className="inline-flex items-center gap-1.5 font-mono text-xs font-medium text-slate-800 bg-slate-100 px-2 py-1 rounded">
                              <span>{zone.network_cidr}</span>
                              <span className="text-[10px] text-slate-500 font-sans">
                                (IPv{zone.ip_version})
                              </span>
                            </div>
                          </td>
                          <td className="px-6 py-4">
                            <span className="inline-flex rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
                              {zone.zone_type}
                            </span>
                          </td>
                          <td className="px-6 py-4 text-center font-semibold text-slate-700">
                            {zone.priority}
                          </td>
                          <td className="px-6 py-4 text-center">
                            {zone.allow_student_presence ? (
                              <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-600">
                                <Check className="w-3.5 h-3.5" /> Allowed
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 text-xs font-medium text-slate-400">
                                <X className="w-3.5 h-3.5" /> Prohibited
                              </span>
                            )}
                          </td>
                          <td className="px-6 py-4 text-center">
                            <span
                              className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                                zone.status === 'ACTIVE'
                                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                  : 'bg-slate-100 text-slate-600 border border-slate-200'
                              }`}
                            >
                              {zone.status}
                            </span>
                          </td>
                          <td className="px-6 py-4 text-right">
                            <button
                              onClick={() => handleToggleZoneStatus(zone)}
                              className="text-xs font-medium text-indigo-600 hover:text-indigo-800 hover:underline"
                            >
                              {zone.status === 'ACTIVE' ? 'Deactivate' : 'Activate'}
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* ===================================================================== */}
        {/* TAB 2: RISK REVIEW QUEUE                                              */}
        {/* ===================================================================== */}
        {activeTab === 'risks' && (
          <div className="space-y-6">
            {/* Invariant Governance Banner */}
            <div className="rounded-xl border border-indigo-200 bg-indigo-50/60 p-4 text-sm text-indigo-900 flex items-start gap-3">
              <ShieldCheck className="w-5 h-5 text-indigo-600 mt-0.5 shrink-0" />
              <div>
                <span className="font-semibold">Deterministic Anti-Cheat Invariant:</span> Anti-cheat
                risk signals are factorized diagnostic records logged strictly for authorized human
                review. Status transitions (Acknowledge, Resolve, Dismiss) are immutably recorded in
                the audit ledger and{' '}
                <span className="font-bold underline">
                  never automatically alter student attendance or impose disciplinary sanctions
                </span>
                .
              </div>
            </div>

            {/* Filter Bar */}
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm flex flex-wrap items-center gap-4">
              <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
                <Filter className="w-4 h-4 text-slate-400" />
                Filters:
              </div>

              <div>
                <select
                  value={riskStatusFilter}
                  onChange={(e) => setRiskStatusFilter(e.target.value)}
                  className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 shadow-sm focus:border-indigo-500 focus:outline-none"
                >
                  <option value="">All Statuses</option>
                  <option value="OPEN">OPEN</option>
                  <option value="ACKNOWLEDGED">ACKNOWLEDGED</option>
                  <option value="RESOLVED">RESOLVED</option>
                  <option value="DISMISSED">DISMISSED</option>
                </select>
              </div>

              <div>
                <select
                  value={riskSeverityFilter}
                  onChange={(e) => setRiskSeverityFilter(e.target.value)}
                  className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 shadow-sm focus:border-indigo-500 focus:outline-none"
                >
                  <option value="">All Severities</option>
                  <option value="CRITICAL">CRITICAL</option>
                  <option value="HIGH">HIGH</option>
                  <option value="MEDIUM">MEDIUM</option>
                  <option value="LOW">LOW</option>
                  <option value="INFO">INFO</option>
                </select>
              </div>

              {(riskStatusFilter || riskSeverityFilter) && (
                <button
                  onClick={() => {
                    setRiskStatusFilter('');
                    setRiskSeverityFilter('');
                  }}
                  className="text-xs text-indigo-600 hover:text-indigo-800 font-medium"
                >
                  Clear Filters
                </button>
              )}
            </div>

            {/* Risk Signals Table */}
            <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-slate-600">
                  <thead className="bg-slate-50 text-xs font-semibold uppercase text-slate-500 border-b border-slate-200">
                    <tr>
                      <th className="px-6 py-3">Detected</th>
                      <th className="px-6 py-3">Signal Type</th>
                      <th className="px-6 py-3">Severity</th>
                      <th className="px-6 py-3">Subject</th>
                      <th className="px-6 py-3 text-center">Points</th>
                      <th className="px-6 py-3 text-center">Status</th>
                      <th className="px-6 py-3 text-right">Review Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {riskSignals.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="px-6 py-12 text-center text-slate-400">
                          <CheckCircle2 className="w-10 h-10 mx-auto mb-2 text-emerald-400" />
                          No risk signals matching the selected criteria.
                        </td>
                      </tr>
                    ) : (
                      riskSignals.map((sig) => (
                        <tr key={sig.id} className="hover:bg-slate-50/75 transition-colors">
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="font-mono text-xs text-slate-800">
                              {new Date(sig.detected_at).toLocaleString()}
                            </div>
                            <div className="text-[11px] text-slate-400">v{sig.rule_version}</div>
                          </td>
                          <td className="px-6 py-4">
                            <div className="font-semibold text-slate-900">{sig.signal_type}</div>
                            {sig.context && typeof sig.context === 'object' && (
                              <div className="text-xs text-slate-500 max-w-xs truncate">
                                {String(sig.context.reason || sig.context.rule || '')}
                              </div>
                            )}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            {getSeverityBadge(sig.severity)}
                          </td>
                          <td className="px-6 py-4">
                            <span className="font-mono text-xs text-slate-700">
                              {sig.subject_user_id
                                ? `${sig.subject_type}: ${sig.subject_user_id.slice(0, 8)}...`
                                : sig.subject_type}
                            </span>
                          </td>
                          <td className="px-6 py-4 text-center font-bold text-slate-800">
                            {sig.risk_points ?? '-'}
                          </td>
                          <td className="px-6 py-4 text-center whitespace-nowrap">
                            {getStatusBadge(sig.status)}
                          </td>
                          <td className="px-6 py-4 text-right whitespace-nowrap">
                            <div className="flex items-center justify-end gap-2">
                              <button
                                onClick={() => setSelectedSignal(sig)}
                                className="p-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                                title="Inspect Context Details"
                              >
                                <Eye className="w-4 h-4" />
                              </button>

                              {sig.status === 'OPEN' && (
                                <button
                                  onClick={() => handleAcknowledgeSignal(sig.id)}
                                  className="px-2.5 py-1 text-xs font-semibold rounded-lg bg-amber-50 text-amber-700 border border-amber-200 hover:bg-amber-100"
                                >
                                  Ack
                                </button>
                              )}

                              {(sig.status === 'OPEN' || sig.status === 'ACKNOWLEDGED') && (
                                <>
                                  <button
                                    onClick={() => {
                                      setReviewModalSignal(sig);
                                      setReviewModalAction('RESOLVE');
                                      setReviewNote('');
                                    }}
                                    className="px-2.5 py-1 text-xs font-semibold rounded-lg bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100"
                                  >
                                    Resolve
                                  </button>
                                  <button
                                    onClick={() => {
                                      setReviewModalSignal(sig);
                                      setReviewModalAction('DISMISS');
                                      setReviewNote('');
                                    }}
                                    className="px-2.5 py-1 text-xs font-semibold rounded-lg bg-slate-100 text-slate-600 border border-slate-200 hover:bg-slate-200"
                                  >
                                    Dismiss
                                  </button>
                                </>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* ===================================================================== */}
        {/* TAB 3: RADIO ENVIRONMENT DIAGNOSTICS                                  */}
        {/* ===================================================================== */}
        {activeTab === 'radio' && (
          <div className="space-y-6">
            {/* Domain Invariant Disclaimer Banner */}
            <div className="rounded-xl border border-amber-200 bg-amber-50/70 p-4 text-sm text-amber-900 flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-amber-600 mt-0.5 shrink-0" />
              <div>
                <span className="font-semibold">Radio Diagnostics Invariant:</span> RSSI percentile
                metrics summarize classroom radio frequency distribution and receiver sensitivity.
                RF signal propagation is non-linear and affected by dynamic physical human occupancy
                and multipath reflection;{' '}
                <span className="font-bold underline">
                  raw RSSI values must never be converted or interpreted as geometric distance
                  metrics
                </span>
                .
              </div>
            </div>

            {/* Query Filter */}
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm flex flex-wrap items-center gap-4">
              <div className="flex-1 min-w-[240px]">
                <label className="block text-xs font-semibold text-slate-500 mb-1">
                  Filter by Attendance Session ID (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. 01a0ab8a-..."
                  value={radioSessionId}
                  onChange={(e) => setRadioSessionId(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-mono text-slate-800 shadow-sm focus:border-indigo-500 focus:outline-none"
                />
              </div>
              <div className="self-end">
                <button
                  onClick={loadData}
                  disabled={isLoading}
                  className="rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-indigo-700 disabled:opacity-50"
                >
                  Analyze Radio Environment
                </button>
              </div>
            </div>

            {/* Diagnostic Metrics Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    Observations
                  </span>
                  <Activity className="w-5 h-5 text-indigo-500" />
                </div>
                <p className="mt-2 text-3xl font-bold text-slate-900">
                  {radioSummary?.observation_count ?? 0}
                </p>
                <p className="mt-1 text-xs text-slate-500">Collected BLE RSSI samples</p>
              </div>

              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    Median RSSI
                  </span>
                  <Radio className="w-5 h-5 text-emerald-500" />
                </div>
                <p className="mt-2 text-3xl font-bold text-emerald-600">
                  {radioSummary?.median_rssi !== null && radioSummary?.median_rssi !== undefined
                    ? `${radioSummary.median_rssi} dBm`
                    : 'N/A'}
                </p>
                <p className="mt-1 text-xs text-slate-500">50th percentile signal baseline</p>
              </div>

              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    Interquartile Span (P25 - P75)
                  </span>
                  <Layers className="w-5 h-5 text-blue-500" />
                </div>
                <p className="mt-2 text-2xl font-bold text-blue-600">
                  {radioSummary?.p25_rssi !== null && radioSummary?.p75_rssi !== null
                    ? `${radioSummary?.p25_rssi} to ${radioSummary?.p75_rssi} dBm`
                    : 'N/A'}
                </p>
                <p className="mt-1 text-xs text-slate-500">Core 50% signal dispersion</p>
              </div>

              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    Signal Extrema
                  </span>
                  <Activity className="w-5 h-5 text-amber-500" />
                </div>
                <p className="mt-2 text-2xl font-bold text-amber-600">
                  {radioSummary?.min_rssi !== null && radioSummary?.max_rssi !== null
                    ? `${radioSummary?.min_rssi} / ${radioSummary?.max_rssi} dBm`
                    : 'N/A'}
                </p>
                <p className="mt-1 text-xs text-slate-500">Min (Weakest) / Max (Strongest)</p>
              </div>
            </div>

            {/* Percentile Breakdown Grid */}
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm space-y-6">
              <h3 className="text-base font-semibold text-slate-900">
                Classroom BLE RSSI Distribution Percentiles
              </h3>

              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3 text-center">
                <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                  <span className="text-xs font-semibold text-slate-500">P10 (Weak Edge)</span>
                  <p className="mt-1 text-lg font-bold text-slate-800">
                    {radioSummary?.p10_rssi ? `${radioSummary.p10_rssi} dBm` : '-'}
                  </p>
                </div>
                <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                  <span className="text-xs font-semibold text-slate-500">P25 (Q1)</span>
                  <p className="mt-1 text-lg font-bold text-slate-800">
                    {radioSummary?.p25_rssi ? `${radioSummary.p25_rssi} dBm` : '-'}
                  </p>
                </div>
                <div className="p-3 bg-indigo-50 rounded-lg border border-indigo-200">
                  <span className="text-xs font-semibold text-indigo-700">P50 (Median)</span>
                  <p className="mt-1 text-lg font-bold text-indigo-900">
                    {radioSummary?.median_rssi ? `${radioSummary.median_rssi} dBm` : '-'}
                  </p>
                </div>
                <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                  <span className="text-xs font-semibold text-slate-500">P75 (Q3)</span>
                  <p className="mt-1 text-lg font-bold text-slate-800">
                    {radioSummary?.p75_rssi ? `${radioSummary.p75_rssi} dBm` : '-'}
                  </p>
                </div>
                <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                  <span className="text-xs font-semibold text-slate-500">P90 (Strong Edge)</span>
                  <p className="mt-1 text-lg font-bold text-slate-800">
                    {radioSummary?.p90_rssi ? `${radioSummary.p90_rssi} dBm` : '-'}
                  </p>
                </div>
                <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                  <span className="text-xs font-semibold text-slate-500">Max (Peak)</span>
                  <p className="mt-1 text-lg font-bold text-slate-800">
                    {radioSummary?.max_rssi ? `${radioSummary.max_rssi} dBm` : '-'}
                  </p>
                </div>
              </div>

              <div className="border-t border-slate-200 pt-4 flex flex-col sm:flex-row items-start sm:items-center justify-between text-xs text-slate-500 gap-2">
                <div>
                  Diagnostic calculated at:{' '}
                  {radioSummary?.computed_at
                    ? new Date(radioSummary.computed_at).toLocaleString()
                    : 'Not computed'}
                </div>
                <div className="flex items-center gap-4 font-mono">
                  <span className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" /> Strong (&gt; -65
                    dBm)
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-amber-500" /> Fair (-65 to -80
                    dBm)
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-rose-500" /> Weak (&lt; -80 dBm)
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ======================================================================= */}
      {/* MODAL: CREATE CAMPUS NETWORK ZONE                                       */}
      {/* ======================================================================= */}
      {showCreateZoneModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl space-y-5">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <h3 className="text-lg font-bold text-slate-900">Create Campus Network Zone</h3>
              <button
                onClick={() => setShowCreateZoneModal(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateZone} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Zone Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Science Building Wi-Fi Subnet"
                  value={newZoneName}
                  onChange={(e) => setNewZoneName(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-800 focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Zone Code *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. SCI_WIFI_01"
                    value={newZoneCode}
                    onChange={(e) => setNewZoneCode(e.target.value)}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm font-mono uppercase text-slate-800 focus:border-indigo-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Network CIDR *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. 10.10.0.0/16 or 2001:db8::/32"
                    value={newZoneCidr}
                    onChange={(e) => setNewZoneCidr(e.target.value)}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm font-mono text-slate-800 focus:border-indigo-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Zone Type
                  </label>
                  <select
                    value={newZoneType}
                    onChange={(e) => setNewZoneType(e.target.value)}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-800 focus:border-indigo-500 focus:outline-none"
                  >
                    <option value="CAMPUS_TRUSTED">CAMPUS_TRUSTED</option>
                    <option value="CLASSROOM_HOTSPOT">CLASSROOM_HOTSPOT</option>
                    <option value="FACULTY_OFFICE">FACULTY_OFFICE</option>
                    <option value="RESIDENCE_HALL">RESIDENCE_HALL</option>
                    <option value="VPN_REMOTE_ACCESS">VPN_REMOTE_ACCESS</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Priority (0 - 1000)
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="1000"
                    value={newZonePriority}
                    onChange={(e) => setNewZonePriority(Number(e.target.value))}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-800 focus:border-indigo-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="allowStudent"
                  checked={newZoneAllowStudents}
                  onChange={(e) => setNewZoneAllowStudents(e.target.checked)}
                  className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                />
                <label htmlFor="allowStudent" className="text-xs font-medium text-slate-700">
                  Allow Student Attendance Presence Proofs from this Subnet
                </label>
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setShowCreateZoneModal(false)}
                  className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingZone}
                  className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
                >
                  {isSubmittingZone ? 'Creating...' : 'Create Network Zone'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ======================================================================= */}
      {/* MODAL: RISK SIGNAL DETAIL INSPECTION                                    */}
      {/* ======================================================================= */}
      {selectedSignal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-2xl rounded-2xl bg-white p-6 shadow-xl space-y-5 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <div>
                <h3 className="text-lg font-bold text-slate-900">
                  Anti-Cheat Signal: {selectedSignal.signal_type}
                </h3>
                <p className="text-xs text-slate-500 font-mono">ID: {selectedSignal.id}</p>
              </div>
              <button
                onClick={() => setSelectedSignal(null)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="grid grid-cols-2 gap-4 text-sm">
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                <span className="text-xs font-semibold text-slate-500">Severity</span>
                <div className="mt-1">{getSeverityBadge(selectedSignal.severity)}</div>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                <span className="text-xs font-semibold text-slate-500">Status</span>
                <div className="mt-1">{getStatusBadge(selectedSignal.status)}</div>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                <span className="text-xs font-semibold text-slate-500">Detected At</span>
                <div className="mt-1 font-mono text-xs text-slate-800">
                  {new Date(selectedSignal.detected_at).toLocaleString()}
                </div>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                <span className="text-xs font-semibold text-slate-500">Risk Points</span>
                <div className="mt-1 font-bold text-slate-800">
                  {selectedSignal.risk_points ?? 'N/A'}
                </div>
              </div>
            </div>

            {/* Context & Telemetry Breakdown */}
            <div>
              <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                Factor Context & Raw Telemetry
              </h4>
              <pre className="p-4 rounded-xl bg-slate-900 text-emerald-400 font-mono text-xs overflow-x-auto">
                {JSON.stringify(selectedSignal.context || {}, null, 2)}
              </pre>
            </div>

            {selectedSignal.review_note && (
              <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-sm">
                <span className="font-semibold text-amber-900">Review Note Explanation:</span>
                <p className="mt-1 text-amber-800">{selectedSignal.review_note}</p>
                {selectedSignal.reviewed_at && (
                  <p className="mt-2 text-xs text-amber-600 font-mono">
                    Reviewed: {new Date(selectedSignal.reviewed_at).toLocaleString()}
                  </p>
                )}
              </div>
            )}

            <div className="flex justify-end pt-2 border-t border-slate-200">
              <button
                onClick={() => setSelectedSignal(null)}
                className="rounded-lg bg-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-300"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ======================================================================= */}
      {/* MODAL: REVIEW (RESOLVE / DISMISS) WITH MANDATORY NOTE                  */}
      {/* ======================================================================= */}
      {reviewModalSignal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <h3 className="text-lg font-bold text-slate-900">
                {reviewModalAction === 'RESOLVE'
                  ? 'Resolve Anti-Cheat Signal'
                  : 'Dismiss False Positive'}
              </h3>
              <button
                onClick={() => setReviewModalSignal(null)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-slate-600">
              Governance policy requires an explicit review note justifying this decision. The
              action will be permanently attributed to your reviewer credentials in the immutable
              audit ledger.
            </p>

            <form onSubmit={handleReviewSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Justification / Review Note *
                </label>
                <textarea
                  required
                  rows={4}
                  placeholder={
                    reviewModalAction === 'RESOLVE'
                      ? 'e.g. Verified legitimate classroom presence via instructor logs and room Wi-Fi telemetry.'
                      : 'e.g. Student network reported VPN disconnect transient false positive.'
                  }
                  value={reviewNote}
                  onChange={(e) => setReviewNote(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 p-3 text-sm text-slate-800 focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setReviewModalSignal(null)}
                  className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingReview}
                  className={`rounded-lg px-4 py-2 text-sm font-semibold text-white disabled:opacity-50 ${
                    reviewModalAction === 'RESOLVE'
                      ? 'bg-emerald-600 hover:bg-emerald-700'
                      : 'bg-slate-700 hover:bg-slate-800'
                  }`}
                >
                  {isSubmittingReview
                    ? 'Recording...'
                    : reviewModalAction === 'RESOLVE'
                      ? 'Confirm Resolution'
                      : 'Confirm Dismissal'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
