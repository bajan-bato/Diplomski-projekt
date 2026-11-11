"""Odabir reprezentativnog uzorka suggestiona za prvi krug.

Stratifikacija po:
  - vrsti datoteka u paketu (excel / csv / json_xml / geo / other) - kvote proporcionalne populaciji, min. 2
  - duljini ociscenog teksta (short / medium / long / very_long)
  - godini prijedloga
Unutar svake skupine biramo pohlepno da pokrijemo sto vise razlicitih duljina i godina.
Najvise jedan suggestion po paketu. Rezultat je deterministican (seed).
"""
import json
import random
from collections import Counter, defaultdict

from . import db
from .textclean import html_to_text

GEO = {"GEOJSON", "SHP", "KML", "GDB", "FGDB", "WMS"}


def format_group(formats: set[str]) -> str:
    if formats & {"XLSX", "XLS", "XLSM"}:
        return "excel"
    if "CSV" in formats:
        return "csv"
    if formats & {"JSON", "XML"}:
        return "json_xml"
    if formats & GEO:
        return "geo"
    return "other"


def length_bucket(n: int) -> str:
    if n < 150:
        return "short"
    if n < 800:
        return "medium"
    if n < 3000:
        return "long"
    return "very_long"


def population() -> list[dict]:
    fmts = defaultdict(set)
    for r in db.rows("SELECT packageId AS package_id, format AS format FROM RESOURCE"):
        fmts[r["package_id"]].add((r["format"] or "").strip().upper())
    items = []
    # samo suggestioni ciji paket postoji u bazi (neki pokazuju na pakete kojih na CKAN-u vise nema)
    for s in db.rows("""SELECT s.suggestionId AS suggestion_id, s.title AS title, s.text AS text,
                               s.datetime AS datetime, s.packageId AS package_id
                        FROM SUGGESTION s JOIN PACKAGE p ON p.packageId = s.packageId"""):
        clean = html_to_text(s["text"])
        items.append({
            "suggestion_id": s["suggestion_id"],
            "package_id": s["package_id"],
            "title": s["title"],
            "fmt": format_group(fmts[s["package_id"]]),
            "len": length_bucket(len(clean)),
            "chars": len(clean),
            "year": str(s["datetime"])[:4],
        })
    return items


def quotas(counts: Counter, n: int, minimum: int = 2) -> dict:
    total = sum(counts.values())
    q = {g: min(c, max(minimum, round(n * c / total))) for g, c in counts.items()}
    while sum(q.values()) > n:  # skidamo s najvece skupine
        g = max(q, key=lambda k: q[k])
        q[g] -= 1
    while sum(q.values()) < n:  # dodajemo skupini koja je najvise podzastupljena
        g = max((k for k in counts if q[k] < counts[k]), key=lambda k: counts[k] / max(q[k], 1))
        q[g] += 1
    return q


def select(n: int = 20, seed: int = 42) -> list[dict]:
    rng = random.Random(seed)
    items = population()
    rng.shuffle(items)
    by_fmt = defaultdict(list)
    for it in items:
        by_fmt[it["fmt"]].append(it)
    q = quotas(Counter(it["fmt"] for it in items), n)

    chosen, used_packages = [], set()
    for fmt in sorted(by_fmt):
        seen = Counter()
        for _ in range(q[fmt]):
            cands = [c for c in by_fmt[fmt] if c["package_id"] not in used_packages]
            if not cands:
                break
            # rijetko vidjene duljine i godine imaju prednost
            best = max(cands, key=lambda c: 1 / (1 + seen[("len", c["len"])]) + 1 / (1 + seen[("year", c["year"])]))
            chosen.append(best)
            used_packages.add(best["package_id"])
            seen[("len", best["len"])] += 1
            seen[("year", best["year"])] += 1
    return chosen


def select_packages(n: int = 10, seed: int = 7) -> list[dict]:
    """Paketi s natuknicama, rasporedeni po vrsti datoteka i broju natuknica."""
    rng = random.Random(seed)
    fmts = defaultdict(set)
    for r in db.rows("SELECT packageId AS package_id, format AS format FROM RESOURCE"):
        fmts[r["package_id"]].add((r["format"] or "").strip().upper())
    pkgs = db.rows("""SELECT s.packageId AS package_id, p.title AS title, COUNT(*) AS issues
                      FROM ISSUE i JOIN SUGGESTION s ON s.suggestionId = i.suggestionId
                      JOIN PACKAGE p ON p.packageId = s.packageId
                      GROUP BY s.packageId, p.title""")
    for p in pkgs:
        p["fmt"] = format_group(fmts[p["package_id"]])
        p["size"] = "1-3" if p["issues"] <= 3 else "4-7" if p["issues"] <= 7 else "8+"
    rng.shuffle(pkgs)
    by_fmt = defaultdict(list)
    for p in pkgs:
        by_fmt[p["fmt"]].append(p)
    q = quotas(Counter(p["fmt"] for p in pkgs), n, minimum=1)
    chosen = []
    for fmt in sorted(by_fmt):
        seen = Counter()
        for _ in range(q[fmt]):
            cands = [c for c in by_fmt[fmt] if c not in chosen]
            if not cands:
                break
            best = max(cands, key=lambda c: 1 / (1 + seen[c["size"]]))
            chosen.append(best)
            seen[best["size"]] += 1
    return chosen


def save(chosen: list[dict], path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(chosen, ensure_ascii=False, indent=2), encoding="utf-8")


def load(path) -> list[int]:
    return [it["suggestion_id"] for it in json.loads(path.read_text(encoding="utf-8"))]
