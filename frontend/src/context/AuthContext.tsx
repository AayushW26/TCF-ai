'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { fetchTraders, MOCK_TRADERS } from '@/lib/api';

interface Trader {
  id: string;
  business_name: string;
  gstin?: string;
  phone?: string;
  email?: string;
  munim_email?: string;
  state_code?: string;
}

interface AuthContextType {
  user: { email: string; name: string } | null;
  traders: Trader[];
  activeTrader: Trader | null;
  setActiveTrader: (trader: Trader) => void;
  login: (email: string) => void;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<{ email: string; name: string } | null>({
    email: 'ca.abhishek@munim.ai',
    name: 'CA Abhishek Saraf',
  });
  const [traders, setTraders] = useState<Trader[]>(MOCK_TRADERS);
  const [activeTrader, setActiveTrader] = useState<Trader | null>(MOCK_TRADERS[0]);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    async function loadData() {
      try {
        const loadedTraders = await fetchTraders();
        if (loadedTraders && loadedTraders.length > 0) {
          setTraders(loadedTraders);
          setActiveTrader(loadedTraders[0]);
        }
      } catch (err) {
        console.error('Failed to load traders:', err);
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, []);

  const login = (email: string) => {
    const newUser = { email, name: email.split('@')[0].toUpperCase() };
    setUser(newUser);
    localStorage.setItem('tcf_token', 'demo_jwt_token');
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem('tcf_token');
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        traders,
        activeTrader,
        setActiveTrader,
        login,
        logout,
        isLoading,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
