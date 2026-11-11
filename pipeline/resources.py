"""Alati za citanje resursa paketa bez slanja cijelih datoteka LLM-u.

Svaki resurs se preuzme (s cacheom), prepozna mu se stvarni format i ucita u jednu ili vise
tablica (pandas DataFrame, sve vrijednosti kao tekst). Agent zatim dobiva samo:
  - profil (struktura, prvi redovi, stupci)
  - ciljane upite (pandas izraz), pretragu vrijednosti (fuzzy) i sirove retke
Svi izlazi su ograniceni na nekoliko tisuca znakova.
"""
import ast
import builtins
import csv
import difflib
import hashlib
import io
import json
import re
import statistics
import threading
import unicodedata
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timedelta

import pandas as pd

from . import config

MAX_DOWNLOAD = 50 * 1024 * 1024
CACHE_TTL = timedelta(hours=24)
USER_AGENT = "Mozilla/5.0 (compatible; data-quality-pipeline/0.1)"
OUT_MAX = 3500
CELL_MAX = 60
QUERY_TIMEOUT = 20

TABULAR_KINDS = {"csv", "xlsx", "xls", "json", "geojson", "xml"}


class ResourceError(Exception):
    pass


def clip(text: str, n: int = OUT_MAX) -> str:
    return text if len(text) <= n else text[:n] + f"\n...(skraceno, ukupno {len(text)} znakova)"


def short(v, n: int = CELL_MAX) -> str:
    s = str(v).replace("\n", "\\n")
    return s if len(s) <= n else s[: n - 1] + "…"


def norm(s: str) -> str:
    """Za usporedbu: mala slova, bez dijakritika, sazeti razmaci."""
    s = str(s).casefold().replace("đ", "d")
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return " ".join(s.split())


# ---------- preuzimanje ----------

def download(resource: dict) -> tuple[bytes, dict]:
    config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    rid = resource["resource_id"]
    data_path, meta_path = config.CACHE_DIR / rid, config.CACHE_DIR / f"{rid}.json"
    if data_path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if datetime.now() - datetime.fromisoformat(meta["fetched_at"]) < CACHE_TTL and meta.get("url") == resource["url"]:
            return data_path.read_bytes(), meta

    url = resource["url"]
    if not url:
        raise ResourceError("resurs nema URL")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        resp = urllib.request.urlopen(req, timeout=90)
    except urllib.error.HTTPError as e:
        raise ResourceError(f"HTTP {e.code} pri preuzimanju ({url})")
    except Exception as e:
        raise ResourceError(f"preuzimanje nije uspjelo: {e}")
    chunks, total = [], 0
    while True:
        b = resp.read(1 << 20)
        if not b:
            break
        total += len(b)
        if total > MAX_DOWNLOAD:
            raise ResourceError("datoteka je veca od 50 MB, preskacem")
        chunks.append(b)
    data = b"".join(chunks)
    meta = {
        "url": url, "final_url": resp.geturl(), "status": resp.status,
        "content_type": resp.headers.get("Content-Type", ""), "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(), "fetched_at": datetime.now().isoformat(timespec="seconds"),
    }
    data_path.write_bytes(data)
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    return data, meta


# ---------- prepoznavanje i ucitavanje ----------

