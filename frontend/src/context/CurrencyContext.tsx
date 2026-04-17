/**
 * CurrencyContext — global USD/INR toggle with live FX rate.
 *
 * Usage:
 *   const { currency, fxRate, toggle, rateLabel } = useCurrency();
 *   formatCurrency(valueUSD, currency, fxRate)
 */

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import type { Currency } from '../utils/currency';

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
const FALLBACK_RATE = 84.5;
const STORAGE_KEY = 'fiscalogix_currency';

interface CurrencyContextValue {
  currency: Currency;
  fxRate: number;       // USD → INR
  toggle: () => void;
  rateLabel: string;    // e.g. "1 USD = ₹84.50"
  loading: boolean;
}

const CurrencyContext = createContext<CurrencyContextValue>({
  currency: 'USD',
  fxRate: FALLBACK_RATE,
  toggle: () => {},
  rateLabel: `1 USD = ₹${FALLBACK_RATE}`,
  loading: false,
});

export const CurrencyProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currency, setCurrency] = useState<Currency>(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    return (saved === 'INR' || saved === 'USD') ? saved : 'USD';
  });
  const [fxRate, setFxRate] = useState(FALLBACK_RATE);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_BASE}/fx-rate`)
      .then(r => r.json())
      .then(data => {
        if (!cancelled && typeof data.rate === 'number') {
          setFxRate(data.rate);
        }
      })
      .catch(() => { /* fallback stays */ })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  const toggle = useCallback(() => {
    setCurrency(prev => {
      const next: Currency = prev === 'USD' ? 'INR' : 'USD';
      localStorage.setItem(STORAGE_KEY, next);
      return next;
    });
  }, []);

  const rateLabel = `1 USD = ₹${fxRate.toFixed(2)}`;

  return (
    <CurrencyContext.Provider value={{ currency, fxRate, toggle, rateLabel, loading }}>
      {children}
    </CurrencyContext.Provider>
  );
};

export const useCurrency = () => useContext(CurrencyContext);
