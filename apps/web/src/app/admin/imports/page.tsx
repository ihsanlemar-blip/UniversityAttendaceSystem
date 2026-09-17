'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  UploadCloud,
  FileSpreadsheet,
  Download,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  RefreshCw,
  FileText,
  ArrowRight,
  ShieldAlert,
  History,
  Check,
  X,
} from 'lucide-react';

type ImportType = 'STUDENTS' | 'COURSES' | 'OFFERINGS' | 'ENROLLMENTS' | 'LECTURERS' | 'TIMETABLES';
type CommitMode = 'STRICT' | 'PARTIAL';

interface StagedRow {
  row_index: number;
  data: Record<string, any>;
  is_valid: boolean;
  errors?: Record<string, string[]>;
  warnings?: Record<string, string[]>;
}

interface ImportJob {
  id: string;
  university_id: string;
  import_type: ImportType;
  filename: string;
  status: 'PENDING' | 'VALIDATING' | 'PREVIEWED' | 'COMMITTED' | 'PARTIALLY_COMMITTED' | 'FAILED' | 'CANCELLED';
  commit_mode: CommitMode;
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  committed_rows: number;
  error_summary?: Record<string, any>;
  requested_at: string;
  completed_at?: string | null;
}

interface ImportPreview {
  job: ImportJob;
  headers: string[];
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  warning_rows: number;
  sample_rows: StagedRow[];
}

const IMPORT_TYPES: { type: ImportType; label: string; description: string }[] = [
  { type: 'STUDENTS', label: 'Students', description: 'Student profiles, admission dates, numbers' },
  { type: 'COURSES', label: 'Courses', description: 'Curriculum catalog, codes, names, credits' },
  { type: 'OFFERINGS', label: 'Course Offerings', description: 'Semester and section course allocations' },
  { type: 'ENROLLMENTS', label: 'Rosters & Enrollments', description: 'Student enrollments into course offerings' },
  { type: 'LECTURERS', label: 'Lecturers', description: 'Faculty instructors and employee codes' },
  { type: 'TIMETABLES', label: 'Timetables', description: 'Weekly schedules, rooms, recurring timeslots' },
];

