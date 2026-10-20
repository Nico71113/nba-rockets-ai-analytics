export type AnswerMethod = 'sql' | 'refusal';

export interface Evidence {
  source_table: string;
  snapshot_id: string;
  game_ids: string[];
  filters: Record<string, unknown>;
}

export interface AnalyticsResult {
  method: AnswerMethod;
  answer: string;
  metrics: Record<string, number | string | null>;
  calculation: string[];
  evidence: Evidence[];
  coverage_note: string | null;
}

export interface QueryResponse {
  question: string;
  intent: string;
  routing_source: 'local_model' | 'deterministic' | 'deterministic_fallback' | 'coverage_guard';
  interpretation: Record<string, unknown>;
  result: AnalyticsResult;
  elapsed_ms: number | null;
}

export interface GameEvidenceRow {
  game_id: string;
  game_date: string;
  game_type: string;
  away_team: string;
  home_team: string;
  away_score: number;
  home_score: number;
  winner: string;
}

export interface CoverageResponse {
  season_id: string;
  first_game_date: string | null;
  last_game_date: string | null;
  games: number;
  teams: number;
  players: number;
  player_game_rows: number;
  team_game_rows: number;
}

export interface ForecastMetrics {
  mae: number;
  rmse: number;
  attempt_weighted_mae: number;
  attempt_weighted_rmse: number;
}

export type ForecastMethodKey = 'historical_rate' | 'league_mean' | 'shrinkage';

export interface ForecastMethodResult {
  key: ForecastMethodKey;
  label: string;
  description: string;
  metrics: ForecastMetrics;
}

export interface ForecastSplit {
  training_start: string;
  training_end: string;
  testing_start: string;
  testing_end: string;
  validation_training_end: string;
  validation_start: string;
  training_games: number;
  testing_games: number;
}

export interface ForecastCohort {
  players: number;
  minimum_attempts_per_half: number;
  validation_players: number;
  validation_minimum_attempts: number;
}

export interface ForecastErrorCase {
  player_id: number;
  player_name: string;
  primary_team: string;
  first_half_made: number;
  first_half_attempts: number;
  first_half_percentage: number;
  predicted_percentage: number;
  second_half_made: number;
  second_half_attempts: number;
  actual_percentage: number;
  absolute_error: number;
}

export interface ForecastFeaturedPlayer {
  player_id: number;
  player_name: string;
  primary_team: string;
  first_half_percentage: number;
  league_mean_prediction: number;
  shrinkage_prediction: number;
  second_half_percentage: number;
  first_half_attempts: number;
  second_half_attempts: number;
}

export interface ForecastVolumeBucket {
  label: string;
  minimum_attempts: number;
  maximum_attempts: number | null;
  players: number;
  methods: Record<ForecastMethodKey, ForecastMetrics>;
}

export interface ThreePointForecastResponse {
  season_id: string;
  question: string;
  split: ForecastSplit;
  cohort: ForecastCohort;
  league_first_half_percentage: number;
  selected_prior_strength: number;
  validation_rmse: number;
  selection_metric: string;
  methods: ForecastMethodResult[];
  best_method: ForecastMethodKey;
  improvement_vs_historical_rmse_pct: number;
  improvement_vs_league_rmse_pct: number;
  volume_buckets: ForecastVolumeBucket[];
  largest_misses: ForecastErrorCase[];
  featured_player: ForecastFeaturedPlayer | null;
  findings: string[];
  limitations: string[];
}
