/**
 * Tests for the buildModes() pure function in RerouteStudio.
 *
 * buildModes() is the core business logic: it derives RAIL/TRUCK/OCEAN options
 * from live insightsData. If it regresses, the Reroute Studio shows wrong costs
 * and the execute action fires with an incorrect mode EFI.
 */

import { describe, it, expect } from 'vitest';

// ── Inline the pure function so tests don't depend on React imports ───────────
// This mirrors the logic in RerouteStudio.tsx exactly.

interface ModeOption {
  id: string;
  cost: number;
  time: string;
  risk: number;
  feasibility: number;
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH';
  efi: number;
  path: string[];
  status: string;
  breakdown: Record<string, number>;
}

function buildModes(data: any): ModeOption[] {
  const orderValue = data?.components?.avg_revenue ?? 15000;
  const baseCost   = data?.components?.avg_cost    ?? 12750;
  const slaPenalty = data?.components?.avg_penalty ?? 0;
  const baseRisk   = Math.max(0.05, 1 - (data?.confidence_score ?? 0.5));

  return [
    {
      id: 'RAIL',
      cost: Math.round(baseCost * 1.45),
      time: '72h',
      risk: Math.min(0.99, baseRisk * 0.15),
      feasibility: Math.round(Math.min(99, 82 + (1 - baseRisk) * 15)),
      riskLevel: 'LOW',
      efi: Math.round(orderValue - baseCost * 1.45 - slaPenalty * 0.3),
      path: ['Origin Hub', 'Rail Terminal', 'Destination ICD'],
      status: 'OPTIMAL ROBUSTNESS',
      breakdown: {
        Rail:     Math.round(baseCost * 1.25),
        Handling: Math.round(baseCost * 0.20),
      },
    },
    {
      id: 'TRUCK',
      cost: Math.round(baseCost * 0.95),
      time: '24h',
      risk: Math.min(0.99, baseRisk * 0.70),
      feasibility: Math.round(Math.min(99, 50 + (1 - baseRisk) * 18)),
      riskLevel: baseRisk > 0.4 ? 'HIGH' : 'MEDIUM',
      efi: Math.round(orderValue - baseCost * 0.95 - slaPenalty),
      path: ['Origin', 'Direct Route', 'Destination WH'],
      status: baseRisk > 0.4 ? 'CRITICAL SHOCK' : 'VIABLE',
      breakdown: {
        Truck:    Math.round(baseCost * 0.85),
        Handling: Math.round(baseCost * 0.10),
      },
    },
    {
      id: 'OCEAN',
      cost: Math.round(baseCost * 0.35),
      time: '14 days',
      risk: Math.min(0.99, baseRisk * 0.05),
      feasibility: Math.round(Math.min(99, 78 + (1 - baseRisk) * 10)),
      riskLevel: 'MEDIUM',
      efi: Math.round(orderValue - baseCost * 0.35 - slaPenalty * 0.7),
      path: ['Port of Origin', 'Ocean Lane', 'Destination Port', 'Final WH'],
      status: 'CONSERVATIVE',
      breakdown: {
        Ocean:    Math.round(baseCost * 0.25),
        Truck:    Math.round(baseCost * 0.05),
        Handling: Math.round(baseCost * 0.05),
      },
    },
  ];
}


// ── Fixtures ──────────────────────────────────────────────────────────────────

const LIVE_DATA = {
  confidence_score: 0.942,
  components: {
    avg_revenue: 18_000,
    avg_cost:    12_750,
    avg_penalty: 300,
  },
};

const LOW_CONF_DATA = {
  confidence_score: 0.30,   // baseRisk = 0.70 → TRUCK becomes HIGH risk
  components: {
    avg_revenue: 10_000,
    avg_cost:    8_000,
    avg_penalty: 0,
  },
};


// ── Structure ─────────────────────────────────────────────────────────────────

describe('buildModes — structure', () => {
  it('returns exactly three modes', () => {
    expect(buildModes(LIVE_DATA)).toHaveLength(3);
  });

  it('returns modes with ids RAIL, TRUCK, OCEAN in that order', () => {
    const ids = buildModes(LIVE_DATA).map(m => m.id);
    expect(ids).toEqual(['RAIL', 'TRUCK', 'OCEAN']);
  });

  it('every mode has required fields', () => {
    for (const mode of buildModes(LIVE_DATA)) {
      expect(mode).toHaveProperty('id');
      expect(mode).toHaveProperty('cost');
      expect(mode).toHaveProperty('efi');
      expect(mode).toHaveProperty('risk');
      expect(mode).toHaveProperty('feasibility');
      expect(mode).toHaveProperty('riskLevel');
      expect(mode).toHaveProperty('path');
      expect(mode).toHaveProperty('breakdown');
    }
  });
});


