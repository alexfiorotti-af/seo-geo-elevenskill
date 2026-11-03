#!/usr/bin/env python3
"""Valida um sitemap XML ou índice de sitemaps (protocolo sitemaps.org).

Verifica: XML válido, limites (50.000 URLs / 50 MB), URLs absolutas e do mesmo site,
duplicadas, parâmetros e fragmentos, http/https misturados, lastmod em ISO 8601 (W3C)
e plausível (não futuro, não todos iguais). Opcionalmente confere o status de uma amostra.

Uso:
  python3 validate_sitemap.py https://dominio.com/sitemap.xml
  python3 validate_sitemap.py sitemap.xml --site https://dominio.com
  python3 validate_sitemap.py https://dominio.com/sitemap.xml --follow --check-status 20

Saída: 0 sem erros, 1 com erros, 2 falha de uso ou de rede.
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import os
import random
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _seo_common import fetch, is_url, same_site  # noqa: E402

MAX_URLS = 50_000
MAX_BYTES = 50 * 1024 * 1024
W3C_DATETIME = re.compile(
    r"^\d{4}(-\d{2}(-\d{2}(T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2}))?)?)?$"
)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_lastmod(value: str) -> Optional[dt.datetime]:
    v = value.strip().replace("Z", "+00:00")
    for candidate in (v, v[:10]):
        try:
            d = dt.datetime.fromisoformat(candidate)
            return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)
        except ValueError:
            continue
    return None


def validate(body: bytes, source: str, site: Optional[str]) -> Dict[str, Any]:
    findings: List[Dict[str, str]] = []

    def add(level: str, msg: str) -> None:
        findings.append({"nivel": level, "mensagem": msg})

    if body[:2] == b"\x1f\x8b":
        body = gzip.decompress(body)
    if len(body) > MAX_BYTES:
        add("ERRO", f"Arquivo com {len(body) / 1048576:.1f} MB (limite 50 MB descompactado). Divida em vários sitemaps.")
    try:
        root = ET.fromstring(body)
    except ET.ParseError as err:
        add("ERRO", f"XML inválido: {err}.")
        return {"fonte": source, "tipo": None, "total": 0, "urls": [], "achados": findings, "erros": 1}

    kind = _local(root.tag)
    entries: List[Dict[str, Optional[str]]] = []
    child_tag = "url" if kind == "urlset" else "sitemap"
    if kind not in ("urlset", "sitemapindex"):
        add("ERRO", f"Elemento raiz <{kind}>; esperado <urlset> ou <sitemapindex>.")
    for node in root:
        if _local(node.tag) != child_tag:
            continue
        item: Dict[str, Optional[str]] = {"loc": None, "lastmod": None}
        for sub in node:
            name = _local(sub.tag)
            if name in item:
                item[name] = (sub.text or "").strip()
        entries.append(item)

    if kind == "urlset" and not entries:
        add("ERRO", "Sitemap sem nenhuma <url>.")
    if len(entries) > MAX_URLS:
        add("ERRO", f"{len(entries)} entradas (limite 50.000). Use um índice de sitemaps.")

    base = site or (source if is_url(source) else None)
    seen = set()
    schemes = set()
    now = dt.datetime.now(dt.timezone.utc)
    lastmods = []
    bad_lastmod = future = no_lastmod = 0
    problems = {"relativa": 0, "outro_site": 0, "parametro": 0, "fragmento": 0, "duplicada": 0, "sem_loc": 0}
    for e in entries:
        loc = e["loc"]
        if not loc:
            problems["sem_loc"] += 1
            continue
        if not is_url(loc):
            problems["relativa"] += 1
            continue
        parts = urllib.parse.urlsplit(loc)
        schemes.add(parts.scheme)
        if base and not same_site(loc, base):
            problems["outro_site"] += 1
        if parts.query:
            problems["parametro"] += 1
        if parts.fragment:
            problems["fragmento"] += 1
        if loc in seen:
            problems["duplicada"] += 1
        seen.add(loc)
        lm = e["lastmod"]
        if not lm:
            no_lastmod += 1
        elif not W3C_DATETIME.match(lm):
            bad_lastmod += 1
        else:
            parsed = parse_lastmod(lm)
            if parsed is None:
                bad_lastmod += 1
            else:
                lastmods.append(lm)
                if parsed > now + dt.timedelta(days=1):
                    future += 1

    if problems["sem_loc"]:
        add("ERRO", f"{problems['sem_loc']} entrada(s) sem <loc>.")
    if problems["relativa"]:
        add("ERRO", f"{problems['relativa']} URL(s) relativa(s); <loc> exige URL absoluta.")
    if problems["outro_site"]:
        add("ERRO", f"{problems['outro_site']} URL(s) de outro host; um sitemap só lista URLs do próprio site.")
    if problems["duplicada"]:
        add("AVISO", f"{problems['duplicada']} URL(s) duplicada(s).")
    if problems["parametro"] and kind == "urlset":
        add("AVISO", f"{problems['parametro']} URL(s) com parâmetros; liste só as versões canônicas.")
    if problems["fragmento"]:
        add("ERRO", f"{problems['fragmento']} URL(s) com # (fragmento não é URL indexável).")
    if len(schemes) > 1:
        add("AVISO", "Mistura de http e https; liste só a versão canônica (https).")
    if bad_lastmod:
        add("ERRO", f"{bad_lastmod} lastmod fora do formato W3C/ISO 8601 (ex.: 2026-11-03 ou 2026-11-03T14:00:00-03:00).")
    if future:
        add("AVISO", f"{future} lastmod no futuro; datas falsas fazem o Google ignorar o lastmod do site.")
    if no_lastmod and entries:
        add("INFO", f"{no_lastmod} entrada(s) sem lastmod; inclua a data real da última alteração.")
    if len(lastmods) >= 10 and len(set(lastmods)) == 1:
        add("AVISO", "Todos os lastmod são idênticos: parece data de geração, não de alteração. O Google só usa lastmod confiável.")

    return {
        "fonte": source,
        "tipo": kind,
        "total": len(entries),
        "urls": [e["loc"] for e in entries if e["loc"]],
        "achados": findings,
        "erros": sum(1 for f in findings if f["nivel"] == "ERRO"),
    }


def check_status(urls: List[str], sample: int) -> List[Dict[str, Any]]:
    out = []
    for u in random.sample(urls, min(sample, len(urls))):
        try:
            f = fetch(u, method="HEAD")
            if f.status in (405, 501):  # servidor não aceita HEAD
                f = fetch(u)
            out.append({"url": u, "status": f.status, "redirect": bool(f.redirects)})
        except OSError as err:
            out.append({"url": u, "status": None, "erro": str(err)})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("alvo", help="URL ou arquivo do sitemap (aceita .gz)")
    ap.add_argument("--site", help="URL do site (para checar o host quando o alvo é arquivo local)")
    ap.add_argument("--follow", action="store_true", help="em índice de sitemaps, valida também os filhos (até 50)")
    ap.add_argument("--check-status", type=int, default=0, metavar="N", help="confere o status HTTP de N URLs aleatórias")
    ap.add_argument("--format", choices=["md", "json"], default="md")
    args = ap.parse_args()

    try:
        f = fetch(args.alvo)
    except OSError as err:
        print(f"erro: não foi possível ler {args.alvo}: {err}", file=sys.stderr)
        sys.exit(2)
    if f.status is not None and f.status != 200:
        print(f"erro: o sitemap respondeu {f.status}", file=sys.stderr)
        sys.exit(1)

    reports = [validate(f.body, args.alvo, args.site)]
    if args.follow and reports[0]["tipo"] == "sitemapindex":
        for child in reports[0]["urls"][:50]:
            try:
                cf = fetch(child)
                reports.append(validate(cf.body, child, args.site or args.alvo))
            except OSError as err:
                reports.append({"fonte": child, "tipo": None, "total": 0, "urls": [],
                                "achados": [{"nivel": "ERRO", "mensagem": f"não foi possível ler: {err}"}], "erros": 1})

    status_rows: List[Dict[str, Any]] = []
    if args.check_status:
        all_urls = [u for r in reports if r["tipo"] == "urlset" for u in r["urls"]]
        status_rows = check_status(all_urls, args.check_status)
        bad = [s for s in status_rows if s.get("status") != 200 or s.get("redirect")]
        if bad:
            reports[0]["achados"].append({"nivel": "ERRO", "mensagem": f"{len(bad)} de {len(status_rows)} URLs da amostra não respondem 200 direto (redirect, 404 ou erro). Sitemap deve ter só URLs finais 200."})
            reports[0]["erros"] += 1

    total_errors = sum(r["erros"] for r in reports)
    if args.format == "json":
        for r in reports:
            if r["tipo"] == "urlset":
                r.pop("urls", None)  # lista completa pode ser enorme; o relatório mostra o total
        print(json.dumps({"relatorios": reports, "amostra_status": status_rows}, ensure_ascii=False, indent=2))
    else:
        for r in reports:
            print(f"## {r['fonte']}\n\nTipo: {r['tipo']} · Entradas: {r.get('total', 0)}\n")
            if not r["achados"]:
                print("Nenhum problema encontrado.\n")
            for a in r["achados"]:
                print(f"- **{a['nivel']}** {a['mensagem']}")
            print()
        if status_rows:
            print("## Amostra de status\n\n| URL | Status | Redirect |\n|---|---|---|")
            for s in status_rows:
                print(f"| {s['url']} | {s.get('status')} | {'sim' if s.get('redirect') else 'não'} |")
    sys.exit(1 if total_errors else 0)


if __name__ == "__main__":
    main()
