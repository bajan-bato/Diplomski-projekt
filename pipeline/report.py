"""Markdown izvjestaji (extractor i analyzer) za rucni pregled."""
from collections import Counter
from datetime import datetime

from . import config

STATUS_TXT = {0: "POSTOJI", 1: "RIJESENO", 2: "NE ZNA SE"}


def write_analyze_report(records: list[dict]) -> "Path":
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = config.OUTPUT_DIR / f"analyze_report_{datetime.now():%Y%m%d_%H%M%S}.md"
    allv = [v for r in records for v in r["verdicts"].values()]
    st = Counter(v["status"] for v in allv)
    reasons = Counter(v["reason"] for v in allv if v["status"] == 2)
    out = ["# Izvjestaj analyzera", "",
           f"- Paketa: {len(records)} | natuknica: {len(allv)}",
           f"- Postoji (0): {st[0]} | rijeseno (1): {st[1]} | ne zna se (2): {st[2]}",
           f"- Razlozi za 2: {dict(reasons)}",
           f"- Eskalirano: {sum(len(r['escalated']) for r in records)}",
           f"- Trosak: ${sum(r['cost'] for r in records):.4f} ({sum(r['calls'] for r in records)} poziva modela)", ""]
    for r in records:
        pkg = r["package"]
        names = {x["resource_id"]: f"{(x['format'] or '?').strip().upper()} '{x['name'] or '?'}'" for x in pkg["resources"]}
        out += ["---", "", f"## {pkg['title']}", "",
                f"`{pkg['package_id']}` | ANALYSIS {r['analysis_id']} | {r['calls']} poziva | ${r['cost']:.4f}", ""]
        if r["load_errors"]:
            out += ["Resursi koji se nisu mogli ucitati:"]
            out += [f"- {names.get(rid, rid)}: {e}" for rid, e in r["load_errors"].items()]
            out += [""]
        for it in pkg["issues"]:
            v = r["verdicts"].get(it["issue_id"])
            if not v:
                continue
            esc = " (eskalirano)" if v.get("escalated") else ""
            out += [f"- **[{it['issue_id']}] {STATUS_TXT[v['status']]}** ({v['reason']}){esc} - {it['text']}",
                    f"  - specificna: {'da' if it['specific'] else 'NE'} | kategorija: `{it['category']}` | model: {v['model']}",
                    f"  - obrazlozenje: {v['explanation']}",
                    f"  - dokaz: {v['evidence'] or '-'}"]
        out += [""]
    path.write_text("\n".join(out), encoding="utf-8")
    return path


def write_extract_report(records: list[dict]) -> "Path":
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = config.OUTPUT_DIR / f"extract_report_{datetime.now():%Y%m%d_%H%M%S}.md"
    total = sum(r.get("cost", 0) for r in records)
    valid = sum(1 for r in records if r.get("result", {}).get("valid"))
    issues = sum(len(r.get("issue_ids", [])) for r in records)
    errors = sum(1 for r in records if "error" in r)

    out = [
        "# Izvjestaj extractora",
        "",
        f"- Suggestiona: {len(records)} (valjanih {valid}, ignoriranih {len(records) - valid - errors}, gresaka {errors})",
        f"- Natuknica (ISSUE): {issues}",
        f"- Trosak: ${total:.4f}",
        "",
    ]
    for r in records:
        s = r["suggestion"]
        names = {x["resource_id"]: f"{(x['format'] or '?').strip().upper()} '{x['name'] or '?'}'"
                 for x in s["resources"]}
        out += ["---", "", f"## {s['suggestion_id']} - {s['title']}", "",
                f"**Paket:** {s['package_title']}  ", f"**Datum:** {s['datetime']}  ",
                f"**Resursa u paketu:** {len(s['resources'])}", ""]
        text = s["clean_text"]
        out += ["<details><summary>Originalni tekst</summary>", "", text if len(text) < 4000
                else text[:4000] + " …(skraceno u izvjestaju)", "", "</details>", ""]
        if "error" in r:
            out += [f"**GRESKA:** {r['error']}", ""]
            continue
        res = r["result"]
        if not res["valid"]:
            out += [f"**IGNORIRAN:** {res['ignore_reason']}", ""]
            continue
        for iid, it in zip(r["issue_ids"], res["issues"]):
            targets = ", ".join(names.get(t, t) for t in it["target_resources"]) or "svi tablicni / nije navedeno"
            out += [f"- **[{iid}] {it['text']}**",
                    f"  - kategorija: `{it['category']}` | specifican: {'da' if it['specific'] else 'NE'}",
                    f"  - resursi: {targets}",
                    f"  - provjera: {it['check']}"]
        if res.get("skipped_duplicates"):
            out += [f"- _preskoceni duplikati postojecih natuknica: {res['skipped_duplicates']}_"]
        out += ["", f"_model: {r['model']}, trosak: ${r['cost']:.4f}_", ""]
    path.write_text("\n".join(out), encoding="utf-8")
    return path
