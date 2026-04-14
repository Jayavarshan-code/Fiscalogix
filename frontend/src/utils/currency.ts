/**
 * Currency formatting utilities for Fiscalogix.
 *
 * Rules:
 *  - Backend stores everything in USD.
 *  - INR display uses Indian locale (en-IN) with lakh/crore shorthand.
 *  - USD display uses en-US with standard k/M shorthand.
 *  - India GST values are always INR regardless of user preference.
 */

export type Currency = 'USD' | 'INR';

/** Format a raw number with Indian lakh/crore shorthand. */
function formatINR(value: number): string {
  const abs = Math.abs(value);
  const sign = value < 0 ? '-' : '';

  if (abs >= 1_00_00_000) {
    // 1 Cr+
    return `${sign}₹${(abs / 1_00_00_000).toFixed(2)}Cr`;
  }
  if (abs >= 1_00_000) {
    // 1 Lakh+
    return `${sign}₹${(abs / 1_00_000).toFixed(1)}L`;
  }
  // Raw
  return `${sign}₹${abs.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
}

/** Format a raw USD number with k/M shorthand. */
function formatUSD(value: number): string {
  const abs = Math.abs(value);
  const sign = value < 0 ? '-' : '';

  if (abs >= 1_000_000) {
    return `${sign}$${(abs / 1_000_000).toFixed(2)}M`;
  }
  if (abs >= 1_000) {
    return `${sign}$${(abs / 1_000).toFixed(1)}k`;
  }
  return `${sign}$${abs.toLocaleString('en-US', { maximumFractionDigits: 0 })}`;
}

/**
 * Format a monetary value for display.
 *
 * @param valueUSD  - The raw value in USD (as stored in DB).
 * @param currency  - Target display currency ('USD' | 'INR').
 * @param fxRate    - USD→INR rate (from CurrencyContext). Required when currency='INR'.
 */
export function formatCurrency(
  valueUSD: number,
  currency: Currency,
  fxRate: number = 84.5,
): string {
  if (currency === 'INR') {
    return formatINR(valueUSD * fxRate);
  }
  return formatUSD(valueUSD);
}

/**
 * Format a value that is ALREADY in INR (e.g. GST module outputs).
 * Always displays as INR regardless of currency preference.
 */
export function formatINRDirect(valueINR: number): string {
  return formatINR(valueINR);
}

/** Currency symbol only. */
export function currencySymbol(currency: Currency): string {
  return currency === 'INR' ? '₹' : '$';
}