def sniff(data: bytes) -> str:
    body = data.lstrip(b"\xef\xbb\xbf").lstrip()
    if data[:2] == b"PK":
        try:
            names = zipfile.ZipFile(io.BytesIO(data)).namelist()
        except zipfile.BadZipFile:
            return "unknown"
        if any(n.startswith("xl/") for n in names):
            return "xlsx"
        if any(n.startswith("word/") for n in names):
            return "docx"
        return "zip"
    if data[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        return "xls"
    if data[:4] == b"%PDF":
        return "pdf"
    if body[:1] in (b"{", b"["):
        try:
            obj = json.loads(decode_text(data)[0])
            if isinstance(obj, dict) and obj.get("type") == "FeatureCollection":
                return "geojson"
            return "json"
        except Exception:
            pass
    if body[:1] == b"<":
        low = body[:600].lower()
        return "html" if (b"<html" in low or b"<!doctype html" in low) else "xml"
    if b"\x00" in data[:4096]:
        return "unknown"
    return "csv" if data.strip() else "empty"


MOJIBAKE = re.compile(r"Ä[‡Ť†Ť‘]|Å[¡¾½ ]|Ã[„…]|Ĺ[ľ˝]|Ă„|�")


def decode_text(data: bytes) -> tuple[str, str]:
    for enc in ("utf-8-sig", "cp1250", "iso-8859-2"):
        try:
            return data.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace"), "utf-8 (s greskama)"


def _frame(rows: list[list[str]]) -> pd.DataFrame:
    width = max((len(r) for r in rows), default=0)
    return pd.DataFrame([list(r) + [""] * (width - len(r)) for r in rows], dtype=str)


def _with_header(raw: pd.DataFrame) -> pd.DataFrame:
    """df = isti podaci, prvi redak kao zaglavlje (jedinstvena imena)."""
    if raw.empty:
        return raw.copy()
    names, seen = [], {}
    for i, v in enumerate(raw.iloc[0].tolist()):
        n = str(v).strip() or f"Unnamed_{i}"
        if n in seen:
            seen[n] += 1
            n = f"{n}.{seen[n]}"
        else:
            seen[n] = 0
        names.append(n)
    df = raw.iloc[1:].copy()
    df.columns = names
    return df.reset_index(drop=True)


def _table(name: str, raw: pd.DataFrame, header_in_raw: bool = True, **extra) -> dict:
    raw = raw.fillna("").astype(str)
    df = _with_header(raw) if header_in_raw else raw.copy()
    if not header_in_raw:
        raw = pd.concat([pd.DataFrame([list(raw.columns)], columns=raw.columns), raw], ignore_index=True)
        raw.columns = range(raw.shape[1])
    return {"name": name, "raw": raw, "df": df, "extra": extra}


def _trim(rows: list[list[str]]) -> list[list[str]]:
    while rows and not any(c.strip() for c in rows[-1]):
        rows.pop()
    width = max((max((i + 1 for i, c in enumerate(r) if c.strip()), default=0) for r in rows), default=0)
    return [r[:width] for r in rows]


def load_csv(data: bytes) -> list[dict]:
    text, enc = decode_text(data)
    lines = text.splitlines()
    sample = lines[:60]
    best, best_score = ",", -1.0
    for d in (";", ",", "\t", "|"):
        counts = [ln.count(d) for ln in sample if ln.strip()]
        if not counts or max(counts) == 0:
            continue
        med = statistics.median(counts)
        consistency = sum(1 for c in counts if c == med) / len(counts)
        score = med * consistency
        if score > best_score:
            best, best_score = d, score
    rows = list(csv.reader(io.StringIO(text), delimiter=best))
    widths = [len(r) for r in rows if any(c.strip() for c in r)]
    common = statistics.mode(widths) if widths else 0
    return [_table("csv", _frame(rows), encoding=enc, delimiter=best,
                   ragged_rows=sum(1 for w in widths if w != common),
                   suspicious_chars=len(MOJIBAKE.findall(text)))]


def load_xlsx(data: bytes) -> list[dict]:
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True)
    tables = []
    for ws in wb.worksheets:
        rows, colored = [], 0
        for r_i, row in enumerate(ws.iter_rows()):
            vals = []
            for c in row:
                vals.append("" if c.value is None else str(c.value))
                if r_i < 3000 and c.fill is not None and c.fill.fill_type == "solid":
                    rgb = getattr(c.fill.fgColor, "rgb", None)
                    if isinstance(rgb, str) and rgb not in ("00000000", "FFFFFFFF"):
                        colored += 1
            rows.append(vals)
        rows = _trim(rows)
        tables.append(_table(ws.title, _frame(rows), merged_cells=len(ws.merged_cells.ranges),
                             colored_cells=colored))
    return tables


def load_xls(data: bytes) -> list[dict]:
    sheets = pd.read_excel(io.BytesIO(data), sheet_name=None, header=None, dtype=str, engine="xlrd")
    return [_table(name, df.fillna("")) for name, df in sheets.items()]


