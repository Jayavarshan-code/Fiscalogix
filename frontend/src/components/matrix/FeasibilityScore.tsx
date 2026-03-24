import React from 'react';

interface FeasibilityScoreProps {
  score: number;
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH';
}

export const FeasibilityScore: React.FC<FeasibilityScoreProps> = ({ score, riskLevel }) => {
  const getColor = () => {
    if (riskLevel === 'LOW') return 'text-safe';
    if (riskLevel === 'MEDIUM') return 'text-warning';
    return 'text-critical';
  };

  const getBg = () => {
    if (riskLevel === 'LOW') return 'bg-safe/10';
    if (riskLevel === 'MEDIUM') return 'bg-warning/10';
    return 'bg-critical/10';
  };

  return (
    <div className={`flex items-center gap-3 px-3 py-1.5 rounded-full border border-subtle ${getBg()}`}>
      <div className="relative flex items-center justify-center">
        <svg className="w-8 h-8 transform -rotate-90">
          <circle
            cx="16"
            cy="16"
            r="14"
            stroke="currentColor"
            strokeWidth="3"
            fill="transparent"
            className="text-subtle/20"
          />
          <circle
            cx="16"
            cy="16"
            r="14"
            stroke="currentColor"
            strokeWidth="3"
            fill="transparent"
            strokeDasharray={88}
            strokeDashoffset={88 - (88 * score) / 100}
            className={`${getColor()} transition-all duration-1000`}
          />
        </svg>
        <span className="absolute text-[8px] font-black">{score}%</span>
      </div>
      <div>
        <div className="text-[8px] font-black text-muted uppercase tracking-tighter">Feasibility</div>
        <div className={`text-[10px] font-bold uppercase ${getColor()}`}>{riskLevel} RISK</div>
      </div>
    </div>
  );
};