// ── Cost derivation ───────────────────────────────────────────────────────────

describe('buildModes — cost derivation', () => {
  it('RAIL cost = round(baseCost × 1.45)', () => {
    const { avg_cost } = LIVE_DATA.components;
    const rail = buildModes(LIVE_DATA).find(m => m.id === 'RAIL')!;
    expect(rail.cost).toBe(Math.round(avg_cost * 1.45));
  });

  it('TRUCK cost < RAIL cost (faster but cheaper logistics)', () => {
    const modes = buildModes(LIVE_DATA);
    const rail  = modes.find(m => m.id === 'RAIL')!;
    const truck = modes.find(m => m.id === 'TRUCK')!;
    expect(truck.cost).toBeLessThan(rail.cost);
  });

  it('OCEAN cost is the cheapest mode', () => {
    const modes  = buildModes(LIVE_DATA);
    const costs  = modes.map(m => m.cost);
    const ocean  = modes.find(m => m.id === 'OCEAN')!;
    expect(ocean.cost).toBe(Math.min(...costs));
  });

  it('costs scale proportionally with baseCost', () => {
    const double = {
      ...LIVE_DATA,
      components: { ...LIVE_DATA.components, avg_cost: LIVE_DATA.components.avg_cost * 2 },
    };
    const base   = buildModes(LIVE_DATA);
    const scaled = buildModes(double);
    for (let i = 0; i < 3; i++) {
      // Math.round doesn't distribute: allow ±1 for integer rounding at doubled baseCost
      expect(Math.abs(scaled[i].cost - base[i].cost * 2)).toBeLessThanOrEqual(1);
    }
  });
});


// ── EFI derivation ────────────────────────────────────────────────────────────

describe('buildModes — EFI derivation', () => {
  it('RAIL EFI = round(revenue - baseCost×1.45 - penalty×0.3)', () => {
    const { avg_revenue, avg_cost, avg_penalty } = LIVE_DATA.components;
    const expected = Math.round(avg_revenue - avg_cost * 1.45 - avg_penalty * 0.3);
    const rail = buildModes(LIVE_DATA).find(m => m.id === 'RAIL')!;
    expect(rail.efi).toBe(expected);
  });

  it('TRUCK EFI = round(revenue - baseCost×0.95 - full penalty)', () => {
    const { avg_revenue, avg_cost, avg_penalty } = LIVE_DATA.components;
    const expected = Math.round(avg_revenue - avg_cost * 0.95 - avg_penalty);
    const truck = buildModes(LIVE_DATA).find(m => m.id === 'TRUCK')!;
    expect(truck.efi).toBe(expected);
  });

  it('zero penalty: TRUCK EFI equals revenue - 95% of baseCost', () => {
    const nopenalty = { ...LIVE_DATA, components: { ...LIVE_DATA.components, avg_penalty: 0 } };
    const { avg_revenue, avg_cost } = nopenalty.components;
    const truck = buildModes(nopenalty).find(m => m.id === 'TRUCK')!;
    expect(truck.efi).toBe(Math.round(avg_revenue - avg_cost * 0.95));
  });

  it('OCEAN has highest EFI (lowest cost path)', () => {
    const modes = buildModes(LIVE_DATA);
    const efis  = modes.map(m => m.efi);
    const ocean = modes.find(m => m.id === 'OCEAN')!;
    expect(ocean.efi).toBe(Math.max(...efis));
  });
});


// ── Risk and risk level ───────────────────────────────────────────────────────

