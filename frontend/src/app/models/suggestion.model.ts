/** Application-facing model for a SUGGESTION row. Field names mirror the database/API contract exactly. */
export interface Suggestion {
  suggestionId: number;
  text: string;
  title: string;
  /** ISO datetime string as returned by the API. */
  datetime: string;
  packageId: string;
}
