'use client';

import { useState } from 'react';

import type { ChatMessage } from '@/types';
import { CitationCard } from './CitationCard';
import { QualityBadge } from './QualityBadge';
import { StreamingMessage } from './StreamingMessage';

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const [citationsOpen, setCitationsOpen] = useState(false);
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-2xl rounded-tr-sm bg-gradient-to-br from-indigo-500 to-violet-600 px-4 py-3 text-sm text-white shadow-lg shadow-indigo-500/20">
          <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-[90%] space-y-2">
        {/* Assistant bubble */}
        <div className="relative rounded-2xl rounded-tl-sm border border-[#1E1E2E] bg-[#13131F] px-4 py-3 shadow-sm">
          <div className="absolute left-0 top-4 h-10 w-0.5 rounded-r-full bg-gradient-to-b from-indigo-500 to-violet-500" />
          <div className="pl-2">
            {message.isStreaming ? (
              <StreamingMessage content={message.content} />
            ) : (
              <p className="whitespace-pre-wrap text-sm leading-relaxed text-[#F1F5F9]">
                {message.content}
              </p>
            )}

            {/* Latency */}
            {message.latency_ms !== undefined && !message.isStreaming && (
              <p className="mt-2 text-right text-[10px] text-[#64748B]">
                {(message.latency_ms / 1000).toFixed(1)}s
              </p>
            )}
          </div>
        </div>

        {/* Metrics + Citations row */}
        {!message.isStreaming && message.metrics && (
          <div className="flex flex-wrap items-center gap-2 pl-2">
            <QualityBadge metrics={message.metrics} compact />
            {message.citations && message.citations.length > 0 && (
              <button
                onClick={() => setCitationsOpen((v) => !v)}
                className="text-xs text-[#64748B] underline-offset-2 transition hover:text-indigo-400 hover:underline"
              >
                {citationsOpen ? 'Hide' : 'Show'} {message.citations.length} source
                {message.citations.length !== 1 ? 's' : ''}
              </button>
            )}
          </div>
        )}

        {/* Citations accordion */}
        {citationsOpen && message.citations && message.citations.length > 0 && (
          <div className="space-y-2 pl-2">
            {message.citations.map((citation) => (
              <CitationCard key={citation.chunk_id} citation={citation} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
