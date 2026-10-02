import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { map, Observable, shareReplay } from 'rxjs';

import { CoverageResponse, GameEvidenceRow, QueryResponse } from './models';

export const API_BASE_URL = (
  window.__NBA_ANALYTICS_CONFIG__?.apiBaseUrl ?? 'http://localhost:8100'
).replace(/\/$/, '');
export const DEMO_MODE = window.__NBA_ANALYTICS_CONFIG__?.demoMode === true;

interface DemoCatalog {
  coverage: CoverageResponse;
  queries: Record<string, QueryResponse>;
  games: Record<string, GameEvidenceRow>;
}

const normalizeQuestion = (question: string): string =>
  question.trim().toLocaleLowerCase('en-US').replace(/\s+/g, ' ');

const catalogMiss = (question: string): QueryResponse => ({
  question,
  intent: 'demo_catalog_miss',
  routing_source: 'coverage_guard',
  interpretation: {
    intent: 'demo_catalog_miss',
    mode: 'public static showcase'
  },
  result: {
    method: 'refusal',
    answer:
      'This public static showcase contains the seven verified suggested questions only. Run the local PostgreSQL stack for broader natural-language queries.',
    metrics: {},
    calculation: [],
    evidence: [],
    coverage_note:
      'The hosted showcase replays versioned API responses; it does not pretend to run the full database backend in the browser.'
  },
  elapsed_ms: 0
});

@Injectable({ providedIn: 'root' })
export class AnalyticsApiService {
  private readonly demoCatalog$: Observable<DemoCatalog>;

  constructor(private readonly http: HttpClient) {
    const demoCatalogUrl = new URL('demo/catalog.json', document.baseURI).toString();
    this.demoCatalog$ = this.http.get<DemoCatalog>(demoCatalogUrl).pipe(shareReplay(1));
  }

  getCoverage(): Observable<CoverageResponse> {
    if (DEMO_MODE) {
      return this.demoCatalog$.pipe(map((catalog) => catalog.coverage));
    }
    return this.http.get<CoverageResponse>(`${API_BASE_URL}/api/v1/coverage`);
  }

  ask(question: string): Observable<QueryResponse> {
    const cleanQuestion = question.trim();
    if (DEMO_MODE) {
      return this.demoCatalog$.pipe(
        map((catalog) => catalog.queries[normalizeQuestion(cleanQuestion)] ?? catalogMiss(cleanQuestion))
      );
    }
    return this.http.post<QueryResponse>(`${API_BASE_URL}/api/v1/query`, {
      question: cleanQuestion
    });
  }

  getGames(gameIds: string[]): Observable<GameEvidenceRow[]> {
    if (DEMO_MODE) {
      return this.demoCatalog$.pipe(
        map((catalog) =>
          gameIds.flatMap((gameId) => (catalog.games[gameId] ? [catalog.games[gameId]] : []))
        )
      );
    }
    return this.http.get<GameEvidenceRow[]>(`${API_BASE_URL}/api/v1/evidence/games`, {
      params: { game_ids: gameIds.join(',') }
    });
  }
}