def _records(obj, path="$"):
    """Najveca lista objekata u JSON-u (do dubine 3)."""
    best = (path, obj) if isinstance(obj, list) and obj and isinstance(obj[0], dict) else (None, [])
    if isinstance(obj, dict):
        for k, v in obj.items():
            p, r = _records(v, f"{path}.{k}") if isinstance(v, (dict, list)) and path.count(".") < 3 else (None, [])
            if len(r) > len(best[1]):
                best = (p, r)
    return best


def _flat_frame(records: list[dict]) -> pd.DataFrame:
    df = pd.json_normalize(records, max_level=1)
    for c in df.columns:
        df[c] = df[c].map(lambda v: "" if v is None or (isinstance(v, float) and pd.isna(v))
                          else json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else str(v))
    return df


def load_json(data: bytes) -> list[dict]:
    text, enc = decode_text(data)
    obj = json.loads(text)
    path, recs = _records(obj)
    sample = json.dumps(recs[0] if recs else obj, ensure_ascii=False, indent=1)
    top = (f"lista ({len(obj)} elemenata)" if isinstance(obj, list)
           else f"objekt s kljucevima {list(obj)[:15]}" if isinstance(obj, dict) else type(obj).__name__)
    df = _flat_frame(recs) if recs else pd.DataFrame()
    return [_table("json", df, header_in_raw=False, encoding=enc, json_top=top, records_path=path,
                   sample_record=clip(sample, 1200), suspicious_chars=len(MOJIBAKE.findall(text)))]


def load_geojson(data: bytes) -> list[dict]:
    text, enc = decode_text(data)
    obj = json.loads(text)
    feats = obj.get("features", [])
    df = _flat_frame([f.get("properties") or {} for f in feats])
    df["_geometry_type"] = [str((f.get("geometry") or {}).get("type", "")) for f in feats]
    df["_coords"] = [short(json.dumps((f.get("geometry") or {}).get("coordinates")), 80) for f in feats]
    return [_table("geojson", df, header_in_raw=False, encoding=enc, features=len(feats))]


def load_xml(data: bytes) -> list[dict]:
    from lxml import etree
    root = etree.fromstring(data, parser=etree.XMLParser(recover=True, huge_tree=True))
    if root is None:
        raise ResourceError("XML se ne moze parsirati")
    local = lambda el: etree.QName(el).localname if isinstance(el.tag, str) else ""
    counts = {}
    for el in root.iter():
        if el is not root and isinstance(el.tag, str) and len(el):
            counts[local(el)] = counts.get(local(el), 0) + 1
    if not counts:
        raise ResourceError("XML nema ponavljajucih zapisa")
    tag = max(counts, key=counts.get)
    recs = []
    for el in root.iter():
        if isinstance(el.tag, str) and local(el) == tag:
            rec = {f"@{k}": v for k, v in el.attrib.items()}
            for d in el.iter():
                if d is el or not isinstance(d.tag, str):
                    continue
                key = local(d)
                if d.text and d.text.strip():
                    k2, i = key, 1
                    while k2 in rec:
                        i += 1
                        k2 = f"{key}.{i}"
                    rec[k2] = d.text.strip()
                for ak, av in d.attrib.items():
                    rec[f"{key}@{ak}"] = av
            recs.append(rec)
    df = pd.DataFrame(recs).fillna("").astype(str)
    return [_table("xml", df, header_in_raw=False, root=local(root), record_tag=tag)]


LOADERS = {"csv": load_csv, "xlsx": load_xlsx, "xls": load_xls, "json": load_json,
           "geojson": load_geojson, "xml": load_xml}


