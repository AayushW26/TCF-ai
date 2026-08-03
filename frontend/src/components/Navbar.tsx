'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { 
  Building2, 
  ChevronDown, 
  LayoutDashboard, 
  MessageSquareText, 
  FileCheck2, 
  LogOut, 
  ShieldCheck, 
  Radio 
} from 'lucide-react';

export const Navbar = () => {
  const pathname = usePathname();
  const { user, traders, activeTrader, setActiveTrader, logout } = useAuth();
  const [dropdownOpen, setDropdownOpen] = useState(false);

  return (
    <nav className="sticky top-0 z-50 glass-panel border-b border-white/10 px-4 lg:px-8 py-3">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        
        {/* Brand & Logo */}
        <div className="flex items-center space-x-8">
          <Link href="/dashboard" className="flex items-center space-x-3 group">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-500 via-sky-500 to-indigo-500 p-0.5 glow-emerald">
              <div className="w-full h-full bg-navy-900 rounded-[10px] flex items-center justify-center">
                <ShieldCheck className="w-5 h-5 text-emerald-400 group-hover:scale-110 transition-transform" />
              </div>
            </div>
            <div>
              <span className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white via-slate-200 to-emerald-400">
                TCF-ai
              </span>
              <span className="text-[10px] block text-emerald-400 font-semibold tracking-wider uppercase">
                GST Compliance Co-Pilot
              </span>
            </div>
          </Link>

          {/* Navigation Links */}
          <div className="hidden md:flex items-center space-x-1 bg-slate-900/60 p-1 rounded-xl border border-white/5">
            <Link
              href="/dashboard"
              className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-medium transition-all ${
                pathname === '/dashboard'
                  ? 'bg-gradient-to-r from-emerald-500/20 to-sky-500/20 text-emerald-300 border border-emerald-500/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
              }`}
            >
              <LayoutDashboard className="w-4 h-4" />
              <span>CA Dashboard</span>
            </Link>

            <Link
              href="/demo"
              className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-medium transition-all ${
                pathname === '/demo'
                  ? 'bg-gradient-to-r from-emerald-500/20 to-sky-500/20 text-emerald-300 border border-emerald-500/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
              }`}
            >
              <FileCheck2 className="w-4 h-4" />
              <span>GST Portal Simulator</span>
            </Link>

            <Link
              href="/trader"
              className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-medium transition-all ${
                pathname === '/trader'
                  ? 'bg-gradient-to-r from-emerald-500/20 to-sky-500/20 text-emerald-300 border border-emerald-500/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
              }`}
            >
              <MessageSquareText className="w-4 h-4 text-emerald-400 animate-pulse" />
              <span>WhatsApp Ingestion</span>
            </Link>
          </div>
        </div>

        {/* Right Actions: Trader Switcher + User Info */}
        <div className="flex items-center space-x-4">
          
          {/* Backend Status Indicator */}
          <div className="hidden sm:flex items-center space-x-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium">
            <Radio className="w-3.5 h-3.5 animate-pulse" />
            <span>FastAPI Live</span>
          </div>

          {/* Trader Selection Dropdown */}
          <div className="relative">
            <button
              onClick={() => setDropdownOpen(!dropdownOpen)}
              className="flex items-center space-x-3 bg-slate-800/80 hover:bg-slate-700/80 border border-white/10 px-3.5 py-2 rounded-xl text-xs font-medium transition-all"
            >
              <div className="w-6 h-6 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold">
                <Building2 className="w-3.5 h-3.5" />
              </div>
              <div className="text-left hidden sm:block">
                <div className="text-slate-200 font-semibold max-w-[140px] truncate">
                  {activeTrader?.business_name || 'Select Trader'}
                </div>
                <div className="text-[10px] text-slate-400">
                  {activeTrader?.gstin || 'GSTIN Pending'}
                </div>
              </div>
              <ChevronDown className="w-4 h-4 text-slate-400" />
            </button>

            {dropdownOpen && (
              <div className="absolute right-0 mt-2 w-64 glass-panel rounded-2xl shadow-2xl py-2 z-50 border border-white/10 animate-in fade-in slide-in-from-top-2">
                <div className="px-3 py-1.5 text-[11px] font-semibold text-slate-400 uppercase tracking-wider border-b border-white/5">
                  Select Trader Account
                </div>
                <div className="max-h-60 overflow-y-auto py-1">
                  {traders.map((t) => (
                    <button
                      key={t.id}
                      onClick={() => {
                        setActiveTrader(t);
                        setDropdownOpen(false);
                      }}
                      className={`w-full text-left px-3 py-2 text-xs flex items-center justify-between hover:bg-emerald-500/10 transition-colors ${
                        activeTrader?.id === t.id ? 'bg-emerald-500/15 text-emerald-300 font-semibold' : 'text-slate-300'
                      }`}
                    >
                      <div className="truncate">
                        <div className="font-medium truncate">{t.business_name}</div>
                        <div className="text-[10px] text-slate-400">{t.gstin || 'No GSTIN'}</div>
                      </div>
                      {activeTrader?.id === t.id && (
                        <div className="w-2 h-2 rounded-full bg-emerald-400 glow-emerald" />
                      )}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* User Profile */}
          {user && (
            <button
              onClick={logout}
              title="Logout"
              className="p-2 rounded-xl text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-all border border-transparent hover:border-rose-500/20"
            >
              <LogOut className="w-4 h-4" />
            </button>
          )}

        </div>
      </div>
    </nav>
  );
};
