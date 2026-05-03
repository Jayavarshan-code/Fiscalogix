/**
 * Tests for the TemporalRiskTimeline marker derivation logic in ConfidencePanel.
 *
 * The markers IIFE converts scenario_analysis data into timeline markers.
 * If this logic regresses, the TemporalRiskTimeline shows wrong risk scores
 * and signals — the "live" claim becomes a lie.
 */

import { describe, it, expect } from 'vitest';

// ── Mirror the derivation logic from ConfidencePanel.tsx ─────────────────────

interface BackendScenario {
  scenario: string;
  shocks_applied: {
    delay_shift_days: number;
    demand_shift_pct: number;
    fx_shock_pct: number;
    cost_shock_pct: number;
    international_only?: boolean;
  };
  impact: {
    revm_change: number;
    revm_change_pct: number;
    peak_deficit: number;
  };
}

interface TimelineMarker {
  time_hours: number;
  score: number;
  label: string;
  bands: [number, number, number];
  signals: { type: string; message: string }[];
}

const TIME_SLOTS = [0, 14, 28, 48, 72];

function deriveMarkers(scenarios: BackendScenario[]): TimelineMarker[] {
  return scenarios.slice(0, 5).map((s, i) => {
    const changePct = Math.abs(s?.impact?.revm_change_pct ?? 0);
    const score = Math.min(1, Math.max(0.05, changePct / 60));
    const shocks = s?.shocks_applied ?? {};
    const signals: { type: string; message: string }[] = [];

    if (shocks.delay_shift_days > 0)
      signals.push({ type: 'AIS', message: `+${shocks.delay_shift_days}d delay` });
    if (shocks.fx_shock_pct > 0)
      signals.push({ type: 'NEWS', message: `FX shock +${(shocks.fx_shock_pct * 100).toFixed(0)}%` });
    if (shocks.cost_shock_pct > 0)
      signals.push({ type: 'WEATHER', message: `Cost +${(shocks.cost_shock_pct * 100).toFixed(0)}%` });
    if (signals.length === 0)
      signals.push({ type: 'AIS', message: s?.scenario ?? 'Base condition' });

    return {
      time_hours: TIME_SLOTS[i] ?? i * 14,
      score,
      label: (s?.scenario ?? '').split(' ')[0].toUpperCase() || `T${i}`,
      bands: [
        Math.max(0, score - 0.15),
        score,
        Math.min(1, score + 0.20),
      ] as [number, number, number],
      signals,
    };
  });
}


// ── Fixtures ──────────────────────────────────────────────────────────────────

const SCENARIOS: BackendScenario[] = [
  {
    scenario: 'Base Conditions',
    shocks_applied: { delay_shift_days: 0, demand_shift_pct: 0, fx_shock_pct: 0, cost_shock_pct: 0 },
    impact: { revm_change: 0, revm_change_pct: 0, peak_deficit: 0 },
  },
  {
    scenario: 'Port Strike',
    shocks_applied: { delay_shift_days: 5, demand_shift_pct: 0, fx_shock_pct: 0, cost_shock_pct: 0 },
    impact: { revm_change: -4500, revm_change_pct: -25, peak_deficit: 4500 },
  },
  {
    scenario: 'FX Devaluation',
    shocks_applied: { delay_shift_days: 0, demand_shift_pct: 0, fx_shock_pct: 0.12, cost_shock_pct: 0 },
    impact: { revm_change: -2000, revm_change_pct: -15, peak_deficit: 2000 },
  },
  {
    scenario: 'Freight Spike',
    shocks_applied: { delay_shift_days: 0, demand_shift_pct: 0, fx_shock_pct: 0, cost_shock_pct: 0.30 },
    impact: { revm_change: -3000, revm_change_pct: -20, peak_deficit: 3000 },
  },
  {
    scenario: 'Red Sea Reroute',
    shocks_applied: { delay_shift_days: 8, demand_shift_pct: 0, fx_shock_pct: 0.08, cost_shock_pct: 0.15 },
    impact: { revm_change: -6000, revm_change_pct: -40, peak_deficit: 6000 },
  },
];


// ── Output structure ──────────────────────────────────────────────────────────

describe('deriveMarkers — structure', () => {
  it('returns one marker per scenario (max 5)', () => {
    expect(deriveMarkers(SCENARIOS)).toHaveLength(5);
  });

  it('truncates to 5 even when more than 5 scenarios are passed', () => {
    const extra = [...SCENARIOS, ...SCENARIOS];
    expect(deriveMarkers(extra)).toHaveLength(5);
  });

  it('handles empty scenarios array', () => {
    expect(deriveMarkers([])).toHaveLength(0);
  });

  it('each marker has required fields', () => {
    for (const m of deriveMarkers(SCENARIOS)) {
      expect(m).toHaveProperty('time_hours');
      expect(m).toHaveProperty('score');
      expect(m).toHaveProperty('label');
      expect(m).toHaveProperty('bands');
      expect(m).toHaveProperty('signals');
      expect(m.bands).toHaveLength(3);
    }
  });
});


// ── Time slot assignment ──────────────────────────────────────────────────────

