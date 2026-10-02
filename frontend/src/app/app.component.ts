import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  ElementRef,
  OnInit,
  ViewChild
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs';

import { AnalyticsApiService, DEMO_MODE } from './analytics-api.service';
import { CoverageResponse, Evidence, GameEvidenceRow, QueryResponse } from './models';

interface SuggestedQuestion {
  label: string;
  question: string;
}

@Component({
  selector: 'app-root',
  imports: [CommonModule, FormsModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class AppComponent implements OnInit {
  @ViewChild('answerHeading') private answerHeading?: ElementRef<HTMLHeadingElement>;

  readonly suggestions: SuggestedQuestion[] = [
    {
      label: 'Season record',
      question: "What was Houston's regular-season record in 2025-26?"
    },
    {
      label: 'Durant averages',
      question: 'What did Kevin Durant average for Houston during the 2025-26 regular season?'
    },
    {
      label: '30+ point games',
      question: "What was Houston's record when Kevin Durant scored at least 30 points?"
    },
    {
      label: 'Four made threes',
      question: "What was Houston's record when Kevin Durant made at least 4 three-pointers?"
    },
    {
      label: 'January scoring',
      question: 'How many total points did Houston score in January 2026?'
    },
    {
      label: 'Road scoring high',
      question: "What was Kevin Durant's highest points total on the road?"
    },
    {
      label: 'Test a limitation',
      question: 'Which defender guarded Kevin Durant most often this season?'
    }
  ];
  readonly demoMode = DEMO_MODE;

  question = this.suggestions[0].question;
  coverage: CoverageResponse | null = null;
  response: QueryResponse | null = null;
  evidenceRows: GameEvidenceRow[] = [];
  evidenceLoading = false;
  evidenceError = '';
  loadedEvidenceKey = '';
  loadingCoverage = true;
  asking = false;
  apiError = '';

  constructor(
    private readonly api: AnalyticsApiService,
    private readonly changeDetector: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.api
      .getCoverage()
      .pipe(
        finalize(() => {
          this.loadingCoverage = false;
          this.changeDetector.markForCheck();
        })
      )
      .subscribe({
        next: (coverage) => {
          this.coverage = coverage;
          this.changeDetector.markForCheck();
        },
        error: () => {
          this.apiError =
            'The analytics API is offline. Start the backend on port 8100, then refresh this page.';
          this.changeDetector.markForCheck();
        }
      });
  }

  useSuggestion(suggestion: SuggestedQuestion): void {
    this.question = suggestion.question;
    this.ask();
  }

  ask(): void {
    const cleanQuestion = this.question.trim();
    if (!cleanQuestion || this.asking) {
      return;
    }

    this.question = cleanQuestion;
    this.asking = true;
    this.apiError = '';
    this.response = null;
    this.evidenceRows = [];
    this.evidenceError = '';
    this.loadedEvidenceKey = '';

    this.api
      .ask(cleanQuestion)
      .pipe(
        finalize(() => {
          this.asking = false;
          this.changeDetector.markForCheck();
        })
      )
      .subscribe({
        next: (response) => {
          this.response = response;
          this.changeDetector.markForCheck();
          window.setTimeout(() => this.answerHeading?.nativeElement.focus());
        },
        error: (error: HttpErrorResponse) => {
          this.apiError = this.describeError(error);
          this.changeDetector.markForCheck();
        }
      });
  }

  metricLabel(key: string): string {
    return key.replaceAll('_', ' ');
  }

  formatMetric(value: unknown): string {
    if (value === null) {
      return 'Not available';
    }
    return typeof value === 'number' ? value.toLocaleString('en-US') : String(value);
  }

  formatDate(value: string | null): string {
    if (!value) {
      return '—';
    }
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      timeZone: 'UTC'
    }).format(new Date(`${value}T00:00:00Z`));
  }

  objectEntries(value: Record<string, unknown>): [string, unknown][] {
    return Object.entries(value);
  }

  displayValue(value: unknown): string {
    if (value === null || value === undefined || value === '') {
      return 'Any';
    }
    if (typeof value === 'boolean') {
      return value ? 'Yes' : 'No';
    }
    return String(value).replaceAll('_', ' ');
  }

  loadEvidence(evidence: Evidence): void {
    if (!evidence.game_ids.length || this.evidenceLoading) {
      return;
    }
    const evidenceKey = evidence.game_ids.join(',');
    if (this.loadedEvidenceKey === evidenceKey) {
      return;
    }
    this.evidenceLoading = true;
    this.evidenceError = '';
    this.api
      .getGames(evidence.game_ids)
      .pipe(
        finalize(() => {
          this.evidenceLoading = false;
          this.changeDetector.markForCheck();
        })
      )
      .subscribe({
        next: (rows) => {
          this.evidenceRows = rows;
          this.loadedEvidenceKey = evidenceKey;
          this.changeDetector.markForCheck();
        },
        error: (error: HttpErrorResponse) => {
          this.evidenceError = this.describeError(error);
          this.changeDetector.markForCheck();
        }
      });
  }

  downloadEvidenceCsv(): void {
    if (!this.evidenceRows.length) {
      return;
    }
    const columns: (keyof GameEvidenceRow)[] = [
      'game_id',
      'game_date',
      'game_type',
      'away_team',
      'away_score',
      'home_team',
      'home_score',
      'winner'
    ];
    const escape = (value: string | number): string =>
      `"${String(value).replaceAll('"', '""')}"`;
    const csv = [
      columns.join(','),
      ...this.evidenceRows.map((row) => columns.map((column) => escape(row[column])).join(','))
    ].join('\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = 'arcline-evidence.csv';
    link.click();
    URL.revokeObjectURL(url);
  }

  private describeError(error: HttpErrorResponse): string {
    if (error.status === 0) {
      return 'The analytics API could not be reached at localhost:8100. Check that Docker and the backend are running.';
    }
    if (error.status === 422) {
      return 'The question could not be validated. Try one of the suggested question formats.';
    }
    return `The API returned an unexpected error (${error.status}). Please try again.`;
  }
}
