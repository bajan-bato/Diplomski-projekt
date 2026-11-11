"""Postavke pipelinea. Sve se moze nadjacati varijablama okoline (ili .env u korijenu repoa)."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    """Minimalni .env loader (KEY=VALUE po retku); postojece varijable okoline imaju prednost."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(ROOT / ".env")

# Lokalno: SQLite baza iz repoa. Na serveru: postgresql://user:pass@host/db
DATABASE_URL = os.environ.get("DATABASE_URL") or f"sqlite:///{(ROOT / 'db' / 'baza2.db').as_posix()}"

EXTRACTOR_MODEL = os.environ.get("EXTRACTOR_MODEL", "claude-sonnet-5-5")
EXTRACTOR_EFFORT = os.environ.get("EXTRACTOR_EFFORT", "medium")
ANALYZER_MODEL = os.environ.get("ANALYZER_MODEL", "claude-haiku-5-5")
ESCALATION_MODEL = os.environ.get("ESCALATION_MODEL", "claude-sonnet-5-5")

# $ po 1M tokena (ulaz, izlaz) - za procjenu i izvjestaj troska
PRICES = {
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-5-5": (0.10, 0.50),
}

ANALYZER_EFFORT = os.environ.get("ANALYZER_EFFORT", "medium")
ESCALATION_EFFORT = os.environ.get("ESCALATION_EFFORT", "medium")
ANALYZER_CHUNK = int(os.environ.get("ANALYZER_CHUNK", "8"))           # natuknica po jednom agent razgovoru
ESCALATION_MAX_PER_RUN = int(os.environ.get("ESCALATION_MAX_PER_RUN", "20"))  # tvrdi limit eskalacija

OUTPUT_DIR = ROOT / "pipeline" / "output"
CACHE_DIR = ROOT / "pipeline" / "cache"

ISSUE_TEXT_MAX = 255  # ISSUE.text je VARCHAR(255)
