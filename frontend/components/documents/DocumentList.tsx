'use client';

import { FileText, Loader2 } from 'lucide-react';

import { useDocuments } from '@/hooks/useDocuments';
import { DocumentCard } from './DocumentCard';

export function DocumentList() {
  const { data, isLoading, isError, error } = useDocuments(1, 50);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center gap-2 py-12 text-sm text-[#64748B]">
        <Loader2 size={16} className="animate-spin" />
        Loading documents…
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-xl border border-red-500/20 bg-red-500/5 px-4 py-6 text-center text-sm text-red-400">
        Failed to load documents: {(error as Error).message}
      </div>
    );
  }

  const docs = data?.documents ?? [];

  if (docs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-[#1E1E2E] bg-[#13131F] py-12 text-center">
        <FileText size={28} className="text-[#64748B]" />
        <div>
          <p className="text-sm font-medium text-white">No documents yet</p>
          <p className="mt-0.5 text-xs text-[#64748B]">
            Upload your first document above to get started.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <p className="text-xs text-[#64748B]">
        {data?.total ?? 0} document{(data?.total ?? 0) !== 1 ? 's' : ''} indexed
      </p>
      {docs.map((doc) => (
        <DocumentCard key={doc.id} document={doc} />
      ))}
    </div>
  );
}
