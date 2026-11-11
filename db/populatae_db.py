import sqlite3
import urllib.request
import json
from datetime import datetime

DB_PATH = 'baza2.db'


def fetch(url):
    try:
        resp = urllib.request.urlopen(url, timeout=60)
    except Exception:
        return {}

    return json.loads(resp.read())


def get_suggestions():
    data = fetch('https://data.gov.hr/Suggestions/selectAllRow').get('root', [])
    ret = []
    for d in data:
        if not d.get('datasetId') or not (d.get('description') or '').strip():
            continue
        ret.append({
            # suggestionId na portalu ne ide preko 999 i ponavlja se, pa se kombinira s userId
            'suggestionId'  :   d['suggestionId'] + d['userId'] * 1000,
            'text'          :   d['description'],
            'title'         :   d['title'],
            'datetime'      :   d['dateTime'],
            'packageId'     :   d['datasetId']
        })
    return ret


def resource_name(r):
    # Neki resursi nemaju 'name', ali gotovo uvijek imaju 'description'
    return (r.get('name') or r.get('description') or '').strip() or None


def get_packages_and_resources(ids):
    packages    = []
    resources   = []
    for id in ids:
        if not id:
            continue
        print(f"Trying out {id}")
        data = fetch(f'https://data.gov.hr/ckan/api/3/action/package_show?id={id}')
        if not data or not data.get('result'):
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
                'packageId'     :   r['package_id'],
                'name'          :   resource_name(r),
                'hash'          :   r.get('hash') or None,
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


if __name__ == '__main__':
    suggestions = clean_suggestions(get_suggestions())
    packages, resources = get_packages_and_resources(set(s['packageId'] for s in suggestions))

    print(f"Valid suggestions: {len(suggestions)}")
    print(f"Unique packages: {len(packages)}")
    print(f"Unique resources: {len(resources)}")

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    for p in packages:
        cur.execute("INSERT OR IGNORE INTO PACKAGE(packageId, title, description, url) "
                    "VALUES (?, ?, ?, ?);",
                    (p['packageId'], p['title'], p['description'], p['url']))

    for s in suggestions:
        cur.execute("INSERT OR IGNORE INTO SUGGESTION(suggestionId, text, title, datetime, packageId) "
                    "VALUES (?, ?, ?, ?, ?);",
                    (s['suggestionId'], s['text'], s['title'], s['datetime'], s['packageId']))

    for r in resources:
        # name i hash se osvjezavaju i za postojece resurse
        cur.execute("INSERT INTO RESOURCE(resourceId, format, url, packageId, name, hash) "
                    "VALUES (?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(resourceId) DO UPDATE SET name = excluded.name, hash = excluded.hash;",
                    (r['resourceId'], r['format'], r['url'], r['packageId'], r['name'], r['hash']))

    con.commit()
    con.close()
