import type { Citation, EvaluationMetrics, StreamChunk } from '@/types';

export interface StreamCallbacks {
  onToken: (token: string) => void;
  onDone: (citations: Citation[], metrics: EvaluationMetrics, queryId: string) => void;
  onError: (error: string) => void;
}

export async function streamQuery(
  url: string,
  body: object,
  callbacks: StreamCallbacks,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  });

  if (!res.ok || !res.body) {
    callbacks.onError(`Request failed: ${res.status} ${res.statusText}`);
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() ?? '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || !trimmed.startsWith('data:')) continue;

        const data = trimmed.slice(5).trim();
        if (data === '[DONE]') return;

        try {
          const chunk = JSON.parse(data) as StreamChunk;
          handleChunk(chunk, callbacks);
        } catch {
          // malformed SSE line — skip
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

function handleChunk(chunk: StreamChunk, callbacks: StreamCallbacks): void {
  switch (chunk.type) {
    case 'token':
      if (chunk.content) callbacks.onToken(chunk.content);
      break;
    case 'done':
      callbacks.onDone(
        chunk.citations ?? [],
        chunk.metrics ?? defaultMetrics(),
        chunk.query_id ?? '',
      );
      break;
    case 'error':
      callbacks.onError(chunk.content);
      break;
    default:
      break;
  }
}

function defaultMetrics(): EvaluationMetrics {
  return {
    faithfulness: 0,
    answer_relevancy: 0,
    context_recall: 0,
    context_precision: 0,
  };
}
