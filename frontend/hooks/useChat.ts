'use client';

import { useCallback, useRef, useState } from 'react';

import { queryApi } from '@/lib/api';
import { streamQuery } from '@/lib/streaming';
import type { ChatMessage, Citation, EvaluationMetrics } from '@/types';

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(async (content: string, useStream = true) => {
    if (!content.trim() || isLoading) return;

    setError(null);
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      timestamp: new Date(),
    };

    const assistantId = crypto.randomUUID();
    const assistantPlaceholder: ChatMessage = {
      id: assistantId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isStreaming: true,
    };

    setMessages((prev) => [...prev, userMessage, assistantPlaceholder]);
    setIsLoading(true);

    if (useStream) {
      abortRef.current = new AbortController();
      let accumulated = '';

      try {
        await streamQuery(
          queryApi.streamUrl(),
          { query: content, top_k: 5, use_graph: true },
          {
            onToken: (token) => {
              accumulated += token;
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? { ...m, content: accumulated }
                    : m,
                ),
              );
            },
            onDone: (
              citations: Citation[],
              metrics: EvaluationMetrics,
              queryId: string,
            ) => {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? { ...m, citations, metrics, isStreaming: false }
                    : m,
                ),
              );
              setIsLoading(false);
            },
            onError: (err: string) => {
              setError(err);
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? {
                        ...m,
                        content: 'Sorry, an error occurred. Please try again.',
                        isStreaming: false,
                      }
                    : m,
                ),
              );
              setIsLoading(false);
            },
          },
          abortRef.current.signal,
        );
      } catch (e) {
        if ((e as Error).name !== 'AbortError') {
          const msg = (e as Error).message ?? 'Unknown error';
          setError(msg);
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, content: msg, isStreaming: false }
                : m,
            ),
          );
        }
        setIsLoading(false);
      }
    } else {
      try {
        const response = await queryApi.query({ query: content, top_k: 5, use_graph: true });
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? {
                  ...m,
                  content: response.answer,
                  citations: response.citations,
                  metrics: response.metrics,
                  latency_ms: response.latency_ms,
                  graph_entities: response.graph_entities,
                  isStreaming: false,
                }
              : m,
          ),
        );
      } catch (e) {
        const msg = (e as Error).message ?? 'Unknown error';
        setError(msg);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, content: msg, isStreaming: false }
              : m,
          ),
        );
      } finally {
        setIsLoading(false);
      }
    }
  }, [isLoading]);

  const stopStreaming = useCallback(() => {
    abortRef.current?.abort();
    setIsLoading(false);
    setMessages((prev) =>
      prev.map((m) => (m.isStreaming ? { ...m, isStreaming: false } : m)),
    );
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return { messages, isLoading, error, sendMessage, stopStreaming, clearMessages };
}
