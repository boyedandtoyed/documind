'use client';

import { Activity, Brain, Target, Zap } from 'lucide-react';

import { useQualityMetrics } from '@/hooks/useAnalytics';

interface MetricCardProps {
  label: string;
  value: number;
  icon: React.ReactNode;
  description: string;
}

function MetricCard({ label, value, icon, description }: MetricCardProps) {
  const pct = Math.round(value * 100);
  const color =
    pct >= 80 ? 'text-emerald-400' : pct >= 60 ? 'text-amber-400' : 'text-red-400';
  const barColor =
    pct >= 80
      ? 'from-emerald-500 to-emerald-400'
      : pct >= 60
      ? 'from-amber-500 to-amber-400'
      : 'from-red-500 to-red-400';

  return (
    <div className="glass rounded-xl p-5">
      <div className="flex items-start justify-between">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-[#1E1E2E] bg-[#0D0D17] text-indigo-400">
          {icon}
        </div>
        <span className={`text-2xl font-bold tabular-nums ${color}`}>{pct}%</span>
      </div>
      <div className="mt-3">
        <p className="text-sm font-semibold text-white">{label}</p>
        <p className="mt-0.5 text-xs text-[#64748B]">{description}</p>
      </div>
      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-[#1E1E2E]">
        <div
          className={`h-full rounded-full bg-gradient-to-r transition-all duration-700 ${barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="glass rounded-xl p-5">
      <div className="shimmer h-9 w-9 rounded-lg" />
      <div className="mt-3 space-y-2">
        <div className="shimmer h-4 w-24 rounded" />
        <div className="shimmer h-3 w-36 rounded" />
      </div>
      <div className="shimmer mt-3 h-1.5 rounded-full" />
    </div>
  );
}

export function MetricsGrid() {
  const { data, isLoading } = useQualityMetrics();

  if (isLoading || !data) {
    return (
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {[0, 1, 2, 3].map((i) => <SkeletonCard key={i} />)}
      </div>
    );
  }

  const metrics = [
    {
      label: 'Faithfulness',
      value: data.avg_faithfulness,
      icon: <Brain size={17} />,
      description: 'Answer grounded in retrieved context',
    },
    {
      label: 'Answer Relevancy',
      value: data.avg_answer_relevancy,
      icon: <Target size={17} />,
      description: 'How well the answer addresses the query',
    },
    {
      label: 'Context Recall',
      value: data.avg_context_recall,
      icon: <Zap size={17} />,
      description: 'Coverage of necessary information',
    },
    {
      label: 'Context Precision',
      value: data.avg_context_precision,
      icon: <Activity size={17} />,
      description: 'Fraction of retrieved chunks that were useful',
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {metrics.map((m) => (
        <MetricCard key={m.label} {...m} />
      ))}
    </div>
  );
}