class ResourceStore:
    """Ucitani resursi jednog paketa (u memoriji tijekom analize)."""

    def __init__(self, resources: list[dict]):
        self.resources = {r["resource_id"]: r for r in resources}
        self.loaded: dict[str, dict] = {}
        self.any_loaded = False

    def get(self, rid: str) -> dict:
        if rid not in self.resources:
            raise ResourceError(f"nepoznat resourceId {rid}")
        if rid in self.loaded:
            if "error" in self.loaded[rid]:
                raise ResourceError(self.loaded[rid]["error"])
            return self.loaded[rid]
        try:
            data, meta = download(self.resources[rid])
            kind = sniff(data)
            if kind not in LOADERS:
                raise ResourceError(f"format '{kind}' nije podrzan za citanje (deklarirano: "
                                    f"{self.resources[rid]['format']}); potrazi iste podatke u drugom resursu")
            entry = {"meta": meta, "kind": kind, "data": data, "tables": LOADERS[kind](data)}
        except ResourceError as e:
            self.loaded[rid] = {"error": str(e)}
            raise
        except Exception as e:
            self.loaded[rid] = {"error": f"citanje nije uspjelo: {type(e).__name__}: {e}"}
            raise ResourceError(self.loaded[rid]["error"])
        self.loaded[rid] = entry
        self.any_loaded = True
        return entry

    def table(self, rid: str, sheet: str | None) -> dict:
        tables = self.get(rid)["tables"]
        if not sheet:
            return tables[0]
        for t in tables:
            if t["name"] == sheet:
                return t
        raise ResourceError(f"nema lista/tablice '{sheet}'; postoje: {[t['name'] for t in tables]}")


# ---------- alati ----------

def tool_profile(store: ResourceStore, rid: str) -> str:
    e = store.get(rid)
    r, m = store.resources[rid], e["meta"]
    out = [f"RESURS {rid} | deklarirano: {r['format']} | prepoznato: {e['kind']} | "
           f"{m['size'] / 1024:.0f} KB | dohvaceno {m['fetched_at']}"]
    for t in e["tables"]:
        raw, df, x = t["raw"], t["df"], t["extra"]
        info = " | ".join(f"{k}: {v}" for k, v in x.items() if k != "sample_record")
        out.append(f"\nTABLICA '{t['name']}': {len(df)} redaka podataka x {df.shape[1]} stupaca"
                   + (f" | {info}" if info else ""))
        if "sample_record" in x:
            out.append(f"PRVI ZAPIS:\n{x['sample_record']}")
        out.append("PRVIH 6 REDAKA (sirovo, r0 = pretpostavljeno zaglavlje):")
        for i in range(min(6, len(raw))):
            out.append(f" r{i}: " + " | ".join(short(v, 40) for v in raw.iloc[i].tolist()[:25]))
        if len(raw) > 8:
            out.append("ZADNJA 2 RETKA:")
            for i in range(len(raw) - 2, len(raw)):
                out.append(f" r{i}: " + " | ".join(short(v, 40) for v in raw.iloc[i].tolist()[:25]))
        out.append("STUPCI (ime [neprazno/ukupno, jedinstvenih] primjeri):")
        for c in list(df.columns)[:40]:
            col = df[c].astype(str)
            filled = col[col.str.strip() != ""]
            ex = ", ".join(repr(short(v, 30)) for v in filled.unique()[:3])
            out.append(f" - {short(c, 50)} [{len(filled)}/{len(col)}, {filled.nunique()}] {ex}")
        if df.shape[1] > 40:
            out.append(f" ... jos {df.shape[1] - 40} stupaca")
    return clip("\n".join(out), 5000)


def tool_raw_lines(store: ResourceStore, rid: str, start: int, count: int, sheet: str | None) -> str:
    e = store.get(rid)
    count = max(1, min(int(count), 40))
    start = max(0, int(start))
    if e["kind"] in ("xlsx", "xls"):
        raw = store.table(rid, sheet)["raw"]
        lines = [f"r{i}: " + " | ".join(short(v, 50) for v in raw.iloc[i].tolist()[:30])
                 for i in range(start, min(start + count, len(raw)))]
        return clip("\n".join(lines) or "(nema redaka u tom rasponu)") + f"\n[ukupno redaka: {len(raw)}]"
    text, _ = decode_text(e["data"])
    lines = text.splitlines()
    if len(lines) < 5 and len(text) > 3000:  # minificirani JSON/XML -> lijepo formatiranje
        try:
            text = json.dumps(json.loads(text), ensure_ascii=False, indent=1)
        except Exception:
            from lxml import etree
            try:
                text = etree.tostring(etree.fromstring(e["data"]), pretty_print=True).decode("utf-8", "replace")
            except Exception:
                pass
        lines = text.splitlines()
    sel = [f"{i}: {short(ln, 300)}" for i, ln in enumerate(lines[start:start + count], start)]
    return clip("\n".join(sel) or "(nema linija u tom rasponu)") + f"\n[ukupno linija: {len(lines)}]"


