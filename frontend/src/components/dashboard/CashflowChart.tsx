import React from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';

const data = [
  { date: 'Mar 1', cash: 54000 },
  { date: 'Mar 5', cash: 48000 },
  { date: 'Mar 10', cash: 32000 },
  { date: 'Mar 15', cash: 15000 },
  { date: 'Mar 18', cash: -2000 }, // Deficit
  { date: 'Mar 22', cash: 12000 },
  { date: 'Mar 28', cash: 45000 },
  { date: 'Apr 2', cash: 62000 },
];

export const CashflowChart: React.FC = () => {
  return (
    <div style={{ width: '100%', height: '300px' }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={data}
          margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
        >
          <defs>
            <linearGradient id="colorCash" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#2563eb" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="#2563eb" stopOpacity={0}/>
            </linearGradient>
            <linearGradient id="colorDeficit" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
          <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#94a3b8' }} dy={10} />
          <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#94a3b8' }} tickFormatter={(val) => `$${val/1000}k`} />
          <Tooltip 
            contentStyle={{ borderRadius: '8px', border: '1px solid #e2e8f0', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.05)' }}
            formatter={(value: number) => [`$${value.toLocaleString()}`, 'Projected Cash']}
          />
          <ReferenceLine y={0} stroke="#ef4444" strokeDasharray="3 3" />
          <Area 
            type="monotone" 
            dataKey="cash" 
            stroke="#2563eb" 
            strokeWidth={3}
            fillOpacity={1} 
            fill="url(#colorCash)" 
            activeDot={{ r: 6, fill: '#2563eb', stroke: '#fff', strokeWidth: 2 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};
