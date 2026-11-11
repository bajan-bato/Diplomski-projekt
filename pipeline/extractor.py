"""Extractor: suggestion -> lista kratkih, provjerljivih ISSUE natuknica (Claude Sonnet 5.5).

Za svaki suggestion:
  - ocisti HTML, doda kontekst paketa, popis resursa i vec postojece natuknice tog paketa
  - model vrati strukturirani JSON (valid, ignore_reason, issues[], skipped_duplicates[])
  - u bazu ide ISSUE (human readable) + ISSUE_CHECK (za agenta) + PIPELINE_STATE (cache)

Dva nacina rada:
  - extract()        sinkrono, jedan po jedan (za male skupove i testiranje)
  - extract_batch()  Batch API (50% jeftinije) za puni sken; suggestioni se salju u rundama
                     (1. suggestion svakog paketa, pa 2., ...) da deduplikacija vidi ranije natuknice
"""
import hashlib
import json
import time
from collections import defaultdict
from datetime import datetime

import anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request

from . import config, db
from .textclean import html_to_text

CATEGORIES = ["data_content", "structure", "encoding", "metadata", "availability", "feature_request"]

SYSTEM_PROMPT = """Ti si analiticar kvalitete otvorenih podataka s portala data.gov.hr.

Dobivas jedan korisnicki prijedlog (suggestion) za jedan skup podataka (paket), opis paketa, popis datoteka (resursa) u paketu i, ako postoje, natuknice koje su vec izvucene iz ranijih prijedloga za isti paket. Tvoj zadatak je pretvoriti prijedlog u popis zasebnih, provjerljivih problema (ISSUE) u podacima.

Te natuknice kasnije cita automatski agent koji otvara datoteke paketa i odlucuje je li problem JOS UVIJEK prisutan ili je rijesen. Agent NE vidi originalni prijedlog, nego samo tvoje natuknice. Zato svaka natuknica mora sama za sebe biti jasna i sadrzavati sve konkretne podatke iz prijedloga.

PRAVILA

1. Nevaljan prijedlog: postavi valid=false, issues=[] i u ignore_reason kratko napisi zasto, ako je prijedlog:
   - test, spam, prazan ili besmislen tekst
   - samo pohvala ili opci komentar bez ikakvog zahtjeva za promjenom
   - toliko opcenit da se iz njega ne moze izvuci nista konkretno (npr. "poboljsati podatke", "Prijedlog")
   Ako barem dio prijedloga sadrzi konkretan zahtjev, prijedlog je valjan (valid=true, ignore_reason="").

2. Jedna natuknica = jedan problem. Slozene prijedloge razbij na vise natuknica. Ne izmisljaj probleme koji nisu u prijedlogu.
   - Ako se ISTI problem pojavljuje u vise datoteka istog paketa (npr. isti podaci u CSV, JSON i XML, ili ista greska u dvije tablice), napisi JEDNU natuknicu i u target_resources navedi sve te datoteke.
   - Dvije natuknice smiju se odnositi na iste podatke samo ako traze RAZLICITE izmjene.
   - Zahtjevi za novim sadrzajem (novi stupac, novi format, API) su valjani - zadrzi ih.
   - Subjektivne zelje (npr. preimenovati stupac, drugaciji format datuma, maknuti godinu iz datuma) zadrzi ako traze konkretnu izmjenu; izostavi samo zelje bez ikakve konkretne izmjene.

3. text (hrvatski, imperativ, najvise 200 znakova): STO treba ispraviti i GDJE (naziv ili format datoteke, stupac, redak, vrijednost). Doslovno prenesi konkretne vrijednosti iz prijedloga (nazive stupaca, krive i ispravne vrijednosti, primjere).
   Primjer: "Obrisati suvisan redak 'Col1 Col2 Col3' iznad zaglavlja u XLSX 'Proracun 2024'"
   Primjer: "Ispraviti adresu crkve Sv. Petar u Sumi iz 'Glavna 1' u 'Glavna 2' u CSV 'Sakralni objekti'"

4. category, tocno jedna od:
   - data_content: krive, nedostajuce ili nedosljedne vrijednosti u samim podacima (redovi, celije)
   - structure: struktura tablice/datoteke (zaglavlja, suvisni redovi/stupci, spojene celije, nazivi stupaca, vise informacija u jednom stupcu, formati datuma)
   - encoding: krivi znakovi, kodiranje (npr. hrvatska slova), separator, decimalni zarez
   - metadata: metapodaci na portalu (opis, licenca, datum azuriranja, ocjena otvorenosti, autor, rjecnik podataka)
   - availability: datoteka/link ne radi, nije strojno citljiva, krivi format datoteke, pristup trazi prijavu
   - feature_request: zahtjev za NOVIM sadrzajem (novi stupac, novi format datoteke, novi podaci, API)

5. specific. Pitaj se: moze li agent iz natuknice i podataka pouzdano odluciti postoji li problem, bez vanjskog znanja?
   Agent pretrazuje podatke i nepreciznim (fuzzy) trazenjem, pa stupac, zapis ili entitet NE mora biti naveden doslovno tocno - dovoljno je da se moze prepoznati (npr. "stupac s adresom", "klub Dugopolje", "redak s generickim nazivima stupaca iznad zaglavlja", "telefonski brojevi skola").
   specific=true ako se moze prepoznati O CEMU se radi (stupac/atribut, zapis, entitet ili datoteka) I ako je poznato kakvo je ciljano stanje (ispravna vrijednost, trazeni format, sto treba ukloniti, razdvojiti ili dodati) ili je problem mjerljiv u podacima (npr. "stupac X je prazan u svim recima", "iznad zaglavlja postoji redak 'Stupac1 Stupac2'", "pruga R103 nedostaje u popisu", "telefonski brojevi su zapisani u razlicitim formatima").
   specific=false ako vrijedi BILO STO od:
   - ispravna ili ciljana vrijednost nije navedena, a bez nje se ne moze odluciti (npr. "ispraviti adresu, ispravna nije navedena", "ispraviti krivu vrijednost")
   - nikako se ne moze prepoznati koji zapisi, stupci ili datoteke (npr. "neki podaci su krivi", "neki retci nemaju sve atribute" bez ikakvog traga koji)
   - odluka ovisi o vanjskom znanju kojeg nema u podacima (npr. "podaci su zastarjeli", "klub vise ne postoji", "podaci su javno dostupni drugdje")
   - zahtjev je opcenit (npr. "dopuniti metapodatke", "poboljsati opis" bez ikakve naznake sto tocno)

6. check: uputa za agenta, tocno u ovom obliku:
   "PROVJERI: <sto otvoriti i gledati> | POSTOJI AKO: <stanje koje znaci da problem jos postoji> | RIJESENO AKO: <stanje koje znaci da je rijeseno>"
   Budi konkretan (nazivi stupaca, vrijednosti, uzorak). Ako je specific=false, svejedno napisi najbolju mogucu uputu.

7. target_resources: resourceId-jevi iz popisa resursa na koje se natuknica odnosi. Prazna lista ako se odnosi na sve tablicne datoteke, ako nije jasno na koju, ili ako je category=metadata.

8. Oznaka [slika] znaci da je korisnik prilozio sliku koju ne vidis. Ne nagadaj sto je na njoj.

9. Prijedlog moze biti star; opisi problem kako ga je korisnik opisao, agent ce provjeriti trenutno stanje.

10. Duplikati s ranijim prijedlozima: ako je dan popis POSTOJECIH NATUKNICA za ovaj paket, NE stvaraj natuknicu koja trazi istu izmjenu na istim podacima kao postojeca - umjesto toga upisi njen ID u skipped_duplicates. Ako novi prijedlog dodaje konkretne detalje koje postojeca natuknica nema (npr. ispravnu vrijednost ili tocan stupac), napisi novu natuknicu s tim detaljima. Ako su sve izmjene iz prijedloga vec pokrivene, prijedlog je i dalje valjan, issues=[], a svi ID-jevi su u skipped_duplicates.
"""

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "valid": {"type": "boolean"},
        "ignore_reason": {"type": "string"},
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "category": {"type": "string", "enum": CATEGORIES},
                    "specific": {"type": "boolean"},
                    "check": {"type": "string"},
                    "target_resources": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["text", "category", "specific", "check", "target_resources"],
                "additionalProperties": False,
            },
        },
        "skipped_duplicates": {"type": "array", "items": {"type": "integer"}},
    },
    "required": ["valid", "ignore_reason", "issues", "skipped_duplicates"],
    "additionalProperties": False,
}

