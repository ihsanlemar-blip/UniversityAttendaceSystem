'use client';

import React, { ReactNode } from 'react';
import { AppShell } from '@/components/layout';

export default function AdminLayout({ children }: { children: ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
