#!/usr/bin/env python3
"""Rastreia o site inteiro pelos links internos, como um robô de busca (sem executar JavaScript).

Encontra (pilares 1, 2, 3 e 9):
  - links internos quebrados (4xx/5xx) e quem aponta para eles;
  - links internos que passam por redirect (atualize para o destino final);
  - páginas órfãs: estão no sitemap, mas nenhum link interno aponta para elas;
  - inconsistências do sitemap: URL com noindex, fora do ar, redirecionada ou com canonical para outra;
  - páginas indexáveis fora do sitemap;
  - páginas profundas (mais de 3 cliques da página inicial);
  - titles duplicados entre páginas indexáveis.

Respeita o robots.txt (grupo '*' ou o do token seo-geo-elevenskill-audit) e espera entre requisições.

Uso:
  python3 crawl_site.py https://seusite.com.br
  python3 crawl_site.py https://seusite.com.br --max-paginas 1000 --atraso 0.3
  python3 crawl_site.py https://seusite.com.br --sitemap https://seusite.com.br/sitemap.xml --format json

Saída: 0 sem erros; 1 com links quebrados ou erros no sitemap; 2 falha de uso ou de rede.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Set

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _seo_common import UA_TOKEN, fetch, host_key, is_url, normalize  # noqa: E402
from audit_page import PageParser  # noqa: E402
from check_robots import is_allowed, parse_robots, robots_url, select_group  # noqa: E402
from validate_sitemap import validate as validate_sitemap  # noqa: E402

NON_HTML_EXT = re.compile(r"\.(pdf|jpe?g|png|gif|webp|avif|svg|ico|zip|rar|mp4|mp3|webm|mov|docx?|xlsx?|pptx?|csv|txt|xml|json|css|js|woff2?)$", re.I)
MAX_DEPTH_OK = 3
LIST_LIMIT = 50


def clean(url: str) -> str:
    return url.split("#", 1)[0]


def is_internal(url: str, site: str) -> bool:
    parts = urllib.parse.urlsplit(url)
    return parts.scheme in ("http", "https") and host_key(url) == site


def allowed(rules, url: str) -> bool:
    parts = urllib.parse.urlsplit(url)
    return is_allowed(rules, (parts.path or "/") + (f"?{parts.query}" if parts.query else ""))[0]


def new_page(url: str, depth: int) -> Dict[str, Any]:
    return {"url": url, "profundidade": depth, "status": None, "final": None, "redirects": [],
            "html": False, "title": "", "canonical": None, "noindex": False}


def visit(url: str, depth: int, site: str, pages: Dict[str, Dict[str, Any]]):
    """Busca a URL e registra em pages. Se ela redireciona para outra URL interna, o conteúdo é
    registrado na URL final (a de origem fica só como redirect). Retorna (página, parser|None)."""
    info = new_page(url, depth)
    pages[url] = info
    path = urllib.parse.urlsplit(url).path or ""
    try:
        method = "HEAD" if NON_HTML_EXT.search(path) else "GET"
        f = fetch(url, method=method)
        if method == "HEAD" and f.status in (405, 501):
            f = fetch(url)
    except OSError as err:
        info["erro"] = str(err)
        return info, None
    final = clean(f.final_url or url)
    info.update(status=f.status, final=final, redirects=f.redirects)
    page = info
    if f.redirects and final != url:
        if not is_internal(final, site) or final in pages:
            return info, None
        page = new_page(final, depth)
        page.update(status=f.status, final=final)
        pages[final] = page
    if f.status != 200 or "html" not in f.headers.get("content-type", "").lower():
        return page, None
    page["html"] = True
    parser = PageParser()
    parser.feed(f.text())
    parser.close()
    page["title"] = parser.titles[0] if parser.titles else ""
    canon = [l.get("href", "") for l in parser.links if "canonical" in l.get("rel", "").lower().split()]
    base = parser.base_href or final
    page["canonical"] = clean(urllib.parse.urljoin(base, canon[0])) if canon else None
    robots = " ".join(m.get("content", "") for m in parser.metas if m.get("name", "").lower() in ("robots", "googlebot"))
    robots += " " + f.headers.get("x-robots-tag", "")
    page["noindex"] = bool(re.search(r"\b(noindex|none)\b", robots.lower()))
    return page, parser


def crawl(start: str, max_pages: int, delay: float, follow_params: bool,
          respect_robots: bool = True, sitemap_arg: Optional[str] = None) -> Dict[str, Any]:
    site = host_key(start)
    rules = None
    robots_sitemaps: List[str] = []
    try:
        rf = fetch(robots_url(start))
        if rf.status == 200:
            groups, robots_sitemaps = parse_robots(rf.text())
            rules = select_group(groups, UA_TOKEN) if respect_robots else None
    except OSError:
        pass

    pages: Dict[str, Dict[str, Any]] = {}
    inlinks: Dict[str, Set[str]] = defaultdict(set)
    skipped_robots: Set[str] = set()
    skipped_params: Set[str] = set()
    queue = deque([(clean(start), 0)])
    queued = {clean(start)}
    hit_limit = False
    fetched = 0

    while queue:
        url, depth = queue.popleft()
        if len(pages) >= max_pages:
            hit_limit = True
            break
        if url in pages:
            continue
        if rules is not None and not allowed(rules, url):
            skipped_robots.add(url)
            continue
        if fetched and delay:
            time.sleep(delay)
        fetched += 1
        page, parser = visit(url, depth, site, pages)
        if parser is None:
            continue
        base = parser.base_href or page["url"]
        for a in parser.anchors:
            href = (a.get("href") or "").strip()
            if not href or href.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
                continue
            target = clean(urllib.parse.urljoin(base, href))
            if not is_internal(target, site):
                continue
            inlinks[target].add(page["url"])
            if target in queued or target in pages:
                continue
            if urllib.parse.urlsplit(target).query and not follow_params:
                skipped_params.add(target)
                continue
            queued.add(target)
            queue.append((target, depth + 1))
    if queue:
        hit_limit = True

    # --- sitemap ---
    sitemap_urls: List[str] = []
    sitemap_sources = [sitemap_arg] if sitemap_arg else (robots_sitemaps or [urllib.parse.urljoin(start, "/sitemap.xml")])
    sitemap_notes: List[str] = []
    for sm in sitemap_sources[:5]:
        try:
            sf = fetch(sm)
        except OSError as err:
            sitemap_notes.append(f"Sitemap {sm} inacessível: {err}")
            continue
        if sf.status != 200:
            sitemap_notes.append(f"Sitemap {sm} respondeu {sf.status}")
            continue
        rep = validate_sitemap(sf.body, sm, start)
        if rep["tipo"] == "sitemapindex":
            for child in rep["urls"][:50]:
                try:
                    cf = fetch(child)
                    if cf.status == 200:
                        sitemap_urls += validate_sitemap(cf.body, child, start)["urls"]
                except OSError:
                    sitemap_notes.append(f"Sitemap filho {child} inacessível")
        else:
            sitemap_urls += rep["urls"]
    sitemap_set = list(dict.fromkeys(sitemap_urls))
    for u in [u for u in sitemap_set if u not in pages and is_internal(u, site)][:LIST_LIMIT * 2]:
        if rules is not None and not allowed(rules, u):
            continue
        if delay:
            time.sleep(delay)
        page, _ = visit(u, -1, site, pages)
        page["fora_do_rastreio"] = True

    return analyse(start, pages, inlinks, sitemap_set, sitemap_notes, skipped_robots, skipped_params, hit_limit)


def analyse(start, pages, inlinks, sitemap_urls, sitemap_notes, skipped_robots, skipped_params, hit_limit):
    findings: List[Dict[str, Any]] = []

    def add(level: str, msg: str, items: Optional[List[str]] = None) -> None:
        findings.append({"nivel": level, "mensagem": msg, "itens": (items or [])[:LIST_LIMIT]})

    start_c = clean(start)
    html_ok = [p for p in pages.values() if p["html"]]
    indexable = [p for p in html_ok if not p["noindex"]
                 and (p["canonical"] in (None, p["url"], p["final"]))]

    broken = [(u, p) for u, p in pages.items() if u in inlinks and (p["status"] is None or p["status"] >= 400)]
    if broken:
        add("ERRO", f"{len(broken)} link(s) interno(s) quebrado(s). Corrija o link ou crie 301:",
            [f"{u} ({p['status'] or p.get('erro', 'erro')}) ← {', '.join(sorted(inlinks[u])[:3])}" for u, p in broken])

    redirected = [(u, p) for u, p in pages.items() if u in inlinks and p["redirects"] and u != start_c]
    if redirected:
        add("AVISO", f"{len(redirected)} link(s) interno(s) apontam para URL que redireciona. Atualize para o destino final:",
            [f"{u} → {p['final']} ← {', '.join(sorted(inlinks[u])[:3])}" for u, p in redirected])

    deep = [p for p in indexable if p["profundidade"] > MAX_DEPTH_OK]
    if deep:
        add("AVISO", f"{len(deep)} página(s) indexável(is) a mais de {MAX_DEPTH_OK} cliques da inicial. Aproxime com links internos:",
            [f"{p['url']} (nível {p['profundidade']})" for p in deep])

    titles: Dict[str, List[str]] = defaultdict(list)
    original: Dict[str, str] = {}
    for p in indexable:
        if p["title"]:
            key = normalize(p["title"])
            original.setdefault(key, p["title"])
            titles[key].append(p["url"])
    dups = {original[t]: us for t, us in titles.items() if len(us) > 1}
    if dups:
        add("AVISO", f"{len(dups)} title(s) repetido(s) entre páginas indexáveis:",
            [f"\"{t}\": {', '.join(us[:4])}" for t, us in dups.items()])

    linked: Set[str] = set(inlinks)
    for u in list(linked):
        p = pages.get(u)
        if p and p.get("final"):
            linked.add(p["final"])
    linked.add(start_c)
    for p in pages.values():
        if p["url"] == start_c and p.get("final"):
            linked.add(p["final"])

    if sitemap_urls:
        orphans = [u for u in sitemap_urls if u not in linked]
        if orphans:
            note = " (o rastreio parou no limite; parte delas pode só não ter sido alcançada)" if hit_limit else ""
            add("AVISO", f"{len(orphans)} página(s) órfã(s): estão no sitemap, mas nenhum link interno aponta para elas{note}:", orphans)
        sm_bad = []
        for u in sitemap_urls:
            p = pages.get(u)
            if not p:
                continue
            if p["status"] is None or p["status"] >= 400:
                sm_bad.append(f"{u}: responde {p['status'] or 'erro'}")
            elif p["redirects"]:
                sm_bad.append(f"{u}: redireciona para {p['final']}")
            elif p["noindex"]:
                sm_bad.append(f"{u}: tem noindex")
            elif p["canonical"] and p["canonical"] not in (u, p["final"]):
                sm_bad.append(f"{u}: canonical aponta para {p['canonical']}")
        if sm_bad:
            add("ERRO", f"{len(sm_bad)} URL(s) do sitemap não são canônicas, indexáveis e 200 direto:", sm_bad)
        sm_set = set(sitemap_urls)
        missing = [p["url"] for p in indexable if p["profundidade"] >= 0
                   and p["url"] not in sm_set and (p["final"] or p["url"]) not in sm_set]
        if missing:
            add("INFO", f"{len(missing)} página(s) indexável(is) fora do sitemap (inclua se devem ranquear):", missing)
    else:
        add("AVISO", "Nenhum sitemap encontrado (robots.txt sem 'Sitemap:' e /sitemap.xml indisponível).")
    for n in sitemap_notes:
        add("AVISO", n)

    noindex = [p["url"] for p in html_ok if p["noindex"]]
    if noindex:
        add("INFO", f"{len(noindex)} página(s) com noindex (confirme que é intencional):", noindex)
    if skipped_robots:
        add("INFO", f"{len(skipped_robots)} URL(s) não rastreada(s) por bloqueio no robots.txt:", sorted(skipped_robots))
    if skipped_params:
        add("INFO", f"{len(skipped_params)} URL(s) com parâmetros não rastreada(s) (use --seguir-parametros para incluir):", sorted(skipped_params))
    if hit_limit:
        add("INFO", "O rastreio atingiu o limite de páginas; aumente --max-paginas para cobertura completa.")

    order = {"ERRO": 0, "AVISO": 1, "INFO": 2}
    findings.sort(key=lambda f: order[f["nivel"]])
    statuses: Dict[str, int] = defaultdict(int)
    for p in pages.values():
        statuses[str(p["status"])] += 1
    return {
        "inicio": start,
        "paginas_rastreadas": len(pages),
        "html_200": len(html_ok),
        "indexaveis": len(indexable),
        "urls_no_sitemap": len(sitemap_urls),
        "profundidade_maxima": max((p["profundidade"] for p in html_ok), default=0),
        "status": dict(statuses),
        "limite_atingido": hit_limit,
        "achados": findings,
        "erros": sum(1 for f in findings if f["nivel"] == "ERRO"),
        "paginas": list(pages.values()),
    }


def to_md(r: Dict[str, Any]) -> str:
    out = [f"# Rastreio do site: {r['inicio']}", "",
           "| Indicador | Valor |", "|---|---|",
           f"| Páginas rastreadas | {r['paginas_rastreadas']} |",
           f"| HTML com status 200 | {r['html_200']} |",
           f"| Indexáveis (sem noindex, canonical própria) | {r['indexaveis']} |",
           f"| URLs no sitemap | {r['urls_no_sitemap']} |",
           f"| Profundidade máxima | {r['profundidade_maxima']} |",
           f"| Status HTTP | {', '.join(f'{k}: {v}' for k, v in sorted(r['status'].items()))} |", "",
           "## Achados", ""]
    if not r["achados"]:
        out.append("Nenhum problema encontrado.")
    for f in r["achados"]:
        out.append(f"### {f['nivel']}: {f['mensagem']}")
        out += [f"- {i}" for i in f["itens"]]
        out.append("")
    out.append("_Leitura sem JavaScript, como os crawlers de IA. Links criados só por script não são seguidos._")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inicio", help="URL inicial (normalmente a home)")
    ap.add_argument("--max-paginas", type=int, default=300)
    ap.add_argument("--atraso", type=float, default=0.3, help="segundos entre requisições")
    ap.add_argument("--sitemap", help="URL do sitemap (padrão: o do robots.txt ou /sitemap.xml)")
    ap.add_argument("--seguir-parametros", action="store_true", help="rastrear também URLs com ?parâmetros")
    ap.add_argument("--ignorar-robots", action="store_true", help="não respeitar o robots.txt (só no seu próprio site)")
    ap.add_argument("--format", choices=["md", "json"], default="md")
    args = ap.parse_args()
    if not is_url(args.inicio):
        print("erro: informe uma URL completa, ex.: https://seusite.com.br", file=sys.stderr)
        sys.exit(2)
    try:
        result = crawl(args.inicio, args.max_paginas, args.atraso, args.seguir_parametros,
                       respect_robots=not args.ignorar_robots, sitemap_arg=args.sitemap)
    except OSError as err:
        print(f"erro: {err}", file=sys.stderr)
        sys.exit(2)
    if result["paginas_rastreadas"] and all(p["status"] is None for p in result["paginas"]):
        print("erro: nenhuma página respondeu (rede ou URL incorreta)", file=sys.stderr)
        sys.exit(2)
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(to_md(result))
    sys.exit(1 if result["erros"] else 0)


if __name__ == "__main__":
    main()
