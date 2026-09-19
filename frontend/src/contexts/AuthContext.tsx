import { createContext, useContext, useState, type ReactNode } from 'react';
import type { TokenResponse } from '@/schemas/auth';
import { login as apiLogin, register as apiRegister } from '@/api/auth';
import type { LoginRequest, RegisterRequest } from '@/schemas/auth';

interface AuthState {
  token: string | null;
  tenantId: string | null;
  userId: string | null;
  isAuthenticated: boolean;
}

interface AuthContextType extends AuthState {
  login: (data: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    token: localStorage.getItem('token'),
    tenantId: localStorage.getItem('tenantId'),
    userId: localStorage.getItem('userId'),
    isAuthenticated: !!localStorage.getItem('token'),
  });

  const handleAuth = (data: TokenResponse) => {
    localStorage.setItem('token', data.access_token);
    localStorage.setItem('tenantId', data.tenant_id);
    localStorage.setItem('userId', data.user_id);
    setState({
      token: data.access_token,
      tenantId: data.tenant_id,
      userId: data.user_id,
      isAuthenticated: true,
    });
  };

  const login = async (data: LoginRequest) => {
    const res = await apiLogin(data);
    handleAuth(res);
  };

  const register = async (data: RegisterRequest) => {
    const res = await apiRegister(data);
    handleAuth(res);
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('tenantId');
    localStorage.removeItem('userId');
    setState({
      token: null,
      tenantId: null,
      userId: null,
      isAuthenticated: false,
    });
  };

  return (
    <AuthContext.Provider value={{ ...state, login, register, logout }}>
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
