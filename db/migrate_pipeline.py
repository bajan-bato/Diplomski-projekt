"""Jednokratna migracija postojece SQLite baze za AI pipeline.

- RESOURCE: dodaje stupce name i hash i puni ih s CKAN API-ja
- REVIEW: dodaje stupce explanation i evidence
- stvara tablice PIPELINE_STATE i ISSUE_CHECK

Pokretanje (iz mape db/):  python migrate_pipeline.py [putanja_do_baze]
Sigurno je pokrenuti vise puta.
"""
import json
import sqlite3
import sys
import time
import urllib.request

from populatae_db import resource_name

DB_PATH = sys.argv[1] if len(sys.argv) > 1 else 'baza2.db'

NEW_TABLES = """
CREATE TABLE IF NOT EXISTS PIPELINE_STATE
(
  contentHash VARCHAR(64) NOT NULL,
  suggestionId INT NOT NULL,
  processedAt TIMESTAMP NOT NULL,
  ignored INT NOT NULL CHECK (ignored in (0, 1)),
  ignoreReason TEXT,
  model VARCHAR(100) NOT NULL,
  PRIMARY KEY (contentHash)
);
CREATE TABLE IF NOT EXISTS ISSUE_CHECK
(
  issueId INT NOT NULL,
  category VARCHAR(50) NOT NULL,
  specific INT NOT NULL CHECK (specific in (0, 1)),
  checkInstruction TEXT NOT NULL,
  targetResources TEXT,
  PRIMARY KEY (issueId),
  FOREIGN KEY (issueId) REFERENCES ISSUE(issueId)
);
"""


def add_column(cur, table, column, decl):
    cols = [r[1] for r in cur.execute(f"PRAGMA table_info({table})")]
    if column not in cols:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")
        print(f"  + {table}.{column}")


def main():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    print("Shema:")
    add_column(cur, 'RESOURCE', 'name', 'VARCHAR(500)')
    add_column(cur, 'RESOURCE', 'hash', 'VARCHAR(128)')
    add_column(cur, 'REVIEW', 'explanation', 'TEXT')
    add_column(cur, 'REVIEW', 'evidence', 'TEXT')
    cur.executescript(NEW_TABLES)
    con.commit()

    package_ids = [r[0] for r in cur.execute("SELECT packageId FROM PACKAGE")]
    print(f"Dohvacam name/hash za resurse iz {len(package_ids)} paketa...")
    updated = missing_hash = failed = 0
    for i, pid in enumerate(package_ids, 1):
        try:
            url = f'https://data.gov.hr/ckan/api/3/action/package_show?id={pid}'
            data = json.loads(urllib.request.urlopen(url, timeout=60).read())['result']
        except Exception as e:
            failed += 1
            print(f"  ! {pid}: {e}")
            continue
        for r in data.get('resources', []):
            h = r.get('hash') or None
            missing_hash += h is None
            cur.execute("UPDATE RESOURCE SET name = ?, hash = ? WHERE resourceId = ?",
                        (resource_name(r), h, r['id']))
            updated += cur.rowcount
        if i % 25 == 0:
            con.commit()
            print(f"  {i}/{len(package_ids)}")
        time.sleep(0.1)  # ne opterecujemo portal
    con.commit()

    total = cur.execute("SELECT count(*) FROM RESOURCE").fetchone()[0]
    named = cur.execute("SELECT count(*) FROM RESOURCE WHERE name IS NOT NULL").fetchone()[0]
    hashed = cur.execute("SELECT count(*) FROM RESOURCE WHERE hash IS NOT NULL").fetchone()[0]
    print(f"Gotovo. Azurirano {updated} resursa; s nazivom {named}/{total}, s hashom {hashed}/{total}; "
          f"paketa s greskom: {failed}")
    con.close()


if __name__ == '__main__':
    main()
