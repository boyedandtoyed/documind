import { DocumentList } from '@/components/documents/DocumentList';
import { UploadZone } from '@/components/documents/UploadZone';
import { Header } from '@/components/layout/Header';
import { BottomNav, Sidebar } from '@/components/layout/Sidebar';

export default function DocumentsPage() {
  return (
    <div className="page-shell flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-4 pb-20 md:p-6">
          <div className="mx-auto max-w-4xl space-y-6">
            <div>
              <h2 className="text-xl font-semibold text-white">Knowledge Base</h2>
              <p className="mt-1 text-sm text-[#64748B]">
                Upload documents to index. Supports PDF, DOCX, and TXT.
              </p>
            </div>
            <UploadZone />
            <DocumentList />
          </div>
        </main>
      </div>
      <BottomNav />
    </div>
  );
}
