import React, { useEffect, useState } from 'react';
import { Wifi, WifiOff, RefreshCw } from 'lucide-react';

export type ConnectivityStatus = 'ONLINE' | 'OFFLINE' | 'SYNCING' | 'RECONNECTING';

export interface ConnectivityIndicatorProps {
  status?: ConnectivityStatus;
  checkEndpoint?: string;
  className?: string;
  showLabel?: boolean;
}

export function ConnectivityIndicator({
  status: controlledStatus,
  checkEndpoint = '/api/v1/auth/health',
  className = '',
  showLabel = true,
}: ConnectivityIndicatorProps) {
  const [internalStatus, setInternalStatus] = useState<ConnectivityStatus>(() => {
    if (typeof navigator !== 'undefined' && !navigator.onLine) {
      return 'OFFLINE';
    }
    return 'ONLINE';
  });

  useEffect(() => {
    if (controlledStatus) return;

    const handleOnline = () => setInternalStatus('ONLINE');
    const handleOffline = () => setInternalStatus('OFFLINE');

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [controlledStatus]);

  const currentStatus = controlledStatus || internalStatus;

  const config = {
    ONLINE: {
      color: 'bg-emerald-500',
      textColor: 'text-emerald-700',
      bgColor: 'bg-emerald-50 border-emerald-200',
      label: 'Campus Connected',
      icon: <Wifi className="w-3.5 h-3.5 text-emerald-600" />,
    },
    OFFLINE: {
      color: 'bg-amber-500',
      textColor: 'text-amber-800',
      bgColor: 'bg-amber-50 border-amber-200',
      label: 'Offline Mode',
      icon: <WifiOff className="w-3.5 h-3.5 text-amber-600" />,
    },
    SYNCING: {
      color: 'bg-sky-500 animate-spin',
      textColor: 'text-sky-700',
      bgColor: 'bg-sky-50 border-sky-200',
      label: 'Syncing Ledger',
      icon: <RefreshCw className="w-3.5 h-3.5 text-sky-600 animate-spin" />,
    },
    RECONNECTING: {
      color: 'bg-rose-500 animate-pulse',
      textColor: 'text-rose-700',
      bgColor: 'bg-rose-50 border-rose-200',
      label: 'Reconnecting...',
      icon: <WifiOff className="w-3.5 h-3.5 text-rose-600" />,
    },
  };

  const item = config[currentStatus];

  return (
    <div
      title={`Network Status: ${item.label}`}
      className={`inline-flex items-center gap-2 px-2.5 py-1 rounded-full border text-xs font-medium ${item.bgColor} ${item.textColor} ${className}`}
    >
      <span className="relative flex h-2 w-2">
        {currentStatus === 'ONLINE' && (
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
        )}
        <span className={`relative inline-flex rounded-full h-2 w-2 ${item.color}`} />
      </span>
      {item.icon}
      {showLabel && <span>{item.label}</span>}
    </div>
  );
}
