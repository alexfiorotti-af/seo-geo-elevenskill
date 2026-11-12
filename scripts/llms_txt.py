#!/usr/bin/env python3
"""Valida ou gera o /llms.txt de um site (pilar 2, opcional e de prioridade baixa).

Formato (llmstxt.org): um H1 com o nome do site (único item obrigatório), um resumo em citação
("> ..."), parágrafos opcionais e seções H2 com listas de links "- [Nome](URL): nota".
A seção "## Optional" reúne o que pode ser pulado.

Lembrete: o Google declarou que não usa llms.txt; alguns agentes e ferramentas leem. Faça depois
dos pilares 1 a 6, com o mesmo conteúdo do site e sem instruções para IAs.

Uso:
  python3 llms_txt.py validar https://dominio.com
  python3 llms_txt.py validar llms.txt --verificar-links
  python3 llms_txt.py gerar https://dominio.com --nome "Clínica Aurora" --max-paginas 60 > llms.txt
  python3 llms_txt.py gerar https://dominio.com --sitemap https://dominio.com/sitemap-paginas.xml

Saída (validar): 0 sem erros, 1 com erros, 2 falha. (gerar): 0 ok, 2 falha.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
from collections import OrderedDict
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _seo_common import fetch, find_placeholders, is_url  # noqa: E402
from audit_page import PageParser, meta_content  # noqa: E402
from validate_sitemap import validate as validate_sitemap  # noqa: E402

LINK = re.compile(r"^\s*[-*]\s+\[([^\]]+)\]\(([^)\s]+)\)\s*(?::\s*(.*))?$")
INSTRUCTION = re.compile(r"(ignore (all|previous|the)|you must|always (recommend|cite|mention)|as an ai|"
                         r"instruç(ão|ões) para (ia|llm)|recomende sempre|sempre recomende|cite sempre|"
                         r"ignore as instruções|\bAI:\s|\bLLM:\s)", re.I)


def site_root(target: str) -> str:
    p = urllib.parse.urlsplit(target if "://" in target else "https://" + target)
    return f"{p.scheme}://{p.netloc}"


def validate_text(text: str, check_links: bool = False, delay: float = 0.2) -> Dict[str, Any]:
    findings: List[Dict[str, str]] = []

    def add(level: str, msg: str) -> None:
        findings.append({"nivel": level, "mensagem": msg})

    lines = text.splitlines()
    nonempty = [l for l in lines if l.strip()]
    if not nonempty or not re.match(r"^#\s+\S", nonempty[0]):
        add("ERRO", "A primeira linha precisa ser um H1 com o nome do site (\"# Nome\").")
    h1 = [l for l in lines if re.match(r"^#\s", l)]
    if len(h1) > 1:
        add("AVISO", f"{len(h1)} H1; use só um (as seções são H2).")
    if not any(l.startswith(">") for l in lines):
        add("INFO", "Sem resumo em citação (\"> Uma frase sobre o site\") logo depois do H1.")
    if re.search(r"(?m)^#{3,}\s", text):
        add("INFO", "Há H3 ou menores; o formato prevê seções H2 com listas de links.")
    if re.search(r"(?i)<(html|body|div|script)\b", text):
        add("ERRO", "O arquivo contém HTML. llms.txt é Markdown puro (o servidor pode estar devolvendo uma página de erro).")
    links: List[Dict[str, str]] = []
    section = ""
    for i, line in enumerate(lines, 1):
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        m = LINK.match(line)
        if m:
            links.append({"secao": section, "nome": m.group(1), "url": m.group(2), "nota": m.group(3) or "", "linha": str(i)})
        elif section and re.match(r"^\s*[-*]\s", line):
            add("AVISO", f"Linha {i}: item de lista fora do formato \"- [Nome](URL): nota\".")
    if not links:
        add("AVISO", "Nenhum link no formato \"- [Nome](URL)\": o arquivo não aponta para as páginas principais.")
    rel = [l for l in links if not is_url(l["url"])]
    if rel:
        add("AVISO", f"{len(rel)} link(s) com URL relativa (use URL absoluta): " + ", ".join(l["url"] for l in rel[:5]))
    dup = sorted({l["url"] for l in links if [x["url"] for x in links].count(l["url"]) > 1})
    if dup:
        add("INFO", f"{len(dup)} URL(s) repetida(s): " + ", ".join(dup[:5]))
    ph = find_placeholders(text)
    if ph:
        add("ERRO", f"Texto de modelo não substituído: {', '.join(sorted(set(ph)))}.")
    if INSTRUCTION.search(text):
        add("ERRO", "Há instruções para IAs/LLMs no arquivo. O llms.txt descreve o site; ordens para robôs "
                    "são tratadas como manipulação (regra 5 da skill).")
    if len(text.encode("utf-8")) > 100_000:
        add("INFO", "Arquivo acima de 100 KB: o llms.txt deve ser um resumo; o detalhe fica nas páginas.")
    broken: List[str] = []
    if check_links:
        for n, l in enumerate([x for x in links if is_url(x["url"])][:150]):
            if n and delay:
                time.sleep(delay)
            try:
                f = fetch(l["url"], method="HEAD")
                if f.status in (405, 501):
                    f = fetch(l["url"])
                if f.status != 200:
                    broken.append(f"{l['url']} ({f.status})")
            except OSError as err:
                broken.append(f"{l['url']} ({err})")
        if broken:
            add("ERRO", f"{len(broken)} link(s) do llms.txt não respondem 200: " + "; ".join(broken[:10]))
    order = {"ERRO": 0, "AVISO": 1, "INFO": 2}
    findings.sort(key=lambda x: order[x["nivel"]])
    sections = list(OrderedDict.fromkeys(l["secao"] for l in links))
    return {"links": len(links), "secoes": sections, "achados": findings,
            "erros": sum(1 for x in findings if x["nivel"] == "ERRO")}


def label_for(path: str) -> str:
    seg = [s for s in path.split("/") if s]
    if not seg:
        return "Principal"
    name = re.sub(r"[-_]+", " ", seg[0]).strip()
    return name[:1].upper() + name[1:]


def generate(target: str, name: Optional[str], sitemap: Optional[str], max_pages: int, delay: float) -> str:
    root = site_root(target)
    home = fetch(root + "/")
    hp = PageParser()
    hp.feed(home.text())
    hp.close()
    site_name = name or (meta_content(hp.metas, prop="og:site_name") or [""])[0] or (hp.titles[0] if hp.titles else host_label(root))
    summary = (meta_content(hp.metas, name="description") or [""])[0].strip()
    sources = [sitemap] if sitemap else []
    if not sources:
        rb = fetch(root + "/robots.txt")
        if rb.status == 200:
            sources = re.findall(r"(?im)^\s*sitemap:\s*(\S+)", rb.text())
        sources = sources or [root + "/sitemap.xml"]
    urls: List[str] = []
    for sm in sources[:5]:
        sm = urllib.parse.urljoin(root + "/", sm)
        f = fetch(sm)
        if f.status != 200:
            continue
        rep = validate_sitemap(f.body, sm, root)
        if rep["tipo"] == "sitemapindex":
            for child in rep["urls"][:20]:
                cf = fetch(child)
                if cf.status == 200:
                    urls += validate_sitemap(cf.body, child, root)["urls"]
        else:
            urls += rep["urls"]
    urls = list(OrderedDict.fromkeys(u for u in urls if is_url(u)))[:max_pages]
    groups: "OrderedDict[str, List[str]]" = OrderedDict()
    for i, u in enumerate(urls):
        if i and delay:
            time.sleep(delay)
        try:
            f = fetch(u)
        except OSError:
            continue
        if f.status != 200 or "html" not in f.headers.get("content-type", "html"):
            continue
        p = PageParser()
        p.feed(f.text())
        p.close()
        robots = " ".join(meta_content(p.metas, name="robots")) + " " + f.headers.get("x-robots-tag", "")
        if re.search(r"noindex|none", robots, re.I):
            continue
        title = (p.titles[0] if p.titles else u).split(" | ")[0].split(" - ")[0].strip()
        desc = (meta_content(p.metas, name="description") or [""])[0].strip()
        line = f"- [{title}]({u})" + (f": {desc}" if desc else "")
        groups.setdefault(label_for(urllib.parse.urlsplit(u).path), []).append(line)
    out = [f"# {site_name}", ""]
    if summary:
        out += [f"> {summary}", ""]
    for label, items in groups.items():
        out += [f"## {label}", "", *items, ""]
    return "\n".join(out).rstrip() + "\n"


def host_label(root: str) -> str:
    return urllib.parse.urlsplit(root).hostname or root


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validar", help="valida um llms.txt (URL do site, URL do arquivo ou arquivo local)")
    v.add_argument("alvo")
    v.add_argument("--verificar-links", action="store_true", help="confere se cada link responde 200")
    v.add_argument("--atraso", type=float, default=0.2)
    v.add_argument("--format", choices=["md", "json"], default="md")
    g = sub.add_parser("gerar", help="gera um rascunho a partir do sitemap")
    g.add_argument("site")
    g.add_argument("--nome", help="nome do site no H1 (padrão: og:site_name ou title da home)")
    g.add_argument("--sitemap")
    g.add_argument("--max-paginas", type=int, default=80)
    g.add_argument("--atraso", type=float, default=0.3)
    args = ap.parse_args()

    if args.cmd == "gerar":
        try:
            print(generate(args.site, args.nome, args.sitemap, args.max_paginas, args.atraso), end="")
            print("rascunho gerado: revise nomes, notas e ordem antes de publicar.", file=sys.stderr)
        except OSError as err:
            print(f"erro: {err}", file=sys.stderr)
            sys.exit(2)
        return
    target = args.alvo
    if is_url(target) and not urllib.parse.urlsplit(target).path.endswith(".txt"):
        target = site_root(target) + "/llms.txt"
    try:
        f = fetch(target)
    except OSError as err:
        print(f"erro: não foi possível ler {target}: {err}", file=sys.stderr)
        sys.exit(2)
    if f.status is not None and f.status != 200:
        print(f"erro: {target} respondeu {f.status}", file=sys.stderr)
        sys.exit(2)
    r = validate_text(f.text(), args.verificar_links, args.atraso)
    r["alvo"] = target
    if f.headers and "text/html" in f.headers.get("content-type", ""):
        r["achados"].insert(0, {"nivel": "ERRO", "mensagem": "Servido como text/html; use text/plain ou text/markdown."})
        r["erros"] += 1
    if args.format == "json":
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(f"# llms.txt: {target}\n\nLinks: {r['links']} · Seções: {', '.join(s or '(sem seção)' for s in r['secoes']) or '-'}\n")
        print("\n".join(f"- **{x['nivel']}** {x['mensagem']}" for x in r["achados"]) or "Nenhum problema encontrado.")
    sys.exit(1 if r["erros"] else 0)


if __name__ == "__main__":
    main()
