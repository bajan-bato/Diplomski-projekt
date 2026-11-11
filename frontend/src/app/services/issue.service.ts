import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';
import { environment } from '../../environments/environment';
import { Issue } from '../models/issue.model';
import { RawIssue } from './api.dto';
import { toIssue } from './api.mappers';

@Injectable({ providedIn: 'root' })
export class IssueService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiBaseUrl}/issue`;

  getBySuggestionId(suggestionId: number): Observable<Issue[]> {
    const params = new HttpParams().set('suggestionId', suggestionId);
    return this.http
      .get<RawIssue[]>(this.baseUrl, { params })
      .pipe(map((raws) => raws.map(toIssue)));
  }
}
