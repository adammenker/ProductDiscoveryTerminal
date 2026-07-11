export type Recommendation =
  | "pursue"
  | "strong_opportunity"
  | "investigate"
  | "watch"
  | "needs_more_data"
  | "insufficient_data"
  | "skip";

export type ValidationDecision = "pursue" | "investigate" | "watch" | "skip";
export type PaperDecision = "paper_pursue" | "paper_watch" | "paper_skip";
export type OutcomeLabel =
  | "improved"
  | "flat"
  | "deteriorated"
  | "invalidated"
  | "insufficient_data";

export type ProductListItem = {
  id: string;
  canonical_name: string;
  category: string | null;
  status: string;
  latest_score: number | null;
  recommendation: Recommendation | null;
  opportunity_score: number | null;
  evidence_confidence_score: number | null;
  validation_readiness_score: number | null;
  scoring_version: string | null;
  demand_score: number | null;
  demand_proxy_score: number | null;
  growth_score: number | null;
  competition_score: number | null;
  margin_score: number | null;
  pain_point_score: number | null;
  risk_score: number | null;
  confidence_score: number | null;
  explanation: string | null;
  economics_decision: string | null;
  supplier_validation_decision: string | null;
  constraint_eligible: boolean | null;
  cross_source_confidence_score: number | null;
  validation_decision: ValidationDecision | null;
  missing_evidence: string[];
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
  demand_proxy_score?: number | null;
  growth_score: number;
  competition_score: number;
  margin_score: number;
  pain_point_score: number;
  risk_score: number;
  confidence_score: number;
  final_score: number | null;
  opportunity_score?: number | null;
  evidence_confidence_score?: number | null;
  validation_readiness_score?: number | null;
  recommendation: Recommendation;
  recommendation_reasons?: string[];
  missing_evidence?: string[];
  blocking_issues?: string[];
  next_actions?: string[];
  components?: Record<string, ScoreComponent>;
  explanation: string;
  score_breakdown: {
    weights?: Record<string, number>;
    signals?: Record<string, unknown>;
    components?: Record<string, ScoreComponent>;
    [key: string]: unknown;
  };
  created_at: string;
};

export type ScoreComponent = {
  name: string;
  value: number | null;
  status: string;
  coverage: number;
  confidence: number;
  evidence_count: number;
  freshness_days: number | null;
  evidence_ids: string[];
  explanation: string;
  warnings: string[];
  metadata: Record<string, unknown>;
};

export type DiscoverySource = {
  sources: string[];
  primary: string;
  last_updated: string | null;
  confidence: number | null;
};

export type ComparableAsin = {
  id?: string;
  product_id?: string;
  asin: string;
  title: string | null;
  url: string | null;
  price: number | null;
  brand: string | null;
  product_type?: string | null;
  category?: string | null;
  seed_category?: string | null;
  amazon_category?: string | null;
  amazon_product_type?: string | null;
  currency?: string | null;
  dimensions?: Record<string, unknown> | null;
  weight?: number | null;
  relevance_score?: number;
  relevance_status?: string;
  relevance_reasons?: string[];
  automatic_relevance_version?: string;
  manually_overridden?: boolean;
  manual_override_reason?: string | null;
  discovered_from_query?: string | null;
  discovered_at?: string;
  last_refreshed_at?: string;
  metadata?: Record<string, unknown>;
  sales_rank?: number | null;
  review_count?: number | null;
  fees?: number | null;
  source: string | null;
  observed_at?: string | null;
  selected_proxy: boolean;
};

export type MarketplaceHistoryRow = {
  id: string;
  snapshot_cohort_id: string | null;
  observation_fingerprint: string | null;
  asin: string;
  observed_at: string;
  price: number | null;
  featured_offer_price: number | null;
  lowest_offer_price: number | null;
  offer_count: number | null;
  seller_count: number | null;
  bestseller_rank: number | null;
  bestseller_category?: string | null;
  rank_category?: string | null;
  browse_node?: string | null;
  rank_classification?: string | null;
  review_count: number | null;
  rating: number | null;
  fee_estimate: number | null;
  created_at: string;
};

export type HistoricalChange = {
  start?: number | null;
  end?: number | null;
  absolute_change: number | null;
  percent_change: number | null;
};

export type HistoricalSignalWindow = {
  window_days: number;
  sample_count: number;
  cohort_count?: number;
  coverage: number;
  status: string;
  confidence?: number;
  latest_observation_at: string | null;
  cohort_change?: Record<string, HistoricalChange>;
  matched_asin_change?: Record<string, HistoricalChange | number>;
  comparable_churn?: {
    added_asin_count?: number;
    removed_asin_count?: number;
    retained_asin_count?: number;
    starting_cohort_size?: number;
    ending_cohort_size?: number;
    churn_percent?: number | null;
  };
  [key: string]: unknown;
};

export type DerivedSignals = {
  windows: Record<string, HistoricalSignalWindow>;
  snapshot_count: number;
  asin_count: number;
  latest_observation_at: string | null;
};

