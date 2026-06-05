/* eslint-disable react-refresh/only-export-components */
import React, { createContext, useContext, useState } from 'react';

export type Currency = 'USD' | 'INR';

interface CurrencyContextType {
  currency: Currency;
  setCurrency: (currency: Currency) => void;
  formatCurrency: (value: number | null | undefined) => string;
  currencySymbol: string;
}

const CurrencyContext = createContext<CurrencyContextType | undefined>(undefined);

export const CurrencyProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currency, setCurrencyState] = useState<Currency>(() => {
    const saved = localStorage.getItem('folio_currency');
    if (saved === 'USD' || saved === 'INR') {
      return saved;
    }
    return 'INR';
  });

  const setCurrency = (curr: Currency) => {
    setCurrencyState(curr);
    localStorage.setItem('folio_currency', curr);
  };

  const currencySymbol = currency === 'INR' ? '₹' : '$';

  const formatCurrency = (value: number | null | undefined) => {
    const val = value ?? 0;
    const locale = currency === 'INR' ? 'en-IN' : 'en-US';
    return new Intl.NumberFormat(locale, {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(val);
  };

  return (
    <CurrencyContext.Provider value={{ currency, setCurrency, formatCurrency, currencySymbol }}>
      {children}
    </CurrencyContext.Provider>
  );
};

export const useCurrency = () => {
  const context = useContext(CurrencyContext);
  if (context === undefined) {
    throw new Error('useCurrency must be used within a CurrencyProvider');
  }
  return context;
};
