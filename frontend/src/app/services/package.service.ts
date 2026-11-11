import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';
import { environment } from '../../environments/environment';
import { Package } from '../models/package.model';
import { RawPackage } from './api.dto';
import { toPackage } from './api.mappers';

@Injectable({ providedIn: 'root' })
export class PackageService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiBaseUrl}/package`;

  getAll(): Observable<Package[]> {
    return this.http.get<RawPackage[]>(this.baseUrl).pipe(map((raws) => raws.map(toPackage)));
  }

  getById(packageId: string): Observable<Package> {
    return this.http
      .get<RawPackage>(`${this.baseUrl}/${encodeURIComponent(packageId)}`)
      .pipe(map(toPackage));
  }
}
