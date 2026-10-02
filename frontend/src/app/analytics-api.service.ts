import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { CoverageResponse, QueryResponse } from './models';

export const API_BASE_URL = (
  window.__NBA_ANALYTICS_CONFIG__?.apiBaseUrl ?? 'http://localhost:8100'
).replace(/\/$/, '');

@Injectable({ providedIn: 'root' })
export class AnalyticsApiService {
  constructor(private readonly http: HttpClient) {}

  getCoverage(): Observable<CoverageResponse> {
    return this.http.get<CoverageResponse>(`${API_BASE_URL}/api/v1/coverage`);
  }

  ask(question: string): Observable<QueryResponse> {
    return this.http.post<QueryResponse>(`${API_BASE_URL}/api/v1/query`, {
      question: question.trim()
    });
  }
}
