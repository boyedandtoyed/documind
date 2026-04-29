import type {
  Document,
  DocumentListResponse,
  DocumentUploadResponse,
  QualityMetrics,
  QueryRequest,
  QueryResponse,
  UsageStats,
} from '@/types';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1';

class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(detail);
    this.name = 'ApiError';
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const headers = new Headers(init?.headers);
  if (!(init?.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const res = await fetch(url, {
    ...init,
    headers,
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = (await res.json()) as { detail?: string };
      detail = body.detail ?? detail;
    } catch {
      // Non-JSON error responses still surface as HTTP status text.
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) {
    return undefined as T;
  }

  return res.json() as Promise<T>;
}

export const documentsApi = {
  list(page = 1, pageSize = 20): Promise<DocumentListResponse> {
    return request<DocumentListResponse>(`/documents?page=${page}&page_size=${pageSize}`);
  },

  get(id: string): Promise<Document> {
    return request<Document>(`/documents/${id}`);
  },

  upload(file: File): Promise<DocumentUploadResponse> {
    const form = new FormData();
    form.append('file', file);
    return request<DocumentUploadResponse>('/documents/upload', {
      method: 'POST',
      body: form,
    });
  },

  delete(id: string): Promise<void> {
    return request<void>(`/documents/${id}`, { method: 'DELETE' });
  },
};

export const queryApi = {
  query(req: QueryRequest): Promise<QueryResponse> {
    return request<QueryResponse>('/query', {
      method: 'POST',
      body: JSON.stringify(req),
    });
  },

  streamUrl(): string {
    return `${BASE_URL}/query/stream`;
  },
};

export const analyticsApi = {
  usage(): Promise<UsageStats> {
    return request<UsageStats>('/analytics/usage');
  },

  quality(): Promise<QualityMetrics> {
    return request<QualityMetrics>('/analytics/quality');
  },
};

export { ApiError };