PACKAGE_DESC_MAX = 3000
MAX_TOKENS = 16000
BATCH_POLL_SECONDS = 60
BATCH_STATE = config.OUTPUT_DIR / "batch_pending.json"


class ExtractionError(Exception):
    pass


# ---------- priprema ulaza ----------

def content_hash(package_id: str, title: str, text: str) -> str:
    return hashlib.sha256(f"{package_id}\x1f{title}\x1f{text}".encode("utf-8")).hexdigest()


def load_suggestion(suggestion_id: int) -> dict | None:
    found = db.rows(
        """SELECT s.suggestionId AS suggestion_id, s.title AS title, s.text AS text,
                  s.datetime AS datetime, s.packageId AS package_id,
                  p.title AS package_title, p.description AS package_description
           FROM SUGGESTION s JOIN PACKAGE p ON p.packageId = s.packageId
           WHERE s.suggestionId = :sid""",
        sid=suggestion_id,
    )
    if not found:
        return None
    s = found[0]
    s["resources"] = db.rows(
        """SELECT resourceId AS resource_id, format AS format, name AS name
           FROM RESOURCE WHERE packageId = :pid ORDER BY resourceId""",
        pid=s["package_id"],
    )
    s["clean_text"] = html_to_text(s["text"])
    s["content_hash"] = content_hash(s["package_id"], s["title"], s["text"])
    return s


