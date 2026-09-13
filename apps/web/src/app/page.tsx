'use client';

import React, { useEffect, useState } from 'react';

interface HealthStatus {
  status: string;
  service: string;
}

export default function HomePage() {
  const [backendStatus, setBackendStatus] = useState<string>('checking...');
  const [isOnline, setIsOnline] = useState<boolean | null>(null);

  useEffect(() => {
    const checkBackend = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';
        // In local development, check /health/live on the API server host
        const healthUrl = apiUrl.replace(/\/api\/v1\/?$/, '/health/live');
        const res = await fetch(healthUrl, { cache: 'no-store' });
        if (res.ok) {
          const data: HealthStatus = await res.json();
          setBackendStatus(`Connected (${data.service} v${(data as { version?: string }).version || '0.1.0'})`);
          setIsOnline(true);
        } else {
          setBackendStatus(`HTTP ${res.status}`);
          setIsOnline(false);
        }
      } catch {
        setBackendStatus('Backend Unreachable');
        setIsOnline(false);
      }
    };

    checkBackend();
  }, []);

  return (
    <main style={{ padding: '3rem', maxWidth: '800px', margin: '0 auto', textAlign: 'center' }}>
      <h1>Digital Student Attendance System</h1>
      <p style={{ color: '#666', fontSize: '1.2rem', marginTop: '1rem' }}>
        University Academic Attendance & Session Governance Portal
      </p>

      <div style={{
        marginTop: '2rem',
        padding: '1.5rem',
        backgroundColor: '#f4f4f5',
        borderRadius: '8px',
        border: '1px solid #e4e4e7',
        textAlign: 'left'
      }}>
        <h3 style={{ margin: '0 0 0.5rem 0' }}>Platform Status: Milestone 4 Core Foundation</h3>
        <p style={{ margin: '0 0 1rem 0', color: '#52525b', fontSize: '0.95rem' }}>
          Core FastAPI platform, PostgreSQL async engine, Redis cache, and Celery worker established.
        </p>

        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          fontSize: '0.9rem',
          padding: '8px 12px',
          backgroundColor: '#fff',
          borderRadius: '6px',
          border: '1px solid #e4e4e7',
          width: 'fit-content'
        }}>
          <span style={{
            display: 'inline-block',
            width: '10px',
            height: '10px',
            borderRadius: '50%',
            backgroundColor: isOnline === true ? '#22c55e' : isOnline === false ? '#ef4444' : '#eab308'
          }} />
          <span style={{ fontWeight: 500 }}>Backend Status:</span>
          <span style={{ color: '#52525b' }}>{backendStatus}</span>
        </div>
      </div>
    </main>
  );
}
