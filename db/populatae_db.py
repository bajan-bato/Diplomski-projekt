import sqlite3
import urllib.request
import json
import html
import time

conn = sqlite3.connect("baza.db")
cur = conn.cursor()
cur.execute("PRAGMA foreign_keys = ON;")

def insert(cur, table, **kwargs):
    cols = ", ".join(kwargs.keys())
    ph = ", ".join(["?"] * len(kwargs))
    cur.execute(f"INSERT OR IGNORE INTO {table} ({cols}) VALUES ({ph})",
                tuple(kwargs.values()))

def get_data(url, tries=5):
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                return json.loads(r.read())
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            if i == tries - 1:
                raise
            time.sleep(2 ** i)

def get_packages():
    return get_data("https://data.gov.hr/ckan/api/action/package_list")["result"]

def get_suggestions():
    data = get_data("https://data.gov.hr/Suggestions/selectAllRow")["root"]
    res = []
    for el in data:
        res.append(
            {
                "id"          : el["suggestionId"],
                "text"        : html.unescape(el["description"]),
                "title"       : el["title"],
                "datetime"    : el["dateTime"],
                "packageId"   : el["datasetId"]
            }
        )
    return res

def get_packages_and_resources(package):
    url = ("https://data.gov.hr/ckan/api/action/package_search?q=" + '"' + package + '"')
    try:
        data = get_data(url)["result"]["results"][0]
    except(IndexError, KeyError):
        return [], None
    res = []
    pack = {
        "packageId"     : data["id"],
        "title"         : data["title"] or "",
        "description"   : (data.get("organization") or {}).get("description") or "",
        "url"           : data.get("url") or f"https://data.gov.hr/dataset/{data['name']}",
    }
    for el in data["resources"]:
        res.append(
            {
                "resourceId"    : el["id"],
                "format"        : el["format"],
                "url"           : el["url"],
                "packageId"     : el["package_id"],
            }
        )
    return res, pack


resources   = []
datasets    = []
packages    = get_packages()
suggestions = get_suggestions()
for p in packages:
    resource, dataset = get_packages_and_resources(p)
    resources.append(resource)
    datasets.append(dataset)

# package
for d in datasets:
    if d is None:
        continue
    insert(cur, "PACKAGE",
           packageId=d["packageId"],
           title=d["title"],
           description=d["description"],
           url=d["url"])

cur.execute("SELECT packageId FROM PACKAGE")
known_ids = {row[0] for row in cur.fetchall()}

# resource
skipped_res = 0
for group in resources:
    for r in group:
        if r["packageId"] not in known_ids:
            skipped_res += 1
            continue
        insert(cur, "RESOURCE",
               resourceId=r["resourceId"],
               format=r["format"],
               url=r["url"],
               packageId=r["packageId"])

# suggestion
skipped_sug = 0
for s in suggestions:
    if s["packageId"] not in known_ids:
        skipped_sug += 1
        continue
    insert(cur, "SUGGESTION",
           suggestionId=int(s["id"]),
           text=s["text"],
           title=s["title"],
           datetime=s["datetime"],
           packageId=s["packageId"])

conn.commit()
print(f"skipped resources (FK ne postoji):   {skipped_res}")
print(f"skipped suggestions (FK ne postoji): {skipped_sug}")