'use client';

import {
  BarChart3,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  FileText,
  MessageSquare,
  Zap,
} from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';

import { useDocumentCount } from '@/hooks/useDocuments';

interface NavItem {
  href: string;
  label: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
}

const NAV_ITEMS: NavItem[] = [
  { href: '/chat', label: 'Chat', icon: MessageSquare },
  { href: '/documents', label: 'Documents', icon: FileText },
  { href: '/analytics', label: 'Analytics', icon: BarChart3 },
];

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();
  const docCount = useDocumentCount();

  return (
    <aside
      className={`
        relative flex flex-col border-r border-[#1E1E2E] bg-[#0D0D17] transition-all duration-300
        ${collapsed ? 'w-16' : 'w-60'}
        hidden md:flex
      `}
    >
      {/* Logo */}
      <div className="flex h-16 items-center gap-3 border-b border-[#1E1E2E] px-4">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 via-violet-500 to-pink-500">
          <Zap size={16} className="text-white" />
        </div>
        {!collapsed && (
          <span className="text-sm font-semibold tracking-wide text-white">
            DocuMind
          </span>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-1 p-2 pt-4">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + '/');
          return (
            <Link
              key={href}
              href={href}
              className={`
                group relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium
                transition-all duration-150
                ${
                  active
                    ? 'bg-gradient-to-r from-indigo-500/20 via-violet-500/10 to-transparent text-white'
                    : 'text-gray-400 hover:bg-white/5 hover:text-white'
                }
              `}
            >
              {active && (
                <span className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-r-full bg-gradient-to-b from-indigo-400 to-violet-400" />
              )}
              <Icon
                size={18}
                className={active ? 'text-indigo-400' : 'text-gray-500 group-hover:text-gray-300'}
              />
              {!collapsed && (
                <span className="flex-1">{label}</span>
              )}
              {!collapsed && label === 'Documents' && docCount > 0 && (
                <span className="rounded-full bg-indigo-500/20 px-1.5 py-0.5 text-xs font-semibold text-indigo-300">
                  {docCount}
                </span>
              )}
              {collapsed && label === 'Documents' && docCount > 0 && (
                <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-indigo-500 text-[10px] font-bold text-white">
                  {docCount > 9 ? '9+' : docCount}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="border-t border-[#1E1E2E] p-2">
        {!collapsed && (
          <div className="mb-2 px-3 py-2">
            <div className="flex items-center gap-2 text-xs text-gray-600">
              <BookOpen size={12} />
              <span>RAG · Hybrid Search · RAGAS</span>
            </div>
          </div>
        )}
        <button
          onClick={() => setCollapsed((v) => !v)}
          className="flex w-full items-center justify-center gap-2 rounded-lg px-3 py-2 text-gray-500 transition hover:bg-white/5 hover:text-gray-300"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          {!collapsed && <span className="text-xs">Collapse</span>}
        </button>
      </div>
    </aside>
  );
}

// Mobile bottom nav
export function BottomNav() {
  const pathname = usePathname();

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 flex border-t border-[#1E1E2E] bg-[#0D0D17] md:hidden">
      {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
        const active = pathname === href || pathname.startsWith(href + '/');
        return (
          <Link
            key={href}
            href={href}
            className={`
              flex flex-1 flex-col items-center gap-1 py-3 text-xs font-medium transition-colors
              ${active ? 'text-indigo-400' : 'text-gray-500'}
            `}
          >
            <Icon size={20} />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
