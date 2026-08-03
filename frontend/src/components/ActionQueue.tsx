'use client';

import React, { useState } from 'react';
import { 
  AlertTriangle, 
  ShieldAlert, 
  Wrench, 
  Send, 
  CheckCircle2, 
  Clock, 
  Building, 
  ArrowRight,
  Sparkles
} from 'lucide-react';
import { resolveAction } from '@/lib/api';

interface ActionItem {
  id: string;
  trader_id: string;
  action_type: string;
  severity: string;
  title: string;
  description: string;
  affected_amount: number;
  recommended_fix?: string;
  vendor_gstin?: string;
  vendor_name?: string;
  vendor_phone?: string;
  is_resolved: boolean;
}

interface ActionQueueProps {
  actions: ActionItem[];
  onOpenVendorWarning: (action: ActionItem) => void;
  onRefresh: () => void;
}

export const ActionQueue: React.FC<ActionQueueProps> = ({ actions, onOpenVendorWarning, onRefresh }) => {
  const [filter, setFilter] = useState<'ALL' | 'FRAUD_FLAG' | 'ITC_AT_RISK' | 'FIXABLE_BLOCK'>('ALL');
  const [resolvingId, setResolvingId] = useState<string | null>(null);

  const filteredActions = actions.filter((action) => {
    if (action.is_resolved) return false;
    if (filter === 'ALL') return true;
    return action.action_type === filter;
  });

  const handleResolve = async (actionId: string) => {
    setResolvingId(actionId);
    try {
      await resolveAction(actionId, 'Resolved by CA from Dashboard');
      onRefresh();
    } catch (err) {
      console.error('Failed to resolve action:', err);
    } finally {
      setResolvingId(null);
    }
  };

  const getSeverityBadge = (severity: string) => {
    switch (severity.toUpperCase()) {
      case 'CRITICAL':
        return (
          <span className="px-2.5 py-1 rounded-md text-[10px] font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30 flex items-center gap-1 glow-rose">
            <ShieldAlert className="w-3 h-3" /> CRITICAL
          </span>
        );
      case 'HIGH':
        return (
          <span className="px-2.5 py-1 rounded-md text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center gap-1 glow-amber">
            <AlertTriangle className="w-3 h-3" /> HIGH RISK
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-1 rounded-md text-[10px] font-bold bg-sky-500/20 text-sky-300 border border-sky-500/30 flex items-center gap-1">
            <Wrench className="w-3 h-3" /> ACTION REQUIRED
          </span>
        );
    }
  };

  return (
    <div className="glass-panel rounded-2xl p-6 border border-white/10 relative overflow-hidden">
      
      {/* Background Accent */}
      <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-500/5 rounded-full blur-3xl pointer-events-none" />

      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-emerald-400" />
            <h2 className="text-lg font-bold text-white">Prioritized Action Queue</h2>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Auto-ranked compliance issues across fraud, ITC risk, and filing mismatches
          </p>
        </div>

        {/* Filter Pills */}
        <div className="flex flex-wrap gap-1.5 bg-slate-900/80 p-1.5 rounded-xl border border-white/5">
          <button
            onClick={() => setFilter('ALL')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              filter === 'ALL'
                ? 'bg-emerald-500 text-slate-950 shadow-lg glow-emerald'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            All ({actions.filter((a) => !a.is_resolved).length})
          </button>

          <button
            onClick={() => setFilter('FRAUD_FLAG')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              filter === 'FRAUD_FLAG'
                ? 'bg-rose-500 text-white shadow-lg glow-rose'
                : 'text-slate-400 hover:text-rose-300'
            }`}
          >
            Fraud (🚨)
          </button>

          <button
            onClick={() => setFilter('ITC_AT_RISK')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              filter === 'ITC_AT_RISK'
                ? 'bg-amber-500 text-slate-950 shadow-lg glow-amber'
                : 'text-slate-400 hover:text-amber-300'
            }`}
          >
            ITC Risk (⚠️)
          </button>

          <button
            onClick={() => setFilter('FIXABLE_BLOCK')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              filter === 'FIXABLE_BLOCK'
                ? 'bg-sky-500 text-slate-950 shadow-lg glow-sky'
                : 'text-slate-400 hover:text-sky-300'
            }`}
          >
            Fixable (🔧)
          </button>
        </div>
      </div>

      {/* Action Items List */}
      <div className="space-y-4">
        {filteredActions.length === 0 ? (
          <div className="text-center py-12 bg-slate-900/40 rounded-xl border border-dashed border-white/10">
            <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto mb-2 opacity-80" />
            <p className="text-sm font-semibold text-slate-200">Action Queue Clear!</p>
            <p className="text-xs text-slate-400 mt-1">No unresolved compliance issues for this filter.</p>
          </div>
        ) : (
          filteredActions.map((action) => (
            <div
              key={action.id}
              className="glass-panel-interactive rounded-xl p-5 border border-white/10 flex flex-col md:flex-row items-start md:items-center justify-between gap-4"
            >
              {/* Left Details */}
              <div className="flex-1 space-y-2">
                <div className="flex items-center flex-wrap gap-2">
                  {getSeverityBadge(action.severity)}
                  <span className="text-xs font-semibold text-slate-300">{action.title}</span>
                </div>

                <p className="text-xs text-slate-400 leading-relaxed">
                  {action.description}
                </p>

                {action.recommended_fix && (
                  <div className="text-[11px] text-emerald-300 bg-emerald-500/10 border border-emerald-500/20 px-3 py-1.5 rounded-lg font-medium">
                    💡 <span className="font-semibold">Recommended Fix:</span> {action.recommended_fix}
                  </div>
                )}

                {/* Vendor Metadata */}
                {action.vendor_name && (
                  <div className="flex items-center gap-3 text-[11px] text-slate-400 pt-1">
                    <span className="flex items-center gap-1 font-medium text-slate-300">
                      <Building className="w-3.5 h-3.5 text-slate-400" />
                      {action.vendor_name}
                    </span>
                    {action.vendor_gstin && (
                      <span className="bg-slate-800 px-2 py-0.5 rounded text-slate-300 font-mono">
                        {action.vendor_gstin}
                      </span>
                    )}
                  </div>
                )}
              </div>

              {/* Right Side: Affected Amount + Buttons */}
              <div className="flex md:flex-col items-end justify-between md:justify-center w-full md:w-auto pt-3 md:pt-0 border-t md:border-t-0 border-white/5 gap-3">
                <div className="text-left md:text-right">
                  <div className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">
                    Affected Amount
                  </div>
                  <div className="text-lg font-extrabold text-white">
                    ₹{action.affected_amount?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {/* WhatsApp Warning Button */}
                  <button
                    onClick={() => onOpenVendorWarning(action)}
                    className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-500/30 transition-all glow-emerald"
                  >
                    <Send className="w-3.5 h-3.5" />
                    <span>WhatsApp Warning</span>
                  </button>

                  {/* Resolve Button */}
                  <button
                    onClick={() => handleResolve(action.id)}
                    disabled={resolvingId === action.id}
                    className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-white/10 transition-all disabled:opacity-50"
                  >
                    {resolvingId === action.id ? 'Resolving...' : 'Resolve'}
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
