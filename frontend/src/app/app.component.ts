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

import { AnalyticsApiService } from './analytics-api.service';
import { CoverageResponse, QueryResponse } from './models';

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
      label: 'Test a limitation',
      question: 'Which defender guarded Kevin Durant most often this season?'
    }
  ];

  question = this.suggestions[0].question;
  coverage: CoverageResponse | null = null;
  response: QueryResponse | null = null;
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
