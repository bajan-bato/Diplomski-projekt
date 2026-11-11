/** Raw REVIEW.status values as constrained by the database CHECK (status in (0, 1, 2)). */
export enum ReviewStatus {
  NijePopravljeno = 0,
  Popravljeno = 1,
  NijeMoguceOdrediti = 2,
}

/** Application-facing model for a REVIEW row. Field names mirror the database/API contract exactly. */
export interface Review {
  status: ReviewStatus;
  issueId: number;
  analysisId: number;
}

/** Exact Croatian labels required by the spec for each REVIEW.status value. */
export const REVIEW_STATUS_LABELS: Record<ReviewStatus, string> = {
  [ReviewStatus.NijePopravljeno]: 'nije popravljeno',
  [ReviewStatus.Popravljeno]: 'popravljeno',
  [ReviewStatus.NijeMoguceOdrediti]: 'nije moguće odrediti',
};

/** Label shown when an issue has no REVIEW record for the selected analysis. */
export const REVIEW_STATUS_UNAVAILABLE_LABEL = 'status nije dostupan';
