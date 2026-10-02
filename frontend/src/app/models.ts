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