def existing_issues(s: dict) -> list[dict]:
    """Natuknice istog paketa iz DRUGIH suggestiona (za deduplikaciju)."""
    return db.rows(
        """SELECT i.issueId AS issue_id, i.text AS text
           FROM ISSUE i JOIN SUGGESTION s ON s.suggestionId = i.suggestionId
           WHERE s.packageId = :pid AND i.suggestionId <> :sid
           ORDER BY i.issueId""",
        pid=s["package_id"], sid=s["suggestion_id"],
    )


def build_user_message(s: dict, existing: list[dict]) -> str:
    desc = html_to_text(s["package_description"] or "")
    if len(desc) > PACKAGE_DESC_MAX:
        desc = desc[:PACKAGE_DESC_MAX] + " ...(opis paketa skracen)"
    res_lines = "\n".join(
        f"- {r['resource_id']} | {(r['format'] or '?').strip().upper()} | {r['name'] or '(bez naziva)'}"
        for r in s["resources"]
    ) or "- (paket nema resursa)"
    ex_lines = "\n".join(f"- [{e['issue_id']}] {e['text']}" for e in existing) or "- (nema)"
    return (
        f"PAKET: {s['package_title']}\n"
        f"OPIS PAKETA: {desc or '(nema opisa)'}\n\n"
        f"RESURSI (resourceId | format | naziv):\n{res_lines}\n\n"
        f"POSTOJECE NATUKNICE ZA OVAJ PAKET (iz ranijih prijedloga):\n{ex_lines}\n\n"
        f"PRIJEDLOG (datum: {s['datetime']}):\n"
        f"Naslov: {s['title']}\n"
        f"Tekst:\n{s['clean_text']}"
    )


