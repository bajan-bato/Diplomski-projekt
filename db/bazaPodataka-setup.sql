CREATE TABLE PACKAGE
(
  packageId VARCHAR(100) NOT NULL,
  title VARCHAR(255) NOT NULL,
  description TEXT NOT NULL,
  url VARCHAR(1000) NOT NULL,
  PRIMARY KEY (packageId)
);

CREATE TABLE SUGGESTION
(
  suggestionId INT NOT NULL,
  text TEXT NOT NULL,
  title VARCHAR(255) NOT NULL,
  datetime TIMESTAMP NOT NULL,
  packageId VARCHAR(100) NOT NULL,
  PRIMARY KEY (suggestionId),
  FOREIGN KEY (packageId) REFERENCES PACKAGE(packageId)
);

CREATE TABLE ISSUE
(
  issueId INT NOT NULL,
  text VARCHAR(255) NOT NULL,
  suggestionId INT NOT NULL,
  PRIMARY KEY (issueId),
  FOREIGN KEY (suggestionId) REFERENCES SUGGESTION(suggestionId)
);

CREATE TABLE RESOURCE
(
  resourceId VARCHAR(100) NOT NULL,
  format VARCHAR(50) NOT NULL,
  url VARCHAR(1000) NOT NULL,
  packageId VARCHAR(100) NOT NULL,
  name VARCHAR(500),            -- naziv resursa s CKAN-a (ili description ako naziva nema)
  hash VARCHAR(128),            -- CKAN hash datoteke; promjena hasha = podaci su se promijenili
  PRIMARY KEY (resourceId),
  FOREIGN KEY (packageId) REFERENCES PACKAGE(packageId)
);

CREATE TABLE ANALYSIS
(
  analysisId INT NOT NULL,
  datetime TIMESTAMP NOT NULL,
  idPrev INT,
  idNext INT,
  PRIMARY KEY (analysisId),
  FOREIGN KEY (idPrev) REFERENCES ANALYSIS(analysisId),
  FOREIGN KEY (idNext) REFERENCES ANALYSIS(analysisId),
  UNIQUE (idPrev),
  UNIQUE (idNext)
);

CREATE TABLE REVIEW
(
  status INT NOT NULL CHECK (status in (0, 1, 2)),  -- 0 = problem i dalje postoji, 1 = rijeseno, 2 = ne moze se utvrditi
  issueId INT NOT NULL,
  analysisId INT NOT NULL,
  explanation TEXT,             -- kratko obrazlozenje odluke (i razlog za status 2)
  evidence TEXT,                -- dokaz iz podataka (npr. "redak 1 = 'Col1 Col2 Col3'")
  PRIMARY KEY (issueId, analysisId),
  FOREIGN KEY (issueId) REFERENCES ISSUE(issueId),
  FOREIGN KEY (analysisId) REFERENCES ANALYSIS(analysisId)
);

-- ===== Tablice AI pipelinea (ne mijenjaju postojece tablice) =====

-- Koji su suggestioni obradeni. Kljuc je hash sadrzaja (packageId + title + text),
-- jer se suggestionId na data.gov.hr moze ponovno iskoristiti.
CREATE TABLE PIPELINE_STATE
(
  contentHash VARCHAR(64) NOT NULL,
  suggestionId INT NOT NULL,
  processedAt TIMESTAMP NOT NULL,
  ignored INT NOT NULL CHECK (ignored in (0, 1)),  -- 1 = nevaljan / nespecifican suggestion
  ignoreReason TEXT,
  model VARCHAR(100) NOT NULL,
  PRIMARY KEY (contentHash)
);

-- Strojno provjerljivi detalji za svaki ISSUE (za agenta), ISSUE.text ostaje human readable.
CREATE TABLE ISSUE_CHECK
(
  issueId INT NOT NULL,
  category VARCHAR(50) NOT NULL,      -- data_content | structure | encoding | metadata | availability | feature_request
  specific INT NOT NULL CHECK (specific in (0, 1)),  -- 1 = ima konkretnu vrijednost/stupac/redak za provjeru
  checkInstruction TEXT NOT NULL,     -- sto tocno provjeriti i kada je problem rijesen
  targetResources TEXT,               -- JSON lista resourceId-jeva (prazno = svi tablicni resursi)
  PRIMARY KEY (issueId),
  FOREIGN KEY (issueId) REFERENCES ISSUE(issueId)
);
