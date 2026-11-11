import { Package } from '../models/package.model';
import { Suggestion } from '../models/suggestion.model';
import { Issue } from '../models/issue.model';
import { Analysis } from '../models/analysis.model';
import { Review, ReviewStatus } from '../models/review.model';
import { RawAnalysis, RawIssue, RawPackage, RawReview, RawSuggestion } from './api.dto';

export function toPackage(raw: RawPackage): Package {
  return {
    packageId: raw.packageId,
    title: raw.title,
    description: raw.description,
    url: raw.url,
  };
}

export function toSuggestion(raw: RawSuggestion): Suggestion {
  return {
    suggestionId: raw.suggestionId,
    text: raw.text,
    title: raw.title,
    datetime: raw.datetime,
    packageId: raw.packageId,
  };
}

export function toIssue(raw: RawIssue): Issue {
  return {
    issueId: raw.issueId,
    text: raw.text,
    suggestionId: raw.suggestionId,
  };
}

export function toAnalysis(raw: RawAnalysis): Analysis {
  return {
    analysisId: raw.analysisId,
    datetime: raw.datetime,
    idPrev: raw.idPrev,
    idNext: raw.idNext,
  };
}

export function toReview(raw: RawReview): Review {
  return {
    status: raw.status as ReviewStatus,
    issueId: raw.issueId,
    analysisId: raw.analysisId,
  };
}
