import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { PackagesListComponent } from './packages-list';
import { environment } from '../../../environments/environment';

describe('PackagesListComponent', () => {
  let httpMock: HttpTestingController;
  const base = environment.apiBaseUrl;

  function createComponent() {
    TestBed.configureTestingModule({
      imports: [PackagesListComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
    httpMock = TestBed.inject(HttpTestingController);
    const fixture = TestBed.createComponent(PackagesListComponent);
    fixture.detectChanges();
    return fixture;
  }

  afterEach(() => httpMock.verify());

  it('shows a loading state while packages are being fetched', () => {
    const fixture = createComponent();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Učitavanje');
    httpMock.expectOne(`${base}/package`).flush([]);
  });

  it('shows packageId, title and description for each package', () => {
    const fixture = createComponent();
    httpMock.expectOne(`${base}/package`).flush([
      { packageid: 'pkg-a', title: 'Naslov A', description: 'Opis A', url: 'https://example.com/a' },
    ]);
    fixture.detectChanges();

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('pkg-a');
    expect(text).toContain('Naslov A');
    expect(text).toContain('Opis A');
  });

  it('shows an empty state when there are no packages', () => {
    const fixture = createComponent();
    httpMock.expectOne(`${base}/package`).flush([]);
    fixture.detectChanges();

    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Nema dostupnih paketa');
  });

  it('shows an error state when the request fails', () => {
    const fixture = createComponent();
    httpMock.expectOne(`${base}/package`).flush('error', { status: 500, statusText: 'Server Error' });
    fixture.detectChanges();

    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Paketi se nisu mogli učitati');
  });
});
