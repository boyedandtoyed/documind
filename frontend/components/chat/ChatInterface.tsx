'use client';

import { AnimatePresence, motion } from 'framer-motion';
import { Send, Square, Trash2 } from 'lucide-react';
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
      {/* Message list */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        {isEmpty ? (
          <EmptyState />
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

      {/* Error banner */}
      {error && (
        <div className="mx-4 mb-2 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Input area */}
      <div className="border-t border-[#1E1E2E] bg-[#0A0A0F]/80 px-4 py-4 backdrop-blur-sm">
        <form onSubmit={handleSubmit} className="mx-auto max-w-3xl">
          <div className="relative flex items-end gap-2 rounded-xl border border-[#1E1E2E] bg-[#13131F] p-3 focus-within:border-indigo-500/50 focus-within:ring-1 focus-within:ring-indigo-500/20 transition-all">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={handleInput}
              onKeyDown={handleKeyDown}
              placeholder="Ask anything about your documents…"
              rows={1}
              className="flex-1 resize-none bg-transparent text-sm text-[#F1F5F9] placeholder-[#64748B] outline-none"
              style={{ maxHeight: '160px' }}
              disabled={isLoading}
            />
            <div className="flex shrink-0 items-center gap-2">
              {messages.length > 0 && (
                <button
                  type="button"
                  onClick={clearMessages}
                  className="rounded-lg p-1.5 text-[#64748B] transition hover:bg-white/5 hover:text-white"
                  title="Clear chat"
                >
                  <Trash2 size={15} />
                </button>
              )}
              {isLoading ? (
                <button
                  type="button"
                  onClick={stopStreaming}
                  className="flex items-center gap-1.5 rounded-lg bg-red-500/20 px-3 py-1.5 text-xs font-medium text-red-400 transition hover:bg-red-500/30"
                >
                  <Square size={12} />
                  Stop
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={!input.trim()}
                  className="flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-indigo-500 to-violet-500 px-3 py-1.5 text-xs font-semibold text-white transition hover:from-indigo-400 hover:to-violet-400 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  <Send size={13} />
                  Send
                </button>
              )}
            </div>
          </div>
          <p className="mt-1.5 text-center text-[10px] text-[#64748B]">
            gemma3:27b · nomic-embed-text · Qdrant + Neo4j · Fully local
          </p>
        </form>
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 via-violet-500 to-pink-500 shadow-lg shadow-indigo-500/25">
        <span className="text-2xl">⚡</span>
      </div>
      <div>
        <h3 className="text-lg font-semibold text-white">DocuMind</h3>
        <p className="mt-1 max-w-sm text-sm text-[#64748B]">
          Upload documents and ask questions. Answers are grounded in your data with source citations.
        </p>
      </div>
      <div className="flex flex-wrap justify-center gap-2">
        {[
          'Summarize the key findings',
          'What are the main risks?',
          'Compare the two approaches',
        ].map((suggestion) => (
          <span
            key={suggestion}
            className="rounded-full border border-[#1E1E2E] px-3 py-1 text-xs text-[#64748B]"
          >
            {suggestion}
          </span>
        ))}
      </div>
    </div>
  );
}
