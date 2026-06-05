/* eslint-disable react-refresh/only-export-components */
import React, { createContext, useContext } from 'react';

interface CurrencyContextType {
  formatCurrency: (value: number | null | undefined) => string;
  currencySymbol: string;
}

const CurrencyContext = createContext<CurrencyContextType | undefined>(undefined);

export const CurrencyProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const currencySymbol = '₹';

  const formatCurrency = (value: number | null | undefined) => {
    const val = value ?? 0;
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(val);
  };

  return (
    <CurrencyContext.Provider value={{ formatCurrency, currencySymbol }}>
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