def request_params(s: dict, existing: list[dict]) -> dict:
    """Parametri poziva - isti za sinkroni i Batch nacin."""
    return {
        "model": config.EXTRACTOR_MODEL,
        "max_tokens": MAX_TOKENS,
        "system": [{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        "output_config": {
            "effort": config.EXTRACTOR_EFFORT,
            "format": {"type": "json_schema", "schema": OUTPUT_SCHEMA},
        },
        "messages": [{"role": "user", "content": build_user_message(s, existing)}],
    }


def estimate_cost(suggestions: list[dict], batch: bool = False) -> dict:
    """Gruba procjena prije pokretanja (hrvatski tekst ~3 znaka po tokenu)."""
    p_in, p_out = config.PRICES[config.EXTRACTOR_MODEL]
    sys_tokens = len(SYSTEM_PROMPT) / 3
    in_tokens = sum(sys_tokens + len(build_user_message(s, [])) / 3 + 150 for s in suggestions)
    out_tokens = len(suggestions) * 2000  # natuknice + adaptive thinking (gornja procjena)
    usd = in_tokens / 1e6 * p_in + out_tokens / 1e6 * p_out
    return {"suggestions": len(suggestions), "input_tokens": int(in_tokens),
            "output_tokens": int(out_tokens), "usd": usd * (0.5 if batch else 1.0)}


# ---------- obrada odgovora ----------

def parse_message(message) -> dict:
    if message.stop_reason == "refusal":
        raise ExtractionError(f"model je odbio zahtjev ({getattr(message.stop_details, 'category', None)})")
    if message.stop_reason == "max_tokens":
        raise ExtractionError("odgovor odrezan (max_tokens)")
    text = next((b.text for b in message.content if b.type == "text"), None)
    if not text:
        raise ExtractionError("odgovor nema tekstualni blok")
    return json.loads(text)


def usage_cost(message, batch: bool = False) -> float:
    u = message.usage
    p_in, p_out = config.PRICES.get(message.model, config.PRICES[config.EXTRACTOR_MODEL])
    cache_write = getattr(u, "cache_creation_input_tokens", 0) or 0
    cache_read = getattr(u, "cache_read_input_tokens", 0) or 0
    cost = (u.input_tokens * p_in + cache_write * p_in * 1.25 + cache_read * p_in * 0.1
            + u.output_tokens * p_out) / 1e6
    return cost * (0.5 if batch else 1.0)


def normalize(result: dict, s: dict, existing: list[dict]) -> dict:
    """Validacija izlaza modela: poznati resourceId-jevi i ID-jevi duplikata, duljina teksta."""
    valid_res = {r["resource_id"] for r in s["resources"]}
    valid_dup = {e["issue_id"] for e in existing}
    issues = []
    for it in result.get("issues", []) if result.get("valid") else []:
        text = " ".join(it["text"].split())
        if not text:
            continue
        if len(text) > config.ISSUE_TEXT_MAX:
            text = text[: config.ISSUE_TEXT_MAX - 1] + "…"
        issues.append({
            "text": text,
            "category": it["category"],
            "specific": bool(it["specific"]),
            "check": it["check"].strip(),
            "target_resources": [r for r in it["target_resources"] if r in valid_res],
        })
    dups = sorted({d for d in result.get("skipped_duplicates", []) if d in valid_dup})
    valid = bool(result.get("valid")) and bool(issues)
    reason = result.get("ignore_reason", "").strip()
    if result.get("valid") and not issues:
        reason = (f"sve izmjene vec pokrivene postojecim natuknicama {dups}" if dups
                  else reason or "model nije izdvojio nijednu provjerljivu natuknicu")
    return {"valid": valid, "ignore_reason": "" if valid else reason, "issues": issues,
            "skipped_duplicates": dups}


def already_processed(content_hash_: str) -> bool:
    return bool(db.scalar("SELECT COUNT(*) FROM PIPELINE_STATE WHERE contentHash = :h", h=content_hash_))


def clear_previous(suggestion_id: int, content_hash_: str) -> None:
    """Za --force: brise stare natuknice tog suggestiona (samo ako jos nemaju REVIEW)."""
    with db.transaction() as conn:
        reviewed = db.execute(
            conn,
            """SELECT COUNT(*) FROM REVIEW r JOIN ISSUE i ON i.issueId = r.issueId
               WHERE i.suggestionId = :sid""",
            sid=suggestion_id,
        ).scalar()
        if reviewed:
            raise ExtractionError("natuknice vec imaju REVIEW; --force ih ne smije brisati")
        db.execute(conn, "DELETE FROM ISSUE_CHECK WHERE issueId IN "
                         "(SELECT issueId FROM ISSUE WHERE suggestionId = :sid)", sid=suggestion_id)
        db.execute(conn, "DELETE FROM ISSUE WHERE suggestionId = :sid", sid=suggestion_id)
        db.execute(conn, "DELETE FROM PIPELINE_STATE WHERE contentHash = :h", h=content_hash_)


def save(s: dict, result: dict, model_used: str) -> list[int]:
    issue_ids = []
    with db.transaction() as conn:
        for it in result["issues"]:
            iid = db.next_id(conn, "ISSUE", "issueId")
            db.execute(conn, "INSERT INTO ISSUE(issueId, text, suggestionId) VALUES (:i, :t, :s)",
                       i=iid, t=it["text"], s=s["suggestion_id"])
            db.execute(conn,
                       """INSERT INTO ISSUE_CHECK(issueId, category, specific, checkInstruction, targetResources)
                          VALUES (:i, :c, :sp, :ch, :tr)""",
                       i=iid, c=it["category"], sp=int(it["specific"]), ch=it["check"],
                       tr=json.dumps(it["target_resources"]))
            issue_ids.append(iid)
        db.execute(conn,
                   """INSERT INTO PIPELINE_STATE(contentHash, suggestionId, processedAt, ignored, ignoreReason, model)
                      VALUES (:h, :s, :t, :ig, :r, :m)""",
                   h=s["content_hash"], s=s["suggestion_id"], t=datetime.now().replace(microsecond=0),
                   ig=int(not result["valid"]), r=result["ignore_reason"] or None, m=model_used)
    return issue_ids


def handle_message(s: dict, existing: list[dict], message, batch: bool) -> dict:
    """Zajednicko za sinkroni i Batch nacin: parsiraj, validiraj, spremi, vrati zapis za izvjestaj."""
    result = normalize(parse_message(message), s, existing)
    issue_ids = save(s, result, message.model)
    return {"suggestion": s, "result": result, "issue_ids": issue_ids, "model": message.model,
            "usage": message.usage.to_dict(), "cost": usage_cost(message, batch)}


def describe(rec: dict) -> str:
    res = rec["result"]
    status = f"{len(rec['issue_ids'])} natuknica" if res["valid"] else f"IGNORIRAN ({res['ignore_reason']})"
    if res["skipped_duplicates"] and res["valid"]:
        status += f", preskoceni duplikati {res['skipped_duplicates']}"
    return f"{status} | ${rec['cost']:.4f}"


def prepare(suggestion_ids: list[int], force: bool, log) -> list[dict]:
    todo = []
    for sid in suggestion_ids:
        s = load_suggestion(sid)
        if s is None:
            log(f"{sid}: ne postoji u bazi (ili mu paket nedostaje), preskacem")
            continue
        if already_processed(s["content_hash"]):
            if not force:
                log(f"{sid}: vec obraden, preskacem (koristi --force za ponovno)")
                continue
            clear_previous(sid, s["content_hash"])
        todo.append(s)
    return todo


# ---------- sinkroni nacin ----------

def extract(suggestion_ids: list[int], force: bool = False, log=print) -> list[dict]:
    """Obradi zadane suggestione jedan po jedan. Vraca listu zapisa za izvjestaj."""
    client = anthropic.Anthropic()
    todo = prepare(suggestion_ids, force, log)
    records, total = [], 0.0
    for n, s in enumerate(todo, 1):
        existing = existing_issues(s)
        try:
            message = client.beta.messages.create(
                **request_params(s, existing),
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
            rec = handle_message(s, existing, message, batch=False)
        except (ExtractionError, anthropic.APIError, json.JSONDecodeError) as e:
            log(f"[{n}/{len(todo)}] {s['suggestion_id']}: GRESKA - {e}")
            records.append({"suggestion": s, "error": str(e)})
            continue
        total += rec["cost"]
        log(f"[{n}/{len(todo)}] {s['suggestion_id']}: {describe(rec)}")
        records.append(rec)
    log(f"Ukupni trosak: ${total:.4f}")
    return records


# ---------- Batch nacin ----------

def _rounds(todo: list[dict]) -> list[list[dict]]:
    """Runda k = k-ti (po datumu) suggestion svakog paketa."""
    by_pkg = defaultdict(list)
    for s in sorted(todo, key=lambda x: str(x["datetime"])):
        by_pkg[s["package_id"]].append(s)
    rounds = []
    for items in by_pkg.values():
        for k, s in enumerate(items):
            if len(rounds) <= k:
                rounds.append([])
            rounds[k].append(s)
    return rounds


def _wait_and_collect(client, batch_id: str, by_custom_id: dict, log) -> list[dict]:
    while True:
        b = client.messages.batches.retrieve(batch_id)
        if b.processing_status == "ended":
            break
        c = b.request_counts
        log(f"  batch {batch_id}: {b.processing_status} (obradeno {c.succeeded + c.errored}, "
            f"u obradi {c.processing})")
        time.sleep(BATCH_POLL_SECONDS)

    records = []
    for res in client.messages.batches.results(batch_id):
        s, existing = by_custom_id[res.custom_id]
        sid = s["suggestion_id"]
        if res.result.type != "succeeded":
            detail = getattr(getattr(res.result, "error", None), "type", "") or res.result.type
            log(f"  {sid}: GRESKA u batchu ({detail}) - bit ce ponovno poslan pri sljedecem pokretanju")
            records.append({"suggestion": s, "error": f"batch: {detail}"})
            continue
        try:
            rec = handle_message(s, existing, res.result.message, batch=True)
        except (ExtractionError, json.JSONDecodeError) as e:
            log(f"  {sid}: GRESKA - {e}")
            records.append({"suggestion": s, "error": str(e)})
            continue
        log(f"  {sid}: {describe(rec)}")
        records.append(rec)
    return records


def _resume_pending(client, log) -> list[dict]:
    """Ako je prethodno pokretanje prekinuto dok je batch bio u obradi, pokupi njegove rezultate."""
    if not BATCH_STATE.exists():
        return []
    state = json.loads(BATCH_STATE.read_text(encoding="utf-8"))
    log(f"Nastavljam prekinuti batch {state['batch_id']} ({len(state['ids'])} suggestiona)")
    by_custom_id = {}
    for sid in state["ids"]:
        s = load_suggestion(sid)
        if s and not already_processed(s["content_hash"]):
            by_custom_id[f"s{sid}"] = (s, state["existing"].get(str(sid), []))
    records = _wait_and_collect(client, state["batch_id"], by_custom_id, log)
    BATCH_STATE.unlink()
    return records


def extract_batch(suggestion_ids: list[int], force: bool = False, log=print) -> list[dict]:
    client = anthropic.Anthropic()
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    records = _resume_pending(client, log)
    todo = prepare(suggestion_ids, force, log)
    rounds = _rounds(todo)
    log(f"{len(todo)} suggestiona u {len(rounds)} rundi: {[len(r) for r in rounds]}")

    for k, round_items in enumerate(rounds, 1):
        by_custom_id, requests = {}, []
        for s in round_items:
            existing = existing_issues(s)  # ukljucuje natuknice iz prethodnih rundi
            by_custom_id[f"s{s['suggestion_id']}"] = (s, existing)
            requests.append(Request(custom_id=f"s{s['suggestion_id']}",
                                    params=MessageCreateParamsNonStreaming(**request_params(s, existing))))
        b = client.messages.batches.create(requests=requests)
        BATCH_STATE.write_text(json.dumps({
            "batch_id": b.id,
            "ids": [s["suggestion_id"] for s in round_items],
            "existing": {str(s["suggestion_id"]): ex for s, ex in by_custom_id.values()},
        }, ensure_ascii=False), encoding="utf-8")
        log(f"Runda {k}/{len(rounds)}: poslan batch {b.id} ({len(requests)} zahtjeva)")
        records += _wait_and_collect(client, b.id, by_custom_id, log)
        BATCH_STATE.unlink()

    total = sum(r.get("cost", 0) for r in records)
    log(f"Ukupni trosak (batch cijene): ${total:.4f}")
    return records


# ---------- reset ----------

def reset_all(log=print) -> None:
    """Brise sve rezultate extractora (ISSUE, ISSUE_CHECK, PIPELINE_STATE) - samo ako nema REVIEW-a."""
    with db.transaction() as conn:
        reviews = db.execute(conn, "SELECT COUNT(*) FROM REVIEW").scalar()
        if reviews:
            raise ExtractionError(f"u bazi postoji {reviews} REVIEW zapisa; reset bi ih ostavio bez natuknica")
        n_issues = db.execute(conn, "SELECT COUNT(*) FROM ISSUE").scalar()
        db.execute(conn, "DELETE FROM ISSUE_CHECK")
        db.execute(conn, "DELETE FROM ISSUE")
        db.execute(conn, "DELETE FROM PIPELINE_STATE")
    log(f"Obrisano {n_issues} natuknica i stanje extractora.")
