'use client';

import { FileText, Layers, Loader2, Trash2 } from 'lucide-react';
import { useState } from 'react';

import { useDeleteDocument } from '@/hooks/useDocuments';
import type { Document } from '@/types';

interface DocumentCardProps {
  document: Document;
}

const STATUS_STYLES = {
  ready: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
  processing: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
  pending: 'text-blue-400 bg-blue-500/10 border-blue-500/20',
  failed: 'text-red-400 bg-red-500/10 border-red-500/20',
} as const;

const FILE_TYPE_COLORS = {
  pdf: 'text-red-400',
  docx: 'text-blue-400',
  txt: 'text-gray-400',
  md: 'text-purple-400',
} as const;

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

export function DocumentCard({ document }: DocumentCardProps) {
  const [confirmDelete, setConfirmDelete] = useState(false);
  const { mutate: deleteDoc, isPending } = useDeleteDocument();

  function handleDelete() {
    if (!confirmDelete) {
      setConfirmDelete(true);
      setTimeout(() => setConfirmDelete(false), 3000);
      return;
    }
    deleteDoc(document.id);
  }

  const typeColor = FILE_TYPE_COLORS[document.file_type] ?? 'text-gray-400';

  return (
    <div className="flex items-center gap-4 rounded-xl border border-[#1E1E2E] bg-[#13131F] px-4 py-3 transition hover:border-[#2E2E4E]">
      {/* Icon */}
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-[#1E1E2E] bg-[#0D0D17]">
        <FileText size={18} className={typeColor} />
      </div>

      {/* Info */}
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-white">{document.name}</p>
        <div className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-[#64748B]">
          <span>{formatBytes(document.file_size)}</span>
          {document.page_count !== null && <span>{document.page_count}p</span>}
          {document.chunk_count > 0 && (
            <span className="flex items-center gap-1">
              <Layers size={10} />
              {document.chunk_count} chunks
            </span>
          )}
          <span>{formatDate(document.created_at)}</span>
        </div>
      </div>

      {/* Status badge */}
      <span
        className={`shrink-0 rounded-full border px-2 py-0.5 text-xs font-medium capitalize ${
          STATUS_STYLES[document.status]
        }`}
      >
        {document.status === 'processing' && (
          <Loader2 size={10} className="mr-1 inline animate-spin" />
        )}
        {document.status}
      </span>

      {/* Delete */}
      <button
        onClick={handleDelete}
        disabled={isPending}
        className={`shrink-0 rounded-lg p-1.5 text-xs transition ${
          confirmDelete
            ? 'bg-red-500/20 text-red-400 hover:bg-red-500/30'
            : 'text-[#64748B] hover:bg-white/5 hover:text-red-400'
        }`}
        title={confirmDelete ? 'Click again to confirm' : 'Delete document'}
      >
        {isPending ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
      </button>
    </div>
  );
}
