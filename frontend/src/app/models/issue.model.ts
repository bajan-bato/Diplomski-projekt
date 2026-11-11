/** Application-facing model for an ISSUE row. Field names mirror the database/API contract exactly. */
export interface Issue {
  issueId: number;
  text: string;
  suggestionId: number;
}
