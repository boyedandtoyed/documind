import { ChatInterface } from '@/components/chat/ChatInterface';
import { Header } from '@/components/layout/Header';
import { BottomNav, Sidebar } from '@/components/layout/Sidebar';

export default function ChatPage() {
  return (
    <div className="page-shell flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-hidden">
          <ChatInterface />
        </main>
      </div>
      <BottomNav />
    </div>
  );
}
