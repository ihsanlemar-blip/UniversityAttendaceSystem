'use client';

import React, { useState, useCallback } from 'react';
import {
  BarChart3,
  Download,
  Filter,
  FileSpreadsheet,
  AlertTriangle,
  CheckCircle2,
  AlertCircle,
  Clock,
  Layers,
  Search,
  RefreshCw,
  Building2,
  GraduationCap,
  Users,
} from 'lucide-react';

interface CourseRosterItem {
  student_id: string;
  student_number: string;
  student_name: string;
  eligible_sessions: number;
  attendance_credit: number;
  attendance_percentage: number;
  present_count: number;
  late_count: number;
  absent_count: number;
  excused_count: number;
  leave_count: number;
  has_revision: boolean;
  threshold_status: 'ABOVE_THRESHOLD' | 'NEAR_THRESHOLD' | 'BELOW_THRESHOLD';
}

interface CourseRosterReport {
  course_offering_id: string;
  course_code: string;
  course_name: string;
  semester_code: string;
  section_code?: string | null;
  total_sessions_conducted: number;
  threshold_percentage: number;
  near_threshold_margin: number;
  total_enrolled: number;
  average_attendance_percentage: number;
  above_threshold_count: number;
  near_threshold_count: number;
  below_threshold_count: number;
  roster: CourseRosterItem[];
  page: number;
  page_size: number;
  total_pages: number;
}

interface DepartmentReport {
  academic_unit_id: string;
  academic_unit_code: string;
  academic_unit_name: string;
  total_courses: number;
  total_offerings: number;
  total_students_enrolled: number;
  department_average_percentage: number;
  below_threshold_count: number;
  near_threshold_count: number;
  above_threshold_count: number;
  offerings: {
    course_offering_id: string;
    course_code: string;
    course_name: string;
    semester_code: string;
    section_code?: string | null;
    enrolled_count: number;
    conducted_sessions_count: number;
    average_attendance_percentage: number;
    below_threshold_count: number;
    near_threshold_count: number;
  }[];
}

interface SessionReport {
  session_id: string;
  course_code: string;
  course_name: string;
  semester_code: string;
  section_code?: string | null;
  lecturer_name?: string | null;
  building_code?: string | null;
  room_number?: string | null;
  status: string;
  roster_count: number;
  start_credited_count: number;
  middle_credited_count: number;
  end_credited_count: number;
  present_count: number;
  late_count: number;
  absent_count: number;
  excused_count: number;
  leave_count: number;
  manual_count: number;
  offline_count: number;
  revision_count: number;
}

