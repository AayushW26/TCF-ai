'use client';

import React from 'react';
import { Users, AlertTriangle, CheckCircle, ShieldAlert, Calendar } from 'lucide-react';

interface Supplier {
  supplier_gstin: string;
  supplier_name?: string;
  compliance_score: number;
  total_months_tracked: number;
  months_filed: number;
  total_invoice_count: number;
  total_invoice_value: number;
  is_flagged: boolean;
  flag_reason?: string;
  last_invoice_date?: string;
}

interface SupplierHealthTableProps {
  suppliers: Supplier[];
}

export const SupplierHealthTable: React.FC<SupplierHealthTableProps> = ({ suppliers }) => {
  return (
    <div className="glass-panel rounded-2xl p-6 border border-white/10">
      
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-2">
            <Users className="w-5 h-5 text-emerald-400" />
            <h2 className="text-lg font-bold text-white">Supplier Health & Compliance</h2>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            GSTR-1 filing consistency scores across all active vendor accounts
          </p>
        </div>

        <div className="text-xs font-semibold text-slate-400 bg-slate-900/60 px-3 py-1.5 rounded-lg border border-white/5">
          Flagged Vendors: <span className="text-rose-400 font-bold">{suppliers.filter(s => s.is_flagged).length}</span> / {suppliers.length}
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="border-b border-white/10 text-slate-400 font-semibold uppercase text-[10px] tracking-wider">
              <th className="pb-3 px-3">Supplier Name & GSTIN</th>
              <th className="pb-3 px-3">Filing Consistency</th>
              <th className="pb-3 px-3 text-center">Compliance Score</th>
              <th className="pb-3 px-3 text-right">Total Business</th>
              <th className="pb-3 px-3 text-center">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {suppliers.map((sup) => {
              const isLow = sup.compliance_score < 60;
              return (
                <tr key={sup.supplier_gstin} className="hover:bg-white/5 transition-colors">
                  
                  {/* Name & GSTIN */}
                  <td className="py-3.5 px-3">
                    <div className="font-semibold text-slate-200">
                      {sup.supplier_name || 'Unknown Supplier'}
                    </div>
                    <div className="text-[11px] text-slate-400 font-mono mt-0.5">
                      {sup.supplier_gstin}
                    </div>
                  </td>

                  {/* Filing Consistency Bar */}
                  <td className="py-3.5 px-3">
                    <div className="flex items-center space-x-3">
                      <div className="w-24 bg-slate-800 h-2 rounded-full overflow-hidden border border-white/5">
                        <div
                          className={`h-full rounded-full transition-all ${
                            isLow ? 'bg-rose-500' : 'bg-emerald-400 glow-emerald'
                          }`}
                          style={{ width: `${sup.compliance_score}%` }}
                        />
                      </div>
                      <span className="text-[11px] text-slate-300 font-medium">
                        {sup.months_filed} / {sup.total_months_tracked} mos
                      </span>
                    </div>
                  </td>

                  {/* Compliance Score Pill */}
                  <td className="py-3.5 px-3 text-center">
                    <span
                      className={`inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold ${
                        isLow
                          ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                          : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                      }`}
                    >
                      {sup.compliance_score.toFixed(0)}%
                    </span>
                  </td>

                  {/* Total Business */}
                  <td className="py-3.5 px-3 text-right font-semibold text-slate-200">
                    ₹{sup.total_invoice_value?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                  </td>

                  {/* Status Flag */}
                  <td className="py-3.5 px-3 text-center">
                    {sup.is_flagged ? (
                      <span className="inline-flex items-center gap-1 text-[10px] font-bold text-rose-400 bg-rose-500/10 px-2 py-1 rounded border border-rose-500/20">
                        <ShieldAlert className="w-3 h-3" /> Flagged
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-400 bg-emerald-500/10 px-2 py-1 rounded border border-emerald-500/20">
                        <CheckCircle className="w-3 h-3" /> Compliant
                      </span>
                    )}
                  </td>

                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

    </div>
  );
};