export default function DataImportCenterPage() {
  const [selectedType, setSelectedType] = useState<ImportType>('STUDENTS');
  const [commitMode, setCommitMode] = useState<CommitMode>('STRICT');
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [history, setHistory] = useState<ImportJob[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState<boolean>(true);
  const [actionMessage, setActionMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [isCommitting, setIsCommitting] = useState<boolean>(false);

  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';

  const getAuthHeaders = useCallback((): HeadersInit => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') || localStorage.getItem('access_token') : null;
    return {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      Accept: 'application/json',
    };
  }, []);

  const fetchHistory = useCallback(async () => {
    setIsLoadingHistory(true);
    try {
      const res = await fetch(`${apiBaseUrl}/imports/history?page=1&page_size=20`, {
        headers: getAuthHeaders(),
      });
      if (res.ok) {
        const json = await res.json();
        setHistory(json.data?.items || []);
      }
    } catch {
      // Ignore network errors on refresh
    } finally {
      setIsLoadingHistory(false);
    }
  }, [apiBaseUrl, getAuthHeaders]);

  useEffect(() => {
    let ignore = false;
    async function loadInitial() {
      try {
        const res = await fetch(`${apiBaseUrl}/imports/history?page=1&page_size=20`, {
          headers: getAuthHeaders(),
        });
        if (res.ok && !ignore) {
          const json = await res.json();
          setHistory(json.data?.items || []);
        }
      } catch {
        // Ignore
      } finally {
        if (!ignore) {
          setIsLoadingHistory(false);
        }
      }
    }
    loadInitial();
    return () => {
      ignore = true;
    };
  }, [apiBaseUrl, getAuthHeaders]);

  const handleDownloadTemplate = async (format: 'CSV' | 'XLSX') => {
    try {
      const url = `${apiBaseUrl}/imports/template/${selectedType}?format=${format}`;
      window.open(url, '_blank');
    } catch {
      setActionMessage({ type: 'error', text: 'Failed to download template.' });
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setPreview(null);
      setActionMessage(null);
    }
  };

  const handleStageAndPreview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setActionMessage({ type: 'error', text: 'Please select a CSV or XLSX spreadsheet file.' });
      return;
    }

    setIsUploading(true);
    setActionMessage(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('import_type', selectedType);
    formData.append('commit_mode', commitMode);

    try {
      const res = await fetch(`${apiBaseUrl}/imports/preview`, {
        method: 'POST',
        headers: {
          ...(typeof window !== 'undefined' && localStorage.getItem('token')
            ? { Authorization: `Bearer ${localStorage.getItem('token')}` }
            : {}),
        },
        body: formData,
      });

      const json = await res.json();
      if (res.ok && json.data) {
        setPreview(json.data);
        setActionMessage({
          type: 'success',
          text: `File staged successfully. ${json.data.valid_rows} valid, ${json.data.invalid_rows} invalid rows detected.`,
        });
        fetchHistory();
      } else {
        setActionMessage({
          type: 'error',
          text: json.detail || json.message || 'Validation failed. Check row formatting.',
        });
      }
    } catch {
      setActionMessage({ type: 'error', text: 'Error connecting to server for import staging.' });
    } finally {
      setIsUploading(false);
    }
  };

  const handleCommit = async (mode: CommitMode) => {
    if (!preview?.job?.id) return;
    setIsCommitting(true);
    setActionMessage(null);

    try {
      const res = await fetch(`${apiBaseUrl}/imports/${preview.job.id}/commit`, {
        method: 'POST',
        headers: {
          ...getAuthHeaders(),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ commit_mode: mode }),
      });

      const json = await res.json();
      if (res.ok) {
        setActionMessage({
          type: 'success',
          text: `Import committed successfully! ${json.data?.committed_rows || 0} production records created/updated.`,
        });
        setPreview(null);
        setFile(null);
        fetchHistory();
      } else {
        setActionMessage({
          type: 'error',
          text: json.detail || json.message || 'Failed to commit import.',
        });
      }
    } catch {
      setActionMessage({ type: 'error', text: 'Failed to communicate with import engine.' });
    } finally {
      setIsCommitting(false);
    }
  };

  const handleCancel = async () => {
    if (!preview?.job?.id) return;
    try {
      await fetch(`${apiBaseUrl}/imports/${preview.job.id}/cancel`, {
        method: 'POST',
        headers: getAuthHeaders(),
      });
      setPreview(null);
      setFile(null);
      setActionMessage({ type: 'success', text: 'Staged import session cancelled.' });
      fetchHistory();
    } catch {
      setActionMessage({ type: 'error', text: 'Failed to cancel staged import.' });
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
              <UploadCloud className="h-7 w-7 text-indigo-600" />
              Institutional Data Import Center
            </h1>
            <p className="text-sm text-slate-600 mt-1">
              Upload, pre-validate, preview, and atomically commit institutional academic datasets.
            </p>
          </div>
          <button
            onClick={fetchHistory}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-white border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 transition-colors shadow-sm"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh History
          </button>
        </div>

        {/* Action Alerts */}
        {actionMessage && (
          <div
            className={`p-4 rounded-lg flex items-center justify-between shadow-sm border ${
              actionMessage.type === 'success'
                ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                : 'bg-rose-50 border-rose-200 text-rose-800'
            }`}
          >
            <div className="flex items-center gap-2">
              {actionMessage.type === 'success' ? (
                <CheckCircle2 className="h-5 w-5 text-emerald-600" />
              ) : (
                <XCircle className="h-5 w-5 text-rose-600" />
              )}
              <span className="font-medium text-sm">{actionMessage.text}</span>
            </div>
            <button
              onClick={() => setActionMessage(null)}
              className="text-slate-400 hover:text-slate-600"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        {/* Entity Selector Tabs */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {IMPORT_TYPES.map((item) => {
            const isSelected = selectedType === item.type;
            return (
              <button
                key={item.type}
                type="button"
                onClick={() => {
                  setSelectedType(item.type);
                  setPreview(null);
                }}
                className={`text-left p-3.5 rounded-xl border transition-all ${
                  isSelected
                    ? 'border-indigo-600 bg-indigo-50/50 shadow-sm ring-2 ring-indigo-500/20'
                    : 'border-slate-200 bg-white hover:border-slate-300'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className={`text-sm font-semibold ${isSelected ? 'text-indigo-900' : 'text-slate-800'}`}>
                    {item.label}
                  </span>
                  {isSelected && <Check className="h-4 w-4 text-indigo-600" />}
                </div>
                <p className="text-xs text-slate-500 line-clamp-2">{item.description}</p>
              </button>
            );
          })}
        </div>

        {/* Staging & Upload Card */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-100">
            <div>
              <h2 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
                <FileSpreadsheet className="h-5 w-5 text-indigo-600" />
                Upload Dataset for {IMPORT_TYPES.find((t) => t.type === selectedType)?.label}
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Always download and inspect the official template before uploading custom files.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => handleDownloadTemplate('CSV')}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-colors"
              >
                <Download className="h-3.5 w-3.5" />
                Template (CSV)
              </button>
              <button
                type="button"
                onClick={() => handleDownloadTemplate('XLSX')}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-colors"
              >
                <Download className="h-3.5 w-3.5" />
                Template (Excel)
              </button>
            </div>
          </div>

          <form onSubmit={handleStageAndPreview} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1.5">
                  Select CSV or XLSX File
                </label>
                <input
                  type="file"
                  accept=".csv, .xlsx"
                  onChange={handleFileChange}
                  className="block w-full text-xs text-slate-500 file:mr-3 file:py-2 file:px-3.5 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 border border-slate-300 rounded-lg cursor-pointer bg-slate-50 p-1"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1.5">
                  Validation Commitment Mode
                </label>
                <select
                  value={commitMode}
                  onChange={(e) => setCommitMode(e.target.value as CommitMode)}
                  className="w-full text-xs border border-slate-300 rounded-lg p-2.5 bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="STRICT">STRICT — Entire batch fails if any row is invalid (Default)</option>
                  <option value="PARTIAL">PARTIAL — Valid rows commit, invalid rows staged for review</option>
                </select>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                type="submit"
                disabled={!file || isUploading}
                className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg shadow-sm transition-all disabled:opacity-50"
              >
                {isUploading ? (
                  <>
                    <RefreshCw className="h-4 w-4 animate-spin" />
                    Validating Dataset...
                  </>
                ) : (
                  <>
                    <ArrowRight className="h-4 w-4" />
                    Stage & Validate Dataset
                  </>
                )}
              </button>
            </div>
          </form>
        </div>

        {/* Validation Preview Section */}
        {preview && (
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-6">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
              <div>
                <h3 className="text-base font-semibold text-slate-900 flex items-center gap-2">
                  <FileText className="h-5 w-5 text-indigo-600" />
                  Staging & Validation Summary
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Inspect row status and validation flags before committing data into the system.
                </p>
              </div>
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={handleCancel}
                  className="px-3 py-1.5 text-xs font-medium bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-colors"
                >
                  Discard
                </button>
                {commitMode === 'PARTIAL' && preview.valid_rows > 0 && (
                  <button
                    type="button"
                    disabled={isCommitting}
                    onClick={() => handleCommit('PARTIAL')}
                    className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold bg-amber-600 hover:bg-amber-700 text-white rounded-lg transition-colors shadow-sm disabled:opacity-50"
                  >
                    Commit Valid Rows ({preview.valid_rows})
                  </button>
                )}
                <button
                  type="button"
                  disabled={preview.invalid_rows > 0 || isCommitting}
                  onClick={() => handleCommit('STRICT')}
                  className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg transition-colors shadow-sm disabled:opacity-50"
                >
                  {isCommitting ? 'Committing...' : `Commit Entire Dataset (${preview.total_rows})`}
                </button>
              </div>
            </div>

            {/* Metric KPI Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-3.5">
                <span className="text-xs text-slate-500 font-medium">Total Rows</span>
                <p className="text-xl font-bold text-slate-900 mt-1">{preview.total_rows}</p>
              </div>
              <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3.5">
                <span className="text-xs text-emerald-700 font-medium">Valid Rows</span>
                <p className="text-xl font-bold text-emerald-800 mt-1">{preview.valid_rows}</p>
              </div>
              <div className={`rounded-lg p-3.5 border ${preview.invalid_rows > 0 ? 'bg-rose-50 border-rose-200' : 'bg-slate-50 border-slate-200'}`}>
                <span className={`text-xs font-medium ${preview.invalid_rows > 0 ? 'text-rose-700' : 'text-slate-500'}`}>Invalid Rows</span>
                <p className={`text-xl font-bold mt-1 ${preview.invalid_rows > 0 ? 'text-rose-800' : 'text-slate-900'}`}>{preview.invalid_rows}</p>
              </div>
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-3.5">
                <span className="text-xs text-amber-700 font-medium">Warning Rows</span>
                <p className="text-xl font-bold text-amber-800 mt-1">{preview.warning_rows}</p>
              </div>
            </div>

            {/* Staged Rows Sample Table */}
            <div className="space-y-2">
              <h4 className="text-xs font-semibold text-slate-700 uppercase tracking-wider">
                Staged Row Preview (First {preview.sample_rows.length} Rows)
              </h4>
              <div className="overflow-x-auto border border-slate-200 rounded-lg max-h-96">
                <table className="w-full text-left text-xs text-slate-600">
                  <thead className="bg-slate-100 text-slate-700 font-semibold border-b border-slate-200 sticky top-0">
                    <tr>
                      <th className="p-2.5 w-16">Row #</th>
                      <th className="p-2.5 w-24">Status</th>
                      <th className="p-2.5">Errors / Warnings</th>
                      <th className="p-2.5">Data Content</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {preview.sample_rows.map((r) => (
                      <tr key={r.row_index} className={r.is_valid ? 'hover:bg-slate-50' : 'bg-rose-50/40 hover:bg-rose-50/70'}>
                        <td className="p-2.5 font-mono text-slate-500">{r.row_index}</td>
                        <td className="p-2.5">
                          {r.is_valid ? (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
                              <CheckCircle2 className="h-3 w-3" />
                              Valid
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-800">
                              <XCircle className="h-3 w-3" />
                              Error
                            </span>
                          )}
                        </td>
                        <td className="p-2.5">
                          {r.errors && Object.keys(r.errors).length > 0 ? (
                            <div className="space-y-0.5">
                              {Object.entries(r.errors).map(([field, msgs]) => (
                                <p key={field} className="text-rose-700 font-medium">
                                  <span className="font-semibold">{field}:</span> {msgs.join(', ')}
                                </p>
                              ))}
                            </div>
                          ) : r.warnings && Object.keys(r.warnings).length > 0 ? (
                            <div className="space-y-0.5">
                              {Object.entries(r.warnings).map(([field, msgs]) => (
                                <p key={field} className="text-amber-700 font-medium">
                                  <span className="font-semibold">{field}:</span> {msgs.join(', ')}
                                </p>
                              ))}
                            </div>
                          ) : (
                            <span className="text-slate-400 italic">No validation issues</span>
                          )}
                        </td>
                        <td className="p-2.5 font-mono text-slate-700 max-w-xs truncate">
                          {JSON.stringify(r.data)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* History Table */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-semibold text-slate-900 flex items-center gap-2">
                <History className="h-5 w-5 text-indigo-600" />
                Recent Import History
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Audit trail of historical dataset uploads, validation runs, and commit outcomes.
              </p>
            </div>
          </div>

          <div className="overflow-x-auto border border-slate-200 rounded-lg">
            <table className="w-full text-left text-xs text-slate-600">
              <thead className="bg-slate-100 text-slate-700 font-semibold border-b border-slate-200">
                <tr>
                  <th className="p-3">Import Job</th>
                  <th className="p-3">Type</th>
                  <th className="p-3">Mode</th>
                  <th className="p-3">Status</th>
                  <th className="p-3">Rows (Total / Valid / Invalid / Committed)</th>
                  <th className="p-3">Requested At</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {isLoadingHistory ? (
                  <tr>
                    <td colSpan={6} className="p-6 text-center text-slate-400">
                      Loading import history...
                    </td>
                  </tr>
                ) : history.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="p-6 text-center text-slate-400">
                      No import jobs on record for this university tenant.
                    </td>
                  </tr>
                ) : (
                  history.map((job) => (
                    <tr key={job.id} className="hover:bg-slate-50">
                      <td className="p-3 font-medium text-slate-800">
                        <div>{job.filename}</div>
                        <div className="text-slate-400 text-[10px] font-mono">{job.id}</div>
                      </td>
                      <td className="p-3 font-semibold text-slate-700">{job.import_type}</td>
                      <td className="p-3">
                        <span className="font-mono text-slate-600">{job.commit_mode}</span>
                      </td>
                      <td className="p-3">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${
                            job.status === 'COMMITTED'
                              ? 'bg-emerald-100 text-emerald-800'
                              : job.status === 'PARTIALLY_COMMITTED'
                              ? 'bg-amber-100 text-amber-800'
                              : job.status === 'FAILED'
                              ? 'bg-rose-100 text-rose-800'
                              : job.status === 'CANCELLED'
                              ? 'bg-slate-100 text-slate-700'
                              : 'bg-indigo-100 text-indigo-800'
                          }`}
                        >
                          {job.status}
                        </span>
                      </td>
                      <td className="p-3 font-mono">
                        {job.total_rows} / {job.valid_rows} / {job.invalid_rows} /{' '}
                        <span className="font-bold text-slate-900">{job.committed_rows}</span>
                      </td>
                      <td className="p-3 text-slate-500">
                        {new Date(job.requested_at).toLocaleString()}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