export default function AttendanceReportsDashboardPage() {
  const [activeTab, setActiveTab] = useState<'roster' | 'department' | 'session'>('roster');

  // Course Roster State
  const [offeringId, setOfferingId] = useState<string>('');
  const [thresholdFilter, setThresholdFilter] = useState<string>('ALL');
  const [rosterReport, setRosterReport] = useState<CourseRosterReport | null>(null);
  const [isLoadingRoster, setIsLoadingRoster] = useState<boolean>(false);

  // Department State
  const [departmentId, setDepartmentId] = useState<string>('');
  const [departmentReport, setDepartmentReport] = useState<DepartmentReport | null>(null);
  const [isLoadingDept, setIsLoadingDept] = useState<boolean>(false);

  // Session State
  const [sessionId, setSessionId] = useState<string>('');
  const [sessionReport, setSessionReport] = useState<SessionReport | null>(null);
  const [isLoadingSession, setIsLoadingSession] = useState<boolean>(false);

  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';

  const getAuthHeaders = useCallback((): HeadersInit => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') || localStorage.getItem('access_token') : null;
    return {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      Accept: 'application/json',
    };
  }, []);

  const handleFetchRoster = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!offeringId.trim()) {
      setErrorMessage('Please enter a valid Course Offering UUID.');
      return;
    }
    setIsLoadingRoster(true);
    setErrorMessage(null);

    const filterParam = thresholdFilter !== 'ALL' ? `&threshold_status=${thresholdFilter}` : '';
    try {
      const res = await fetch(
        `${apiBaseUrl}/reports/attendance/course-offerings/${offeringId.trim()}?page=1&page_size=100${filterParam}`,
        { headers: getAuthHeaders() }
      );
      const json = await res.json();
      if (res.ok && json.data) {
        setRosterReport(json.data);
      } else {
        setErrorMessage(json.detail || json.message || 'Course offering report not found.');
        setRosterReport(null);
      }
    } catch {
      setErrorMessage('Failed to connect to reporting service.');
    } finally {
      setIsLoadingRoster(false);
    }
  };

  const handleFetchDepartment = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!departmentId.trim()) {
      setErrorMessage('Please enter an Academic Unit / Department UUID.');
      return;
    }
    setIsLoadingDept(true);
    setErrorMessage(null);

    try {
      const res = await fetch(
        `${apiBaseUrl}/reports/attendance/department/${departmentId.trim()}`,
        { headers: getAuthHeaders() }
      );
      const json = await res.json();
      if (res.ok && json.data) {
        setDepartmentReport(json.data);
      } else {
        setErrorMessage(json.detail || json.message || 'Department report not found.');
        setDepartmentReport(null);
      }
    } catch {
      setErrorMessage('Failed to connect to reporting service.');
    } finally {
      setIsLoadingDept(false);
    }
  };

  const handleFetchSession = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!sessionId.trim()) {
      setErrorMessage('Please enter an Attendance Session UUID.');
      return;
    }
    setIsLoadingSession(true);
    setErrorMessage(null);

    try {
      const res = await fetch(
        `${apiBaseUrl}/reports/attendance/sessions/${sessionId.trim()}`,
        { headers: getAuthHeaders() }
      );
      const json = await res.json();
      if (res.ok && json.data) {
        setSessionReport(json.data);
      } else {
        setErrorMessage(json.detail || json.message || 'Session report not found.');
        setSessionReport(null);
      }
    } catch {
      setErrorMessage('Failed to connect to reporting service.');
    } finally {
      setIsLoadingSession(false);
    }
  };

  const handleExportRoster = (format: 'CSV' | 'XLSX') => {
    if (!offeringId.trim()) return;
    const filterParam = thresholdFilter !== 'ALL' ? `&threshold_status=${thresholdFilter}` : '';
    const url = `${apiBaseUrl}/reports/attendance/course-offerings/${offeringId.trim()}/export?format=${format}${filterParam}`;
    window.open(url, '_blank');
  };

  const handleExportDepartment = (format: 'CSV' | 'XLSX') => {
    if (!departmentId.trim()) return;
    const url = `${apiBaseUrl}/reports/attendance/department/${departmentId.trim()}/export?format=${format}`;
    window.open(url, '_blank');
  };

  const handleExportSession = (format: 'CSV' | 'XLSX') => {
    if (!sessionId.trim()) return;
    const url = `${apiBaseUrl}/reports/attendance/sessions/${sessionId.trim()}/export?format=${format}`;
    window.open(url, '_blank');
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
              <BarChart3 className="h-7 w-7 text-indigo-600" />
              Institutional Attendance Analytics & Reports
            </h1>
            <p className="text-sm text-slate-600 mt-1">
              Authoritative institutional reports, threshold analytics, and secure multi-format exports.
            </p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex border-b border-slate-200 gap-6">
          <button
            onClick={() => {
              setActiveTab('roster');
              setErrorMessage(null);
            }}
            className={`pb-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition-colors ${
              activeTab === 'roster'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <GraduationCap className="h-4 w-4" />
            Course Roster Report
          </button>
          <button
            onClick={() => {
              setActiveTab('department');
              setErrorMessage(null);
            }}
            className={`pb-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition-colors ${
              activeTab === 'department'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <Building2 className="h-4 w-4" />
            Department & Faculty Aggregates
          </button>
          <button
            onClick={() => {
              setActiveTab('session');
              setErrorMessage(null);
            }}
            className={`pb-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition-colors ${
              activeTab === 'session'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <Clock className="h-4 w-4" />
            Session Operational Report
          </button>
        </div>

        {/* Error Alert */}
        {errorMessage && (
          <div className="p-4 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-rose-600 shrink-0" />
            <span className="text-sm font-medium">{errorMessage}</span>
          </div>
        )}

        {/* Tab 1: Course Roster Report */}
        {activeTab === 'roster' && (
          <div className="space-y-6">
            {/* Search & Filter Controls */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
              <form onSubmit={handleFetchRoster} className="flex flex-col md:flex-row gap-3 items-end">
                <div className="flex-1">
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Course Offering ID (UUID)
                  </label>
                  <div className="relative">
                    <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                    <input
                      type="text"
                      placeholder="e.g. 01a09a40-a1d7-769b-a02f-..."
                      value={offeringId}
                      onChange={(e) => setOfferingId(e.target.value)}
                      className="w-full pl-9 pr-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Threshold Status Filter
                  </label>
                  <select
                    value={thresholdFilter}
                    onChange={(e) => setThresholdFilter(e.target.value)}
                    className="text-xs border border-slate-300 rounded-lg p-2 bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="ALL">All Enrolled Students</option>
                    <option value="ABOVE_THRESHOLD">Above Threshold (≥ 75%)</option>
                    <option value="NEAR_THRESHOLD">Near Threshold (70% - 74.9%)</option>
                    <option value="BELOW_THRESHOLD">Below Threshold (&lt; 70%)</option>
                  </select>
                </div>

                <button
                  type="submit"
                  disabled={isLoadingRoster}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg transition-colors flex items-center gap-1.5 shadow-sm disabled:opacity-50"
                >
                  {isLoadingRoster ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Search className="h-3.5 w-3.5" />}
                  Generate Report
                </button>
              </form>
            </div>

            {/* Roster Report Content */}
            {rosterReport && (
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-6">
                {/* Header & Export Actions */}
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-100 pb-4">
                  <div>
                    <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                      <GraduationCap className="h-6 w-6 text-indigo-600" />
                      {rosterReport.course_code}: {rosterReport.course_name}
                    </h2>
                    <p className="text-xs text-slate-500 mt-1">
                      Semester: <span className="font-semibold text-slate-700">{rosterReport.semester_code}</span> | Section:{' '}
                      <span className="font-semibold text-slate-700">{rosterReport.section_code || 'All'}</span>
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleExportRoster('CSV')}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-colors"
                    >
                      <Download className="h-3.5 w-3.5" />
                      Export CSV (Safe UTF-8)
                    </button>
                    <button
                      onClick={() => handleExportRoster('XLSX')}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold bg-indigo-50 hover:bg-indigo-100 text-indigo-700 rounded-lg transition-colors"
                    >
                      <FileSpreadsheet className="h-3.5 w-3.5" />
                      Export Excel (XLSX)
                    </button>
                  </div>
                </div>

                {/* KPI Metrics */}
                <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
                    <span className="text-xs text-slate-500 font-medium">Total Enrolled</span>
                    <p className="text-xl font-bold text-slate-900 mt-0.5">{rosterReport.total_enrolled}</p>
                  </div>
                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
                    <span className="text-xs text-slate-500 font-medium">Sessions Held</span>
                    <p className="text-xl font-bold text-slate-900 mt-0.5">{rosterReport.total_sessions_conducted}</p>
                  </div>
                  <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-3">
                    <span className="text-xs text-indigo-700 font-medium">Class Average %</span>
                    <p className="text-xl font-bold text-indigo-900 mt-0.5">{rosterReport.average_attendance_percentage.toFixed(1)}%</p>
                  </div>
                  <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3">
                    <span className="text-xs text-emerald-700 font-medium">Above Threshold (≥{rosterReport.threshold_percentage}%)</span>
                    <p className="text-xl font-bold text-emerald-800 mt-0.5">{rosterReport.above_threshold_count}</p>
                  </div>
                  <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
                    <span className="text-xs text-amber-700 font-medium">Near Threshold</span>
                    <p className="text-xl font-bold text-amber-800 mt-0.5">{rosterReport.near_threshold_count}</p>
                  </div>
                  <div className="bg-rose-50 border border-rose-200 rounded-lg p-3">
                    <span className="text-xs text-rose-700 font-medium">Below Threshold</span>
                    <p className="text-xl font-bold text-rose-800 mt-0.5">{rosterReport.below_threshold_count}</p>
                  </div>
                </div>

                {/* Roster Data Table */}
                <div className="overflow-x-auto border border-slate-200 rounded-lg">
                  <table className="w-full text-left text-xs text-slate-600">
                    <thead className="bg-slate-100 text-slate-700 font-semibold border-b border-slate-200">
                      <tr>
                        <th className="p-3">Student</th>
                        <th className="p-3">Eligible Sessions</th>
                        <th className="p-3">Attendance Credit</th>
                        <th className="p-3">Attendance %</th>
                        <th className="p-3">Threshold Status</th>
                        <th className="p-3">P / L / A / E / Leave</th>
                        <th className="p-3">Revisions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200">
                      {rosterReport.roster.length === 0 ? (
                        <tr>
                          <td colSpan={7} className="p-6 text-center text-slate-400">
                            No students match the selected threshold filter.
                          </td>
                        </tr>
                      ) : (
                        rosterReport.roster.map((s) => (
                          <tr key={s.student_id} className="hover:bg-slate-50">
                            <td className="p-3 font-medium text-slate-800">
                              <div>{s.student_name}</div>
                              <div className="text-slate-400 text-[10px] font-mono">{s.student_number}</div>
                            </td>
                            <td className="p-3 font-mono">{s.eligible_sessions}</td>
                            <td className="p-3 font-mono font-semibold">{s.attendance_credit.toFixed(1)}</td>
                            <td className="p-3 font-mono font-bold text-slate-900">
                              {s.attendance_percentage.toFixed(1)}%
                            </td>
                            <td className="p-3">
                              {s.threshold_status === 'ABOVE_THRESHOLD' ? (
                                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
                                  <CheckCircle2 className="h-3 w-3" />
                                  Above Threshold
                                </span>
                              ) : s.threshold_status === 'NEAR_THRESHOLD' ? (
                                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800">
                                  <AlertTriangle className="h-3 w-3" />
                                  Near Threshold
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-800">
                                  <AlertCircle className="h-3 w-3" />
                                  Below Threshold
                                </span>
                              )}
                            </td>
                            <td className="p-3 font-mono text-slate-500">
                              <span className="text-emerald-700 font-semibold">{s.present_count}P</span> /{' '}
                              <span className="text-amber-700 font-semibold">{s.late_count}L</span> /{' '}
                              <span className="text-rose-700 font-semibold">{s.absent_count}A</span> /{' '}
                              <span className="text-sky-700 font-semibold">{s.excused_count}E</span> /{' '}
                              <span className="text-indigo-700 font-semibold">{s.leave_count}Lv</span>
                            </td>
                            <td className="p-3 font-mono">
                              {s.has_revision ? (
                                <span className="text-amber-600 font-semibold">Yes</span>
                              ) : (
                                <span className="text-slate-400">None</span>
                              )}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Department & Faculty Aggregates */}
        {activeTab === 'department' && (
          <div className="space-y-6">
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
              <form onSubmit={handleFetchDepartment} className="flex gap-3 items-end">
                <div className="flex-1">
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Department / Academic Unit ID (UUID)
                  </label>
                  <div className="relative">
                    <Building2 className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                    <input
                      type="text"
                      placeholder="e.g. academic unit uuid..."
                      value={departmentId}
                      onChange={(e) => setDepartmentId(e.target.value)}
                      className="w-full pl-9 pr-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isLoadingDept}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg transition-colors flex items-center gap-1.5 shadow-sm disabled:opacity-50"
                >
                  {isLoadingDept ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Search className="h-3.5 w-3.5" />}
                  View Department
                </button>
              </form>
            </div>

            {departmentReport && (
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-6">
                <div className="flex items-center justify-between border-b border-slate-100 pb-4">
                  <div>
                    <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                      <Building2 className="h-6 w-6 text-indigo-600" />
                      {departmentReport.academic_unit_code}: {departmentReport.academic_unit_name}
                    </h2>
                    <p className="text-xs text-slate-500 mt-1">
                      Aggregated metrics across all active courses and course offerings.
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleExportDepartment('CSV')}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-colors"
                    >
                      <Download className="h-3.5 w-3.5" />
                      Export CSV
                    </button>
                    <button
                      onClick={() => handleExportDepartment('XLSX')}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold bg-indigo-50 hover:bg-indigo-100 text-indigo-700 rounded-lg transition-colors"
                    >
                      <FileSpreadsheet className="h-3.5 w-3.5" />
                      Export Excel
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-3.5">
                    <span className="text-xs text-indigo-700 font-medium">Department Average %</span>
                    <p className="text-2xl font-bold text-indigo-900 mt-1">
                      {departmentReport.department_average_percentage.toFixed(1)}%
                    </p>
                  </div>
                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-3.5">
                    <span className="text-xs text-slate-500 font-medium">Total Offerings</span>
                    <p className="text-2xl font-bold text-slate-900 mt-1">{departmentReport.total_offerings}</p>
                  </div>
                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-3.5">
                    <span className="text-xs text-slate-500 font-medium">Total Students Enrolled</span>
                    <p className="text-2xl font-bold text-slate-900 mt-1">{departmentReport.total_students_enrolled}</p>
                  </div>
                  <div className="bg-rose-50 border border-rose-200 rounded-lg p-3.5">
                    <span className="text-xs text-rose-700 font-medium">Below Threshold Students</span>
                    <p className="text-2xl font-bold text-rose-800 mt-1">{departmentReport.below_threshold_count}</p>
                  </div>
                </div>

                {/* Offerings Table */}
                <div className="overflow-x-auto border border-slate-200 rounded-lg">
                  <table className="w-full text-left text-xs text-slate-600">
                    <thead className="bg-slate-100 text-slate-700 font-semibold border-b border-slate-200">
                      <tr>
                        <th className="p-3">Course Offering</th>
                        <th className="p-3">Semester</th>
                        <th className="p-3">Enrolled</th>
                        <th className="p-3">Sessions Held</th>
                        <th className="p-3">Average %</th>
                        <th className="p-3">Below Threshold</th>
                        <th className="p-3">Near Threshold</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200">
                      {departmentReport.offerings.map((off) => (
                        <tr key={off.course_offering_id} className="hover:bg-slate-50">
                          <td className="p-3 font-medium text-slate-800">
                            <div>{off.course_code}: {off.course_name}</div>
                            <div className="text-[10px] text-slate-400">Section: {off.section_code || 'All'}</div>
                          </td>
                          <td className="p-3">{off.semester_code}</td>
                          <td className="p-3 font-mono">{off.enrolled_count}</td>
                          <td className="p-3 font-mono">{off.conducted_sessions_count}</td>
                          <td className="p-3 font-mono font-bold text-indigo-900">
                            {off.average_attendance_percentage.toFixed(1)}%
                          </td>
                          <td className="p-3 font-mono text-rose-700 font-semibold">{off.below_threshold_count}</td>
                          <td className="p-3 font-mono text-amber-700 font-semibold">{off.near_threshold_count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab 3: Session Operational Report */}
        {activeTab === 'session' && (
          <div className="space-y-6">
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
              <form onSubmit={handleFetchSession} className="flex gap-3 items-end">
                <div className="flex-1">
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Attendance Session ID (UUID)
                  </label>
                  <div className="relative">
                    <Clock className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                    <input
                      type="text"
                      placeholder="e.g. session uuid..."
                      value={sessionId}
                      onChange={(e) => setSessionId(e.target.value)}
                      className="w-full pl-9 pr-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isLoadingSession}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg transition-colors flex items-center gap-1.5 shadow-sm disabled:opacity-50"
                >
                  {isLoadingSession ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Search className="h-3.5 w-3.5" />}
                  View Session
                </button>
              </form>
            </div>

            {sessionReport && (
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-6">
                <div className="flex items-center justify-between border-b border-slate-100 pb-4">
                  <div>
                    <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                      <Clock className="h-6 w-6 text-indigo-600" />
                      Session {sessionReport.session_id.slice(0, 8)}... ({sessionReport.status})
                    </h2>
                    <p className="text-xs text-slate-500 mt-1">
                      {sessionReport.course_code}: {sessionReport.course_name} | Lecturer:{' '}
                      <span className="font-semibold text-slate-700">{sessionReport.lecturer_name || 'Assigned'}</span> | Room:{' '}
                      <span className="font-semibold text-slate-700">
                        {sessionReport.building_code || ''} {sessionReport.room_number || ''}
                      </span>
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleExportSession('CSV')}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-colors"
                    >
                      <Download className="h-3.5 w-3.5" />
                      Export CSV
                    </button>
                    <button
                      onClick={() => handleExportSession('XLSX')}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold bg-indigo-50 hover:bg-indigo-100 text-indigo-700 rounded-lg transition-colors"
                    >
                      <FileSpreadsheet className="h-3.5 w-3.5" />
                      Export Excel
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-3.5">
                    <span className="text-xs text-slate-500 font-medium">Enrolled Roster</span>
                    <p className="text-2xl font-bold text-slate-900 mt-1">{sessionReport.roster_count}</p>
                  </div>
                  <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3.5">
                    <span className="text-xs text-emerald-700 font-medium">Start Checkpoint Credited</span>
                    <p className="text-2xl font-bold text-emerald-800 mt-1">{sessionReport.start_credited_count}</p>
                  </div>
                  <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-3.5">
                    <span className="text-xs text-indigo-700 font-medium">Middle Checkpoint Credited</span>
                    <p className="text-2xl font-bold text-indigo-800 mt-1">{sessionReport.middle_credited_count}</p>
                  </div>
                  <div className="bg-purple-50 border border-purple-200 rounded-lg p-3.5">
                    <span className="text-xs text-purple-700 font-medium">End Checkpoint Credited</span>
                    <p className="text-2xl font-bold text-purple-800 mt-1">{sessionReport.end_credited_count}</p>
                  </div>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
                    <span className="text-xs text-slate-500 font-medium">Present</span>
                    <p className="text-lg font-bold text-emerald-700 mt-0.5">{sessionReport.present_count}</p>
                  </div>
                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
                    <span className="text-xs text-slate-500 font-medium">Late</span>
                    <p className="text-lg font-bold text-amber-700 mt-0.5">{sessionReport.late_count}</p>
                  </div>
                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
                    <span className="text-xs text-slate-500 font-medium">Absent</span>
                    <p className="text-lg font-bold text-rose-700 mt-0.5">{sessionReport.absent_count}</p>
                  </div>
                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
                    <span className="text-xs text-slate-500 font-medium">Excused</span>
                    <p className="text-lg font-bold text-sky-700 mt-0.5">{sessionReport.excused_count}</p>
                  </div>
                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
                    <span className="text-xs text-slate-500 font-medium">Leave</span>
                    <p className="text-lg font-bold text-indigo-700 mt-0.5">{sessionReport.leave_count}</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
