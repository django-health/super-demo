import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { Platform } from 'react-native';

import { api } from './api';
import * as storage from './storage';

const TOKEN_KEY = 'superdemo.token';
const USERNAME_KEY = 'superdemo.username';

interface AuthState {
  token: string | null;
  username: string | null;
  ready: boolean;
  signIn: (username: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

function deviceName(): string {
  return Platform.select({
    ios: 'iPhone app',
    android: 'Android app',
    default: 'Web app',
  });
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [username, setUsername] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    Promise.all([storage.getItem(TOKEN_KEY), storage.getItem(USERNAME_KEY)]).then(
      ([storedToken, storedUsername]) => {
        setToken(storedToken);
        setUsername(storedUsername);
        setReady(true);
      },
    );
  }, []);

  const signIn = async (user: string, password: string) => {
    const result = await api.login(user, password, deviceName(), Platform.OS);
    await storage.setItem(TOKEN_KEY, result.token);
    await storage.setItem(USERNAME_KEY, result.username);
    setToken(result.token);
    setUsername(result.username);
  };

  const signOut = async () => {
    if (token) {
      await api.logout(token).catch(() => {});
    }
    await storage.removeItem(TOKEN_KEY);
    await storage.removeItem(USERNAME_KEY);
    setToken(null);
    setUsername(null);
  };

  return (
    <AuthContext.Provider value={{ token, username, ready, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth must be used inside AuthProvider');
  return value;
}
