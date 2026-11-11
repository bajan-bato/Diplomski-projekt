import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'packages' },
  {
    path: 'packages',
    loadComponent: () =>
      import('./pages/packages-list/packages-list').then((m) => m.PackagesListComponent),
  },
  {
    path: 'packages/:packageId/suggestions',
    loadComponent: () =>
      import('./pages/suggestions-list/suggestions-list').then(
        (m) => m.SuggestionsListComponent,
      ),
  },
  {
    path: 'suggestions/:suggestionId',
    loadComponent: () =>
      import('./pages/suggestion-detail/suggestion-detail').then(
        (m) => m.SuggestionDetailComponent,
      ),
  },
  {
    path: 'statistics',
    loadComponent: () => import('./pages/statistics/statistics').then((m) => m.StatisticsComponent),
  },
  {
    path: '**',
    loadComponent: () => import('./pages/not-found/not-found').then((m) => m.NotFoundComponent),
  },
];
