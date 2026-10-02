import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { AnalyticsApiService } from './analytics-api.service';

describe('AnalyticsApiService', () => {
  let service: AnalyticsApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [AnalyticsApiService, provideHttpClient(), provideHttpClientTesting()]
    });
    service = TestBed.inject(AnalyticsApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('loads the fixed-snapshot coverage endpoint', () => {
    service.getCoverage().subscribe();

    const request = http.expectOne('http://localhost:8100/api/v1/coverage');
    expect(request.request.method).toBe('GET');
    request.flush({});
  });

  it('trims and posts a natural-language question', () => {
    service.ask('  What was Houston\'s record?  ').subscribe();

    const request = http.expectOne('http://localhost:8100/api/v1/query');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({ question: "What was Houston's record?" });
    request.flush({});
  });

  it('loads auditable game rows for the evidence IDs', () => {
    service.getGames(['game-2', 'game-1']).subscribe();

    const request = http.expectOne(
      'http://localhost:8100/api/v1/evidence/games?game_ids=game-2,game-1'
    );
    expect(request.request.method).toBe('GET');
    request.flush([]);
  });
});
