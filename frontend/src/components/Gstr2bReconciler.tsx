'use client';

import React, { useState } from 'react';
import { UploadCloud, RefreshCw, CheckCircle2, FileJson, AlertCircle, Layers } from 'lucide-react';
import { triggerReconciliation } from '@/lib/api';

interface Gstr2bReconcilerProps {
  traderId: string;
  onReconciliationComplete: () => void;
}

export const Gstr2bReconciler: React.FC<Gstr2bReconcilerProps> = ({ traderId, onReconciliationComplete }) => {
  const [isRunning, setIsRunning] = useState(false);
  const [reconResult, setReconResult] = useState<any | null>(null);

  const handleRunReconciliation = async () => {
    setIsRunning(true);
    try {
      const result = await triggerReconciliation(traderId);
      setReconResult(result);
      onReconciliationComplete();
    } catch (err) {
      console.error('Reconciliation failed:', err);
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="glass-panel rounded-2xl p-6 border border-white/10 relative overflow-hidden">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2">
            <Layers className="w-5 h-5 text-emerald-400" />
            <h2 className="text-lg font-bold text-white">GSTR-2B 3-Pass Reconciliation</h2>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Exact match → Levenshtein fuzzy match → Amount & Date fallback engine
          </p>
        </div>

        <button
          onClick={handleRunReconciliation}
          disabled={isRunning}
          className="flex items-center space-x-2 px-5 py-2.5 rounded-xl text-xs font-bold bg-gradient-to-r from-emerald-500 to-sky-500 hover:from-emerald-400 hover:to-sky-400 text-slate-950 transition-all glow-emerald disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${isRunning ? 'animate-spin' : ''}`} />
          <span>{isRunning ? 'Matching Invoices...' : 'Run 3-Pass Reconciliation'}</span>
        </button>
      </div>

      {/* File Dropzone & Status */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        
        {/* Dropzone Card */}
        <div className="border-2 border-dashed border-white/10 hover:border-emerald-500/30 rounded-xl p-5 text-center bg-slate-900/40 transition-all group cursor-pointer flex flex-col items-center justify-center">
          <FileJson className="w-8 h-8 text-emerald-400 mb-2 group-hover:scale-110 transition-transform" />
          <p className="text-xs font-bold text-slate-200">Upload GSTR-2B JSON</p>
          <p className="text-[10px] text-slate-400 mt-1">
            Drag & drop official GST portal GSTR-2B JSON file here
          </p>
        </div>

        {/* Results Panel */}
        <div className="bg-slate-900/60 rounded-xl p-5 border border-white/5">
          {reconResult ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between text-xs border-b border-white/10 pb-2">
                <span className="font-bold text-emerald-400 flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4" /> Pass 1 (Exact Matches):
                </span>
                <span className="font-mono text-white font-bold">{reconResult.exact_matches}</span>
              </div>

              <div className="flex items-center justify-between text-xs border-b border-white/10 pb-2">
                <span className="font-bold text-amber-400 flex items-center gap-1.5">
                  <RefreshCw className="w-3.5 h-3.5" /> Pass 2 (Fuzzy Matches):
                </span>
                <span className="font-mono text-white font-bold">{reconResult.fuzzy_matches}</span>
              </div>

              <div className="flex items-center justify-between text-xs border-b border-white/10 pb-2">
                <span className="font-bold text-sky-400 flex items-center gap-1.5">
                  <Layers className="w-3.5 h-3.5" /> Pass 3 (Amount+Date Matches):
                </span>
                <span className="font-mono text-white font-bold">{reconResult.amount_date_matches}</span>
              </div>

              <div className="flex items-center justify-between text-xs pt-1">
                <span className="font-bold text-rose-400 flex items-center gap-1.5">
                  <AlertCircle className="w-3.5 h-3.5" /> Unmatched (Risk Actions):
                </span>
                <span className="font-mono text-rose-300 font-bold">{reconResult.unmatched_invoices}</span>
              </div>
            </div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-center text-slate-400 py-6">
              <Layers className="w-7 h-7 text-slate-500 mb-2" />
              <p className="text-xs font-medium">No reconciliation run yet for current period.</p>
              <p className="text-[10px] text-slate-500 mt-0.5">Click "Run 3-Pass Reconciliation" above to execute.</p>
            </div>
          )}
        </div>

      </div>

    </div>
  );
};
