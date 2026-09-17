import {
  LayoutDashboard,
  ClipboardCheck,
  Smartphone,
  UploadCloud,
  FileSpreadsheet,
  ShieldAlert,
  Sliders,
  GraduationCap,
} from 'lucide-react';

export interface NavItem {
  title: string;
  href: string;
  icon: any;
  permission?: string;
  badgeKey?: string;
  exact?: boolean;
}

export interface NavGroup {
  group: string;
  items: NavItem[];
}

export const NAVIGATION_CONFIG: NavGroup[] = [
  {
    group: 'Overview',
    items: [
      {
        title: 'Dashboard',
        href: '/admin',
        icon: LayoutDashboard,
        exact: true,
      },
    ],
  },
  {
    group: 'Attendance Operations',
    items: [
      {
        title: 'Operational Reviews',
        href: '/admin/attendance/reviews',
        icon: ClipboardCheck,
        permission: 'attendance.corrections.review',
        badgeKey: 'pending_corrections_count',
      },
    ],
  },
  {
    group: 'Device Trust',
    items: [
      {
        title: 'Device Management',
        href: '/admin/devices',
        icon: Smartphone,
        permission: 'devices.read',
        badgeKey: 'pending_devices_count',
      },
    ],
  },
  {
    group: 'Institutional Data',
    items: [
      {
        title: 'Import Center',
        href: '/admin/imports',
        icon: UploadCloud,
        permission: 'imports.read',
      },
      {
        title: 'Attendance Reports',
        href: '/admin/reports/attendance',
        icon: FileSpreadsheet,
        permission: 'reports.attendance.read',
      },
    ],
  },
  {
    group: 'Security & Integrity',
    items: [
      {
        title: 'Risk Signals & Defense',
        href: '/admin/security',
        icon: ShieldAlert,
        permission: 'security.risk_signals.read',
        badgeKey: 'open_risk_signals_count',
      },
      {
        title: 'Attendance Policy',
        href: '/admin/settings/attendance',
        icon: Sliders,
        permission: 'attendance_policies.read',
      },
    ],
  },
  {
    group: 'Academic Portals',
    items: [
      {
        title: 'Lecturer Console',
        href: '/lecturer',
        icon: GraduationCap,
      },
    ],
  },
];
