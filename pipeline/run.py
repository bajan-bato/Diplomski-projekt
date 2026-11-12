"""Ulazna tocka pipelinea.

Primjeri (iz korijena repoa):
  python -m pipeline.run sample --n 20                 # odabir reprezentativnog uzorka
  python -m pipeline.run extract --sample --dry-run    # procjena troska bez poziva API-ja
  python -m pipeline.run extract --sample              # extractor nad uzorkom
  python -m pipeline.run extract --ids 4064441 2839368 # extractor nad zadanim suggestionima
  python -m pipeline.run extract --all --limit 50      # jos neobradeni suggestioni
  python -m pipeline.run extract --all --batch         # puni sken preko Batch API-ja (50% jeftinije)
  python -m pipeline.run reset-extract --yes           # obrisi sve natuknice i kreni ispocetka
"""
import argparse
import sys
import warnings

# Bezopasna upozorenja biblioteka (regex u agentovim pandas upitima, Excel zaglavlja/podnozja) - samo zagaduju log
warnings.filterwarnings("ignore", message="This pattern is interpreted as a regular expression")
warnings.filterwarnings("ignore", message="Cannot parse header or footer")
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

from . import config, db, extractor, report, sample

SAMPLE_PATH = config.ROOT / "pipeline" / "sample_20.json"


def cmd_sample(args):
    chosen = sample.select(args.n, args.seed)
    sample.save(chosen, SAMPLE_PATH)
    print(f"Spremljeno {len(chosen)} suggestiona u {SAMPLE_PATH.relative_to(config.ROOT)}\n")
    print(f"{'id':>9}  {'format':9} {'duljina':10} {'god.':5} naslov")
    for c in chosen:
        print(f"{c['suggestion_id']:>9}  {c['fmt']:9} {c['len']:10} {c['year']:5} {c['title'][:60]}")


def cmd_extract(args):
    if args.sample:
        ids = sample.load(SAMPLE_PATH)
    elif args.ids:
        ids = args.ids
    else:
        done = {r["suggestion_id"] for r in db.rows("SELECT suggestionId AS suggestion_id FROM PIPELINE_STATE")}
        ids = [r["suggestion_id"] for r in db.rows(
            "SELECT suggestionId AS suggestion_id FROM SUGGESTION ORDER BY datetime")
            if r["suggestion_id"] not in done]
        if args.limit:
            ids = ids[: args.limit]

    suggestions = [s for s in (extractor.load_suggestion(i) for i in ids) if s]
    if not args.force:
        suggestions = [s for s in suggestions if not extractor.already_processed(s["content_hash"])]
    est = extractor.estimate_cost(suggestions, batch=args.batch)
    print(f"Model: {config.EXTRACTOR_MODEL} (effort {config.EXTRACTOR_EFFORT}) | "
          f"nacin: {'Batch API' if args.batch else 'sinkrono'} | baza: {config.DATABASE_URL}")
    print(f"Procjena: {est['suggestions']} suggestiona za obradu, ~{est['input_tokens']:,} ulaznih + "
          f"~{est['output_tokens']:,} izlaznih tokena = ~${est['usd']:.2f} (gornja granica)")
    if args.dry_run:
        return
    run = extractor.extract_batch if args.batch else extractor.extract
    records = run(ids, force=args.force)
    if records:
        path = report.write_extract_report(records)
        print(f"Izvjestaj: {path.relative_to(config.ROOT)}")


ANALYZE_SAMPLE_PATH = config.ROOT / "pipeline" / "analyze_sample_10.json"


def cmd_analyze_sample(args):
    chosen = sample.select_packages(args.n, args.seed)
    sample.save(chosen, ANALYZE_SAMPLE_PATH)
    print(f"Spremljeno {len(chosen)} paketa u {ANALYZE_SAMPLE_PATH.relative_to(config.ROOT)}\n")
    for c in chosen:
        print(f"{c['fmt']:9} {c['issues']:>3} natuknica  {c['title'][:70]}")


