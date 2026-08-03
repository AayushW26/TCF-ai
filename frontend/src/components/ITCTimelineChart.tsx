'use client';

import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';
import { TrendingUp } from 'lucide-react';

interface TimelinePoint {
  period: string;
  confirmed: number;
  at_risk: number;
  blocked: number;
  fraud_flagged: number;
  total: number;
}

interface ITCTimelineChartProps {
  data: TimelinePoint[];
}

export const ITCTimelineChart: React.FC<ITCTimelineChartProps> = ({ data }) => {
  return (
    <div className="glass-panel rounded-2xl p-6 border border-white/10 relative overflow-hidden">
      
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-emerald-400" />
            <h2 className="text-lg font-bold text-white">6-Month ITC Claim Trend</h2>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Historical breakdown of confirmed claims, blocked credits, and fraud flags
          </p>
        </div>

        {/* Legend Pills */}
        <div className="hidden sm:flex items-center space-x-3 text-[11px] font-medium text-slate-300">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 glow-emerald" />
            Confirmed
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
            At Risk
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-sky-500" />
            Blocked
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500 glow-rose" />
            Fraud
          </div>
        </div>
      </div>

      {/* Recharts Container */}
      <div className="h-72 w-full pt-2">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.05)" />
            <XAxis
              dataKey="period"
              stroke="#64748b"
              fontSize={11}
              tickLine={false}
            />
            <YAxis
              stroke="#64748b"
              fontSize={11}
              tickLine={false}
              tickFormatter={(val) => `₹${(val / 1000).toFixed(0)}k`}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'rgba(15, 23, 42, 0.95)',
                borderColor: 'rgba(255, 255, 255, 0.1)',
                borderRadius: '12px',
                fontSize: '12px',
                color: '#fff',
                boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)',
              }}
              formatter={(value: any) => [`₹${Number(value).toLocaleString('en-IN')}`, '']}
            />
            <Bar dataKey="confirmed" stackId="a" fill="#10b981" radius={[0, 0, 4, 4]} name="Confirmed" />
            <Bar dataKey="at_risk" stackId="a" fill="#f59e0b" name="At Risk" />
            <Bar dataKey="blocked" stackId="a" fill="#0284c7" name="Blocked §17(5)" />
            <Bar dataKey="fraud_flagged" stackId="a" fill="#f43f5e" radius={[4, 4, 0, 0]} name="Fraud Flagged" />
          </BarChart>
        </ResponsiveContainer>
      </div>

    </div>
  );
};
