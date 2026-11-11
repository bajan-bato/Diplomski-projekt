# Frontend

## Setup

```bash
cd frontend
npm install
```

## Configuring the backend base URL

- `src/environments/environment.development.ts` — used by `ng serve`
  (defaults to `http://localhost:5201/api`).

- `src/environments/environment.ts` — production build (`ng
build`)

## Running

```bash
npm start        # ng serve, http://localhost:4200
npm run build    # production build into dist/frontend
```

Run the backend separately, it listens
on `http://localhost:5201` (or `https://localhost:7275`)

## Endpoints and wha they return

GET /api/package

returns Package[]
Package:
packageId
title
description
url

GET /api/package/{packageId}

returns Package
same fields as above

GET /api/suggestion

returns Suggestion[]
Suggestion:
suggestionId
text
title
datetime
packageId

GET /api/suggestion/{id}

returns Suggestion
same fields as above

GET /api/issue?suggestionId={id}

returns Issue[]
Issue:
issueId
text
suggestionId

GET /api/analysis

returns Analysis[]
Analysis:
analysisId
datetime
idPrev
idNext

GET /api/analysis/{analysisId}

returns Analysis
same fields as above

GET /api/review?suggestionId={id}&analysisId={analysisId}

returns Review[]
Review:
status
issueId
analysisId