def cmd_analyze(args):
    from . import analyzer
    if args.sample:
        import json
        ids = [p["package_id"] for p in json.loads(ANALYZE_SAMPLE_PATH.read_text(encoding="utf-8"))]
    elif args.all:
        ids = analyzer.pending_packages()
        if args.limit:
            ids = ids[: args.limit]
    else:
        ids = args.packages
    n_issues = sum(db.scalar("""SELECT COUNT(*) FROM ISSUE i JOIN SUGGESTION s ON s.suggestionId = i.suggestionId
                                WHERE s.packageId = :p""", p=p) for p in ids)
    p_in, p_out = config.PRICES[config.ANALYZER_MODEL]
    turns = sum(1 for _ in ids) * 4 + n_issues * 2
    est = turns * 15000 / 1e6 * p_in + turns * 1500 / 1e6 * p_out
    print(f"Model: {config.ANALYZER_MODEL} (+ eskalacija {config.ESCALATION_MODEL}, najvise "
          f"{config.ESCALATION_MAX_PER_RUN if not args.no_escalation else 0}) | baza: {config.DATABASE_URL}")
    print(f"{len(ids)} paketa, {n_issues} natuknica | procjena Haiku: ~${est:.2f} (bez cachea, gornja granica) "
          f"+ eskalacije ~$0.05-0.10 po natuknici")
    if args.max_cost is not None:
        print(f"Limit troska za ovo pokretanje: ${args.max_cost:.2f}")
    if args.dry_run:
        return
    records = analyzer.analyze(ids, escalate=not args.no_escalation, max_cost=args.max_cost)
    if records:
        path = report.write_analyze_report(records)
        print(f"Izvjestaj: {path.relative_to(config.ROOT)}")


def cmd_reset(args):
    if not args.yes:
        print("Ovo brise SVE natuknice (ISSUE, ISSUE_CHECK) i stanje extractora (PIPELINE_STATE).")
        print("Pokreni ponovno s --yes ako si siguran.")
        return
    extractor.reset_all()


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="pipeline")
    sub = p.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("sample", help="odaberi reprezentativni uzorak suggestiona")
    ps.add_argument("--n", type=int, default=20)
    ps.add_argument("--seed", type=int, default=42)
    ps.set_defaults(func=cmd_sample)

    pe = sub.add_parser("extract", help="suggestion -> ISSUE natuknice")
    src = pe.add_mutually_exclusive_group(required=True)
    src.add_argument("--sample", action="store_true", help=f"koristi {SAMPLE_PATH.name}")
    src.add_argument("--ids", type=int, nargs="+")
    src.add_argument("--all", action="store_true", help="svi jos neobradeni")
    pe.add_argument("--limit", type=int)
    pe.add_argument("--force", action="store_true", help="ponovno obradi (brise stare natuknice bez REVIEW-a)")
    pe.add_argument("--dry-run", action="store_true", help="samo procjena troska")
    pe.add_argument("--batch", action="store_true", help="Batch API (50%% jeftinije, sporije) - za puni sken")
    pe.set_defaults(func=cmd_extract)

    pas = sub.add_parser("analyze-sample", help="odaberi reprezentativne pakete za test analize")
    pas.add_argument("--n", type=int, default=10)
    pas.add_argument("--seed", type=int, default=7)
    pas.set_defaults(func=cmd_analyze_sample)

    pa = sub.add_parser("analyze", help="provjeri jesu li natuknice paketa jos prisutne (ANALYSIS + REVIEW)")
    srcp = pa.add_mutually_exclusive_group(required=True)
    srcp.add_argument("--sample", action="store_true", help=f"koristi {ANALYZE_SAMPLE_PATH.name}")
    srcp.add_argument("--packages", nargs="+")
    srcp.add_argument("--all", action="store_true", help="svi paketi s jos neanaliziranim natuknicama")
    pa.add_argument("--limit", type=int, help="najvise N paketa (uz --all)")
    pa.add_argument("--max-cost", type=float, help="zaustavi kad trosak ovog pokretanja dosegne iznos ($)")
    pa.add_argument("--no-escalation", action="store_true")
    pa.add_argument("--dry-run", action="store_true")
    pa.set_defaults(func=cmd_analyze)

    pra = sub.add_parser("reset-analysis", help="obrisi sve ANALYSIS i REVIEW zapise (natuknice ostaju)")
    pra.add_argument("--yes", action="store_true")
    pra.set_defaults(func=lambda a: __import__("pipeline.analyzer", fromlist=["x"]).reset_all() if a.yes
                     else print("Ovo brise sve ANALYSIS i REVIEW zapise. Pokreni s --yes ako si siguran."))

    pr = sub.add_parser("reset-extract", help="obrisi sve natuknice i stanje extractora")
    pr.add_argument("--yes", action="store_true")
    pr.set_defaults(func=cmd_reset)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
