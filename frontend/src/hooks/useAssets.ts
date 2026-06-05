import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../api/client';
import type { Asset } from '../types';

export function useAssets() {
  return useQuery<Asset[]>({
    queryKey: ['assets'],
    queryFn: async () => {
      const response = await api.get('/assets');
      return response.data;
    },
  });
}

export function useCreateAsset() {
  const queryClient = useQueryClient();
  return useMutation<Asset, Error, { ticker: string; name?: string }>({
    mutationFn: async (payload) => {
      const response = await api.post('/assets', payload);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assets'] });
    },
  });
}
