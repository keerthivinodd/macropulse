export type MacroPulseDirection = "up" | "down" | "neutral";

export interface MacroPulseIndicator {
  key: string;
  symbol: string;
  label: string;
  value: string;
  sub: string;
  change: string;
  dir: MacroPulseDirection;
  source: string;
  as_of: string;
}

export interface MacroPulseSourceStatus {
  name: string;
  status: "live" | "fallback";
  latency: string;
  coverage: string;
}

export interface MacroPulseRealtimeResponse {
  headline: string;
  narrative: string;
  anomaly_confidence: number;
  market_confidence_score: number;
  global_sentiment_change: number;
  generated_at: string;
  indicators: MacroPulseIndicator[];
  sources: MacroPulseSourceStatus[];
}

export interface AlertSummary {
  id: string;
  title: string;
  tier: "P1" | "P2" | "P3";
  status: string;
  macro_variable: string;
  confidence_score: number;
  created_at: string;
}

export interface KPITiles {
  repo_rate_pct: number | null;
  repo_rate_change_bps: number | null;
  repo_rate_alert: boolean;
  usd_inr_rate: number | null;
  usd_inr_7d_change_pct: number | null;
  fx_alert: boolean;
  wpi_index: number | null;
  wpi_mom_change_pct: number | null;
  inflation_alert: boolean;
  brent_usd: number | null;
  brent_mom_change_pct: number | null;
  oil_alert: boolean;
}

export interface DataFreshness {
  rbi: string | null;
  fx_rates: string | null;
  commodities: string | null;
  news: string | null;
}

export interface SensitivityMetric {
  impact_cr: number;
  label: string;
}

export type SensitivityMatrix = Record<string, SensitivityMetric>;

export interface MacroPulseDashboard {
  tenant_id: string;
  primary_currency: string;
  generated_at: string;
  kpi_tiles: KPITiles;
  live_alerts: AlertSummary[];
  sensitivity_matrix: SensitivityMatrix;
  data_freshness: DataFreshness;
}

export interface DebtProfile {
  total_loan_amount_cr: number;
  rate_type: "MCLR" | "Fixed" | "Floating";
  current_effective_rate_pct: number;
  floating_proportion_pct: number;
  short_term_debt_cr: number;
  long_term_debt_cr: number;
}

export interface FXExposure {
  net_usd_exposure_m: number;
  net_aed_exposure_m: number;
  net_sar_exposure_m: number;
  hedge_ratio_pct: number;
  hedge_instrument: "Forward" | "Options" | "Natural" | "None";
}

export interface COGSProfile {
  total_cogs_cr: number;
  steel_pct: number;
  petroleum_pct: number;
  electronics_pct: number;
  freight_pct: number;
  other_pct: number;
}

export interface InvestmentPortfolio {
  gsec_holdings_cr: number;
  modified_duration: number;
}

export interface LogisticsProfile {
  primary_routes: string[];
  monthly_shipment_value_cr: number;
  inventory_buffer_days: number;
}

export interface NotificationConfig {
  email?: string | null;
  teams_webhook?: string | null;
  slack_webhook?: string | null;
  channels: Array<"email" | "teams" | "slack">;
}

export interface TenantProfile {
  tenant_id: string;
  company_name: string;
  primary_region: "IN" | "UAE" | "SA";
  primary_currency: "INR" | "AED" | "SAR";
  debt: DebtProfile;
  fx: FXExposure;
  cogs: COGSProfile;
  portfolio: InvestmentPortfolio;
  logistics: LogisticsProfile;
  notification_config: NotificationConfig;
  created_at?: string;
  updated_at?: string;
}

export interface SensitivityResponse {
  source: "cache" | "calculated";
  data: SensitivityMatrix;
}

export interface AlertResponse {
  id: string;
  tenant_id: string;
  alert_type: string;
  tier: "P1" | "P2" | "P3";
  title: string;
  body: string;
  source_citation: string;
  confidence_score: number;
  financial_impact_cr: number | null;
  macro_variable: string;
  status: string;
  created_at: string;
  dispatched_at: string | null;
}

export interface HITLPendingAlert {
  alert_id: string;
  tenant_id: string;
  title: string;
  body: string;
  confidence_score: number;
  source_citation: string;
  reason: string;
  created_at: string;
}

export interface GuardrailViolation {
  id: string;
  tenant_id: string;
  alert_title: string | null;
  source_citation: string | null;
  reason: string;
  created_at: string;
}

// ── Day 5 types ──────────────────────────────────────────────────────────────

export interface CFOBriefPipelineStep {
  step: string;
  status: "completed" | "failed" | "skipped";
  duration_ms: number;
  [key: string]: unknown;
}

export interface CFOBriefPipelineResult {
  tenant_id: string;
  trigger_time: string;
  total_duration_ms: number;
  steps_completed: number;
  steps_total: number;
  confidence_score: number;
  publish_status: "publish" | "review" | "hitl_queue";
  errors: string[];
  steps: CFOBriefPipelineStep[];
  brief?: Record<string, unknown>;
  export_result?: Record<string, unknown>;
  notification_result?: Record<string, unknown>;
}

export interface CostModelRecord {
  requests: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_cost_usd: number;
}

export interface CostRoutingStatus {
  total_requests: number;
  total_cost_usd: number;
  by_model: Record<string, CostModelRecord>;
  budget: Record<string, unknown>;
}

export interface EventLogEntry {
  event_id: string;
  event_type: string;
  channel: string;
  tenant_id: string;
  timestamp: string;
  source: string;
  version: string;
  [key: string]: unknown;
}

export interface AgentMetrics {
  total_requests: number;
  p50_ms: number;
  p95_ms: number;
  p99_ms: number;
  avg_confidence: number;
  [key: string]: unknown;
}

export interface MacroPulseAgentSource {
  name: string;
  category: "official" | "market" | "news" | "model";
  detail: string;
}

export interface MacroPulseAgentQueryResponse {
  query_type: "interest_rate" | "fx" | "commodity" | "combined" | "overview";
  impact: string;
  confidence: number;
  publish_status: "publish" | "review" | "hitl_queue";
  recommended_action: string;
  sources: MacroPulseAgentSource[];
  regional_context: string;
  scenario_output: Record<string, unknown>;
  analytics: Record<string, unknown>;
}
