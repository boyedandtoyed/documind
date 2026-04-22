'use client';

import { useQuery } from '@tanstack/react-query';

import { analyticsApi } from '@/lib/api';

export function useUsageStats() {
  return useQuery({
    queryKey: ['analytics', 'usage'],
    queryFn: analyticsApi.usage,
    refetchInterval: 60_000,
    staleTime: 30_000,
  });
}

export function useQualityMetrics() {
  return useQuery({
    queryKey: ['analytics', 'quality'],
    queryFn: analyticsApi.quality,
    refetchInterval: 120_000,
    staleTime: 60_000,
  });
}
