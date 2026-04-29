'use client';

import { Zap } from 'lucide-react';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL?.replace('/api/v1', '') ?? 'http://localhost:8000';

const PAGE_TITLES: Record<string, { title: string; description: string }> = {
  '/chat': { title: 'Chat', description: 'Ask questions about your documents' },
  '/documents': { title: 'Documents', description: 'Manage your knowledge base' },
  '/analytics': { title: 'Analytics', description: 'Monitor RAG quality metrics' },
};

type OllamaStatus = 'checking' | 'online' | 'offline';

export function Header() {
  const pathname = usePathname();
  const meta = PAGE_TITLES[pathname] ?? { title: 'DocuMind', description: 'Production RAG Engine' };
  const [ollamaStatus, setOllamaStatus] = useState<OllamaStatus>('checking');

  useEffect(() => {
    let alive = true;

    async function checkHealth() {
      try {
        const res = await fetch(`${BASE_URL}/health`, { cache: 'no-store' });
        if (!alive) return;
        if (res.ok) {
          const data = await res.json();
          setOllamaStatus(data.ollama?.reachable ? 'online' : 'offline');
        } else {
          setOllamaStatus('offline');
        }
      } catch {
        if (alive) setOllamaStatus('offline');
      }
    }

    void checkHealth();
    const timer = setInterval(() => void checkHealth(), 30_000);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, []);

  return (
    <header className="flex min-h-16 items-center justify-between gap-4 border-b border-[#1E1E2E] bg-[#0A0A0F]/80 px-4 py-3 backdrop-blur-sm md:px-6">
      <div className="flex min-w-0 items-center gap-3">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 via-violet-500 to-pink-500 md:hidden">
          <Zap size={16} className="text-white" />
        </div>
        <div className="min-w-0">
          <h1 className="truncate text-sm font-semibold text-white">{meta.title}</h1>
          <p className="truncate text-xs text-[#64748B]">{meta.description}</p>
        </div>
      </div>

      {ollamaStatus === 'checking' ? (
        <span className="flex shrink-0 items-center gap-1.5 rounded-full border border-[#1E1E2E] bg-[#13131F] px-3 py-1 text-xs text-[#64748B]">
          <span className="h-1.5 w-1.5 rounded-full bg-[#64748B] pulse-dot" />
          <span className="hidden sm:inline">Connecting...</span>
          <span className="sm:hidden">Check</span>
        </span>
      ) : ollamaStatus === 'online' ? (
        <span className="flex shrink-0 items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-400">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 pulse-dot" />
          <span className="hidden sm:inline">gemma3:27b / P40 / Local</span>
          <span className="sm:hidden">Local</span>
        </span>
      ) : (
        <span className="flex shrink-0 items-center gap-1.5 rounded-full border border-red-500/30 bg-red-500/10 px-3 py-1 text-xs font-medium text-red-400">
          <span className="h-1.5 w-1.5 rounded-full bg-red-400" />
          <span className="hidden sm:inline">Ollama offline</span>
          <span className="sm:hidden">Offline</span>
        </span>
      )}
    </header>
  );
}
