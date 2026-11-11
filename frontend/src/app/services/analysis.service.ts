import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';
import { environment } from '../../environments/environment';
import { Analysis } from '../models/analysis.model';
import { RawAnalysis } from './api.dto';
import { toAnalysis } from './api.mappers';

@Injectable({ providedIn: 'root' })
export class AnalysisService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiBaseUrl}/analysis`;

  getAll(): Observable<Analysis[]> {
    return this.http.get<RawAnalysis[]>(this.baseUrl).pipe(map((raws) => raws.map(toAnalysis)));
  }

  getById(analysisId: number): Observable<Analysis> {
    return this.http.get<RawAnalysis>(`${this.baseUrl}/${analysisId}`).pipe(map(toAnalysis));
  }
}
