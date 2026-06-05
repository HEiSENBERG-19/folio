import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../api/client';
import type { Transaction, TxType, CsvImportResult } from '../types';

export interface TransactionFilters {
  account_id?: number;
  asset_id?: number;
  tx_type?: TxType;
  skip?: number;
  limit?: number;
}

export function useTransactions(filters?: TransactionFilters) {
  return useQuery<Transaction[]>({
    queryKey: ['transactions', filters],
    queryFn: async () => {
      const response = await api.get('/transactions', { params: filters });
      return response.data;
    },
  });
}

export function useCreateTransaction() {
  const queryClient = useQueryClient();
  return useMutation<
    Transaction,
    Error,
    {
      account_id: number;
      asset_id?: number | null;
      tx_type: TxType;
      quantity: number;
      price_per_unit: number;
      total_amount: number;
      notes: string;
      executed_at: string;
    }
  >({
    mutationFn: async (payload) => {
      const response = await api.post('/transactions', payload);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      queryClient.invalidateQueries({ queryKey: ['portfolio'] });
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
    },
  });
}

export function useDeleteTransaction() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, number>({
    mutationFn: async (id) => {
      await api.delete(`/transactions/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      queryClient.invalidateQueries({ queryKey: ['portfolio'] });
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
    },
  });
}

export function useImportCsv() {
  const queryClient = useQueryClient();
  return useMutation<CsvImportResult, Error, File>({
    mutationFn: async (file) => {
      const formData = new FormData();
      formData.append('file', file);
      const response = await api.post('/transactions/import', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      queryClient.invalidateQueries({ queryKey: ['portfolio'] });
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
      queryClient.invalidateQueries({ queryKey: ['assets'] });
    },
  });
}
