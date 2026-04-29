'use client';

import { Clock, FileText, Layers, MessageSquare, TrendingUp } from 'lucide-react';

import { useUsageStats } from '@/hooks/useAnalytics';

function StatRow({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-center justify-between border-b border-[#1E1E2E] py-3 last:border-0">
      <div className="flex items-center gap-2 text-sm text-[#64748B]">
        <span className="text-indigo-400">{icon}</span>
        {label}
      </div>
      <span className="text-sm font-semibold tabular-nums text-white">{value}</span>
    </div>
  );
}

export function UsageStats() {
  const { data, isLoading } = useUsageStats();

  if (isLoading || !data) {
    return (
      <div className="glass rounded-xl p-6">
        <p className="mb-4 text-sm font-semibold text-white">Usage Statistics</p>
        <div className="space-y-3">
          {[0, 1, 2, 3, 4].map((i) => (
            <div key={i} className="flex justify-between border-b border-[#1E1E2E] py-3 last:border-0">
              <div className="shimmer h-4 w-32 rounded" />
              <div className="shimmer h-4 w-16 rounded" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="glass rounded-xl p-6">
      <p className="mb-2 text-sm font-semibold text-white">Usage Statistics</p>
      <StatRow icon={<MessageSquare size={14} />} label="Total queries" value={data.total_queries.toLocaleString()} />
      <StatRow icon={<TrendingUp size={14} />} label="Queries today" value={data.queries_today.toLocaleString()} />
      <StatRow icon={<FileText size={14} />} label="Documents indexed" value={data.total_documents.toLocaleString()} />
      <StatRow icon={<Layers size={14} />} label="Total chunks" value={data.total_chunks.toLocaleString()} />
      <StatRow
        icon={<Clock size={14} />}
        label="Avg. response time"
        value={data.avg_latency_ms > 0 ? `${(data.avg_latency_ms / 1000).toFixed(1)}s` : '-'}
      />
    </div>
  );
}
