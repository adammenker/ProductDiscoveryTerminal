import type {
  BacktestSummary,
  ConstraintEvaluation,
  DiscoveryRun,
  DiscoveryRunInput,
  OutcomeCreateResponse,
  OutcomeInput,
  PaperTrade,
  PipelineRunInput,
  PipelineRunResponse,
  PluginCatalog,
  PluginRunSummary,
  ComparableAsin,
  ComparableUpdateInput,
  ProductCreateInput,
  ProductCreateResponse,
  ProductDetail,
  ProductFilters,
  ProductListResponse,
  ProductResearchInput,
  ProductResearchResponse,
  RecommendationFeedbackInput,
  SeedList,
  SeedListInput,
  ProductValidation,
  SnapshotInput,
  SnapshotResponse,
  SupplierQuote,
  SupplierQuoteInput
  , ValidationProject, SupplierRecord
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
    let message = body;
    try {
      const parsed = JSON.parse(body) as { detail?: string };
      message = parsed.detail ?? body;
    } catch {
      // Preserve non-JSON error bodies from proxies and the API.
    }
    throw new Error(message || `Request failed with ${response.status}`);
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

function post<T>(path: string, body: unknown) {
  return fetchJson<T>(path, {
    method: "POST",
    body: JSON.stringify(body)
  });
}

function patch<T>(path: string, body: unknown) {
  return fetchJson<T>(path, {
    method: "PATCH",
    body: JSON.stringify(body)
  });
}

export const api = {
  products: (filters?: ProductFilters) =>
    fetchJson<ProductListResponse>(`/products${toQuery(filters)}`),
  opportunities: (filters?: ProductFilters) =>
    fetchJson<ProductListResponse>(`/opportunities${toQuery(filters)}`),
  product: (id: string) => fetchJson<ProductDetail>(`/products/${id}`),
  createProduct: (input: ProductCreateInput) => post<ProductCreateResponse>("/products", input),
  updateComparable: (productId: string, asin: string, input: ComparableUpdateInput) =>
    patch<ComparableAsin>(`/products/${productId}/comparables/${encodeURIComponent(asin)}`, input),
  createRecommendationFeedback: (productId: string, input: RecommendationFeedbackInput) =>
    post<Record<string, unknown>>(`/products/${productId}/feedback`, input),
  productValidation: (id: string) =>
    fetchJson<ProductValidation>(`/products/${id}/validation`),
  supplierQuotes: (id: string) =>
    fetchJson<SupplierQuote[]>(`/products/${id}/supplier-quotes`),
  createSupplierQuote: (id: string, input: SupplierQuoteInput) =>
    post<SupplierQuote>(`/products/${id}/supplier-quotes`, input),
  evaluateConstraints: (id: string, profileId?: string) =>
    post<ConstraintEvaluation>(
      `/products/${id}/evaluate-constraints${profileId ? `?profile_id=${encodeURIComponent(profileId)}` : ""}`,
      {}
    ),
  createSnapshot: (id: string, input: SnapshotInput) =>
    post<SnapshotResponse>(`/products/${id}/snapshots`, input),
  paperTrades: () => fetchJson<PaperTrade[]>("/paper-trades"),
  addPaperTradeOutcome: (id: string, input: OutcomeInput) =>
    post<OutcomeCreateResponse>(`/paper-trades/${id}/outcomes`, input),
  backtestSummary: () => fetchJson<BacktestSummary>("/backtests/summary"),
  plugins: () => fetchJson<PluginCatalog>("/plugins"),
  pluginRuns: (limit = 50) => fetchJson<PluginRunSummary[]>(`/plugin-runs?limit=${limit}`),
  runPipeline: (input: PipelineRunInput = {}) =>
    post<PipelineRunResponse>("/ingestion/run", input),
  researchProduct: (input: ProductResearchInput) =>
    post<ProductResearchResponse>("/ingestion/research", input),
  refreshExistingProducts: (limit = 10) =>
    post<PipelineRunResponse>(`/ingestion/refresh-existing?limit=${limit}`, {}),
  seedLists: () => fetchJson<SeedList[]>("/discovery/seed-lists"),
  createSeedList: (input: SeedListInput) =>
    post<SeedList>("/discovery/seed-lists", input),
  discoveryRuns: (limit = 25) =>
    fetchJson<DiscoveryRun[]>(`/discovery/runs?limit=${limit}&include_details=false`),
  discoveryRun: (id: string) => fetchJson<DiscoveryRun>(`/discovery/runs/${id}`),
  createDiscoveryRun: (input: DiscoveryRunInput) =>
    post<DiscoveryRun>("/discovery/runs", input),
  validationProjects: (status?: string) => fetchJson<ValidationProject[]>(`/validation-projects${status ? `?status=${encodeURIComponent(status)}` : ""}`),
  validationProject: (id: string) => fetchJson<ValidationProject>(`/validation-projects/${id}`),
  startValidation: (productId: string, input: Record<string, unknown> = {}) => post<ValidationProject>("/validation-projects", { product_id: productId, ...input }),
  transitionValidation: (id: string, to_status: string, reason: string) => post<ValidationProject>(`/validation-projects/${id}/transition`, { to_status, reason, actor: "local_user" }),
  refreshValidationPacket: (id: string) => post(`/validation-projects/${id}/marketplace-packets/refresh`, {}),
  savePoeEvidence: (id: string, input: Record<string, unknown>) => fetchJson(`/validation-projects/${id}/poe-evidence`, { method: "PUT", body: JSON.stringify(input) }),
  generateRfq: (id: string) => post(`/validation-projects/${id}/rfqs/generate`, {}),
  reviseRfq: (projectId: string, rfqId: string, input: Record<string, unknown>) => patch(`/validation-projects/${projectId}/rfqs/${rfqId}`, input),
  suppliers: () => fetchJson<SupplierRecord[]>("/suppliers"),
  createSupplier: (input: Record<string, unknown>) => post<SupplierRecord>("/suppliers", input),
  createValidationQuote: (id: string, input: Record<string, unknown>) => post(`/validation-projects/${id}/quotes`, input),
  evaluateValidationGates: (id: string) => post(`/validation-projects/${id}/gates/evaluate`, {}),
  overrideValidationGate: (id: string, gate: string, reason: string) => post(`/validation-projects/${id}/gates/${gate}/override`, { reason, actor: "local_user" })
};