def tool_search(store: ResourceStore, rid: str, text: str, column: str | None, sheet: str | None) -> str:
    e = store.get(rid)
    q = norm(text)
    if not q:
        return "prazan upit"
    tables = [store.table(rid, sheet)] if sheet else e["tables"]
    out = []
    for t in tables:
        df = t["df"]
        cols = [c for c in df.columns if (not column or norm(column) in norm(c))]
        if column and not cols:
            out.append(f"[{t['name']}] nema stupca slicnog '{column}'. Stupci: {[short(c, 30) for c in df.columns][:30]}")
            continue
        header_hits = [c for c in df.columns if q in norm(c)]
        if header_hits:
            out.append(f"[{t['name']}] u NAZIVIMA stupaca: {header_hits[:10]}")
        hits = []
        for c in cols:
            col = df[c].astype(str)
            mask = col.map(lambda v: q in norm(v))
            for idx in col[mask].index[:20]:
                hits.append((idx, c, col[idx]))
        if hits:
            out.append(f"[{t['name']}] tocnih pogodaka (podniz, bez obzira na dijakritike): {len(hits)}"
                       + (" (prikazano do 15)" if len(hits) > 15 else ""))
            out += [f"  redak {i} | {short(c, 30)} = {short(v, 120)}" for i, c, v in hits[:15]]
            continue
        # nema tocnih - fuzzy po jedinstvenim vrijednostima
        uniq = {}
        for c in cols:
            for idx, v in df[c].astype(str).items():
                if v.strip() and len(v) <= 300 and len(uniq) < 20000 and v not in uniq:
                    uniq[v] = (idx, c)
        q_tok = q.split()
        scored = []
        for v, (idx, c) in uniq.items():
            nv = norm(v)
            best = difflib.SequenceMatcher(None, q, nv).ratio()
            toks = nv.split()
            if len(toks) > len(q_tok):
                for k in range(len(toks) - len(q_tok) + 1):
                    w = " ".join(toks[k:k + len(q_tok)])
                    best = max(best, difflib.SequenceMatcher(None, q, w).ratio())
            if best >= 0.7:
                scored.append((best, idx, c, v))
        scored.sort(reverse=True)
        if scored:
            out.append(f"[{t['name']}] nema tocnih pogodaka; najslicnije vrijednosti:")
            out += [f"  {s:.2f} | redak {i} | {short(c, 30)} = {short(v, 120)}" for s, i, c, v in scored[:12]]
        else:
            out.append(f"[{t['name']}] nema tocnih ni slicnih pogodaka (prag slicnosti 0.70)")
    out.append("(redak N = indeks u df, tj. sirovi redak N+1 ako je r0 zaglavlje)")
    return clip("\n".join(out))


# --- ograniceni pandas izrazi ---

_FORBIDDEN_NAMES = {"open", "exec", "eval", "compile", "__import__", "globals", "locals", "vars", "getattr",
                    "setattr", "delattr", "input", "breakpoint", "exit", "quit", "help", "os", "sys",
                    "subprocess", "shutil", "pathlib", "builtins", "importlib", "type", "object", "memoryview"}
_ALLOWED_TO = {"to_string", "to_dict", "to_list", "to_numeric", "to_datetime", "to_frame", "to_records"}
_SAFE_BUILTINS = {n: getattr(builtins, n)
                  for n in ("len", "min", "max", "sum", "sorted", "set", "list", "dict", "tuple", "str", "int",
                            "float", "bool", "range", "enumerate", "zip", "any", "all", "abs", "round",
                            "isinstance", "map", "filter", "repr", "reversed")}


