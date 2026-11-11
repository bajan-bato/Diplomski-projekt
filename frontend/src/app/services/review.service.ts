import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';
import { environment } from '../../environments/environment';
import { Review } from '../models/review.model';
import { RawReview } from './api.dto';
import { toReview } from './api.mappers';

@Injectable({ providedIn: 'root' })
export class ReviewService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiBaseUrl}/review`;

  getForSuggestionAndAnalysis(suggestionId: number, analysisId: number): Observable<Review[]> {
    const params = new HttpParams().set('suggestionId', suggestionId).set('analysisId', analysisId);
    return this.http
      .get<RawReview[]>(this.baseUrl, { params })
      .pipe(map((raws) => raws.map(toReview)));
  }
}
