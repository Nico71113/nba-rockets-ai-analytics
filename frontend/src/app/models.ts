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
  interpretation: Record<string, unknown>;
  result: AnalyticsResult;
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
