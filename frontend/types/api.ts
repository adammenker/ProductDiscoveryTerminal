export type Recommendation =
  | "strong_opportunity"
  | "investigate"
  | "watch"
  | "needs_more_data"
  | "skip";

export type ProductListItem = {
  id: string;
  canonical_name: string;
  category: string | null;
  status: string;
  latest_score: number | null;
  recommendation: Recommendation | null;
  demand_score: number | null;
  growth_score: number | null;
  competition_score: number | null;
  margin_score: number | null;
  pain_point_score: number | null;
  risk_score: number | null;
  confidence_score: number | null;
  explanation: string | null;
  updated_at: string;
};

export type ProductListResponse = {
  items: ProductListItem[];
  total: number;
};

export type ScoreRecord = {
  id: string;
  product_id: string;
  scoring_version: string;
  demand_score: number;
  growth_score: number;
  competition_score: number;
  margin_score: number;
  pain_point_score: number;
  risk_score: number;
  confidence_score: number;
  final_score: number;
  recommendation: Recommendation;
  explanation: string;
  score_breakdown: {
    weights?: Record<string, number>;
    signals?: Record<string, unknown>;
  };
  created_at: string;
};

export type ProductDetail = {
  product: {
    id: string;
    canonical_name: string;
    category: string | null;
    subcategory: string | null;
    description: string | null;
    status: string;
    created_at: string;
    updated_at: string;
  };
  aliases: Array<Record<string, unknown>>;
  latest_score: ScoreRecord | null;
  market_signals: Array<Record<string, unknown>>;
  supplier_signals: Array<Record<string, unknown>>;
  cost_models: Array<Record<string, unknown>>;
  insights: Array<Record<string, unknown>>;
  recent_observations: Array<Record<string, unknown>>;
};

export type PluginInfo = {
  name: string;
  version: string;
  enabled: boolean;
  type: string;
  description: string | null;
  supports: string[];
};

export type PluginCatalog = {
  ingestion: PluginInfo[];
  analyzers: PluginInfo[];
};

export type PluginRunSummary = {
  id: string | null;
  plugin_name: string;
  plugin_type: string | null;
  status: string;
  records_created: number;
  records_updated: number;
  error_message: string | null;
  started_at: string | null;
  finished_at: string | null;
};

export type PipelineRunResponse = {
  status: string;
  plugin_runs: PluginRunSummary[];
  products_updated: number;
  scores_updated: number;
  observations_created: number;
  errors: string[];
};

export type ProductFilters = {
  q?: string;
  category?: string;
  min_score?: number;
  recommendation?: string;
  limit?: number;
  offset?: number;
};