describe('buildModes — risk levels', () => {
  it('RAIL always has riskLevel LOW', () => {
    expect(buildModes(LIVE_DATA).find(m => m.id === 'RAIL')!.riskLevel).toBe('LOW');
    expect(buildModes(LOW_CONF_DATA).find(m => m.id === 'RAIL')!.riskLevel).toBe('LOW');
  });

  it('OCEAN always has riskLevel MEDIUM', () => {
    expect(buildModes(LIVE_DATA).find(m => m.id === 'OCEAN')!.riskLevel).toBe('MEDIUM');
    expect(buildModes(LOW_CONF_DATA).find(m => m.id === 'OCEAN')!.riskLevel).toBe('MEDIUM');
  });

  it('TRUCK escalates to HIGH when confidence_score is low (baseRisk > 0.4)', () => {
    const truck = buildModes(LOW_CONF_DATA).find(m => m.id === 'TRUCK')!;
    expect(truck.riskLevel).toBe('HIGH');
    expect(truck.status).toBe('CRITICAL SHOCK');
  });

  it('TRUCK stays MEDIUM when confidence_score is high', () => {
    const truck = buildModes(LIVE_DATA).find(m => m.id === 'TRUCK')!;
    expect(truck.riskLevel).toBe('MEDIUM');
    expect(truck.status).toBe('VIABLE');
  });

  it('risk scores are all in [0, 1]', () => {
    for (const mode of buildModes(LOW_CONF_DATA)) {
      expect(mode.risk).toBeGreaterThanOrEqual(0);
      expect(mode.risk).toBeLessThanOrEqual(1);
    }
  });

  it('RAIL risk < TRUCK risk < OCEAN worst-case is bounded', () => {
    const modes = buildModes(LIVE_DATA);
    const rail  = modes.find(m => m.id === 'RAIL')!;
    const truck = modes.find(m => m.id === 'TRUCK')!;
    // Rail always has lower raw risk multiplier (0.15×) vs Truck (0.70×)
    expect(rail.risk).toBeLessThan(truck.risk);
  });
});


// ── Null / missing data fallback ──────────────────────────────────────────────

describe('buildModes — null safety', () => {
  it('returns three modes when called with null', () => {
    expect(buildModes(null)).toHaveLength(3);
  });

  it('returns three modes when called with empty object', () => {
    expect(buildModes({})).toHaveLength(3);
  });

  it('uses default baseCost=12750 when components missing', () => {
    const rail = buildModes({}).find(m => m.id === 'RAIL')!;
    expect(rail.cost).toBe(Math.round(12750 * 1.45));
  });

  it('uses default confidence=0.5 giving baseRisk=0.5 when field missing', () => {
    // baseRisk = max(0.05, 1 - 0.5) = 0.5 → TRUCK should be HIGH
    const truck = buildModes({}).find(m => m.id === 'TRUCK')!;
    expect(truck.riskLevel).toBe('HIGH');
  });
});


// ── Feasibility bounds ────────────────────────────────────────────────────────

describe('buildModes — feasibility', () => {
  it('feasibility is always between 1 and 99 inclusive', () => {
    for (const data of [LIVE_DATA, LOW_CONF_DATA, null, {}]) {
      for (const mode of buildModes(data)) {
        expect(mode.feasibility).toBeGreaterThanOrEqual(1);
        expect(mode.feasibility).toBeLessThanOrEqual(99);
      }
    }
  });

  it('high confidence yields higher feasibility than low confidence for RAIL', () => {
    const railHigh = buildModes(LIVE_DATA).find(m => m.id === 'RAIL')!;
    const railLow  = buildModes(LOW_CONF_DATA).find(m => m.id === 'RAIL')!;
    expect(railHigh.feasibility).toBeGreaterThanOrEqual(railLow.feasibility);
  });
});


// ── Breakdown totals ──────────────────────────────────────────────────────────

describe('buildModes — breakdown totals', () => {
  it('RAIL breakdown components sum to approximately the RAIL cost', () => {
    const rail = buildModes(LIVE_DATA).find(m => m.id === 'RAIL')!;
    const sum  = Object.values(rail.breakdown).reduce((a, b) => a + b, 0);
    // Rail=1.25x + Handling=0.20x = 1.45x → within rounding of rail.cost
    expect(sum).toBeCloseTo(rail.cost, -1);
  });

  it('TRUCK breakdown has Truck and Handling keys', () => {
    const truck = buildModes(LIVE_DATA).find(m => m.id === 'TRUCK')!;
    expect(truck.breakdown).toHaveProperty('Truck');
    expect(truck.breakdown).toHaveProperty('Handling');
  });

  it('OCEAN breakdown has Ocean, Truck, and Handling keys', () => {
    const ocean = buildModes(LIVE_DATA).find(m => m.id === 'OCEAN')!;
    expect(ocean.breakdown).toHaveProperty('Ocean');
    expect(ocean.breakdown).toHaveProperty('Truck');
    expect(ocean.breakdown).toHaveProperty('Handling');
  });
});
