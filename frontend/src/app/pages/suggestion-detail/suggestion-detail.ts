import { HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { catchError, distinctUntilChanged, forkJoin, map, of } from 'rxjs';
import { StatusLabelComponent } from '../../components/status-label/status-label';
import { Analysis } from '../../models/analysis.model';
import { Issue } from '../../models/issue.model';
import { Package } from '../../models/package.model';
import { ReviewStatus } from '../../models/review.model';
import { Suggestion } from '../../models/suggestion.model';
import { AnalysisService } from '../../services/analysis.service';
import { IssueService } from '../../services/issue.service';
import { PackageService } from '../../services/package.service';
import { ReviewService } from '../../services/review.service';
import { SuggestionService } from '../../services/suggestion.service';

type NavDirection = 'prev' | 'next';

@Component({
  selector: 'app-suggestion-detail',
  imports: [RouterLink, StatusLabelComponent],
  templateUrl: './suggestion-detail.html',
  styleUrl: './suggestion-detail.scss',
})
export class SuggestionDetailComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly suggestionService = inject(SuggestionService);
  private readonly packageService = inject(PackageService);
  private readonly issueService = inject(IssueService);
  private readonly analysisService = inject(AnalysisService);
  private readonly reviewService = inject(ReviewService);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly suggestion = signal<Suggestion | null>(null);
  protected readonly pkg = signal<Package | null>(null);
  protected readonly issues = signal<Issue[]>([]);
  protected readonly currentAnalysis = signal<Analysis | null>(null);
  protected readonly noAnalyses = signal(false);
  protected readonly reviewsByIssueId = signal<Map<number, ReviewStatus>>(new Map());

  protected readonly loading = signal(true);
  protected readonly notFound = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly loadingAnalysisNav = signal(false);
  protected readonly analysisNavError = signal<string | null>(null);

  /** Guards against an in-flight suggestion load resolving after the route changed. */
  private suggestionLoadToken = 0;
  /** Guards against an in-flight analysis navigation resolving after it was superseded. */
  private analysisNavToken = 0;

  constructor() {
    this.route.paramMap
      .pipe(
        map((params) => Number(params.get('suggestionId'))),
        distinctUntilChanged(),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((suggestionId) => this.loadSuggestion(suggestionId));
  }

  private loadSuggestion(suggestionId: number): void {
    const token = ++this.suggestionLoadToken;
    this.loading.set(true);
    this.notFound.set(false);
    this.error.set(null);
    this.currentAnalysis.set(null);
    this.noAnalyses.set(false);
    this.reviewsByIssueId.set(new Map());

    this.suggestionService
      .getById(suggestionId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (suggestion) => {
          if (token !== this.suggestionLoadToken) {
            return;
          }
          this.suggestion.set(suggestion);
          this.loadRelatedData(suggestion, token);
        },
        error: (err: HttpErrorResponse) => {
          if (token !== this.suggestionLoadToken) {
            return;
          }
          this.loading.set(false);
          if (err.status === 404) {
            this.notFound.set(true);
          } else {
            this.error.set('Prijedlog se nije mogao učitati. Pokušajte ponovno kasnije.');
          }
        },
      });
  }

  private loadRelatedData(suggestion: Suggestion, token: number): void {
    forkJoin({
      pkg: this.packageService.getById(suggestion.packageId).pipe(
        catchError(() => of(null)),
      ),
      issues: this.issueService.getBySuggestionId(suggestion.suggestionId).pipe(
        catchError(() => of([] as Issue[])),
      ),
      analyses: this.analysisService.getAll().pipe(catchError(() => of([] as Analysis[]))),
    })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(({ pkg, issues, analyses }) => {
        if (token !== this.suggestionLoadToken) {
          return;
        }
        this.pkg.set(pkg);
        this.issues.set(issues);

        if (analyses.length === 0) {
          this.noAnalyses.set(true);
          this.loading.set(false);
          return;
        }

        // No established convention for the "current" analysis exists yet;
        // per spec, fall back to the most recent one by datetime.
        const mostRecent = analyses.reduce((latest, candidate) =>
          new Date(candidate.datetime).getTime() > new Date(latest.datetime).getTime()
            ? candidate
            : latest,
        );
        this.currentAnalysis.set(mostRecent);
        this.loadReviews(suggestion.suggestionId, mostRecent.analysisId, token, this.analysisNavToken);
        this.loading.set(false);
      });
  }

  private loadReviews(
    suggestionId: number,
    analysisId: number,
    suggestionToken: number,
    navToken: number,
  ): void {
    this.reviewService
      .getForSuggestionAndAnalysis(suggestionId, analysisId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (reviews) => {
          if (suggestionToken !== this.suggestionLoadToken || navToken !== this.analysisNavToken) {
            return;
          }
          this.reviewsByIssueId.set(new Map(reviews.map((r) => [r.issueId, r.status])));
          this.loadingAnalysisNav.set(false);
        },
        error: () => {
          if (suggestionToken !== this.suggestionLoadToken || navToken !== this.analysisNavToken) {
            return;
          }
          this.analysisNavError.set('Statusi pregleda se nisu mogli učitati.');
          this.loadingAnalysisNav.set(false);
        },
      });
  }

  protected navigate(direction: NavDirection): void {
    const current = this.currentAnalysis();
    const suggestion = this.suggestion();
    if (!current || !suggestion) {
      return;
    }
    const targetId = direction === 'prev' ? current.idPrev : current.idNext;
    if (targetId === null) {
      return;
    }

    const navToken = ++this.analysisNavToken;
    const suggestionToken = this.suggestionLoadToken;
    this.loadingAnalysisNav.set(true);
    this.analysisNavError.set(null);

    this.analysisService
      .getById(targetId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (analysis) => {
          if (navToken !== this.analysisNavToken || suggestionToken !== this.suggestionLoadToken) {
            return;
          }
          this.currentAnalysis.set(analysis);
          this.loadReviews(suggestion.suggestionId, analysis.analysisId, suggestionToken, navToken);
        },
        error: () => {
          if (navToken !== this.analysisNavToken || suggestionToken !== this.suggestionLoadToken) {
            return;
          }
          this.analysisNavError.set('Sljedeća analiza se nije mogla učitati.');
          this.loadingAnalysisNav.set(false);
        },
      });
  }

  protected reviewStatusFor(issueId: number): ReviewStatus | null {
    return this.reviewsByIssueId().get(issueId) ?? null;
  }
}
