import React from 'react';
import type { ReactNode } from 'react';
import { ArrowUpRight, ArrowDownRight } from 'lucide-react';
import './KPICard.css';

interface KPICardProps {
  title: string;
  value: string;
  trend?: number; // percentage change
  trendLabel?: string;
  icon?: ReactNode;
  status?: 'safe' | 'warning' | 'critical' | 'neutral';
}

export const KPICard: React.FC<KPICardProps> = ({ 
  title, 
  value, 
  trend, 
  trendLabel, 
  icon,
  status = 'neutral' 
}) => {
  const isPositive = trend && trend > 0;
  
  return (
    <div className={`premium-card kpi-card interactive-hover status-${status}`}>
      <div className="kpi-header">
        <span className="kpi-title">{title}</span>
        {icon && <div className="kpi-icon-wrapper">{icon}</div>}
      </div>
      
      <div className="kpi-body">
        <h3 className="kpi-value">{value}</h3>
      </div>
      
      {trend !== undefined && (
        <div className="kpi-footer">
          <div className={`kpi-trend ${isPositive ? 'trend-up' : 'trend-down'}`}>
            {isPositive ? <ArrowUpRight size={16} /> : <ArrowDownRight size={16} />}
            <span>{Math.abs(trend)}%</span>
          </div>
          {trendLabel && <span className="trend-label">{trendLabel}</span>}
        </div>
      )}
    </div>
  );
};
