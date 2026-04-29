import type { Metadata } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import './globals.css';
import { Providers } from './providers';

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' });
const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
});

export const metadata: Metadata = {
  title: 'DocuMind - Local RAG Engine',
  description:
    'Production-grade RAG engine. Fully local, no cloud APIs. gemma3:27b, nomic-embed-text, Qdrant, and Neo4j.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrainsMono.variable}`}>
      <body className="bg-[#0A0A0F] font-sans text-[#F1F5F9] antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
