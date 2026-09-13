import type { Metadata } from 'next';
import React from 'react';

export const metadata: Metadata = {
  title: 'Digital Student Attendance System',
  description: 'University Student Attendance & Academic Session Governance',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" dir="ltr">
      <body style={{ fontFamily: 'system-ui, -apple-system, sans-serif', margin: 0, padding: 0 }}>
        {children}
      </body>
    </html>
  );
}
