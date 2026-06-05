import { useQuery } from '@tanstack/react-query';
import api from '../api/client';
import type { PortfolioSummary, PortfolioHistory, AllocationSlice, PortfolioInsights } from '../types';

export function usePortfolioSummary() {
  return useQuery<PortfolioSummary>({
    queryKey: ['portfolio', 'summary'],
    queryFn: async () => {
      const response = await api.get('/portfolio/summary');
      return response.data;
    },
  });
}

export function usePortfolioHistory(period: string) {
  return useQuery<PortfolioHistory>({
    queryKey: ['portfolio', 'history', period],
    queryFn: async () => {
      const response = await api.get('/portfolio/history', {
        params: { period },
      });
      return response.data;
    },
  });
}

export function usePortfolioAllocation() {
  return useQuery<AllocationSlice[]>({
    queryKey: ['portfolio', 'allocation'],
    queryFn: async () => {
      const response = await api.get('/portfolio/allocation');
      return response.data;
    },
  });
}

export function usePortfolioInsights() {
  return useQuery<PortfolioInsights>({
    queryKey: ['portfolio', 'insights'],
    queryFn: async () => {
      const response = await api.get('/portfolio/insights');
      return response.data;
    },
  });
}
