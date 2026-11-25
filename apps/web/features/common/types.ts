export type Metric = {
  key: string;
  label: string;
  value: string | null;
  unit: string;
  formula: string;
  inputs: Record<string, string | null>;
  rule_ids: string[];
  simplified: boolean;
  note: string | null;
};

export type Citation = {
  source_key: string;
  official_title: string;
  authority: string;
  source_type: string;
  article_number: string;
  quote: string;
  official_url: string;
  version: string;
  retrieved_at: string;
  validated: boolean;
  validation_note: string | null;
  rule_id?: string;
  rule_version?: string;
};

export type TimelineNode = {
  id: string;
  step: number;
  date: string | null;
  event_type: string;
  title_zh: string;
  title_en: string;
  status: string;
  trigger_condition: string;
  financial_impact: Record<string, string>;
  rule_ids: string[];
  legal_basis: Citation[];
  contract_basis: string[];
  investor_rights: string[];
  investor_obligations: string[];
  broker_rights: string[];
  broker_obligations: string[];
  required_evidence: string[];
  deadline: string | null;
  deadline_note: string | null;
  uncertainty: string[];
  possible_next_events: string[];
  plain_language: string | null;
  unreviewed: boolean;
  ai_checked?: boolean;
  unverified: boolean;
};

export type RuleSummary = {
  rule_id: string;
  version: string;
  rule_name: string;
  review_status: string;
  is_demo: boolean;
  plain_language: string;
  parameters: Record<string, string>;
  citation_validated: boolean;
  has_official_source: boolean;
  citations: Citation[];
};

export type RuleEvaluation = {
  matched: string[];
  unmatched: string[];
  missing_facts: Record<string, string[]>;
  triggered_events: string[];
  unreviewed_rules: string[];
  unverified_rules: string[];
  conflicts: unknown[];
};

export type MarginCalcResult = {
  calculation_version: string;
  rule_version: string;
  legal_source_version: string;
  as_of: string;
  metrics: Record<string, Metric>;
  warnings: { code: string; message: string }[];
  assumptions: string[];
  rule_evaluation: RuleEvaluation;
  rules: RuleSummary[];
  curve: { price: string; maintenance_ratio: string | null; gross_pnl: string; net_pnl: string; market_value: string; financing: string }[] | null;
};

export type ScenarioResult = {
  trading_type: "margin" | "day_trading";
  calculation_version: string;
  rule_version: string;
  rule_versions: Record<string, string>;
  parameters: Record<string, string>;
  opening?: Record<string, Metric>;
  metrics?: Record<string, Metric>;
  states?: { step: number; date: string; label?: string; price: string; financing: string; maintenance_ratio_pct: string | null; in_margin_call: boolean; metrics: Record<string, Metric>; disposal?: Record<string, Metric> | null }[];
  timeline: TimelineNode[];
  assumptions: string[];
  warnings: { code: string; message: string }[];
  rules: RuleSummary[];
  rule_evaluation?: RuleEvaluation;
};
