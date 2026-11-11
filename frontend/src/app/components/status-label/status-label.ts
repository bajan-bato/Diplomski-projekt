import { Component, computed, input } from '@angular/core';
import {
  REVIEW_STATUS_LABELS,
  REVIEW_STATUS_UNAVAILABLE_LABEL,
  ReviewStatus,
} from '../../models/review.model';

type StatusVariant = 'fixed' | 'unfixed' | 'unknown' | 'unavailable';

/**
 * Displays a review status as both an icon and a text label (Croatian
 * wording per spec), so status is never communicated by colour alone.
 * Pass `null` when no REVIEW record exists for the selected analysis.
 */
@Component({
  selector: 'app-status-label',
  templateUrl: './status-label.html',
  styleUrl: './status-label.scss',
})
export class StatusLabelComponent {
  readonly status = input<ReviewStatus | null>(null);

  protected readonly label = computed(() => {
    const status = this.status();
    return status === null ? REVIEW_STATUS_UNAVAILABLE_LABEL : REVIEW_STATUS_LABELS[status];
  });

  protected readonly variant = computed<StatusVariant>(() => {
    const status = this.status();
    if (status === null) {
      return 'unavailable';
    }
    switch (status) {
      case ReviewStatus.Popravljeno:
        return 'fixed';
      case ReviewStatus.NijePopravljeno:
        return 'unfixed';
      default:
        return 'unknown';
    }
  });

  protected readonly icon = computed(() => {
    switch (this.variant()) {
      case 'fixed':
        return '✓';
      case 'unfixed':
        return '✗';
      case 'unknown':
        return '?';
      default:
        return '–';
    }
  });
}