export type CostScenario = {
  selling_price: number;
  amazon_fees: number;
  target_profit: number;
  max_landed_cost: number;
  supplier_landed_cost: number | null;
  margin_of_safety: number | null;
  estimated_profit_margin_after_allowances: number | null;
  target_margin_percent: number;
  decision: string;
  [key: string]: unknown;
};

export type SensitivityRow = {
  price_label: string;
  selling_price: number;
  target_margin_percent: number;
  low_fees: number;
  modeled_fees: number;
  high_fees: number;
};

export type EconomicsValidator = {
  modeled: CostScenario | null;
  scenarios: CostScenario[];
  sensitivity: SensitivityRow[];
  decision: string;
  modeled_price: number | null;
  price_range: { low: number | null; modeled: number | null; high: number | null };
  fee_source: string | null;
  fee_source_confidence: number | string | null;
  fee_provenance?: {
    fee_source?: string;
    modeled_price_source?: string;
    comparable_asin?: string | null;
    status?: string;
    confidence?: string | number;
  };
  amazon_fees: number | null;
  comparable_asin: string | null;
  assumptions: Record<string, unknown>;
  warnings: string[];
  updated_at: string | null;
};

export type SupplierQuote = {
  id: string;
  product_id: string;
  source: string;
  supplier_name: string | null;
  supplier_url: string | null;
  quote_date: string | null;
  unit_cost: number;
  freight_cost_per_unit: number | null;
  packaging_cost_per_unit: number | null;
  supplier_landed_cost: number;
  max_landed_cost: number | null;
  margin_of_safety: number | null;
  decision: string;
  moq: number | null;
  lead_time_days: number | null;
  country: string | null;
  currency: string;
  quote_status: string;
  confidence: number;
  notes: string | null;
  metadata: Record<string, unknown>;
  age_days: number | null;
  created_at: string;
  updated_at: string;
};

export type SupplierValidation = {
  quotes: SupplierQuote[];
  supplier_validation_score: number;
  viable_quote_count: number;
  decision: string;
  max_landed_cost: number | null;
  source: string;
  updated_at: string | null;
};

export type ConstraintMessage = {
  rule: string;
  message: string;
  risk_type?: string;
};

export type RiskFlag = {
  risk_type: string;
  severity: string;
  confidence: number;
  evidence: string[];
  source: string | string[];
};

export type ConstraintEvaluation = {
  id?: string;
  rule_profile_id: string;
  rule_profile_name: string;
  hard_failures: ConstraintMessage[];
  soft_warnings: ConstraintMessage[];
  risk_flags: RiskFlag[];
  constraint_score: number | null;
  eligible: boolean;
  explanation: string;
  evaluation_status?: string;
  evaluation_version?: string | null;
  evaluated_at?: string | null;
  created_at: string | null;
};

export type EvidenceRow = {
  area: string;
  signal: string;
  direction: "positive" | "negative" | "missing" | string;
  source_count: number;
  strength: number;
  freshness_days: number | null;
  confidence: number;
  evidence_links: string[];
  notes: string;
  [key: string]: unknown;
};

export type EvidenceMatrix = {
  rows: EvidenceRow[];
  cross_source_confidence_score: number;
  missing_evidence: string[];
  sources: string[];
  updated_at: string | null;
};

export type ProductValidation = {
  economics_validator: EconomicsValidator;
  supplier_validation: SupplierValidation;
  constraint_evaluation: ConstraintEvaluation;
  evidence_matrix: EvidenceMatrix;
  validation_decision: {
    decision: ValidationDecision;
    thesis: string;
    cross_source_confidence_score: number;
    missing_evidence: string[];
  };
};

export type OpportunitySnapshot = {
  id: string;
  product_id: string;
  snapshot_date: string;
  snapshot_reason: string;
  discovery_source: string | null;
  canonical_name: string;
  category: string | null;
  final_score: number | null;
  recommendation: string | null;
  component_scores: Record<string, unknown>;
  cost_ceiling: Record<string, unknown>;
  supplier_validation: Record<string, unknown>;
  constraint_evaluation: Record<string, unknown>;
  evidence_matrix: Record<string, unknown>;
  thesis: string | null;
  created_at: string;
};

export type OutcomeMeasurement = {
  id: string;
  window_days: number;
  measured_at: string;
  outcome_label: OutcomeLabel;
  outcome_score: number | null;
  price_change: number | null;
  review_count_change: number | null;
  rank_change: number | null;
  search_interest_change: number | null;
  seller_count_change: number | null;
  supplier_cost_change: number | null;
  notes: string | null;
  metadata: Record<string, unknown>;
};

