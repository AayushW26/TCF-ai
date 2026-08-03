'use client';

import React, { useEffect, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { 
  fetchSummary, 
  fetchActions, 
  fetchTimeline, 
  fetchSuppliers, 
  fetchInvoices,
  triggerReconciliation 
} from '@/lib/api';
import { ActionQueue } from '@/components/ActionQueue';
import { ITCTimelineChart } from '@/components/ITCTimelineChart';
import { SupplierHealthTable } from '@/components/SupplierHealthTable';
import { Gstr2bReconciler } from '@/components/Gstr2bReconciler';
import { VendorWarningModal } from '@/components/VendorWarningModal';
import { 
  ShieldCheck, 
  AlertTriangle, 
  CheckCircle2, 
  XCircle, 
  FileText, 
  Download, 
  Search, 
  Filter,
  Sparkles,
  Building2
} from 'lucide-react';

export default function CADashboardPage() {
  const { activeTrader } = useAuth();
  
  const [summary, setSummary] = useState<any>(null);
  const [actions, setActions] = useState<any[]>([]);
  const [timeline, setTimeline] = useState<any[]>([]);
  const [suppliers, setSuppliers] = useState<any[]>([]);
  const [invoices, setInvoices] = useState<any[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');

  const [selectedActionForWarning, setSelectedActionForWarning] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isGeneratingPdf, setIsGeneratingPdf] = useState(false);

  const loadDashboardData = async () => {
    if (!activeTrader) return;
    setIsLoading(true);
    try {
      const [sumData, actData, timeData, supData, invData] = await Promise.all([
        fetchSummary(activeTrader.id),
        fetchActions(activeTrader.id),
        fetchTimeline(activeTrader.id),
        fetchSuppliers(activeTrader.id),
        fetchInvoices(activeTrader.id),
      ]);

      setSummary(sumData);
      setActions(actData);
      setTimeline(timeData);
      setSuppliers(supData);
      setInvoices(invData);
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, [activeTrader]);

  const handleGeneratePdf = () => {
    setIsGeneratingPdf(true);
    setTimeout(() => {
      setIsGeneratingPdf(false);
      window.open(`/api/v1/dashboard/reports/generate/${activeTrader?.id || 'demo'}`, '_blank');
    }, 1200);
  };

  const filteredInvoices = invoices.filter((inv) => {
    const matchesSearch =
      (inv.supplier_name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (inv.invoice_number || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (inv.supplier_gstin || '').toLowerCase().includes(searchQuery.toLowerCase());

    const matchesStatus = statusFilter === 'ALL' || inv.itc_status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const itc = summary?.itc_summary || {
    total_itc: 485200,
    confirmed: 312000,
    at_risk: 84500,
    fixable_blocked: 42300,
    fraud_flagged: 18000
  };

  return (
    <div className="space-y-8 pb-16">
      
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 glass-panel p-6 rounded-3xl border border-white/10 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-80 h-80 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />

        <div>
          <div className="flex items-center space-x-2 text-xs font-semibold text-emerald-400 mb-1">
            <Building2 className="w-4 h-4" />
            <span>Active Account: {activeTrader?.business_name || 'Shree Ganesh Traders'}</span>
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold text-white">
            GST Compliance Control Center
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Multi-Tenant CA Overview — Real-time invoice risk analysis & GSTR-2B reconciliation
          </p>
        </div>

        {/* Generate Report Button */}
        <button
          onClick={handleGeneratePdf}
          disabled={isGeneratingPdf}
          className="flex items-center space-x-2 px-5 py-2.5 rounded-xl text-xs font-bold bg-gradient-to-r from-emerald-500 to-sky-500 hover:from-emerald-400 hover:to-sky-400 text-slate-950 transition-all glow-emerald shadow-lg disabled:opacity-50"
        >
          <Download className="w-4 h-4" />
          <span>{isGeneratingPdf ? 'Generating PDF...' : 'Download Compliance Report'}</span>
        </button>
      </div>

      {/* 5 KPI Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        
        {/* Total ITC */}
        <div className="glass-card p-5 rounded-2xl border border-white/10 relative overflow-hidden">
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
            Total Inward ITC
          </div>
          <div className="text-2xl font-extrabold text-white mt-1">
            ₹{itc.total_itc?.toLocaleString('en-IN', { minimumFractionDigits: 0 })}
          </div>
          <div className="text-[10px] text-slate-400 mt-2 flex items-center justify-between border-t border-white/5 pt-2">
            <span>{summary?.recent_invoices || 12} Invoices</span>
            <span className="text-emerald-400 font-semibold">100% Total</span>
          </div>
        </div>

        {/* Confirmed ITC */}
        <div className="glass-card p-5 rounded-2xl border border-emerald-500/30 relative overflow-hidden bg-emerald-500/5 glow-emerald">
          <div className="text-[11px] font-semibold text-emerald-400 uppercase tracking-wider flex items-center justify-between">
            <span>Confirmed ITC</span>
            <CheckCircle2 className="w-4 h-4" />
          </div>
          <div className="text-2xl font-extrabold text-emerald-300 mt-1">
            ₹{itc.confirmed?.toLocaleString('en-IN', { minimumFractionDigits: 0 })}
          </div>
          <div className="text-[10px] text-emerald-400/80 mt-2 flex items-center justify-between border-t border-emerald-500/20 pt-2">
            <span>Clean §16 Claims</span>
            <span className="font-bold">{((itc.confirmed / (itc.total_itc || 1)) * 100).toFixed(0)}%</span>
          </div>
        </div>

        {/* At Risk ITC */}
        <div className="glass-card p-5 rounded-2xl border border-amber-500/30 relative overflow-hidden bg-amber-500/5 glow-amber">
          <div className="text-[11px] font-semibold text-amber-400 uppercase tracking-wider flex items-center justify-between">
            <span>ITC At Risk</span>
            <AlertTriangle className="w-4 h-4" />
          </div>
          <div className="text-2xl font-extrabold text-amber-300 mt-1">
            ₹{itc.at_risk?.toLocaleString('en-IN', { minimumFractionDigits: 0 })}
          </div>
          <div className="text-[10px] text-amber-400/80 mt-2 flex items-center justify-between border-t border-amber-500/20 pt-2">
            <span>GSTR-2B Unmatched</span>
            <span className="font-bold">{((itc.at_risk / (itc.total_itc || 1)) * 100).toFixed(0)}%</span>
          </div>
        </div>

        {/* Blocked Credits */}
        <div className="glass-card p-5 rounded-2xl border border-sky-500/30 relative overflow-hidden bg-sky-500/5 glow-sky">
          <div className="text-[11px] font-semibold text-sky-400 uppercase tracking-wider flex items-center justify-between">
            <span>Blocked §17(5)</span>
            <XCircle className="w-4 h-4" />
          </div>
          <div className="text-2xl font-extrabold text-sky-300 mt-1">
            ₹{itc.fixable_blocked?.toLocaleString('en-IN', { minimumFractionDigits: 0 })}
          </div>
          <div className="text-[10px] text-sky-400/80 mt-2 flex items-center justify-between border-t border-sky-500/20 pt-2">
            <span>Ineligible Invoices</span>
            <span className="font-bold">{((itc.fixable_blocked / (itc.total_itc || 1)) * 100).toFixed(0)}%</span>
          </div>
        </div>

        {/* Fraud Flagged */}
        <div className="glass-card p-5 rounded-2xl border border-rose-500/30 relative overflow-hidden bg-rose-500/5 glow-rose">
          <div className="text-[11px] font-semibold text-rose-400 uppercase tracking-wider flex items-center justify-between">
            <span>Fraud Flagged</span>
            <ShieldCheck className="w-4 h-4" />
          </div>
          <div className="text-2xl font-extrabold text-rose-300 mt-1">
            ₹{itc.fraud_flagged?.toLocaleString('en-IN', { minimumFractionDigits: 0 })}
          </div>
          <div className="text-[10px] text-rose-400/80 mt-2 flex items-center justify-between border-t border-rose-500/20 pt-2">
            <span>Score ≥ 70 Risk</span>
            <span className="font-bold">{((itc.fraud_flagged / (itc.total_itc || 1)) * 100).toFixed(0)}%</span>
          </div>
        </div>

      </div>

      {/* Prioritized Action Queue */}
      <ActionQueue
        actions={actions}
        onOpenVendorWarning={(action) => setSelectedActionForWarning(action)}
        onRefresh={loadDashboardData}
      />

      {/* 6-Month Timeline Chart & GSTR-2B Suite */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <ITCTimelineChart data={timeline} />
        <Gstr2bReconciler traderId={activeTrader?.id || 'demo'} onReconciliationComplete={loadDashboardData} />
      </div>

      {/* Supplier Health Monitor */}
      <SupplierHealthTable suppliers={suppliers} />

      {/* Invoice Vault / Explorer Table */}
      <div className="glass-panel rounded-2xl p-6 border border-white/10">
        
        {/* Header & Controls */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <FileText className="w-5 h-5 text-emerald-400" />
              <span>Extracted Invoice Vault</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Multimodal Gemini OCR invoices parsed from WhatsApp, Email, & Uploads
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Search Input */}
            <div className="relative">
              <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Search supplier, GSTIN, invoice #..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="bg-slate-900/80 border border-white/10 rounded-xl pl-9 pr-4 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500/50 w-64"
              />
            </div>

            {/* Filter Dropdown */}
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-slate-900/80 border border-white/10 rounded-xl px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-emerald-500/50"
            >
              <option value="ALL">All Statuses</option>
              <option value="CONFIRMED">Confirmed ✅</option>
              <option value="AT_RISK">At Risk ⚠️</option>
              <option value="INELIGIBLE">Ineligible ❌</option>
              <option value="FRAUD_FLAGGED">Fraud Flagged 🚨</option>
            </select>
          </div>
        </div>

        {/* Invoice Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-white/10 text-slate-400 font-semibold uppercase text-[10px] tracking-wider">
                <th className="pb-3 px-3">Invoice # & Date</th>
                <th className="pb-3 px-3">Supplier Name & GSTIN</th>
                <th className="pb-3 px-3 text-right">Taxable Value</th>
                <th className="pb-3 px-3 text-right">Total Tax</th>
                <th className="pb-3 px-3 text-center">ITC Status</th>
                <th className="pb-3 px-3 text-center">Fraud Score</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {filteredInvoices.map((inv) => {
                const totalTax = (inv.cgst || 0) + (inv.sgst || 0) + (inv.igst || 0) + (inv.cess || 0);
                return (
                  <tr key={inv.id} className="hover:bg-white/5 transition-colors">
                    
                    <td className="py-3.5 px-3">
                      <div className="font-semibold text-slate-200 font-mono">
                        {inv.invoice_number || 'N/A'}
                      </div>
                      <div className="text-[11px] text-slate-400 mt-0.5">
                        {inv.invoice_date || 'N/A'}
                      </div>
                    </td>

                    <td className="py-3.5 px-3">
                      <div className="font-semibold text-slate-200">
                        {inv.supplier_name || 'Unknown Supplier'}
                      </div>
                      <div className="text-[11px] text-slate-400 font-mono mt-0.5">
                        {inv.supplier_gstin || 'No GSTIN'}
                      </div>
                    </td>

                    <td className="py-3.5 px-3 text-right font-medium text-slate-300">
                      ₹{inv.total_taxable_value?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </td>

                    <td className="py-3.5 px-3 text-right font-bold text-white">
                      ₹{totalTax.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </td>

                    <td className="py-3.5 px-3 text-center">
                      <span className={`inline-block px-2.5 py-1 rounded-md text-[10px] font-bold ${
                        inv.itc_status === 'CONFIRMED' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' :
                        inv.itc_status === 'AT_RISK' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30' :
                        inv.itc_status === 'FRAUD_FLAGGED' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30' :
                        'bg-sky-500/20 text-sky-300 border border-sky-500/30'
                      }`}>
                        {inv.itc_status}
                      </span>
                    </td>

                    <td className="py-3.5 px-3 text-center">
                      <span className={`font-mono text-xs font-bold ${inv.fraud_score >= 70 ? 'text-rose-400' : 'text-slate-300'}`}>
                        {inv.fraud_score}/100
                      </span>
                    </td>

                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

      </div>

      {/* Vendor Warning Modal */}
      <VendorWarningModal
        action={selectedActionForWarning}
        onClose={() => setSelectedActionForWarning(null)}
        onSuccess={loadDashboardData}
      />

    </div>
  );
}
