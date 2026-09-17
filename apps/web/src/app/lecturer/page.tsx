'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import {
  GraduationCap,
  Calendar,
  Clock,
  QrCode,
  Users,
  CheckCircle2,
  AlertCircle,
  Play,
  ArrowRight,
  RefreshCw,
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
  Dialog,
  KpiCard,
} from '@/components/ui';
import { LecturerQrDisplay } from '@/components/LecturerQrDisplay';

interface ClassItem {
  id: string;
  course_code: string;
  course_name: string;
  room_number: string;
  start_time: string;
  end_time: string;
  enrolled_count: number;
  session_id?: string;
  checkpoint_id?: string;
  status: 'SCHEDULED' | 'IN_PROGRESS' | 'COMPLETED';
}

export default function LecturerPortalPage() {
  const { user, token } = useAuth();
  const [selectedCheckpoint, setSelectedCheckpoint] = useState<{
    checkpointId: string;
    courseCode: string;
    courseName: string;
  } | null>(null);

  // Mock initial today's schedule for demonstration/foundation
  const [classes, setClasses] = useState<ClassItem[]>([
    {
      id: 'occ-01',
      course_code: 'CS-301',
      course_name: 'Database Management Systems',
      room_number: 'Engineering Hall 204',
      start_time: '08:30 UTC',
      end_time: '10:00 UTC',
      enrolled_count: 42,
      checkpoint_id: 'cp-start-001',
      status: 'IN_PROGRESS',
    },
    {
      id: 'occ-02',
      course_code: 'CS-402',
      course_name: 'Distributed Systems & Cloud Computing',
      room_number: 'Science Lab B-12',
      start_time: '10:30 UTC',
      end_time: '12:00 UTC',
      enrolled_count: 35,
      status: 'SCHEDULED',
    },
    {
      id: 'occ-03',
      course_code: 'SE-201',
      course_name: 'Software Engineering Principles',
      room_number: 'Lecture Hall 1',
      start_time: '14:00 UTC',
      end_time: '15:30 UTC',
      enrolled_count: 48,
      status: 'SCHEDULED',
    },
  ]);

  return (
    <AppShell>
      <PageHeader
        title="Lecturer Academic Console"
        description="Launch live attendance sessions, broadcast cryptographic rotating QR tokens, and review roster verification."
        breadcrumbs={[{ label: 'Lecturer Console' }]}
        actions={
          <div className="flex items-center gap-2">
            <Link href="/admin/reports/attendance">
              <Button variant="outline" size="sm" className="bg-white">
                View Reports
              </Button>
            </Link>
          </div>
        }
      />

      {/* Instructor Profile & Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="md:col-span-2 p-5 bg-gradient-to-r from-sky-900 to-indigo-950 text-white rounded-xl shadow-xs flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-white/10 backdrop-blur-sm border border-white/20 flex items-center justify-center text-sky-300">
              <GraduationCap className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">
                {user?.username || 'Faculty Instructor'}
              </h2>
              <p className="text-xs text-sky-200 mt-0.5">
                Department of Computer Science & Engineering
              </p>
              <div className="flex items-center gap-2 mt-2">
                <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-sky-800/80 text-sky-200 border border-sky-600/40">
                  ACTIVE INSTRUCTOR
                </span>
                <span className="text-[11px] text-sky-300">
                  ID: {user?.id.slice(0, 8)}...
                </span>
              </div>
            </div>
          </div>
        </div>

        <KpiCard
          title="Classes Today"
          value={classes.length}
          subtitle="Scheduled meetings"
          icon={<Calendar className="w-5 h-5 text-sky-600" />}
          variant="info"
        />

        <KpiCard
          title="Active Sessions"
          value={classes.filter((c) => c.status === 'IN_PROGRESS').length}
          subtitle="Attendance broadcast live"
          icon={<QrCode className="w-5 h-5 text-emerald-600" />}
          variant="success"
        />
      </div>

      {/* Today's Schedule & Session Launcher */}
      <Card className="mb-8">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Today&apos;s Class Meetings & Sessions</CardTitle>
            <CardDescription>
              Select an active occurrence to broadcast dynamic QR tokens or initialize checkpoint recording.
            </CardDescription>
          </div>
          <Badge variant="default" size="sm">
            UTC Calendar Date
          </Badge>
        </CardHeader>
        <CardContent className="p-0">
          <div className="divide-y divide-slate-200">
            {classes.map((cls) => {
              const isInProgress = cls.status === 'IN_PROGRESS';

              return (
                <div
                  key={cls.id}
                  className="p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-slate-50 transition-colors"
                >
                  <div className="flex items-start gap-3.5">
                    <div
                      className={`p-3 rounded-xl shrink-0 ${
                        isInProgress
                          ? 'bg-emerald-100 text-emerald-700'
                          : 'bg-slate-100 text-slate-600'
                      }`}
                    >
                      {isInProgress ? (
                        <QrCode className="w-6 h-6 animate-pulse" />
                      ) : (
                        <Calendar className="w-6 h-6" />
                      )}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-800 border border-slate-200">
                          {cls.course_code}
                        </span>
                        <h4 className="text-sm font-semibold text-slate-900">
                          {cls.course_name}
                        </h4>
                      </div>
                      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-1 text-xs text-slate-500">
                        <span className="flex items-center gap-1">
                          <Clock className="w-3.5 h-3.5 text-slate-400" />
                          {cls.start_time} - {cls.end_time}
                        </span>
                        <span className="flex items-center gap-1">
                          <Building className="w-3.5 h-3.5 text-slate-400" />
                          {cls.room_number}
                        </span>
                        <span className="flex items-center gap-1">
                          <Users className="w-3.5 h-3.5 text-slate-400" />
                          {cls.enrolled_count} Enrolled
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2.5 shrink-0 self-end md:self-center">
                    {isInProgress ? (
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={() =>
                          setSelectedCheckpoint({
                            checkpointId: cls.checkpoint_id || 'cp-001',
                            courseCode: cls.course_code,
                            courseName: cls.course_name,
                          })
                        }
                        className="bg-emerald-600 hover:bg-emerald-700 focus:ring-emerald-500 shadow-sm"
                      >
                        <QrCode className="w-4 h-4 mr-1.5" />
                        Display Rotating QR
                      </Button>
                    ) : (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() =>
                          setSelectedCheckpoint({
                            checkpointId: 'cp-temp-new',
                            courseCode: cls.course_code,
                            courseName: cls.course_name,
                          })
                        }
                      >
                        <Play className="w-3.5 h-3.5 mr-1 text-sky-600" />
                        Start Checkpoint
                      </Button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* QR Code Presentation Dialog */}
      {selectedCheckpoint && (
        <Dialog
          isOpen={!!selectedCheckpoint}
          onClose={() => setSelectedCheckpoint(null)}
          title={`Dynamic Checkpoint QR: ${selectedCheckpoint.courseCode}`}
          description="Tokens rotate automatically every 30 seconds. Point the classroom projector here."
          maxWidth="lg"
        >
          <div className="py-2">
            <LecturerQrDisplay
              checkpointId={selectedCheckpoint.checkpointId}
              authToken={token || ''}
              courseCode={selectedCheckpoint.courseCode}
              courseName={selectedCheckpoint.courseName}
              onClose={() => setSelectedCheckpoint(null)}
            />
          </div>
        </Dialog>
      )}
    </AppShell>
  );
}
