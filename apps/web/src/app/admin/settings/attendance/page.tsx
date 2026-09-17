'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Sliders,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  Clock,
  RefreshCw,
  Save,
  HelpCircle,
  History,
  Lock,
} from 'lucide-react';

interface AttendancePolicy {
  id: string;
  name: string;
  scope_type: string;
  min_attendance_percentage: number;
  late_threshold_minutes: number;
  lecturer_correction_window_hours: number;
  required_checkpoint_count: number;
  checkpoint_duration_seconds: number;
  token_rotation_seconds: number;
  network_presence_mode: string;
  lecturer_network_presence_mode: string;
  allow_university_wide_zones: boolean;
  created_at: string;
}

export default function AttendancePolicySettingsPage() {
  const [policies, setPolicies] = useState<AttendancePolicy[]>([]);
  const [selectedPolicyId, setSelectedPolicyId] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSaving, setIsSaving] = useState<boolean>(false);

  // Form inputs
  const [policyName, setPolicyName] = useState<string>('Institutional Standard Policy');
  const [minPercentage, setMinPercentage] = useState<number>(75.0);
  const [lateMinutes, setLateMinutes] = useState<number>(10);
  const [correctionHours, setCorrectionHours] = useState<number>(24);
  const [checkpointsCount, setCheckpointsCount] = useState<number>(3);
  const [checkpointDuration, setCheckpointDuration] = useState<number>(300);
  const [tokenRotation, setTokenRotation] = useState<number>(30);
  const [networkPresenceMode, setNetworkPresenceMode] = useState<string>('DISABLED');
  const [lecturerNetworkMode, setLecturerNetworkMode] = useState<string>('DISABLED');
  const [allowUniWideZones, setAllowUniWideZones] = useState<boolean>(true);

  // Mandatory Audit Justification
  const [auditJustification, setAuditJustification] = useState<string>('');

  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';

  const getAuthHeaders = useCallback((): HeadersInit => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') || localStorage.getItem('access_token') : null;
    return {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      'Content-Type': 'application/json',
      Accept: 'application/json',
    };
  }, []);

  const fetchPolicies = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await fetch(`${apiBaseUrl}/attendance/policies`, {
        headers: getAuthHeaders(),
      });
      if (res.ok) {
        const json = await res.json();
        const items = json.data?.items || json.data || [];
        setPolicies(items);
        if (items.length > 0) {
          const current = items[0];
          setSelectedPolicyId(current.id);
          setPolicyName(current.name);
          setMinPercentage(current.min_attendance_percentage);
          setLateMinutes(current.late_threshold_minutes);
          setCorrectionHours(current.lecturer_correction_window_hours);
          setCheckpointsCount(current.required_checkpoint_count);
          setCheckpointDuration(current.checkpoint_duration_seconds);
          setTokenRotation(current.token_rotation_seconds);
          setNetworkPresenceMode(current.network_presence_mode || 'DISABLED');
          setLecturerNetworkMode(current.lecturer_network_presence_mode || 'DISABLED');
          setAllowUniWideZones(current.allow_university_wide_zones ?? true);
        }
      }
    } catch {
      // Ignore initial network errors
    } finally {
      setIsLoading(false);
    }
  }, [apiBaseUrl, getAuthHeaders]);

  useEffect(() => {
    let ignore = false;
    async function loadInitial() {
      try {
        const res = await fetch(`${apiBaseUrl}/attendance/policies`, {
          headers: getAuthHeaders(),
        });
        if (res.ok && !ignore) {
          const json = await res.json();
          const items = json.data?.items || json.data || [];
          setPolicies(items);
          if (items.length > 0) {
            const current = items[0];
            setSelectedPolicyId(current.id);
            setPolicyName(current.name);
            setMinPercentage(current.min_attendance_percentage);
            setLateMinutes(current.late_threshold_minutes);
            setCorrectionHours(current.lecturer_correction_window_hours);
            setCheckpointsCount(current.required_checkpoint_count);
            setCheckpointDuration(current.checkpoint_duration_seconds);
            setTokenRotation(current.token_rotation_seconds);
            setNetworkPresenceMode(current.network_presence_mode || 'DISABLED');
            setLecturerNetworkMode(current.lecturer_network_presence_mode || 'DISABLED');
            setAllowUniWideZones(current.allow_university_wide_zones ?? true);
          }
        }
      } catch {
        // Ignore initial
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    }
    loadInitial();
    return () => {
      ignore = true;
    };
  }, [apiBaseUrl, getAuthHeaders]);

  const handleSavePolicy = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!auditJustification.trim()) {
      setStatusMessage({
        type: 'error',
        text: 'A non-empty audit justification is required to modify institutional attendance policies.',
      });
      return;
    }

    setIsSaving(true);
    setStatusMessage(null);

    const payload = {
      name: policyName,
      scope_type: 'UNIVERSITY',
      min_attendance_percentage: Number(minPercentage),
      late_threshold_minutes: Number(lateMinutes),
      lecturer_correction_window_hours: Number(correctionHours),
      required_checkpoint_count: Number(checkpointsCount),
      checkpoint_duration_seconds: Number(checkpointDuration),
      token_rotation_seconds: Number(tokenRotation),
      network_presence_mode: networkPresenceMode,
      lecturer_network_presence_mode: lecturerNetworkMode,
      allow_university_wide_zones: allowUniWideZones,
      audit_justification: auditJustification.trim(),
    };

    try {
      const res = await fetch(`${apiBaseUrl}/attendance/policies`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(payload),
      });

      const json = await res.json();
      if (res.ok) {
        setStatusMessage({
          type: 'success',
          text: 'Institutional attendance policy updated and prospectively activated. Recorded in audit ledger.',
        });
        setAuditJustification('');
        fetchPolicies();
      } else {
        setStatusMessage({
          type: 'error',
          text: json.detail || json.message || 'Failed to update policy.',
        });
      }
    } catch {
      setStatusMessage({
        type: 'error',
        text: 'Error connecting to policy management service.',
      });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
              <Sliders className="h-7 w-7 text-indigo-600" />
              Institutional Attendance Policy Configuration
            </h1>
            <p className="text-sm text-slate-600 mt-1">
              Configure baseline minimum threshold, checkpoint frequencies, and operational review windows.
            </p>
          </div>
        </div>

        {/* Prospective Application Invariant Alert */}
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4.5 text-amber-900 flex items-start gap-3 shadow-sm">
          <AlertTriangle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
          <div className="text-xs space-y-1">
            <p className="font-bold text-sm">Prospective Application Invariant (INV-06, ADR-011)</p>
            <p className="text-amber-800">
              Policy threshold and checkpoint configurations apply <span className="font-semibold">prospectively</span> to future sessions and new evaluations. Closed sessions, past student attendance records, and immutable audit logs remain strictly preserved and unaffected.
            </p>
          </div>
        </div>

        {/* Status Alerts */}
        {statusMessage && (
          <div
            className={`p-4 rounded-lg flex items-center gap-2 border shadow-sm ${
              statusMessage.type === 'success'
                ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                : 'bg-rose-50 border-rose-200 text-rose-800'
            }`}
          >
            {statusMessage.type === 'success' ? (
              <CheckCircle2 className="h-5 w-5 text-emerald-600" />
            ) : (
              <AlertTriangle className="h-5 w-5 text-rose-600" />
            )}
            <span className="text-xs font-semibold">{statusMessage.text}</span>
          </div>
        )}

        {/* Policy Configuration Form */}
        <form onSubmit={handleSavePolicy} className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-6">
          <div className="border-b border-slate-100 pb-4">
            <h2 className="text-base font-semibold text-slate-900">Institutional Baseline Rules</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              These settings serve as university-wide defaults unless overridden by course-specific policies.
            </p>
          </div>

          <div className="space-y-4">
            {/* Policy Name */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Policy Display Name
              </label>
              <input
                type="text"
                value={policyName}
                onChange={(e) => setPolicyName(e.target.value)}
                required
                className="w-full text-xs border border-slate-300 rounded-lg p-2.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            {/* Threshold & Margin */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Minimum Attendance Threshold (%)
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    min="0"
                    max="100"
                    step="0.5"
                    value={minPercentage}
                    onChange={(e) => setMinPercentage(parseFloat(e.target.value) || 0)}
                    required
                    className="w-full text-xs border border-slate-300 rounded-lg p-2.5 font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                  <span className="text-xs font-bold text-slate-500">%</span>
                </div>
                <p className="text-[11px] text-slate-400 mt-1">
                  Default institutional threshold is 75.0%. Values range from 0.0% to 100.0%.
                </p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Near-Threshold Informative Margin (%)
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    value={5.0}
                    disabled
                    className="w-full text-xs border border-slate-200 bg-slate-100 rounded-lg p-2.5 font-mono text-slate-600 cursor-not-allowed"
                  />
                  <span className="text-xs font-bold text-slate-400">%</span>
                </div>
                <p className="text-[11px] text-slate-400 mt-1">
                  Warning margin: students within {(minPercentage - 5.0).toFixed(1)}% – {(minPercentage - 0.1).toFixed(1)}% are tagged as Near Threshold.
                </p>
              </div>
            </div>

            {/* Operational Windows */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Late Arrival Margin (Minutes)
                </label>
                <input
                  type="number"
                  min="0"
                  max="120"
                  value={lateMinutes}
                  onChange={(e) => setLateMinutes(parseInt(e.target.value, 10) || 0)}
                  className="w-full text-xs border border-slate-300 rounded-lg p-2.5 font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Correction Window (Hours)
                </label>
                <input
                  type="number"
                  min="1"
                  max="720"
                  value={correctionHours}
                  onChange={(e) => setCorrectionHours(parseInt(e.target.value, 10) || 0)}
                  className="w-full text-xs border border-slate-300 rounded-lg p-2.5 font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Required Checkpoints Count
                </label>
                <select
                  value={checkpointsCount}
                  onChange={(e) => setCheckpointsCount(parseInt(e.target.value, 10))}
                  className="w-full text-xs border border-slate-300 rounded-lg p-2.5 bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value={1}>1 Checkpoint (START only)</option>
                  <option value={2}>2 Checkpoints (START & END)</option>
                  <option value={3}>3 Checkpoints (START, MIDDLE, END)</option>
                </select>
              </div>
            </div>

            {/* Checkpoint Durations & Token Rotation */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Checkpoint Active Duration (Seconds)
                </label>
                <input
                  type="number"
                  min="60"
                  max="3600"
                  value={checkpointDuration}
                  onChange={(e) => setCheckpointDuration(parseInt(e.target.value, 10) || 60)}
                  className="w-full text-xs border border-slate-300 rounded-lg p-2.5 font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
                <p className="text-[11px] text-slate-400 mt-1">Default: 300 seconds (5 minutes).</p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  QR Token Rotation Window (Seconds)
                </label>
                <input
                  type="number"
                  min="10"
                  max="120"
                  value={tokenRotation}
                  onChange={(e) => setTokenRotation(parseInt(e.target.value, 10) || 30)}
                  className="w-full text-xs border border-slate-300 rounded-lg p-2.5 font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
                <p className="text-[11px] text-slate-400 mt-1">Standard rotation: 30s (±1 step tolerance).</p>
              </div>
            </div>

            {/* Network Presence Mode */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Student Campus Presence Mode
                </label>
                <select
                  value={networkPresenceMode}
                  onChange={(e) => setNetworkPresenceMode(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded-lg p-2.5 bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="DISABLED">DISABLED (GPS/Network Proof Optional)</option>
                  <option value="AUDIT_ONLY">AUDIT_ONLY (Flag Anomaly, Do Not Block)</option>
                  <option value="ENFORCED">ENFORCED (Require Verified Network/Zone)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Lecturer Host Presence Mode
                </label>
                <select
                  value={lecturerNetworkMode}
                  onChange={(e) => setLecturerNetworkMode(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded-lg p-2.5 bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="DISABLED">DISABLED</option>
                  <option value="AUDIT_ONLY">AUDIT_ONLY</option>
                  <option value="ENFORCED">ENFORCED</option>
                </select>
              </div>
            </div>

            {/* Mandatory Audit Justification */}
            <div className="pt-2">
              <label className="block text-xs font-bold text-indigo-900 mb-1 flex items-center gap-1.5">
                <Lock className="h-3.5 w-3.5 text-indigo-600" />
                Mandatory Audit Justification
              </label>
              <textarea
                rows={2}
                value={auditJustification}
                onChange={(e) => setAuditJustification(e.target.value)}
                placeholder="State the institutional reason or academic committee approval for modifying this attendance policy..."
                required
                className="w-full text-xs border border-indigo-200 rounded-lg p-2.5 bg-indigo-50/20 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
              <p className="text-[11px] text-slate-400 mt-1">
                Your user ID and justification are permanently recorded in the immutable audit ledger.
              </p>
            </div>
          </div>

          <div className="flex justify-end pt-4 border-t border-slate-100">
            <button
              type="submit"
              disabled={isSaving || !auditJustification.trim()}
              className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg shadow-sm transition-all disabled:opacity-50"
            >
              {isSaving ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  Saving & Auditing Policy...
                </>
              ) : (
                <>
                  <Save className="h-4 w-4" />
                  Save & Apply Prospectively
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
