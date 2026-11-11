/** Application-facing model for an ANALYSIS row. Field names mirror the database/API contract exactly. */
export interface Analysis {
  analysisId: number;
  /** ISO datetime string as returned by the API. */
  datetime: string;
  /** Previous analysis in the sequence, or null if this is the first one. */
  idPrev: number | null;
  /** Next analysis in the sequence, or null if this is the last one. */
  idNext: number | null;
}
