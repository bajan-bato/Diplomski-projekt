import { HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { DatePipe } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { catchError, distinctUntilChanged, map, of, switchMap, tap } from 'rxjs';
import { Package } from '../../models/package.model';
import { Suggestion } from '../../models/suggestion.model';
import { PackageService } from '../../services/package.service';
import { SuggestionService } from '../../services/suggestion.service';

interface LoadResult {
  pkg: Package | null;
  suggestions: Suggestion[];
  notFound: boolean;
}

@Component({
  selector: 'app-suggestions-list',
  imports: [RouterLink, DatePipe],
  templateUrl: './suggestions-list.html',
  styleUrl: './suggestions-list.scss',
})
export class SuggestionsListComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly packageService = inject(PackageService);
  private readonly suggestionService = inject(SuggestionService);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly pkg = signal<Package | null>(null);
  protected readonly suggestions = signal<Suggestion[]>([]);
  protected readonly loading = signal(true);
  protected readonly notFound = signal(false);
  protected readonly error = signal<string | null>(null);

  constructor() {
    this.route.paramMap
      .pipe(
        map((params) => params.get('packageId')!),
        distinctUntilChanged(),
        tap(() => {
          this.loading.set(true);
          this.error.set(null);
          this.notFound.set(false);
        }),
        switchMap((packageId) => this.loadForPackage(packageId)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((result) => {
        this.loading.set(false);
        this.notFound.set(result.notFound);
        this.pkg.set(result.pkg);
        this.suggestions.set(result.suggestions);
      });
  }

  private loadForPackage(packageId: string) {
    return this.packageService.getById(packageId).pipe(
      switchMap((pkg) =>
        this.suggestionService
          .getByPackageId(packageId)
          .pipe(map((suggestions) => ({ pkg, suggestions, notFound: false }))),
      ),
      catchError((err: HttpErrorResponse) => {
        if (err.status === 404) {
          return of<LoadResult>({ pkg: null, suggestions: [], notFound: true });
        }
        this.error.set('Prijedlozi se nisu mogli učitati. Pokušajte ponovno kasnije.');
        return of<LoadResult>({ pkg: null, suggestions: [], notFound: false });
      }),
    );
  }
}
