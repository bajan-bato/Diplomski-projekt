import { TestBed } from '@angular/core/testing';
import { StatusLabelComponent } from './status-label';
import { ReviewStatus } from '../../models/review.model';

describe('StatusLabelComponent', () => {
  function render(status: ReviewStatus | null) {
    const fixture = TestBed.createComponent(StatusLabelComponent);
    fixture.componentRef.setInput('status', status);
    fixture.detectChanges();
    return (fixture.nativeElement as HTMLElement).textContent?.trim() ?? '';
  }

  it('shows "nije popravljeno" for status 0', () => {
    expect(render(ReviewStatus.NijePopravljeno)).toContain('nije popravljeno');
  });

  it('shows "popravljeno" for status 1', () => {
    expect(render(ReviewStatus.Popravljeno)).toContain('popravljeno');
  });

  it('shows "nije moguće odrediti" for status 2', () => {
    expect(render(ReviewStatus.NijeMoguceOdrediti)).toContain('nije moguće odrediti');
  });

  it('shows the neutral fallback when no review record exists, never status 0', () => {
    const text = render(null);
    expect(text).toContain('status nije dostupan');
    expect(text).not.toContain('nije popravljeno');
  });
});
