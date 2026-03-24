import React from 'react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip } from 'recharts';

const data = [
  { subject: 'FX Volatility', A: 85, fullMark: 100 },
  { subject: 'Carrier Delay', A: 92, fullMark: 100 },
  { subject: 'Port Congestion', A: 45, fullMark: 100 },
  { subject: 'Demand Drop', A: 30, fullMark: 100 },
  { subject: 'Credit Risk', A: 60, fullMark: 100 },
];

export const RiskRadar: React.FC = () => {
  return (
    <div style={{ width: '100%', height: '300px' }}>
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart cx="50%" cy="50%" outerRadius="70%" data={data}>
          <PolarGrid stroke="#e2e8f0" />
          <PolarAngleAxis dataKey="subject" tick={{ fill: '#475569', fontSize: 11 }} />
          <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
          <Tooltip 
             contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.05)' }}
          />
          <Radar name="Risk Index" dataKey="A" stroke="#ef4444" fill="#ef4444" fillOpacity={0.4} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
};
