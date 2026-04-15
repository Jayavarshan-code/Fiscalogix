import { useQuery, useMutation } from '@tanstack/react-query';
import { apiService } from '../services/api';
import type { DashboardData, MLPerformance, RedisStatus } from '../services/api';

// ── staleTime constants ───────────────────────────────────────────────────────
const STALE = {
  realtime:   0,              // always re-fetch on mount (spatial risks, model health)
  short:      30_000,         // 30s  — live dashboard KPIs
  medium:     5 * 60_000,     // 5min — cashflow, shipment grid
  long:       15 * 60_000,    // 15min — ML perf, redis status (infrequently changes)
};

// ── Dashboard ─────────────────────────────────────────────────────────────────

export const useExecutiveOverview = (tenantId = 'default_tenant') =>
  useQuery<DashboardData, Error>({
    queryKey:       ['executiveOverview', tenantId],
    queryFn:        () => apiService.getExecutiveOverview(tenantId),
    staleTime:      STALE.short,
    refetchInterval: 60_000,   // auto-refresh KPIs every minute
  });

export const usePredictiveCashflow = (tenantId = 'default_tenant') =>
  useQuery<any, Error>({
    queryKey:  ['predictiveCashflow', tenantId],
    queryFn:   () => apiService.getPredictiveCashflow(tenantId),
    staleTime: STALE.medium,
  });

// ── Spatial risks ─────────────────────────────────────────────────────────────

export const useSpatialRisks = () =>
  useQuery<any, Error>({
    queryKey:        ['spatialRisks'],
    queryFn:         () => apiService.getSpatialRisks(),
    staleTime:       STALE.realtime,
    refetchInterval: 5 * 60_000,   // poll every 5 min (matches old setInterval)
  });

// ── Model governance ──────────────────────────────────────────────────────────

export const useModelHealth = () =>
  useQuery<any, Error>({
    queryKey:        ['modelHealth'],
    queryFn:         () => apiService.getModelHealth(),
    staleTime:       STALE.realtime,
    refetchInterval: 60_000,        // poll every 60s (matches old setInterval)
  });

export const useMLPerformance = () =>
  useQuery<MLPerformance, Error>({
    queryKey:  ['mlPerformance'],
    queryFn:   () => apiService.getMLPerformance(),
    staleTime: STALE.long,
  });

// ── Redis status ──────────────────────────────────────────────────────────────
// Best-effort probe — never retry on failure, never throw into error boundary.

export const useRedisStatus = () =>
  useQuery<RedisStatus | null, Error>({
    queryKey:  ['redisStatus'],
    queryFn:   () => apiService.getRedisStatus().catch(() => null),
    staleTime: STALE.long,
    retry:     false,
  });

// ── Shipment grid (Intelligence Matrix) ──────────────────────────────────────

export const useShipmentGrid = (
  page: number,
  sortBy: string,
  sortDir: 'asc' | 'desc',
) =>
  useQuery<any, Error>({
    queryKey:  ['shipmentGrid', page, sortBy, sortDir],
    queryFn:   () => apiService.getShipmentGrid(page, sortBy, sortDir),
    staleTime: STALE.medium,
    placeholderData: (prev: any) => prev,   // keep previous page visible while next loads
  });

// ── Shipment insights + explainability (ConfidencePanel) ─────────────────────

export const useShipmentInsights = (shipmentId: string | null) =>
  useQuery<any, Error>({
    queryKey:  ['shipmentInsights', shipmentId],
    queryFn:   () => apiService.getShipmentInsights(shipmentId!),
    enabled:   !!shipmentId,
    staleTime: STALE.short,
  });

export const useConfidenceExplain = (shipmentId: string | null) =>
  useQuery<any, Error>({
    queryKey:  ['confidenceExplain', shipmentId],
    queryFn:   () => apiService.getConfidenceExplain(shipmentId!),
    enabled:   !!shipmentId,
    staleTime: STALE.short,
    retry:     1,   // explain endpoint can be slow — one retry only
  });

// ── AR default enrichment (RecoveryDashboard) ────────────────────────────────

export const useARDefault = (
  customers: { customer_id: string; order_value: number; credit_days: number; historical_defaults?: number }[],
) =>
  useQuery<any[], Error>({
    queryKey:  ['arDefault', customers.map(c => c.customer_id).join(',')],
    queryFn:   () => apiService.getARDefault(customers),
    staleTime: STALE.medium,
    enabled:   customers.length > 0,
  });

// ── India GST ─────────────────────────────────────────────────────────────────

export const useGSTCost = (
  shipments: Parameters<typeof apiService.getGSTCost>[0],
  enabled = true,
) =>
  useQuery<any[], Error>({
    queryKey:  ['gstCost', shipments.map(s => s.shipment_id).join(',')],
    queryFn:   () => apiService.getGSTCost(shipments),
    staleTime: STALE.medium,
    enabled:   enabled && shipments.length > 0,
  });

export const useIndiaRoutes = () =>
  useQuery<any, Error>({
    queryKey:  ['indiaRoutes'],
    queryFn:   () => apiService.getIndiaRoutes(),
    staleTime: STALE.long,
  });

// ── Mutations ─────────────────────────────────────────────────────────────────

export const useExecuteActionMutation = () =>
  useMutation({
    mutationFn: (payload: {
      action_type: string;
      shipment_id: string;
      erp_target: string;
      confidence_score: number;
      parameters?: any;
    }) => apiService.executeAction(payload),
  });

export const useMapERPFieldsMutation = () =>
  useMutation({
    mutationFn: (headers: string[]) => apiService.mapERPFields(headers),
  });