def _check_code(code: str) -> ast.Module:
    tree = ast.parse(code, mode="exec")
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal, ast.With, ast.AsyncWith,
                             ast.Delete)):
            raise ResourceError(f"nedopustena naredba: {type(node).__name__}")
        if isinstance(node, ast.Attribute):
            a = node.attr
            if a.startswith("_") or a.startswith("read_") or (a.startswith("to_") and a not in _ALLOWED_TO):
                raise ResourceError(f"nedopusten atribut: {a}")
        if isinstance(node, ast.Name) and (node.id in _FORBIDDEN_NAMES or node.id.startswith("__")):
            raise ResourceError(f"nedopusteno ime: {node.id}")
    return tree


def _render(v) -> str:
    if isinstance(v, pd.DataFrame):
        return v.to_string(max_rows=30, max_cols=15, max_colwidth=60)
    if isinstance(v, pd.Series):
        return v.to_string(max_rows=40)
    return repr(v)


def tool_query(store: ResourceStore, rid: str, code: str, sheet: str | None) -> str:
    t = store.table(rid, sheet)
    tree = _check_code(code)
    ns = {"__builtins__": _SAFE_BUILTINS, "df": t["df"].copy(), "raw": t["raw"].copy(), "pd": pd, "re": re}
    last = tree.body.pop() if tree.body and isinstance(tree.body[-1], ast.Expr) else None
    result = {}

    def run():
        try:
            if tree.body:
                exec(compile(tree, "<upit>", "exec"), ns)
            result["value"] = eval(compile(ast.Expression(last.value), "<upit>", "eval"), ns) if last else "(nema izraza za ispis; zadnja linija treba biti izraz)"
        except Exception as e:
            result["error"] = f"{type(e).__name__}: {e}"

    th = threading.Thread(target=run, daemon=True)
    th.start()
    th.join(QUERY_TIMEOUT)
    if th.is_alive():
        return f"GRESKA: upit traje dulje od {QUERY_TIMEOUT}s"
    if "error" in result:
        return f"GRESKA: {result['error']}"
    return clip(_render(result["value"]), 3000)


def tool_check_url(store: ResourceStore, rid: str) -> str:
    r = store.resources[rid]
    try:
        _, m = download(r)
    except ResourceError as e:
        return f"NEDOSTUPNO: {e}"
    login = "login" in m["final_url"].lower() or "prijava" in m["final_url"].lower()
    return (f"HTTP {m['status']} | content-type: {m['content_type']} | {m['size']} B | konacni URL: {m['final_url']}"
            + (" | PREUSMJERENO NA PRIJAVU" if login else ""))


def tool_package_metadata(package_id: str) -> str:
    url = f"https://data.gov.hr/ckan/api/3/action/package_show?id={package_id}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        d = json.loads(urllib.request.urlopen(req, timeout=60).read())["result"]
    except Exception as e:
        return f"GRESKA pri dohvatu metapodataka: {e}"
    keep = ["title", "license_title", "metadata_created", "metadata_modified", "data_refresh_frequency",
            "openess", "author", "maintainer", "version", "url", "theme", "access_rights"]
    out = [f"{k}: {short(d.get(k), 200)}" for k in keep if d.get(k) not in (None, "", [])]
    out.append(f"organization: {(d.get('organization') or {}).get('title')}")
    out.append(f"tags: {[t.get('name') for t in d.get('tags', [])][:20]}")
    for ex in d.get("extras", [])[:20]:
        out.append(f"extra {ex.get('key')}: {short(ex.get('value'), 150)}")
    out.append(f"notes (opis): {short(d.get('notes') or '', 1500)}")
    out.append("RESURSI:")
    for r in d.get("resources", []):
        out.append(f" - {r.get('id')} | {r.get('format')} | {short(r.get('name') or '', 80)} | "
                   f"opis: {short(r.get('description') or '', 150)} | last_modified: {r.get('last_modified')} | "
                   f"url: {short(r.get('url') or '', 120)}")
    return clip("\n".join(out), 5000)
