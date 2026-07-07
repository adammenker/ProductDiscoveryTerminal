import type {
  PipelineRunResponse,
  PluginCatalog,
  PluginRunSummary,
  ProductDetail,
  ProductFilters,
  ProductListResponse
} from "@/types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    }
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `Request failed with ${response.status}`);
  }

  return response.json() as Promise<T>;
}

function toQuery(filters: ProductFilters = {}) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    params.set(key, String(value));
  });
  const query = params.toString();
  return query ? `?${query}` : "";
}

export const api = {
  products: (filters?: ProductFilters) =>
    fetchJson<ProductListResponse>(`/products${toQuery(filters)}`),
  opportunities: (filters?: ProductFilters) =>
    fetchJson<ProductListResponse>(`/opportunities${toQuery(filters)}`),
  product: (id: string) => fetchJson<ProductDetail>(`/products/${id}`),
  plugins: () => fetchJson<PluginCatalog>("/plugins"),
  pluginRuns: (limit = 50) => fetchJson<PluginRunSummary[]>(`/plugin-runs?limit=${limit}`),
  runPipeline: () =>
    fetchJson<PipelineRunResponse>("/ingestion/run", {
      method: "POST",
      body: JSON.stringify({})
    })
};

