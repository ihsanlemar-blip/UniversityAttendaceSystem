'use client';

import React, { useEffect, useState, useRef, useCallback } from 'react';

export interface QrTokenData {
  token: string;
  checkpoint_id: string;
  checkpoint_type: 'START' | 'MIDDLE' | 'END' | string;
  issued_at: string;
  expires_at: string;
  rotation_seconds: number;
  server_time: string;
  refresh_after_seconds: number;
}

interface LecturerQrDisplayProps {
  checkpointId: string;
  authToken: string;
  courseCode?: string;
  courseName?: string;
  occurrenceDate?: string;
  apiBaseUrl?: string;
  onClose?: () => void;
}

export const LecturerQrDisplay: React.FC<LecturerQrDisplayProps> = ({
  checkpointId,
  authToken,
  courseCode = 'CS-101',
  courseName = 'Introduction to Computer Science',
  occurrenceDate,
  apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1',
  onClose,
}) => {
  const [tokenData, setTokenData] = useState<QrTokenData | null>(null);
  const [secondsRemaining, setSecondsRemaining] = useState<number>(30);
  const [status, setStatus] = useState<'loading' | 'active' | 'expired' | 'error'>('loading');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [refreshCounter, setRefreshCounter] = useState<number>(0);
  const containerRef = useRef<HTMLDivElement>(null);

  const triggerRefresh = useCallback(() => {
    setRefreshCounter((c) => c + 1);
  }, []);

  // Fetch token on mount, checkpoint change, or refreshCounter trigger
  useEffect(() => {
    let isSubscribed = true;

    async function loadToken() {
      try {
        const url = `${apiBaseUrl.replace(/\/+$/, '')}/attendance/checkpoints/${checkpointId}/qr-token`;
        const res = await fetch(url, {
          method: 'GET',
          headers: {
            Authorization: `Bearer ${authToken}`,
            Accept: 'application/json',
            'Cache-Control': 'no-cache',
          },
          cache: 'no-store',
        });

        if (!isSubscribed) return;

        if (!res.ok) {
          const errJson = await res.json().catch(() => ({}));
          const code = errJson?.error?.code || errJson?.detail || `HTTP_${res.status}`;
          if (code === 'CHECKPOINT_WINDOW_EXPIRED' || code === 'CHECKPOINT_NOT_OPEN') {
            setStatus('expired');
            setErrorMessage('Attendance checkpoint window has concluded.');
          } else {
            setStatus('error');
            setErrorMessage(errJson?.error?.message || `Failed to fetch token (${code})`);
          }
          return;
        }

        const json = await res.json();
        if (!isSubscribed) return;
        const data: QrTokenData = json.data;
        setTokenData(data);
        setStatus('active');
        setErrorMessage(null);
        setSecondsRemaining(Math.max(1, data.refresh_after_seconds || data.rotation_seconds || 30));
      } catch (err: unknown) {
        if (!isSubscribed) return;
        setStatus('error');
        setErrorMessage(err instanceof Error ? err.message : 'Network error communicating with server.');
      }
    }

    loadToken();

    return () => {
      isSubscribed = false;
    };
  }, [apiBaseUrl, checkpointId, authToken, refreshCounter]);

  // Rotation countdown timer
  useEffect(() => {
    if (status !== 'active') return;

    const timer = setInterval(() => {
      setSecondsRemaining((prev) => {
        if (prev <= 1) {
          triggerRefresh();
          return 30;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [status, triggerRefresh]);

  const toggleFullscreen = () => {
    if (!containerRef.current) return;
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen().catch(() => {});
      setIsFullscreen(true);
    } else {
      document.exitFullscreen().catch(() => {});
      setIsFullscreen(false);
    }
  };

  const getCheckpointBadgeColor = (type: string) => {
    switch (type) {
      case 'START':
        return { bg: '#2563eb', text: '#ffffff' };
      case 'MIDDLE':
        return { bg: '#d97706', text: '#ffffff' };
      case 'END':
        return { bg: '#7c3aed', text: '#ffffff' };
      default:
        return { bg: '#4b5563', text: '#ffffff' };
    }
  };

  const badgeColors = tokenData ? getCheckpointBadgeColor(tokenData.checkpoint_type) : { bg: '#9ca3af', text: '#fff' };
  const rotationSec = tokenData?.rotation_seconds || 30;
  const progressPercent = Math.min(100, Math.max(0, (secondsRemaining / rotationSec) * 100));

  return (
    <div
      ref={containerRef}
      style={{
        backgroundColor: '#0f172a',
        color: '#f8fafc',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '2rem',
        boxSizing: 'border-box',
      }}
    >
      {/* Top Header */}
      <header
        style={{
          width: '100%',
          maxWidth: '1000px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderBottom: '1px solid #334155',
          paddingBottom: '1rem',
        }}
      >
        <div>
          <div style={{ fontSize: '1.25rem', fontWeight: 700, letterSpacing: '0.025em' }}>
            {courseCode} — {courseName}
          </div>
          <div style={{ fontSize: '0.875rem', color: '#94a3b8', marginTop: '0.25rem' }}>
            Classroom Attendance Verification • {occurrenceDate || new Date().toLocaleDateString()}
          </div>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          {tokenData && (
            <span
              style={{
                backgroundColor: badgeColors.bg,
                color: badgeColors.text,
                padding: '0.35rem 0.85rem',
                borderRadius: '9999px',
                fontSize: '0.875rem',
                fontWeight: 700,
                letterSpacing: '0.05em',
              }}
            >
              {tokenData.checkpoint_type} CHECKPOINT
            </span>
          )}
          <button
            onClick={toggleFullscreen}
            style={{
              backgroundColor: '#1e293b',
              color: '#f1f5f9',
              border: '1px solid #475569',
              padding: '0.4rem 0.8rem',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '0.875rem',
            }}
          >
            {isFullscreen ? 'Exit Fullscreen' : 'Projector Mode'}
          </button>
          {onClose && (
            <button
              onClick={onClose}
              style={{
                backgroundColor: '#dc2626',
                color: '#ffffff',
                border: 'none',
                padding: '0.4rem 0.8rem',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '0.875rem',
              }}
            >
              Close
            </button>
          )}
        </div>
      </header>

      {/* Main QR Display Section */}
      <main
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '2rem 0',
          width: '100%',
          maxWidth: '600px',
        }}
      >
        {status === 'loading' && (
          <div style={{ textAlign: 'center', padding: '3rem' }}>
            <div style={{ fontSize: '1.25rem', color: '#94a3b8' }}>Establishing Cryptographic Session...</div>
          </div>
        )}

        {status === 'expired' && (
          <div
            style={{
              backgroundColor: '#1e293b',
              border: '1px solid #ef4444',
              borderRadius: '12px',
              padding: '2.5rem',
              textAlign: 'center',
              width: '100%',
            }}
          >
            <div style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>⏱️</div>
            <h2 style={{ color: '#ef4444', margin: '0 0 0.5rem 0' }}>Checkpoint Closed</h2>
            <p style={{ color: '#94a3b8', margin: 0 }}>
              The attendance window for this checkpoint has ended. No further check-ins will be accepted.
            </p>
          </div>
        )}

        {status === 'error' && (
          <div
            style={{
              backgroundColor: '#1e293b',
              border: '1px solid #dc2626',
              borderRadius: '12px',
              padding: '2rem',
              textAlign: 'center',
              width: '100%',
            }}
          >
            <h3 style={{ color: '#ef4444', margin: '0 0 0.5rem 0' }}>Display Error</h3>
            <p style={{ color: '#cbd5e1', fontSize: '0.95rem' }}>{errorMessage}</p>
            <button
              onClick={triggerRefresh}
              style={{
                marginTop: '1rem',
                backgroundColor: '#2563eb',
                color: '#ffffff',
                border: 'none',
                padding: '0.5rem 1rem',
                borderRadius: '6px',
                cursor: 'pointer',
              }}
            >
              Retry Connection
            </button>
          </div>
        )}

        {status === 'active' && tokenData && (
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              backgroundColor: '#ffffff',
              padding: '2.5rem',
              borderRadius: '24px',
              boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
              color: '#0f172a',
              width: '100%',
              maxWidth: '440px',
              boxSizing: 'border-box',
            }}
          >
            {/* Visual QR Code Container */}
            <div
              style={{
                width: '320px',
                height: '320px',
                backgroundColor: '#f8fafc',
                border: '4px solid #0f172a',
                borderRadius: '16px',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '1rem',
                boxSizing: 'border-box',
                position: 'relative',
              }}
            >
              {/* High-visibility QR Visual Mock/Canvas with Token Payload */}
              <div
                style={{
                  width: '100%',
                  height: '100%',
                  display: 'grid',
                  gridTemplateColumns: 'repeat(5, 1fr)',
                  gridTemplateRows: 'repeat(5, 1fr)',
                  gap: '4px',
                  backgroundColor: '#0f172a',
                  padding: '12px',
                  borderRadius: '8px',
                  boxSizing: 'border-box',
                }}
              >
                {Array.from({ length: 25 }).map((_, idx) => {
                  const isCorner =
                    idx === 0 || idx === 1 || idx === 5 || idx === 6 ||
                    idx === 3 || idx === 4 || idx === 8 || idx === 9 ||
                    idx === 15 || idx === 16 || idx === 20 || idx === 21;
                  const isSeed = (tokenData.token.charCodeAt(idx % tokenData.token.length) + idx) % 2 === 0;
                  return (
                    <div
                      key={idx}
                      style={{
                        backgroundColor: isCorner || isSeed ? '#ffffff' : '#0f172a',
                        borderRadius: '2px',
                      }}
                    />
                  );
                })}
              </div>
            </div>

            {/* Instruction Callout */}
            <div
              style={{
                marginTop: '1.25rem',
                fontSize: '1rem',
                fontWeight: 600,
                color: '#1e293b',
                textAlign: 'center',
              }}
            >
              Scan with University Attendance App
            </div>
            <div
              style={{
                fontSize: '0.8rem',
                color: '#64748b',
                marginTop: '0.25rem',
                textAlign: 'center',
              }}
            >
              Dynamic presence token rotates every {tokenData.rotation_seconds}s
            </div>

            {/* Rotation Countdown Bar */}
            <div
              style={{
                width: '100%',
                marginTop: '1.5rem',
                backgroundColor: '#e2e8f0',
                borderRadius: '9999px',
                height: '8px',
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  width: `${progressPercent}%`,
                  height: '100%',
                  backgroundColor: secondsRemaining <= 5 ? '#ef4444' : '#2563eb',
                  transition: 'width 1s linear',
                }}
              />
            </div>

            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                width: '100%',
                marginTop: '0.5rem',
                fontSize: '0.8rem',
                color: '#64748b',
              }}
            >
              <span>Token Rotation:</span>
              <span
                style={{
                  fontWeight: 700,
                  color: secondsRemaining <= 5 ? '#ef4444' : '#0f172a',
                }}
              >
                {secondsRemaining}s remaining
              </span>
            </div>
          </div>
        )}
      </main>

      {/* Footer Info */}
      <footer
        style={{
          width: '100%',
          maxWidth: '1000px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderTop: '1px solid #334155',
          paddingTop: '1rem',
          fontSize: '0.8rem',
          color: '#64748b',
        }}
      >
        <div>
          Authority: University UTC Server Clock • Offline/Screenshot Tokens Expire in {rotationSec}s
        </div>
        <div>Security Modality: ONLINE_DYNAMIC_QR (HS256)</div>
      </footer>
    </div>
  );
};

export default LecturerQrDisplay;
