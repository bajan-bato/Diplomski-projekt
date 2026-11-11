import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { of } from 'rxjs';
import { SuggestionsListComponent } from './suggestions-list';
import { environment } from '../../../environments/environment';

describe('SuggestionsListComponent', () => {
  let httpMock: HttpTestingController;
  const base = environment.apiBaseUrl;

  function createComponent() {
    TestBed.configureTestingModule({
      imports: [SuggestionsListComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: ActivatedRoute,
          useValue: { paramMap: of(convertToParamMap({ packageId: 'pkg-a' })) },
        },
      ],
    });
    httpMock = TestBed.inject(HttpTestingController);
    const fixture = TestBed.createComponent(SuggestionsListComponent);
    fixture.detectChanges();
    return fixture;
  }

  afterEach(() => httpMock.verify());

  it('shows only suggestions belonging to the selected package with suggestionId, title and datetime', () => {
    const fixture = createComponent();

    httpMock
      .expectOne(`${base}/package/pkg-a`)
      .flush({ packageid: 'pkg-a', title: 'Paket A', description: 'Opis', url: 'https://example.com' });

    httpMock.expectOne(`${base}/suggestion`).flush([
      { suggestionid: 1, text: 't1', title: 'Prvi prijedlog', datetime: '2024-01-01T10:00:00', packageid: 'pkg-a' },
      { suggestionid: 2, text: 't2', title: 'Drugi prijedlog', datetime: '2024-02-01T10:00:00', packageid: 'pkg-b' },
    ]);

    fixture.detectChanges();
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Prvi prijedlog');
    expect(text).toContain('#1');
    expect(text).not.toContain('Drugi prijedlog');
  });

  it('shows a not-found state when the package does not exist', () => {
    const fixture = createComponent();

    httpMock.expectOne(`${base}/package/pkg-a`).flush('missing', { status: 404, statusText: 'Not Found' });

    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Paket nije pronađen');
  });
});
