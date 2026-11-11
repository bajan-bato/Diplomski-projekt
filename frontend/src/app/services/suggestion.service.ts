import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';
import { environment } from '../../environments/environment';
import { Suggestion } from '../models/suggestion.model';
import { RawSuggestion } from './api.dto';
import { toSuggestion } from './api.mappers';

@Injectable({ providedIn: 'root' })
export class SuggestionService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiBaseUrl}/suggestion`;

  getAll(): Observable<Suggestion[]> {
    return this.http.get<RawSuggestion[]>(this.baseUrl).pipe(map((raws) => raws.map(toSuggestion)));
  }

  getByPackageId(packageId: string): Observable<Suggestion[]> {
    return this.getAll().pipe(
      map((suggestions) => suggestions.filter((s) => s.packageId === packageId)),
    );
  }

  getById(suggestionId: number): Observable<Suggestion> {
    return this.http.get<RawSuggestion>(`${this.baseUrl}/${suggestionId}`).pipe(map(toSuggestion));
  }
}
