CREATE TABLE PACKAGE
(
  packageId VARCHAR(100) NOT NULL,
  title VARCHAR(100) NOT NULL,
  description VARCHAR(1000) NOT NULL,
  url VARCHAR(1000) NOT NULL,
  PRIMARY KEY (packageId)
);

CREATE TABLE SUGGESTION
(
  suggestionId INT NOT NULL,
  text VARCHAR(1000) NOT NULL,
  title VARCHAR(100) NOT NULL,
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
  status INT NOT NULL CHECK (status in (0, 1, 2)),
  issueId INT NOT NULL,
  analysisId INT NOT NULL,
  PRIMARY KEY (issueId, analysisId),
  FOREIGN KEY (issueId) REFERENCES ISSUE(issueId),
  FOREIGN KEY (analysisId) REFERENCES ANALYSIS(analysisId)
);