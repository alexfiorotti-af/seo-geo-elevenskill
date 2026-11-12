#!/usr/bin/env python3
"""Monitora mudanças de SEO entre duas datas (pilar 11): tira uma "foto" das páginas-chave e compara.

Pega deploys que derrubam tráfego em silêncio: noindex acidental, canonical trocado, title
reescrito pelo CMS, JSON-LD que sumiu, conteúdo que passou a depender de JavaScript, redirect novo.

A foto guarda, por URL: status, URL final, redirects, title, description, canonical, robots
(meta + X-Robots-Tag), H1, tipos de JSON-LD, hreflang, palavras no HTML, links internos e um
hash do texto visível. São dados públicos da página; guarde as fotos fora do repositório
(ex.: relatorios/, que o .gitignore já ignora).

Uso:
  python3 drift.py foto https://dominio.com/ https://dominio.com/servicos/ --saida relatorios/antes.json
  python3 drift.py foto --lista urls.txt --saida relatorios/antes.json
  python3 drift.py foto --sitemap https://dominio.com/sitemap.xml --max 200 --saida relatorios/antes.json
  python3 drift.py comparar relatorios/antes.json                       # compara com o site agora
  python3 drift.py comparar relatorios/antes.json --atual relatorios/depois.json --format json

Saída (comparar): 0 sem mudanças críticas, 1 com mudança crítica (ERRO), 2 falha.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _seo_common import fetch, html_to_text, is_url, load_json, normalize, same_site  # noqa: E402
from audit_page import PageParser, collect_types, meta_content  # noqa: E402
from validate_sitemap import validate as validate_sitemap  # noqa: E402


def snapshot_url(url: str) -> Dict[str, Any]:
    try:
        f = fetch(url)
    except OSError as err:
        return {"url": url, "status": None, "erro": str(err)}
    snap: Dict[str, Any] = {"url": url, "status": f.status, "final": f.final_url, "redirects": len(f.redirects)}
    if f.status != 200 or "html" not in f.headers.get("content-type", "html"):
        return snap
    html = f.text()
    p = PageParser()
    p.feed(html)
    p.close()
    types: List[str] = []
    for raw in p.jsonld_raw:
        try:
            collect_types(json.loads(raw), types)
        except json.JSONDecodeError:
            types.append("(JSON-LD inválido)")
    base = p.base_href or f.final_url or url
    canon = [l.get("href", "") for l in p.links if "canonical" in l.get("rel", "").lower().split()]
    robots = " ".join(meta_content(p.metas, name="robots") + meta_content(p.metas, name="googlebot"))
    robots = " ".join(filter(None, [robots.strip(), f.headers.get("x-robots-tag", "").strip()])).lower()
    hreflang = sorted(f"{l.get('hreflang', '').lower()}={urllib.parse.urljoin(base, l.get('href', ''))}"
                      for l in p.links if "alternate" in l.get("rel", "").lower().split() and l.get("hreflang"))
    text = html_to_text(html)
    internal = sum(1 for a in p.anchors if a.get("href") and is_url(urllib.parse.urljoin(base, a["href"]))
                   and same_site(urllib.parse.urljoin(base, a["href"]), base))
    snap.update({
        "title": p.titles[0] if p.titles else "",
        "description": (meta_content(p.metas, name="description") or [""])[0].strip(),
        "canonical": urllib.parse.urljoin(base, canon[0]) if canon else None,
        "robots": robots,
        "h1": [h["text"] for h in p.headings if h["level"] == 1],
        "jsonld": sorted(set(types)),
        "hreflang": hreflang,
        "palavras": len(re.findall(r"\w+", text)),
        "links_internos": internal,
        "hash_texto": hashlib.sha256(normalize(text).encode("utf-8")).hexdigest()[:16],
    })
    return snap


def urls_from_sitemap(sitemap: str, limit: int) -> List[str]:
    f = fetch(sitemap)
    if f.status != 200:
        raise OSError(f"sitemap respondeu {f.status}")
    rep = validate_sitemap(f.body, sitemap, None)
    urls = rep["urls"]
    if rep["tipo"] == "sitemapindex":
        urls = []
        for child in rep["urls"][:20]:
            cf = fetch(child)
            if cf.status == 200:
                urls += validate_sitemap(cf.body, child, None)["urls"]
            if len(urls) >= limit:
                break
    return list(dict.fromkeys(urls))[:limit]


def take(urls: List[str], delay: float) -> Dict[str, Any]:
    pages = []
    for i, u in enumerate(urls):
        if i and delay:
            time.sleep(delay)
        pages.append(snapshot_url(u))
    return {"data": dt.datetime.now().isoformat(timespec="seconds"), "paginas": pages}


def is_noindex(robots: str) -> bool:
    return bool(re.search(r"\b(noindex|none)\b", robots or ""))


def diff(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
    old = {p["url"]: p for p in before["paginas"]}
    new = {p["url"]: p for p in after["paginas"]}
    changes: List[Dict[str, str]] = []

    def add(level: str, url: str, msg: str) -> None:
        changes.append({"nivel": level, "url": url, "mensagem": msg})

    for url, a in old.items():
        b = new.get(url)
        if b is None:
            add("AVISO", url, "URL não está na foto nova (não foi verificada).")
            continue
        if a.get("status") != b.get("status"):
            lvl = "ERRO" if a.get("status") == 200 else "INFO"
            add(lvl, url, f"Status mudou: {a.get('status')} → {b.get('status')}.")
            if b.get("status") != 200:
                continue
        if (a.get("final") or url) != (b.get("final") or url):
            add("AVISO", url, f"Agora redireciona para {b.get('final')} (antes: {a.get('final')}).")
        if not is_noindex(a.get("robots", "")) and is_noindex(b.get("robots", "")):
            add("ERRO", url, f"noindex apareceu (robots: \"{b.get('robots')}\").")
        elif is_noindex(a.get("robots", "")) and not is_noindex(b.get("robots", "")):
            add("INFO", url, "noindex removido: a página voltou a ser indexável.")
        if "nosnippet" in (b.get("robots") or "") and "nosnippet" not in (a.get("robots") or ""):
            add("AVISO", url, "nosnippet apareceu: a página sai dos snippets e dos recursos de IA do Google.")
        if a.get("canonical") != b.get("canonical"):
            lvl = "ERRO" if b.get("canonical") and b.get("canonical") != (b.get("final") or url) else "AVISO"
            add(lvl, url, f"Canonical mudou: {a.get('canonical')} → {b.get('canonical')}.")
        for field, lvl in (("title", "AVISO"), ("h1", "AVISO"), ("description", "INFO")):
            if a.get(field) != b.get(field):
                add(lvl, url, f"{field} mudou: \"{str(a.get(field))[:80]}\" → \"{str(b.get(field))[:80]}\".")
        lost = sorted(set(a.get("jsonld") or []) - set(b.get("jsonld") or []))
        gained = sorted(set(b.get("jsonld") or []) - set(a.get("jsonld") or []))
        if lost:
            add("AVISO", url, f"JSON-LD sumiu: {', '.join(lost)}.")
        if gained:
            add("INFO", url, f"JSON-LD novo: {', '.join(gained)}.")
        if a.get("hreflang") != b.get("hreflang"):
            add("AVISO", url, "hreflang mudou.")
        wa, wb = a.get("palavras") or 0, b.get("palavras") or 0
        if wa >= 100 and wb < wa * 0.7:
            add("AVISO", url, f"Texto no HTML do servidor caiu de {wa} para {wb} palavras (conteúdo removido ou passou a depender de JS).")
        elif a.get("hash_texto") and a.get("hash_texto") != b.get("hash_texto"):
            add("INFO", url, f"Texto da página mudou ({wa} → {wb} palavras).")
        la, lb = a.get("links_internos") or 0, b.get("links_internos") or 0
        if la >= 10 and lb < la * 0.5:
            add("AVISO", url, f"Links internos caíram de {la} para {lb} (menu/rodapé mudou?).")
    for url in new:
        if url not in old:
            add("INFO", url, "URL nova (sem foto anterior).")
    order = {"ERRO": 0, "AVISO": 1, "INFO": 2}
    changes.sort(key=lambda x: (order[x["nivel"]], x["url"]))
    return {"antes": before.get("data"), "depois": after.get("data"), "paginas": len(old), "mudancas": changes,
            "erros": sum(1 for c in changes if c["nivel"] == "ERRO")}


def to_md(r: Dict[str, Any]) -> str:
    out = [f"# Mudanças de SEO: {r['antes']} → {r['depois']}", "", f"Páginas comparadas: {r['paginas']}", ""]
    if not r["mudancas"]:
        return "\n".join(out + ["Nenhuma mudança."])
    out += ["| Nível | URL | Mudança |", "|---|---|---|"]
    out += [f"| {c['nivel']} | {c['url']} | {c['mensagem']} |" for c in r["mudancas"]]
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("foto", help="captura o estado atual das URLs")
    f.add_argument("urls", nargs="*")
    f.add_argument("--lista", help="arquivo com uma URL por linha")
    f.add_argument("--sitemap", help="usar as URLs do sitemap")
    f.add_argument("--max", type=int, default=200)
    f.add_argument("--atraso", type=float, default=0.3)
    f.add_argument("--saida", required=True, help="arquivo JSON da foto")
    c = sub.add_parser("comparar", help="compara uma foto com o site agora ou com outra foto")
    c.add_argument("antes")
    c.add_argument("--atual", help="foto mais recente (se omitido, captura agora)")
    c.add_argument("--atraso", type=float, default=0.3)
    c.add_argument("--salvar-atual", help="salva a captura feita agora neste arquivo")
    c.add_argument("--format", choices=["md", "json"], default="md")
    args = ap.parse_args()
    try:
        if args.cmd == "foto":
            urls = list(args.urls)
            if args.lista:
                with open(args.lista, encoding="utf-8") as fh:
                    urls += [l.strip() for l in fh if is_url(l.strip())]
            if args.sitemap:
                urls += urls_from_sitemap(args.sitemap, args.max)
            urls = list(dict.fromkeys(u for u in urls if is_url(u)))[:args.max]
            if not urls:
                print("erro: informe URLs, --lista ou --sitemap", file=sys.stderr)
                sys.exit(2)
            snap = take(urls, args.atraso)
            os.makedirs(os.path.dirname(os.path.abspath(args.saida)), exist_ok=True)
            with open(args.saida, "w", encoding="utf-8") as fh:
                json.dump(snap, fh, ensure_ascii=False, indent=2)
            print(f"foto de {len(urls)} URL(s) salva em {args.saida}")
            return
        before = load_json(args.antes)
        if args.atual:
            after = load_json(args.atual)
        else:
            after = take([p["url"] for p in before["paginas"]], args.atraso)
            if args.salvar_atual:
                with open(args.salvar_atual, "w", encoding="utf-8") as fh:
                    json.dump(after, fh, ensure_ascii=False, indent=2)
    except (OSError, ValueError, KeyError) as err:
        print(f"erro: {err}", file=sys.stderr)
        sys.exit(2)
    r = diff(before, after)
    print(json.dumps(r, ensure_ascii=False, indent=2) if args.format == "json" else to_md(r))
    sys.exit(1 if r["erros"] else 0)


if __name__ == "__main__":
    main()
