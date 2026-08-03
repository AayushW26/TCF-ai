'use client';

import React, { useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { FileCheck, ShieldCheck, CheckCircle, XCircle, Clock, AlertTriangle, ArrowRight } from 'lucide-react';

export default function GstPortalSimulationPage() {
  const { activeTrader } = useAuth();
  const [activeTab, setActiveTab] = useState<'IMS' | 'GSTR3B'>('IMS');
  const [imsActions, setImsActions] = useState<Record<string, 'ACCEPT' | 'REJECT' | 'PENDING'>>({
    'inv-101': 'REJECT',
    'inv-102': 'ACCEPT',
    'inv-103': 'PENDING',
    'inv-104': 'REJECT',
  });

  const handleAction = (invId: string, action: 'ACCEPT' | 'REJECT' | 'PENDING') => {
    setImsActions((prev) => ({ ...prev, [invId]: action }));
  };

  return (
    <div className="space-y-6 pb-16">
      
      {/* Header Banner */}
      <div className="glass-panel p-6 rounded-3xl border border-white/10 relative overflow-hidden">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2 text-xs font-semibold text-sky-400 mb-1">
              <FileCheck className="w-4 h-4" />
              <span>Official GST Portal Demo & Training Simulation</span>
            </div>
            <h1 className="text-2xl font-extrabold text-white">
              Invoice Management System (IMS) & GSTR-3B Auto-Draft
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              Context-aware simulation mirroring government portal actions for trader: <strong className="text-slate-200">{activeTrader?.business_name || 'Shree Ganesh Traders'}</strong>
            </p>
          </div>

          <div className="flex items-center space-x-2 bg-slate-900/80 p-1.5 rounded-xl border border-white/10">
            <button
              onClick={() => setActiveTab('IMS')}
              className={`px-4 py-2 rounded-lg text-xs font-bold transition-all ${
                activeTab === 'IMS'
                  ? 'bg-sky-500 text-slate-950 glow-sky'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              IMS Action Desk
            </button>
            <button
              onClick={() => setActiveTab('GSTR3B')}
              className={`px-4 py-2 rounded-lg text-xs font-bold transition-all ${
                activeTab === 'GSTR3B'
                  ? 'bg-emerald-500 text-slate-950 glow-emerald'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              GSTR-3B Auto-Draft
            </button>
          </div>
        </div>
      </div>

      {activeTab === 'IMS' ? (
        /* IMS Interface */
        <div className="glass-panel rounded-2xl p-6 border border-white/10 space-y-6">
          <div className="flex items-center justify-between border-b border-white/10 pb-4">
            <div>
              <h2 className="text-base font-bold text-white">Recipient Action Desk — IMS Portal</h2>
              <p className="text-xs text-slate-400">Accept, Reject, or Pending invoices filed by suppliers in GSTR-1</p>
            </div>
            <div className="text-xs text-slate-300 bg-slate-900/60 px-3 py-1.5 rounded-lg border border-white/5">
              Period: <span className="text-emerald-400 font-bold">July 2026</span>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-white/10 text-slate-400 font-semibold uppercase text-[10px] tracking-wider">
                  <th className="pb-3 px-3">Supplier GSTIN & Name</th>
                  <th className="pb-3 px-3">Invoice # & Date</th>
                  <th className="pb-3 px-3 text-right">Taxable Value</th>
                  <th className="pb-3 px-3 text-right">Eligible Tax</th>
                  <th className="pb-3 px-3 text-center">TCF-ai AI Recommendation</th>
                  <th className="pb-3 px-3 text-center">IMS Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                
                {/* Inv 101 - Fraud */}
                <tr className="hover:bg-white/5 transition-colors">
                  <td className="py-4 px-3">
                    <div className="font-semibold text-slate-200">Mahavir Logistics & Transport</div>
                    <div className="text-[11px] text-slate-400 font-mono">27AABCM9012K1ZX</div>
                  </td>
                  <td className="py-4 px-3 font-mono">
                    <div>INV-904</div>
                    <div className="text-[11px] text-slate-400">2026-08-01</div>
                  </td>
                  <td className="py-4 px-3 text-right font-medium">₹50,000.00</td>
                  <td className="py-4 px-3 text-right font-bold text-white">₹9,000.00</td>
                  <td className="py-4 px-3 text-center">
                    <span className="px-2.5 py-1 rounded text-[10px] font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30">
                      🚨 REJECT (Fraud Score 78/100)
                    </span>
                  </td>
                  <td className="py-4 px-3 text-center">
                    <div className="flex items-center justify-center space-x-1.5">
                      <button
                        onClick={() => handleAction('inv-101', 'ACCEPT')}
                        className={`px-2.5 py-1 rounded text-[10px] font-bold transition-all ${
                          imsActions['inv-101'] === 'ACCEPT' ? 'bg-emerald-500 text-slate-950' : 'bg-slate-800 text-slate-400 hover:text-white'
                        }`}
                      >
                        Accept
                      </button>
                      <button
                        onClick={() => handleAction('inv-101', 'REJECT')}
                        className={`px-2.5 py-1 rounded text-[10px] font-bold transition-all ${
                          imsActions['inv-101'] === 'REJECT' ? 'bg-rose-500 text-white shadow-lg glow-rose' : 'bg-slate-800 text-slate-400 hover:text-white'
                        }`}
                      >
                        Reject
                      </button>
                    </div>
                  </td>
                </tr>

                {/* Inv 102 - Confirmed */}
                <tr className="hover:bg-white/5 transition-colors">
                  <td className="py-4 px-3">
                    <div className="font-semibold text-slate-200">Bajaj Raw Materials Pvt Ltd</div>
                    <div className="text-[11px] text-slate-400 font-mono">27AAACB1122D1Z4</div>
                  </td>
                  <td className="py-4 px-3 font-mono">
                    <div>BRM-2026-089</div>
                    <div className="text-[11px] text-slate-400">2026-08-02</div>
                  </td>
                  <td className="py-4 px-3 text-right font-medium">₹1,20,000.00</td>
                  <td className="py-4 px-3 text-right font-bold text-white">₹21,600.00</td>
                  <td className="py-4 px-3 text-center">
                    <span className="px-2.5 py-1 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                      ✅ ACCEPT (Clean §16 Claim)
                    </span>
                  </td>
                  <td className="py-4 px-3 text-center">
                    <div className="flex items-center justify-center space-x-1.5">
                      <button
                        onClick={() => handleAction('inv-102', 'ACCEPT')}
                        className={`px-2.5 py-1 rounded text-[10px] font-bold transition-all ${
                          imsActions['inv-102'] === 'ACCEPT' ? 'bg-emerald-500 text-slate-950 shadow-lg glow-emerald' : 'bg-slate-800 text-slate-400 hover:text-white'
                        }`}
                      >
                        Accept
                      </button>
                      <button
                        onClick={() => handleAction('inv-102', 'REJECT')}
                        className={`px-2.5 py-1 rounded text-[10px] font-bold transition-all ${
                          imsActions['inv-102'] === 'REJECT' ? 'bg-rose-500 text-white' : 'bg-slate-800 text-slate-400 hover:text-white'
                        }`}
                      >
                        Reject
                      </button>
                    </div>
                  </td>
                </tr>

                {/* Inv 104 - Ineligible */}
                <tr className="hover:bg-white/5 transition-colors">
                  <td className="py-4 px-3">
                    <div className="font-semibold text-slate-200">Unnati Motors Pvt Ltd</div>
                    <div className="text-[11px] text-slate-400 font-mono">27AAACU1122K1Z3</div>
                  </td>
                  <td className="py-4 px-3 font-mono">
                    <div>VH-882</div>
                    <div className="text-[11px] text-slate-400">2026-07-29</div>
                  </td>
                  <td className="py-4 px-3 text-right font-medium">₹8,50,000.00</td>
                  <td className="py-4 px-3 text-right font-bold text-white">₹1,53,000.00</td>
                  <td className="py-4 px-3 text-center">
                    <span className="px-2.5 py-1 rounded text-[10px] font-bold bg-sky-500/20 text-sky-300 border border-sky-500/30">
                      ❌ REJECT / BLOCK (§17(5)(a))
                    </span>
                  </td>
                  <td className="py-4 px-3 text-center">
                    <div className="flex items-center justify-center space-x-1.5">
                      <button
                        onClick={() => handleAction('inv-104', 'ACCEPT')}
                        className={`px-2.5 py-1 rounded text-[10px] font-bold transition-all ${
                          imsActions['inv-104'] === 'ACCEPT' ? 'bg-emerald-500 text-slate-950' : 'bg-slate-800 text-slate-400 hover:text-white'
                        }`}
                      >
                        Accept
                      </button>
                      <button
                        onClick={() => handleAction('inv-104', 'REJECT')}
                        className={`px-2.5 py-1 rounded text-[10px] font-bold transition-all ${
                          imsActions['inv-104'] === 'REJECT' ? 'bg-rose-500 text-white shadow-lg glow-rose' : 'bg-slate-800 text-slate-400 hover:text-white'
                        }`}
                      >
                        Reject
                      </button>
                    </div>
                  </td>
                </tr>

              </tbody>
            </table>
          </div>
        </div>
      ) : (
        /* GSTR-3B Auto-Draft Table */
        <div className="glass-panel rounded-2xl p-6 border border-white/10 space-y-6">
          <div className="flex items-center justify-between border-b border-white/10 pb-4">
            <div>
              <h2 className="text-base font-bold text-white">GSTR-3B Table 4 — Eligible & Ineligible ITC Summary</h2>
              <p className="text-xs text-slate-400">Populated automatically based on accepted IMS actions & GSTR-2B data</p>
            </div>
            <div className="text-xs text-slate-300 bg-slate-900/60 px-3 py-1.5 rounded-lg border border-white/5">
              Status: <span className="text-emerald-400 font-bold">Auto-Drafted</span>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-white/10 text-slate-400 font-semibold uppercase text-[10px] tracking-wider bg-slate-900/40">
                  <th className="py-3 px-3">Table 4 — Details of ITC</th>
                  <th className="py-3 px-3 text-right">Integrated Tax (IGST)</th>
                  <th className="py-3 px-3 text-right">Central Tax (CGST)</th>
                  <th className="py-3 px-3 text-right">State Tax (SGST)</th>
                  <th className="py-3 px-3 text-right">Cess</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 font-mono">
                <tr>
                  <td className="py-3.5 px-3 font-semibold text-slate-200">(A) ITC Available (All Other ITC)</td>
                  <td className="py-3.5 px-3 text-right text-emerald-400">₹0.00</td>
                  <td className="py-3.5 px-3 text-right text-emerald-400">₹1,56,000.00</td>
                  <td className="py-3.5 px-3 text-right text-emerald-400">₹1,56,000.00</td>
                  <td className="py-3.5 px-3 text-right text-emerald-400">₹0.00</td>
                </tr>

                <tr>
                  <td className="py-3.5 px-3 font-semibold text-rose-300">(B) ITC Reversed — As per §17(5) Blocked Credits</td>
                  <td className="py-3.5 px-3 text-right text-rose-400">₹0.00</td>
                  <td className="py-3.5 px-3 text-right text-rose-400">₹14,200.00</td>
                  <td className="py-3.5 px-3 text-right text-rose-400">₹14,200.00</td>
                  <td className="py-3.5 px-3 text-right text-rose-400">₹0.00</td>
                </tr>

                <tr className="bg-emerald-500/10 font-extrabold text-white text-sm">
                  <td className="py-4 px-3 font-sans">(C) Net ITC Available (A - B)</td>
                  <td className="py-4 px-3 text-right">₹0.00</td>
                  <td className="py-4 px-3 text-right text-emerald-300">₹1,41,800.00</td>
                  <td className="py-4 px-3 text-right text-emerald-300">₹1,41,800.00</td>
                  <td className="py-4 px-3 text-right">₹0.00</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}

    </div>
  );
}
