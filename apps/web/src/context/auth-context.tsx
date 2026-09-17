'use client';

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { useRouter, usePathname } from 'next/navigation';

export interface UserProfile {
  id: string;
  university_id: string;
  username: string;
  email?: string | null;
  phone?: string | null;
  preferred_language?: string;
  status?: string;
  must_change_password: boolean;
  roles: string[];
  permissions: string[];
}

export interface AuthContextType {
  user: UserProfile | null;
  token: string | null;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<{ success: boolean; mustChangePassword?: boolean; error?: string }>;
  logout: () => Promise<void>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<{ success: boolean; error?: string }>;
  hasPermission: (permissionCode: string) => boolean;
  hasRole: (roleName: string) => boolean;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const router = useRouter();
  const pathname = usePathname();

  const fetchProfile = useCallback(async (authToken: string): Promise<UserProfile | null> => {
    try {
      const res = await fetch(`${API_BASE}/auth/me`, {
        headers: {
          Authorization: `Bearer ${authToken}`,
          Accept: 'application/json',
        },
      });
      if (res.ok) {
        const json = await res.json();
        return json.data as UserProfile;
      }
      return null;
    } catch {
      return null;
    }
  }, []);

  useEffect(() => {
    const initAuth = async () => {
      try {
        const savedToken = localStorage.getItem('token') || localStorage.getItem('access_token');
        if (savedToken) {
          setToken(savedToken);
          const profile = await fetchProfile(savedToken);
          if (profile) {
            setUser(profile);
            // If user must change password and not currently on change-password page, redirect
            if (profile.must_change_password && pathname !== '/change-password') {
              router.push('/change-password');
            }
          } else {
            // Expired or invalid token
            localStorage.removeItem('token');
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            setToken(null);
            setUser(null);
          }
        }
      } catch {
        // Fallback for storage or parse issues
      } finally {
        setIsLoading(false);
      }
    };

    initAuth();
  }, [fetchProfile, pathname, router]);

  const login = async (username: string, password: string) => {
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        body: JSON.stringify({ username, password }),
      });

      const body = await res.json();

      if (!res.ok) {
        const errorMsg = body?.detail || body?.message || 'Authentication failed. Please check your credentials.';
        return { success: false, error: typeof errorMsg === 'string' ? errorMsg : JSON.stringify(errorMsg) };
      }

      const loginData = body.data;
      const accessToken = loginData.access_token;
      const refreshToken = loginData.refresh_token;

      localStorage.setItem('token', accessToken);
      localStorage.setItem('access_token', accessToken);
      if (refreshToken) {
        localStorage.setItem('refresh_token', refreshToken);
      }
      setToken(accessToken);

      const profile = await fetchProfile(accessToken);
      if (profile) {
        setUser(profile);
        if (profile.must_change_password) {
          router.push('/change-password');
          return { success: true, mustChangePassword: true };
        }

        // Determine destination based on roles
        const isLecturer = profile.roles.includes('LECTURER');
        const isAdmin = profile.roles.some((r) =>
          ['SUPER_ADMIN', 'SYSTEM_ADMIN', 'FACULTY_DEAN', 'DEPARTMENT_HEAD', 'AUDITOR'].includes(r)
        );

        if (isAdmin) {
          router.push('/admin');
        } else if (isLecturer) {
          router.push('/lecturer');
        } else {
          router.push('/admin');
        }

        return { success: true, mustChangePassword: false };
      }

      return { success: false, error: 'Failed to retrieve profile after authentication.' };
    } catch (err: any) {
      return { success: false, error: err?.message || 'Network error occurred during sign in.' };
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    try {
      if (token) {
        await fetch(`${API_BASE}/auth/logout`, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            Accept: 'application/json',
          },
        });
      }
    } catch {
      // Ignore network errors on logout
    } finally {
      localStorage.removeItem('token');
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      setToken(null);
      setUser(null);
      router.push('/login');
    }
  };

  const changePassword = async (currentPassword: string, newPassword: string) => {
    if (!token) {
      return { success: false, error: 'Session expired. Please log in again.' };
    }

    try {
      const res = await fetch(`${API_BASE}/auth/change-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
          Accept: 'application/json',
        },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });

      const body = await res.json();
      if (!res.ok) {
        const errorMsg = body?.detail || body?.message || 'Failed to update password.';
        return { success: false, error: typeof errorMsg === 'string' ? errorMsg : JSON.stringify(errorMsg) };
      }

      // Refresh profile to reflect must_change_password = false
      const updated = await fetchProfile(token);
      if (updated) {
        setUser(updated);
      }

      return { success: true };
    } catch (err: any) {
      return { success: false, error: err?.message || 'Network error during password update.' };
    }
  };

  const hasPermission = useCallback(
    (permissionCode: string): boolean => {
      if (!user) return false;
      return user.permissions.includes(permissionCode) || user.roles.includes('SUPER_ADMIN');
    },
    [user]
  );

  const hasRole = useCallback(
    (roleName: string): boolean => {
      if (!user) return false;
      return user.roles.includes(roleName);
    },
    [user]
  );

  const refreshUser = useCallback(async () => {
    if (token) {
      const profile = await fetchProfile(token);
      if (profile) {
        setUser(profile);
      }
    }
  }, [token, fetchProfile]);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        login,
        logout,
        changePassword,
        hasPermission,
        hasRole,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
