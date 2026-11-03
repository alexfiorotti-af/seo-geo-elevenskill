"""Funções compartilhadas pelos scripts da skill seo-geo-elevenskill.

Só biblioteca padrão (Python 3.9+). Nenhum dado é enviado a terceiros além do site consultado.
"""
from __future__ import annotations

import gzip
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Dict, List, Optional

DEFAULT_UA = "Mozilla/5.0 (compatible; seo-geo-elevenskill-audit/1.0; +https://github.com/alexfiorotti-af/seo-geo-elevenskill)"
TIMEOUT = 20


@dataclass
class Fetched:
    source: str                     # URL pedida ou caminho do arquivo
    final_url: Optional[str]        # URL final após redirects (None para arquivo local)
    status: Optional[int]           # status HTTP (None para arquivo local)
    headers: Dict[str, str] = field(default_factory=dict)
    body: bytes = b""
    redirects: List[str] = field(default_factory=list)
    is_file: bool = False

    def text(self) -> str:
        data = self.body
        if data[:2] == b"\x1f\x8b":
            data = gzip.decompress(data)
        charset = "utf-8"
        ctype = self.headers.get("content-type", "")
        m = re.search(r"charset=([\w-]+)", ctype, re.I)
        if m:
            charset = m.group(1)
        try:
            return data.decode(charset, errors="replace")
        except LookupError:
            return data.decode("utf-8", errors="replace")


class _RecordingRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self) -> None:
        super().__init__()
        self.chain: List[str] = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: N802
        self.chain.append(f"{code} {req.full_url} -> {newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def is_url(value: str) -> bool:
    return value.lower().startswith(("http://", "https://"))


def fetch(source: str, user_agent: str = DEFAULT_UA, method: str = "GET") -> Fetched:
    """Lê uma URL (sem executar JavaScript, como um crawler de IA) ou um arquivo local."""
    if not is_url(source):
        with open(source, "rb") as fh:
            return Fetched(source=source, final_url=None, status=None, body=fh.read(), is_file=True)

    redirect = _RecordingRedirect()
    opener = urllib.request.build_opener(redirect)
    req = urllib.request.Request(source, method=method, headers={
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip",
    })
    try:
        with opener.open(req, timeout=TIMEOUT) as resp:
            headers = {k.lower(): v for k, v in resp.headers.items()}
            body = resp.read() if method != "HEAD" else b""
            if headers.get("content-encoding", "").lower() == "gzip" and body:
                body = gzip.decompress(body)
            return Fetched(source, resp.geturl(), resp.status, headers, body, redirect.chain)
    except urllib.error.HTTPError as err:
        headers = {k.lower(): v for k, v in (err.headers.items() if err.headers else [])}
        body = err.read() or b""
        return Fetched(source, err.geturl() or source, err.code, headers, body, redirect.chain)


def die(msg: str, code: int = 2) -> None:
    print(f"erro: {msg}", file=sys.stderr)
    sys.exit(code)


def normalize(text: str) -> str:
    """Minúsculas, sem acento, espaços simples (para comparar palavras-chave)."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text.lower()).strip()


# Largura aproximada em pixels de cada caractere em Arial 20px (fonte usada nos títulos do
# resultado de busca no desktop). É uma ESTIMATIVA para prever corte, não um valor oficial.
_NARROW = set("iljtfI|!.,:;'`íìï")
_MEDIUM_NARROW = set("r()[]{}-/\\\" ")
_WIDE = set("mwMW")
_UPPER_WIDE = set("ABCDEGHKNOQRSUVXYZÁÃÂÀÉÊÓÕÔÚÇ")


def pixel_width(text: str, font_px: float = 20.0) -> int:
    scale = font_px / 20.0
    total = 0.0
    for ch in text or "":
        if ch in _NARROW:
            w = 4.5
        elif ch in _MEDIUM_NARROW:
            w = 6.7
        elif ch in _WIDE:
            w = 16.0
        elif ch in _UPPER_WIDE:
            w = 13.5
        elif ch.isupper():
            w = 12.2
        elif ch.isdigit():
            w = 11.1
        else:
            w = 10.2
        total += w
    return int(round(total * scale))


TITLE_MAX_PX = 580
TITLE_MIN_CHARS = 30
DESC_MIN_CHARS = 70
DESC_MAX_CHARS = 160

PLACEHOLDER_PATTERNS = [
    r"dominio\.com", r"example\.(com|org)", r"seu-dominio", r"SEU[-_ ]DOMINIO",
    r"Nome (exato )?da empresa", r"Nome do (site|serviço|produto)", r"SKU-REAL",
    r"perfil-oficial", r"perfil-real", r"\+55-00-0000", r"Lorem ipsum",
]


def find_placeholders(text: str) -> List[str]:
    hits = []
    for pat in PLACEHOLDER_PATTERNS:
        m = re.search(pat, text, re.I)
        if m:
            hits.append(m.group(0))
    return hits


def same_site(url_a: str, url_b: str) -> bool:
    a = urllib.parse.urlsplit(url_a).hostname or ""
    b = urllib.parse.urlsplit(url_b).hostname or ""
    strip = lambda h: h[4:] if h.startswith("www.") else h  # noqa: E731
    return strip(a.lower()) == strip(b.lower())


def env_or(value: Optional[str], env_name: str) -> Optional[str]:
    return value if value else os.environ.get(env_name)
