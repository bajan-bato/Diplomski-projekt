"""Ciscenje HTML teksta suggestiona prije slanja LLM-u."""
import html
import re
import warnings

from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning

# neki suggestioni su samo URL; to je u redu, nije poziv za dohvat stranice
warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

_BLOCK_TAGS = ["p", "div", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "figure", "table", "ul", "ol"]


def html_to_text(raw: str) -> str:
    soup = BeautifulSoup(raw or "", "html.parser")

    # Slike ne mozemo vidjeti, ali model treba znati da je korisnik nesto pokazao slikom
    for img in soup.find_all("img"):
        img.replace_with(" [slika] ")
    for a in soup.find_all("a"):
        href = a.get("href")
        if href and href not in a.get_text():
            a.append(f" ({href})")
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for li in soup.find_all("li"):
        li.insert_before("\n- ")
    for td in soup.find_all(["td", "th"]):
        td.insert_after(" | ")
    for tag in soup.find_all(_BLOCK_TAGS):
        tag.insert_after("\n")

    text = html.unescape(soup.get_text())
    text = re.sub(r"[ \t\xa0]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # vise uzastopnih [slika] spojimo u jednu oznaku
    text = re.sub(r"(\[slika\]\s*){2,}", "[slika] ", text)
    return text.strip()
