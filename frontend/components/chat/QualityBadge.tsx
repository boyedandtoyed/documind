'use client';

import type { EvaluationMetrics } from '@/types';

interface QualityBadgeProps {
  metrics: EvaluationMetrics;
  compact?: boolean;
}

function scoreColor(score: number): string {
  if (score >= 0.8) return 'text-emerald-400 bg-emerald-500/15 border-emerald-500/30';
  if (score >= 0.6) return 'text-yellow-400 bg-yellow-500/15 border-yellow-500/30';
  return 'text-red-400 bg-red-500/15 border-red-500/30';
}

function scoreLabel(score: number): string {
  if (score >= 0.8) return 'High';
  if (score >= 0.6) return 'Medium';
  return 'Low';
}

export function QualityBadge({ metrics, compact = false }: QualityBadgeProps) {
  const { faithfulness } = metrics;

  if (compact) {
    return (
      <span
        className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-semibold ${scoreColor(faithfulness)}`}
        title={`Faithfulness: ${(faithfulness * 100).toFixed(0)}%`}
      >
        <span className="h-1.5 w-1.5 rounded-full bg-current" />
        {(faithfulness * 100).toFixed(0)}%
      </span>
    );
  }

  return (
    <div className="mt-3 flex flex-wrap gap-2">
      <MetricPill label="Faithfulness" value={metrics.faithfulness} />
      <MetricPill label="Relevancy" value={metrics.answer_relevancy} />
      <MetricPill label="Recall" value={metrics.context_recall} />
      <MetricPill label="Precision" value={metrics.context_precision} />
    </div>
  );
}

function MetricPill({ label, value }: { label: string; value: number }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${scoreColor(value)}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current opacity-80" />
      {label}: {(value * 100).toFixed(0)}%
    </span>
  );
}
