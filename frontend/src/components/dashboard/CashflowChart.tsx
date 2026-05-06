import React, { useState } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from 'recharts';
import { usePredictiveCashflow, useExecutiveOverview } from '../../hooks/queries';

const HORIZONS = ['Current', 'Day 30', 'Day 60', 'Day 90'];

const fmt = (v: number | null | undefined) => {
  const n = Number.isFinite(v as number) ? (v as number) : 0;
  if (Math.abs(n) >= 1e6) return `$${(n / 1e6).toFixed(2)}M`;
  if (Math.abs(n) >= 1e3) return `$${(n / 1e3).toFixed(1)}k`;
  return `$${n.toLocaleString()}`;
};

const CostPill: React.FC<{ label: string; value: number }> = ({ label, value }) => (
  <div style={{
    padding: '8px 10px', borderRadius: 6,
    background: 'rgba(239,68,68,0.07)', border: '1px solid rgba(239,68,68,0.18)',
  }}>
    <div style={{ color: '#94a3b8', fontSize: 10, marginBottom: 2 }}>{label}</div>
    <div style={{ fontWeight: 700, color: '#ef4444', fontSize: 12 }}>{fmt(value)}</div>
  </div>
);

const CustomDot = (props: any) => {
  const { cx, cy, index, selectedIdx, onSelect } = props;
  const isSelected = selectedIdx === index;
  return (
    <circle
      cx={cx} cy={cy}
      r={isSelected ? 9 : 5}
      fill={isSelected ? '#1d4ed8' : '#3b82f6'}
      stroke="#fff" strokeWidth={2}
      style={{ cursor: 'pointer' }}
      onClick={() => onSelect(isSelected ? null : index)}
    />
  );
};

export const CashflowChart: React.FC = () => {
  const { data: cfData }       = usePredictiveCashflow();
  const { data: overview }     = useExecutiveOverview();
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);

  const trajectory = cfData?.trajectory ?? [0, 0, 0, 0];
  const chartData  = HORIZONS.map((date, i) => ({ date, cash: trajectory[i] ?? 0 }));

  const totalPipeline = cfData?.total_ar_pipeline ?? 0;
  const badDebt       = cfData?.bad_debt_provision ?? 0;
  const bd            = overview?.summary?.breakdown;

  const selected = selectedIdx !== null ? chartData[selectedIdx] : null;

  return (
    <div>
      {/* Chart */}
      <div style={{ width: '100%', height: 280 }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="colorCash" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#2563eb" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#2563eb" stopOpacity={0}   />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
            <XAxis
              dataKey="date" axisLine={false} tickLine={false}
              tick={{ fontSize: 12, fill: '#94a3b8' }} dy={10}
            />
            <YAxis
              axisLine={false} tickLine={false}
              tick={{ fontSize: 12, fill: '#94a3b8' }}
              tickFormatter={v => `$${(v / 1000).toFixed(0)}k`}
            />
            <Tooltip
              contentStyle={{ borderRadius: 8, border: '1px solid #e2e8f0', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)' }}
              formatter={(value: any) => [`$${Number(value).toLocaleString()}`, 'Projected Cash']}
            />
            <ReferenceLine y={0} stroke="#ef4444" strokeDasharray="3 3" />
            <Area
              type="monotone" dataKey="cash"
              stroke="#2563eb" strokeWidth={3}
              fillOpacity={1} fill="url(#colorCash)"
              dot={(props: any) => (
                <CustomDot
                  key={props.index}
                  {...props}
                  selectedIdx={selectedIdx}
                  onSelect={setSelectedIdx}
                />
              )}
              activeDot={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Hint */}
      <p style={{ fontSize: 10, color: '#94a3b8', marginTop: 6, marginBottom: 12 }}>
        Click any data point to open its projection breakdown.
      </p>

      {/* Summary strip — always visible */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 12 }}>
        <div style={{
          flex: 1, padding: '10px 14px', borderRadius: 8,
          background: 'rgba(37,99,235,0.08)', border: '1px solid rgba(37,99,235,0.2)',
        }}>
          <div style={{ fontSize: 10, color: '#94a3b8', marginBottom: 2 }}>Total AR Pipeline</div>
          <div style={{ fontWeight: 700, fontSize: 14 }}>{fmt(totalPipeline)}</div>
        </div>
        <div style={{
          flex: 1, padding: '10px 14px', borderRadius: 8,
          background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)',
        }}>
          <div style={{ fontSize: 10, color: '#94a3b8', marginBottom: 2 }}>Bad Debt Provision</div>
          <div style={{ fontWeight: 700, fontSize: 14, color: '#ef4444' }}>{fmt(badDebt)}</div>
        </div>
      </div>

      {/* Drill-down panel — opens on point click */}
      {selected && (
        <div style={{
          padding: '14px 16px', borderRadius: 10,
          background: 'rgba(37,99,235,0.05)', border: '1px solid rgba(37,99,235,0.25)',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: '#2563eb' }}>
              Projection Breakdown — {selected.date}
            </span>
            <button
              onClick={() => setSelectedIdx(null)}
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#94a3b8', fontSize: 12 }}
              aria-label="Close breakdown"
            >
              ✕
            </button>
          </div>

          {/* Cashflow outcome */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 14 }}>
            <div>
              <div style={{ fontSize: 10, color: '#94a3b8', marginBottom: 2 }}>Projected Cash Inflow</div>
              <div style={{
                fontWeight: 700, fontSize: 18,
                color: selected.cash >= 0 ? '#22c55e' : '#ef4444',
              }}>
                {fmt(selected.cash)}
              </div>
            </div>
            {totalPipeline > 0 && (
              <div>
                <div style={{ fontSize: 10, color: '#94a3b8', marginBottom: 2 }}>Share of AR Pipeline</div>
                <div style={{ fontWeight: 700, fontSize: 18 }}>
                  {((Math.abs(selected.cash) / totalPipeline) * 100).toFixed(1)}%
                </div>
              </div>
            )}
          </div>

          {/* Cost drivers from financial engine */}
          {bd ? (
            <>
              <div style={{
                fontSize: 10, color: '#94a3b8', fontWeight: 700,
                textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8,
              }}>
                Cost drivers eating into margin (Financial Engine)
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
                <CostPill label="Delay Cost"        value={bd.delay_cost        ?? 0} />
                <CostPill label="SLA Penalties"     value={bd.penalty_cost      ?? 0} />
                <CostPill label="Inventory Holding" value={bd.inventory_holding  ?? 0} />
                <CostPill label="Opportunity Cost"  value={bd.opportunity_cost  ?? 0} />
              </div>
              <div style={{ marginTop: 10, fontSize: 10, color: '#94a3b8' }}>
                These are portfolio-wide costs. The proportion attributable to this horizon scales
                with the share of AR pipeline above.
              </div>
            </>
          ) : (
            <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 4 }}>
              Cost driver breakdown available after shipment data ingestion and engine run.
            </div>
          )}
        </div>
      )}
    </div>
  );
};
