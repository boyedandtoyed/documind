'use client';

import { FileText } from 'lucide-react';
import { useState } from 'react';

import type { Citation } from '@/types';

interface CitationCardProps {
  citation: Citation;
}

export function CitationCard({ citation }: CitationCardProps) {
  const [expanded, setExpanded] = useState(false);
  const score = Math.round(citation.relevance_score * 100);

  return (
    <div className="rounded-lg border border-[#1E1E2E] bg-[#0D0D17] p-3 text-xs">
      {/* Header row */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <FileText size={13} className="shrink-0 text-indigo-400" />
          <span className="truncate font-medium text-[#F1F5F9]">{citation.document_name}</span>
          {citation.page_number !== null && (
            <span className="shrink-0 text-[#64748B]">p.{citation.page_number}</span>
          )}
        </div>
        {/* Relevance score bar */}
        <div className="flex shrink-0 items-center gap-1.5">
          <div className="h-1.5 w-16 overflow-hidden rounded-full bg-[#1E1E2E]">
            <div
              className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-violet-500 transition-all"
              style={{ width: `${score}%` }}
            />
          </div>
          <span className="text-[#64748B]">{score}%</span>
        </div>
      </div>

      {/* Excerpt */}
      <button
        onClick={() => setExpanded((v) => !v)}
        className="mt-2 w-full text-left text-[#64748B] transition hover:text-[#94A3B8]"
      >
        <p className={`font-mono leading-relaxed ${expanded ? '' : 'line-clamp-2'}`}>
          {citation.text_excerpt}
        </p>
        {!expanded && citation.text_excerpt.length > 120 && (
          <span className="text-indigo-400">… show more</span>
        )}
        {expanded && <span className="text-indigo-400">show less</span>}
      </button>
    </div>
  );
}
