'use client';

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { useQualityMetrics } from '@/hooks/useAnalytics';

const LINES = [
  { key: 'faithfulness', color: '#6366F1', label: 'Faithfulness' },
  { key: 'answer_relevancy', color: '#8B5CF6', label: 'Relevancy' },
  { key: 'context_recall', color: '#EC4899', label: 'Recall' },
] as const;

export function QualityChart() {
  const { data, isLoading } = useQualityMetrics();

  if (isLoading) {
    return (
      <div className="glass rounded-xl p-6">
        <p className="mb-4 text-sm font-semibold text-white">Quality Over Time</p>
        <div className="shimmer h-48 rounded-lg" />
      </div>
    );
  }

  const chartData = (data?.metrics_over_time ?? []).map((row) => ({
    ...row,
    faithfulness: Math.round(row.faithfulness * 100),
    answer_relevancy: Math.round(row.answer_relevancy * 100),
    context_recall: Math.round(row.context_recall * 100),
  }));

  if (chartData.length === 0) {
    return (
      <div className="glass rounded-xl p-6">
        <p className="mb-4 text-sm font-semibold text-white">Quality Over Time</p>
        <div className="flex h-48 items-center justify-center text-center text-sm text-[#64748B]">
          No query history yet. Start asking questions to see trends.
        </div>
      </div>
    );
  }

  return (
    <div className="glass rounded-xl p-6">
      <p className="mb-4 text-sm font-semibold text-white">Quality Over Time</p>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={chartData} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1E1E2E" />
          <XAxis
            dataKey="date"
            tick={{ fill: '#64748B', fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: '#1E1E2E' }}
          />
          <YAxis
            domain={[0, 100]}
            tick={{ fill: '#64748B', fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => `${v}%`}
          />
          <Tooltip
            contentStyle={{
              background: '#13131F',
              border: '1px solid #1E1E2E',
              borderRadius: '8px',
              fontSize: '12px',
              color: '#F1F5F9',
            }}
            formatter={(value: number) => [`${value}%`]}
          />
          <Legend
            wrapperStyle={{ fontSize: '12px', color: '#64748B' }}
            iconType="circle"
            iconSize={8}
          />
          {LINES.map(({ key, color, label }) => (
            <Line
              key={key}
              type="monotone"
              dataKey={key}
              name={label}
              stroke={color}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: color, strokeWidth: 0 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
