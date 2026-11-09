import sqlite3
import urllib.request
import json
from datetime import datetime

def fetch(url):
    try:
        resp = urllib.request.urlopen(url)
    except:
        return {}
        
    return json.loads(resp.read())

def get_suggestions():
    data = fetch('https://data.gov.hr/Suggestions/selectAllRow')['root']
    ret = []
    for d in data:
        if not d['datasetId'] or d['text'].strip() == "":
            continue
        ret.append({
            'suggestionId'  :   d['suggestionId'] + d['userId'] * 1000,
            'text'          :   d['description'],
            'title'         :   d['title'],
            'datetime'      :   d['dateTime'],
            'packageId'     :   d['datasetId']
        })
    return ret

def get_packages_and_resources(ids):
    packages    = []
    resources   = []
    for id in ids:
        if not id:
            continue
        print(f"Trying out {id}")
        try:
            data = fetch(f'https://data.gov.hr/ckan/api/3/action/package_show?id={id}')
            if not data['result']:
                continue
        except:
            continue
        data = data['result']
        packages.append({
            'packageId'     :   data['id'],
            'title'         :   data['title'],
            'description'   :   data['notes'] or '',
            'url'           :   f'https://data.gov.hr/ckan/api/3/action/package_show?id={id}'
        })
        for r in data['resources']:
            if not r:
                continue
            resources.append({
                'resourceId'    :   r['id'],
                'format'        :   r['format'] or '',
                'url'           :   r['url'] or '',
                'packageId'     :   r['package_id']
            })
    return packages, resources

def clean_suggestions(s):
    best = {}
    for item in s:
        key = (item['text'], item['title'], item['packageId'])
        dt = datetime.strptime(item['datetime'], "%Y-%m-%d %H:%M:%S")
        if key not in best or dt > best[key][0]:
            best[key] = (dt, item)
    return [item for _, item in best.values()]

suggestions = clean_suggestions(get_suggestions())
packages, resources = get_packages_and_resources(set(id for id in [s['packageId'] for s in suggestions]))

print(f"Valid suggestions: {len(suggestions)}")
print(f"Unique packages: {len(packages)}")
print(f"Unique resources: {len(resources)}")

con = sqlite3.connect('baza2.db')
cur = con.cursor()

for p in packages:
    res = cur.execute("INSERT OR IGNORE INTO PACKAGE(packageId, title, description, url)" 
                      "VALUES (?, ?, ?, ?);", 
                      (p['packageId'], p['title'], p['description'], p['url']))

for s in suggestions:
    res = cur.execute("INSERT OR IGNORE INTO SUGGESTION(suggestionId, text, title, datetime, packageId)" 
                      "VALUES (?, ?, ?, ?, ?);",
                      (s['suggestionId'], s['text'], s['title'], s['datetime'], s['packageId']))
    
for r in resources:
    res = cur.execute("INSERT OR IGNORE INTO RESOURCE(resourceId, format, url, packageId)" 
                      "VALUES (?, ?, ?, ?);",
                      (r['resourceId'], r['format'], r['url'], r['packageId']))

con.commit()
con.close()