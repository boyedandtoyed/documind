'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { documentsApi } from '@/lib/api';
import type { Document } from '@/types';

const DOCS_KEY = ['documents'] as const;

export function useDocuments(page = 1, pageSize = 20) {
  return useQuery({
    queryKey: [...DOCS_KEY, page, pageSize],
    queryFn: () => documentsApi.list(page, pageSize),
    staleTime: 30_000,
  });
}

export function useDocument(id: string) {
  return useQuery({
    queryKey: [...DOCS_KEY, id],
    queryFn: () => documentsApi.get(id),
    enabled: Boolean(id),
  });
}

export function useUploadDocument() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => documentsApi.upload(file),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: DOCS_KEY });
    },
  });
}

export function useDeleteDocument() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => documentsApi.delete(id),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: DOCS_KEY });
    },
  });
}

export function useDocumentCount(): number {
  const { data } = useDocuments(1, 1);
  return data?.total ?? 0;
}
