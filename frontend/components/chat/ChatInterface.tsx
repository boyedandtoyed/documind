'use client';

import { AnimatePresence, motion } from 'framer-motion';
import { BookOpenCheck, Database, FileSearch, LockKeyhole, Send, Square, Trash2 } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

import { useChat } from '@/hooks/useChat';
import { MessageBubble } from './MessageBubble';

export function ChatInterface() {
  const { messages, isLoading, error, sendMessage, stopStreaming, clearMessages } = useChat();
  const [input, setInput] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;
    setInput('');
    void sendMessage(trimmed);
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as React.FormEvent);
    }
  }

  function handleInput(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setInput(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = Math.min(e.target.scrollHeight, 160) + 'px';
  }

  const isEmpty = messages.length === 0;

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto px-4 py-6 pb-32 md:pb-8">
        {isEmpty ? (
          <EmptyState onPick={(value) => setInput(value)} />
        ) : (
          <div className="mx-auto max-w-3xl space-y-6">
            <AnimatePresence initial={false}>
              {messages.map((msg) => (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <MessageBubble message={msg} />
                </motion.div>
              ))}
            </AnimatePresence>
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {error && (
        <div className="mx-4 mb-2 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2 text-sm text-red-400">
          {error}
        </div>
      )}

      <div className="border-t border-[#1E1E2E] bg-[#0A0A0F]/82 px-4 py-4 backdrop-blur-sm">
        <form onSubmit={handleSubmit} className="mx-auto max-w-3xl">
          <div className="relative flex items-end gap-2 rounded-xl border border-[#1E1E2E] bg-[#13131F] p-3 shadow-2xl shadow-black/20 transition-all focus-within:border-indigo-500/50 focus-within:ring-1 focus-within:ring-indigo-500/20">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={handleInput}
              onKeyDown={handleKeyDown}
              placeholder="Ask anything about your documents..."
              rows={1}
              className="max-h-40 min-h-7 flex-1 resize-none bg-transparent text-sm leading-6 text-[#F1F5F9] outline-none placeholder:text-[#64748B]"
              disabled={isLoading}
            />
            <div className="flex shrink-0 items-center gap-2">
              {messages.length > 0 && (
                <button
                  type="button"
                  onClick={clearMessages}
                  className="flex h-8 w-8 items-center justify-center rounded-lg text-[#64748B] transition hover:bg-white/5 hover:text-white"
                  title="Clear chat"
                >
                  <Trash2 size={15} />
                </button>
              )}
              {isLoading ? (
                <button
                  type="button"
                  onClick={stopStreaming}
                  className="flex h-8 items-center gap-1.5 rounded-lg bg-red-500/20 px-3 text-xs font-medium text-red-400 transition hover:bg-red-500/30"
                >
                  <Square size={12} />
                  Stop
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={!input.trim()}
                  className="flex h-8 items-center gap-1.5 rounded-lg bg-gradient-to-r from-indigo-500 to-violet-500 px-3 text-xs font-semibold text-white transition hover:from-indigo-400 hover:to-violet-400 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  <Send size={13} />
                  Send
                </button>
              )}
            </div>
          </div>
          <p className="mt-2 text-center text-[10px] text-[#64748B]">
            gemma3:27b / nomic-embed-text / Qdrant + Neo4j / fully local
          </p>
        </form>
      </div>
    </div>
  );
}

function EmptyState({ onPick }: { onPick: (value: string) => void }) {
  const suggestions = [
    'Summarize the key findings with citations',
    'What are the main risks?',
    'Compare the two approaches',
  ];

  return (
    <div className="mx-auto flex min-h-full max-w-4xl flex-col justify-center gap-8 py-8">
      <motion.div
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="max-w-2xl"
      >
        <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-[#1E1E2E] bg-[#13131F]/80 px-3 py-1 text-xs font-medium text-[#64748B]">
          <LockKeyhole size={13} className="text-indigo-400" />
          Fully local RAG on your own GPU
        </div>
        <h2 className="text-3xl font-semibold tracking-tight text-white sm:text-5xl">
          Ask your documents. Keep every token local.
        </h2>
        <p className="mt-4 max-w-xl text-sm leading-6 text-[#94A3B8] sm:text-base">
          DocuMind indexes PDFs, DOCX, TXT, and Markdown into cited answers with hybrid search,
          graph context, and automatic quality scoring.
        </p>
      </motion.div>

      <div className="grid gap-3 md:grid-cols-3">
        <Feature icon={<FileSearch size={18} />} label="Cited answers" value="Source excerpts stay attached." />
        <Feature icon={<Database size={18} />} label="Hybrid search" value="Dense vectors, sparse BM25, and RRF fusion." />
        <Feature icon={<BookOpenCheck size={18} />} label="Quality scored" value="Faithfulness and relevance on every answer." />
      </div>

      <div className="flex flex-wrap gap-2">
        {suggestions.map((suggestion) => (
          <button
            key={suggestion}
            type="button"
            onClick={() => onPick(suggestion)}
            className="rounded-full border border-[#1E1E2E] bg-[#13131F]/80 px-3 py-2 text-left text-xs font-medium text-[#94A3B8] transition hover:border-indigo-500/50 hover:text-white"
          >
            {suggestion}
          </button>
        ))}
      </div>
    </div>
  );
}

function Feature({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-lg border border-[#1E1E2E] bg-[#13131F]/78 p-4">
      <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500/20 via-violet-500/20 to-pink-500/20 text-indigo-300">
        {icon}
      </div>
      <p className="text-sm font-semibold text-white">{label}</p>
      <p className="mt-1 text-xs leading-5 text-[#64748B]">{value}</p>
    </div>
  );
}
