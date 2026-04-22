'use client';

import { CheckCircle2, FileText, Loader2, Upload, XCircle } from 'lucide-react';
import { useCallback, useState } from 'react';

import { useUploadDocument } from '@/hooks/useDocuments';

type UploadState = 'idle' | 'uploading' | 'success' | 'error';

export function UploadZone() {
  const [dragOver, setDragOver] = useState(false);
  const [uploadState, setUploadState] = useState<UploadState>('idle');
  const [resultMessage, setResultMessage] = useState('');
  const [chunkCount, setChunkCount] = useState(0);
  const { mutateAsync: upload } = useUploadDocument();

  const handleFiles = useCallback(
    async (files: FileList | null) => {
      if (!files || files.length === 0) return;
      const file = files[0];

      const ext = file.name.split('.').pop()?.toLowerCase();
      if (!['pdf', 'docx', 'txt', 'md'].includes(ext ?? '')) {
        setUploadState('error');
        setResultMessage(`Unsupported file type ".${ext}". Use PDF, DOCX, TXT, or MD.`);
        return;
      }

      setUploadState('uploading');
      setResultMessage('');

      try {
        const result = await upload(file);
        setUploadState('success');
        setChunkCount(result.chunk_count);
        setResultMessage(`"${file.name}" indexed into ${result.chunk_count} chunks.`);
        setTimeout(() => setUploadState('idle'), 4000);
      } catch (err) {
        setUploadState('error');
        setResultMessage((err as Error).message ?? 'Upload failed. Please try again.');
      }
    },
    [upload],
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      void handleFiles(e.dataTransfer.files);
    },
    [handleFiles],
  );

  return (
    <div>
      <label
        htmlFor="file-upload"
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        className={`
          flex cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-10 transition-all duration-200
          ${dragOver
            ? 'border-indigo-500 bg-indigo-500/5'
            : 'border-[#1E1E2E] bg-[#13131F] hover:border-indigo-500/50 hover:bg-indigo-500/5'
          }
          ${uploadState === 'uploading' ? 'pointer-events-none opacity-70' : ''}
        `}
      >
        <input
          id="file-upload"
          type="file"
          accept=".pdf,.docx,.txt,.md"
          className="hidden"
          onChange={(e) => void handleFiles(e.target.files)}
          disabled={uploadState === 'uploading'}
        />

        {uploadState === 'uploading' ? (
          <>
            <Loader2 size={32} className="animate-spin text-indigo-400" />
            <div className="text-center">
              <p className="text-sm font-medium text-white">Indexing document…</p>
              <p className="text-xs text-[#64748B]">Chunking · Embedding · Storing</p>
            </div>
            {/* Shimmer progress */}
            <div className="h-1.5 w-48 overflow-hidden rounded-full bg-[#1E1E2E]">
              <div className="shimmer h-full w-full rounded-full" />
            </div>
          </>
        ) : uploadState === 'success' ? (
          <>
            <CheckCircle2 size={32} className="text-emerald-400" />
            <div className="text-center">
              <p className="text-sm font-medium text-white">Done!</p>
              <p className="text-xs text-emerald-400">{resultMessage}</p>
            </div>
          </>
        ) : uploadState === 'error' ? (
          <>
            <XCircle size={32} className="text-red-400" />
            <div className="text-center">
              <p className="text-sm font-medium text-white">Upload failed</p>
              <p className="text-xs text-red-400">{resultMessage}</p>
            </div>
          </>
        ) : (
          <>
            <div className="flex h-14 w-14 items-center justify-center rounded-xl border border-[#1E1E2E] bg-[#0D0D17]">
              <Upload size={24} className="text-indigo-400" />
            </div>
            <div className="text-center">
              <p className="text-sm font-medium text-white">
                Drop a file or <span className="text-indigo-400">browse</span>
              </p>
              <p className="mt-1 text-xs text-[#64748B]">PDF · DOCX · TXT · MD — up to 50 MB</p>
            </div>
            <div className="flex gap-2">
              {['PDF', 'DOCX', 'TXT', 'MD'].map((ext) => (
                <span
                  key={ext}
                  className="flex items-center gap-1 rounded-md border border-[#1E1E2E] px-2 py-1 text-[10px] font-medium text-[#64748B]"
                >
                  <FileText size={10} />
                  {ext}
                </span>
              ))}
            </div>
          </>
        )}
      </label>
    </div>
  );
}