export type PaperTrade = {
  id: string;
  product_id: string;
  snapshot_id: string;
  decision: PaperDecision;
  hypothesis: string | null;
  entry_date: string;
  evaluation_windows: number[];
  status: string;
  snapshot: OpportunitySnapshot;
  outcomes: OutcomeMeasurement[];
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
  discovery_source: DiscoverySource;
  comparable_asins: ComparableAsin[];
  effective_comparables: ComparableAsin[];
  comparable_summary: Record<string, unknown>;
  historical_summary: {
    snapshot_count: number;
    derived_signals: DerivedSignals;
  };
  historical_signals: DerivedSignals;
  marketplace_history: MarketplaceHistoryRow[];
  economics_validator: EconomicsValidator;
  supplier_validation: SupplierValidation;
  constraint_evaluation: ConstraintEvaluation;
  evidence_matrix: EvidenceRow[];
  cross_source_confidence_score: number;
  missing_evidence: string[];
  validation_decision: ProductValidation["validation_decision"];
  recommendation_v2: {
    opportunity_score?: number | null;
    evidence_confidence_score?: number | null;
    validation_readiness_score?: number | null;
    recommendation?: Recommendation | string | null;
    recommendation_reasons?: string[];
    missing_evidence?: string[];
    blocking_issues?: string[];
    next_actions?: string[];
    scoring_version?: string | null;
    components?: Record<string, ScoreComponent>;
  };
  paper_trading_history: PaperTrade[];
};

export type ComparableUpdateInput = {
  relevance_status: string;
  reason?: string | null;
};

export type RecommendationFeedbackInput = {
  verdict: "good_recommendation" | "bad_recommendation" | "uncertain";
  reasons: string[];
  notes?: string | null;
};

export type ProductCreateInput = {
  canonical_name: string;
  category?: string | null;
  description?: string | null;
};

export type ProductCreateResponse = {
  id: string;
  canonical_name: string;
  category: string | null;
  status: string;
  created_at: string;
};

export type SupplierQuoteInput = {
  source?: string;
  supplier_name?: string | null;
  supplier_url?: string | null;
  unit_cost: number;
  freight_cost_per_unit?: number | null;
  packaging_cost_per_unit?: number | null;
  moq?: number | null;
  lead_time_days?: number | null;
  country?: string | null;
  currency?: string;
  quote_status?: "raw" | "parsed" | "needs_review" | "validated" | "rejected" | "expired";
  confidence?: number;
  notes?: string | null;
  metadata?: Record<string, unknown>;
};

export type SnapshotInput = {
  snapshot_reason: string;
  decision?: PaperDecision | null;
  hypothesis?: string | null;
};

export type SnapshotResponse = {
  snapshot: OpportunitySnapshot;
  paper_trade: PaperTrade | null;
};

export type OutcomeInput = {
  window_days: number;
  measured_at?: string | null;
  price_change?: number | null;
  review_count_change?: number | null;
  rank_change?: number | null;
  search_interest_change?: number | null;
  seller_count_change?: number | null;
  supplier_cost_change?: number | null;
  constraint_status_change?: string | null;
  outcome_label: OutcomeLabel;
  outcome_score?: number | null;
  notes?: string | null;
  metadata?: Record<string, unknown>;
};

export type OutcomeCreateResponse = {
  id: string;
  paper_trade_id: string;
  window_days: number;
  measured_at: string;
  outcome_label: OutcomeLabel;
  outcome_score: number | null;
  created_at: string;
};

export type BacktestGroupSummary = {
  count: number;
  measured_count: number;
  improved_rate: number | null;
  average_outcome_score: number | null;
};

export type BacktestSummary = {
  total_paper_trades: number;
  total_outcomes: number;
  top_picks_improved_rate: number | null;
  watch_picks_improved_rate: number | null;
  skip_picks_improved_rate: number | null;
  average_outcome_by_recommendation: Record<string, BacktestGroupSummary>;
  average_outcome_by_discovery_source: Record<string, BacktestGroupSummary>;
};

export type PluginInfo = {
  name: string;
  version: string;
  enabled: boolean;
  type: string;
  description: string | null;
  supports: string[];
  configured?: boolean | null;
  environment?: string | null;
  missing_credentials?: string[];
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

export type PipelineRunInput = {
  plugins?: string[] | null;
  query?: {
    query?: string | null;
    category?: string | null;
    limit?: number;
    metadata?: Record<string, unknown>;
  };
  run_analyzers?: boolean;
  score?: boolean;
};

export type PipelineRunResponse = {
  status: string;
  plugin_runs: PluginRunSummary[];
  products_updated: number;
  scores_updated: number;
  observations_created: number;
  errors: string[];
  message?: string | null;
};

export type ProductResearchInput = {
  query: string;
  category?: string | null;
};

export type ProductResearchResponse = {
  product_id: string;
  canonical_name: string;
  category: string | null;
  created: boolean;
  pipeline: PipelineRunResponse;
};

export type ProductFilters = {
  q?: string;
  category?: string;
  min_score?: number;
  recommendation?: string;
  eligible?: boolean;
  validation_decision?: string;
  limit?: number;
  offset?: number;
};
