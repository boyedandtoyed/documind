import { MetricsGrid } from '@/components/analytics/MetricsGrid';
import { QualityChart } from '@/components/analytics/QualityChart';
import { UsageStats } from '@/components/analytics/UsageStats';
import { Header } from '@/components/layout/Header';
import { BottomNav, Sidebar } from '@/components/layout/Sidebar';

export default function AnalyticsPage() {
  return (
    <div className="page-shell flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-4 pb-20 md:p-6">
          <div className="mx-auto max-w-5xl space-y-6">
            <div>
              <h2 className="text-xl font-semibold text-white">RAG Quality Analytics</h2>
              <p className="mt-1 text-sm text-[#64748B]">
                RAGAS evaluation metrics for faithfulness, relevancy, recall, and precision.
              </p>
            </div>
            <MetricsGrid />
            <QualityChart />
            <UsageStats />
          </div>
        </main>
      </div>
      <BottomNav />
    </div>
  );
}