describe('deriveMarkers — time slots', () => {
  it('assigns canonical time slots [0, 14, 28, 48, 72]', () => {
    const markers = deriveMarkers(SCENARIOS);
    expect(markers.map(m => m.time_hours)).toEqual([0, 14, 28, 48, 72]);
  });

  it('time slots are strictly non-decreasing', () => {
    const hours = deriveMarkers(SCENARIOS).map(m => m.time_hours);
    for (let i = 1; i < hours.length; i++) {
      expect(hours[i]).toBeGreaterThan(hours[i - 1]);
    }
  });
});


// ── Score derivation ──────────────────────────────────────────────────────────

describe('deriveMarkers — score derivation', () => {
  it('base scenario with 0% revm_change_pct yields minimum score (0.05)', () => {
    const marker = deriveMarkers([SCENARIOS[0]])[0];
    expect(marker.score).toBe(0.05);
  });

  it('score = clamp(|revm_change_pct| / 60, 0.05, 1.0)', () => {
    for (const s of SCENARIOS) {
      const expected = Math.min(1, Math.max(0.05, Math.abs(s.impact.revm_change_pct) / 60));
      const marker = deriveMarkers([s])[0];
      expect(marker.score).toBeCloseTo(expected, 10);
    }
  });

  it('score is always in [0.05, 1.0]', () => {
    for (const m of deriveMarkers(SCENARIOS)) {
      expect(m.score).toBeGreaterThanOrEqual(0.05);
      expect(m.score).toBeLessThanOrEqual(1.0);
    }
  });

  it('higher |revm_change_pct| yields higher score', () => {
    const markers = deriveMarkers(SCENARIOS);
    // Red Sea (-40%) should have higher score than Port Strike (-25%)
    const portStrike = markers[1];
    const redSea     = markers[4];
    expect(redSea.score).toBeGreaterThan(portStrike.score);
  });
});


// ── Label derivation ─────────────────────────────────────────────────────────

describe('deriveMarkers — labels', () => {
  it('label is first word of scenario name in uppercase', () => {
    const markers = deriveMarkers(SCENARIOS);
    expect(markers[0].label).toBe('BASE');
    expect(markers[1].label).toBe('PORT');
    expect(markers[2].label).toBe('FX');
    expect(markers[3].label).toBe('FREIGHT');
    expect(markers[4].label).toBe('RED');
  });
});


// ── Band derivation ───────────────────────────────────────────────────────────

describe('deriveMarkers — bands', () => {
  it('bands[0] <= bands[1] <= bands[2]', () => {
    for (const m of deriveMarkers(SCENARIOS)) {
      expect(m.bands[0]).toBeLessThanOrEqual(m.bands[1]);
      expect(m.bands[1]).toBeLessThanOrEqual(m.bands[2]);
    }
  });

  it('bands[1] === score', () => {
    for (const m of deriveMarkers(SCENARIOS)) {
      expect(m.bands[1]).toBe(m.score);
    }
  });

  it('bands are clamped to [0, 1]', () => {
    for (const m of deriveMarkers(SCENARIOS)) {
      expect(m.bands[0]).toBeGreaterThanOrEqual(0);
      expect(m.bands[2]).toBeLessThanOrEqual(1);
    }
  });

  it('band spread is +0.20 above and -0.15 below the score (before clamping)', () => {
    const marker = deriveMarkers([SCENARIOS[1]])[0]; // score ≈ 0.417
    expect(marker.bands[2]).toBeCloseTo(Math.min(1, marker.score + 0.20), 10);
    expect(marker.bands[0]).toBeCloseTo(Math.max(0, marker.score - 0.15), 10);
  });
});


// ── Signal derivation ─────────────────────────────────────────────────────────

describe('deriveMarkers — signals', () => {
  it('base scenario with no shocks gets a fallback AIS signal', () => {
    const marker = deriveMarkers([SCENARIOS[0]])[0];
    expect(marker.signals).toHaveLength(1);
    expect(marker.signals[0].type).toBe('AIS');
    expect(marker.signals[0].message).toBe('Base Conditions');
  });

  it('delay_shift_days > 0 produces AIS delay signal', () => {
    const marker = deriveMarkers([SCENARIOS[1]])[0]; // Port Strike, 5d delay
    const ais = marker.signals.find(s => s.type === 'AIS');
    expect(ais).toBeDefined();
    expect(ais!.message).toBe('+5d delay');
  });

  it('fx_shock_pct > 0 produces NEWS FX signal', () => {
    const marker = deriveMarkers([SCENARIOS[2]])[0]; // FX 12%
    const news = marker.signals.find(s => s.type === 'NEWS');
    expect(news).toBeDefined();
    expect(news!.message).toBe('FX shock +12%');
  });

  it('cost_shock_pct > 0 produces WEATHER cost signal', () => {
    const marker = deriveMarkers([SCENARIOS[3]])[0]; // cost +30%
    const weather = marker.signals.find(s => s.type === 'WEATHER');
    expect(weather).toBeDefined();
    expect(weather!.message).toBe('Cost +30%');
  });

  it('multi-shock scenario produces multiple signals', () => {
    const marker = deriveMarkers([SCENARIOS[4]])[0]; // Red Sea: delay + fx + cost
    expect(marker.signals.length).toBeGreaterThanOrEqual(3);
    const types = marker.signals.map(s => s.type);
    expect(types).toContain('AIS');
    expect(types).toContain('NEWS');
    expect(types).toContain('WEATHER');
  });
});
