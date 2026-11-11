import { TestBed } from '@angular/core/testing';
import { StatisticsComponent } from './statistics';

describe('StatisticsComponent', () => {
  it('renders exactly the "Work in progress" placeholder', () => {
    TestBed.configureTestingModule({ imports: [StatisticsComponent] });
    const fixture = TestBed.createComponent(StatisticsComponent);
    fixture.detectChanges();

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Work in progress');
  });
});
