export interface RawPackage {
  packageId: string;
  title: string;
  description: string;
  url: string;
}

export interface RawSuggestion {
  suggestionId: number;
  text: string;
  title: string;
  datetime: string;
  packageId: string;
}

export interface RawIssue {
  issueId: number;
  text: string;
  suggestionId: number;
}

export interface RawAnalysis {
  analysisId: number;
  datetime: string;
  idPrev: number | null;
  idNext: number | null;
}

export interface RawReview {
  status: number;
  issueId: number;
  analysisId: number;
}
