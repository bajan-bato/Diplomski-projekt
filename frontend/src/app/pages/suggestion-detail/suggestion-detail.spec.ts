import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { of } from 'rxjs';
import { SuggestionDetailComponent } from './suggestion-detail';
import { environment } from '../../../environments/environment';

describe('SuggestionDetailComponent', () => {
  let httpMock: HttpTestingController;
  const base = environment.apiBaseUrl;

  function createComponent() {
    TestBed.configureTestingModule({
      imports: [SuggestionDetailComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: ActivatedRoute,
          useValue: { paramMap: of(convertToParamMap({ suggestionId: '10' })) },
        },
      ],
    });
    httpMock = TestBed.inject(HttpTestingController);
    const fixture = TestBed.createComponent(SuggestionDetailComponent);
    fixture.detectChanges();
    return fixture;
  }

  function flushInitialLoad() {
    httpMock.expectOne(`${base}/suggestion/10`).flush({
      suggestionid: 10,
      text: 'Tekst prijedloga',
      title: 'Naslov prijedloga',
      datetime: '2024-01-01T00:00:00',
      packageid: 'pkg-a',
    });

    httpMock
      .expectOne((req) => req.url === `${base}/package/pkg-a`)
      .flush({ packageid: 'pkg-a', title: 'Paket A', description: 'Opis', url: 'https://example.com' });

    httpMock
      .expectOne((req) => req.url === `${base}/issue` && req.params.get('suggestionId') === '10')
      .flush([
        { issueid: 1, text: 'Issue A', suggestionid: 10 },
        { issueid: 2, text: 'Issue B', suggestionid: 10 },
      ]);

    httpMock.expectOne(`${base}/analysis`).flush([
      { analysisid: 100, datetime: '2024-01-01T00:00:00', idprev: null, idnext: 300 },
      { analysisid: 300, datetime: '2024-03-01T00:00:00', idprev: 100, idnext: null },
    ]);

    httpMock
      .expectOne(
        (req) =>
          req.url === `${base}/review` &&
          req.params.get('suggestionId') === '10' &&
          req.params.get('analysisId') === '300',
      )
      .flush([{ status: 1, issueid: 1, analysisid: 300 }]);
  }

  afterEach(() => httpMock.verify());

  it('loads the suggestion text and all its issues', () => {
    const fixture = createComponent();
    flushInitialLoad();
    fixture.detectChanges();

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Tekst prijedloga');
    expect(text).toContain('Issue A');
    expect(text).toContain('Issue B');
  });

  it('selects the most recent analysis by datetime as the initial selection', () => {
    const fixture = createComponent();
    flushInitialLoad();
    fixture.detectChanges();

    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Analiza #300');
  });

  it('shows the correct status for the selected analysis and the fallback for a missing review', () => {
    const fixture = createComponent();
    flushInitialLoad();
    fixture.detectChanges();

    const component = fixture.componentInstance;
    expect(component['reviewStatusFor'](1)).toBe(1);
    expect(component['reviewStatusFor'](2)).toBeNull();
  });

  it('disables the next arrow and enables prev when idNext is null', () => {
    const fixture = createComponent();
    flushInitialLoad();
    fixture.detectChanges();

    const buttons = (fixture.nativeElement as HTMLElement).querySelectorAll('button[aria-label]');
    const prev = Array.from(buttons).find((b) => b.getAttribute('aria-label') === 'Prethodna analiza')!;
    const next = Array.from(buttons).find((b) => b.getAttribute('aria-label') === 'Sljedeća analiza')!;

    expect((prev as HTMLButtonElement).disabled).toBe(false);
    expect((next as HTMLButtonElement).disabled).toBe(true);
  });

  it('navigates to a non-consecutive previous analysis id and refreshes statuses using the new analysis id', () => {
    const fixture = createComponent();
    flushInitialLoad();
    fixture.detectChanges();

    const prevButton = Array.from(
      (fixture.nativeElement as HTMLElement).querySelectorAll('button[aria-label]'),
    ).find((b) => b.getAttribute('aria-label') === 'Prethodna analiza') as HTMLButtonElement;

    prevButton.click();

    httpMock.expectOne(`${base}/analysis/100`).flush({
      analysisid: 100,
      datetime: '2024-01-01T00:00:00',
      idprev: null,
      idnext: 300,
    });

    httpMock
      .expectOne(
        (req) =>
          req.url === `${base}/review` &&
          req.params.get('suggestionId') === '10' &&
          req.params.get('analysisId') === '100',
      )
      .flush([
        { status: 0, issueid: 1, analysisid: 100 },
        { status: 2, issueid: 2, analysisid: 100 },
      ]);

    fixture.detectChanges();

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Analiza #100');
    expect(text).toContain('nije popravljeno');
    expect(text).toContain('nije moguće odrediti');

    const buttons = (fixture.nativeElement as HTMLElement).querySelectorAll('button[aria-label]');
    const prev = Array.from(buttons).find((b) => b.getAttribute('aria-label') === 'Prethodna analiza')!;
    const next = Array.from(buttons).find((b) => b.getAttribute('aria-label') === 'Sljedeća analiza')!;
    expect((prev as HTMLButtonElement).disabled).toBe(true);
    expect((next as HTMLButtonElement).disabled).toBe(false);
  });

  it('handles there being no analyses at all', () => {
    const fixture = createComponent();

    httpMock.expectOne(`${base}/suggestion/10`).flush({
      suggestionid: 10,
      text: 'Tekst prijedloga',
      title: 'Naslov prijedloga',
      datetime: '2024-01-01T00:00:00',
      packageid: 'pkg-a',
    });
    httpMock
      .expectOne((req) => req.url === `${base}/package/pkg-a`)
      .flush({ packageid: 'pkg-a', title: 'Paket A', description: 'Opis', url: 'https://example.com' });
    httpMock
      .expectOne((req) => req.url === `${base}/issue` && req.params.get('suggestionId') === '10')
      .flush([{ issueid: 1, text: 'Issue A', suggestionid: 10 }]);
    httpMock.expectOne(`${base}/analysis`).flush([]);

    fixture.detectChanges();

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Nema dostupnih analiza');
    expect(text).toContain('status nije dostupan');
  });
});
