#!/usr/bin/env python3
"""Verifica backlinks (pilar 10): os links ainda existem? As páginas linkadas estão no ar?

Dois modos:

  origens   Lê um CSV com as páginas que (supostamente) linkam para o seu site, abre cada uma
            sem executar JavaScript e confere se o link ainda está lá, com qual rel e qual âncora.
            Serve para: links perdidos, distribuição de âncoras e atributos, monitoramento mensal.

  destinos  Lê um CSV com as páginas do SEU site que recebem links (Search Console → Links →
            "Páginas mais linkadas") e confere se respondem 200. Página com backlinks dando 404
            é autoridade jogada fora: crie um 301 para a página equivalente.

Aceita exportações do Search Console, Bing Webmaster Tools, Ahrefs, Semrush ou qualquer CSV
com uma coluna de URLs (detectada pelo nome ou pelo conteúdo).

Uso:
  python3 verify_backlinks.py origens links.csv --dominio seusite.com.br --marca "Nome da Marca"
  python3 verify_backlinks.py destinos paginas-mais-linkadas.csv
  python3 verify_backlinks.py origens links.csv --dominio seusite.com.br --format json --limite 100

Saída: 0 sem problemas; 1 com links perdidos (origens) ou páginas linkadas fora do ar (destinos);
       2 falha de uso.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
from collections import Counter
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _seo_common import (  # noqa: E402
    fetch, find_column, host_key, is_url, normalize, read_csv, to_int,
)
from audit_page import GENERIC_ANCHORS, PageParser  # noqa: E402

SOURCE_ALIASES = [
    "linking page", "pagina com link", "pagina de origem", "url de origem", "referring page url",
    "referring page", "source url", "source page", "url from", "origem", "source", "linking_page",
]
TARGET_ALIASES = [
    "top linked pages", "paginas mais linkadas", "target page", "pagina de destino", "target url",
    "url de destino", "pagina", "page", "url",
]
LINKS_ALIASES = ["incoming links", "links recebidos", "links de entrada", "backlinks", "links"]
SITES_ALIASES = ["linking sites", "sites com links", "referring domains", "dominios de referencia",
                 "dominios", "sites"]
CONCENTRATION_SHARE = 0.30   # heurística: uma mesma âncora comercial em >30% dos links ativos
CONCENTRATION_MIN = 5


def rel_kind(rel: str) -> str:
    tokens = set((rel or "").lower().split())
    kinds = [k for k in ("sponsored", "ugc", "nofollow") if k in tokens]
    return "+".join(kinds) if kinds else "follow"


def anchor_kind(text: str, img_alt: Optional[str], brand_terms: List[str], target_host: str) -> str:
    t = normalize(text)
    if not t and img_alt is not None:
        t = normalize(img_alt)
        if not t:
            return "imagem sem alt"
        kind_prefix = "imagem: "
    else:
        kind_prefix = ""
    if not t:
        return "vazia"
    if re.match(r"^(https?://|www\.)", t) or target_host in t.replace(" ", ""):
        return kind_prefix + "url"
    if any(b and b in t for b in brand_terms):
        return kind_prefix + "marca"
    if t in GENERIC_ANCHORS:
        return kind_prefix + "generica"
    return kind_prefix + "descritiva/palavra-chave"


def check_sources(rows: List[Dict[str, str]], column: str, domain: str, brands: List[str],
                  limit: int, delay: float) -> Dict[str, Any]:
    target = host_key(domain)
    brand_terms = [normalize(b) for b in brands if b.strip()]
    first_label = target.split(".")[0]
    brand_terms.append(normalize(first_label.replace("-", " ")))
    brand_terms.append(normalize(first_label))

    sources = list(dict.fromkeys((r.get(column) or "").strip() for r in rows))
    sources = [s for s in sources if is_url(s)][:limit]
    results: List[Dict[str, Any]] = []
    for i, src in enumerate(sources):
        if i and delay:
            time.sleep(delay)
        item: Dict[str, Any] = {"origem": src, "status": None, "situacao": "", "links": [], "noindex": False}
        try:
            f = fetch(src)
        except OSError as err:
            item.update(situacao="erro de acesso", erro=str(err))
            results.append(item)
            continue
        item["status"] = f.status
        if f.status != 200:
            item["situacao"] = "origem fora do ar"
            results.append(item)
            continue
        parser = PageParser()
        parser.feed(f.text())
        parser.close()
        base = parser.base_href or f.final_url or src
        robots = " ".join(m.get("content", "") for m in parser.metas
                          if m.get("name", "").lower() in ("robots", "googlebot"))
        robots += " " + f.headers.get("x-robots-tag", "")
        item["noindex"] = bool(re.search(r"\b(noindex|none)\b", robots.lower()))
        for a in parser.anchors:
            href = (a.get("href") or "").strip()
            if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue
            absolute = urllib.parse.urljoin(base, href)
            host = host_key(absolute)
            if host == target or host.endswith("." + target):
                text = a.get("text") or ""
                item["links"].append({
                    "alvo": absolute,
                    "rel": rel_kind(a.get("rel", "")),
                    "ancora": text or (f"[imagem] {a.get('img_alt')}" if a.get("img_alt") is not None else ""),
                    "tipo_ancora": anchor_kind(text, a.get("img_alt"), brand_terms, target),
                })
        item["situacao"] = "ativo" if item["links"] else "perdido"
        results.append(item)

    active = [r for r in results if r["situacao"] == "ativo"]
    all_links = [lk for r in active for lk in r["links"]]
    rel_count = Counter(lk["rel"] for lk in all_links)
    kind_count = Counter(lk["tipo_ancora"] for lk in all_links)
    anchor_count = Counter(normalize(lk["ancora"]) for lk in all_links if lk["ancora"])
    findings: List[Dict[str, str]] = []
    lost = [r for r in results if r["situacao"] == "perdido"]
    down = [r for r in results if r["situacao"] in ("origem fora do ar", "erro de acesso")]
    if lost:
        findings.append({"nivel": "AVISO", "mensagem": f"{len(lost)} origem(ns) no ar sem o link: peça de volta (ou confirme se o link é inserido por JavaScript)."})
    if down:
        findings.append({"nivel": "INFO", "mensagem": f"{len(down)} origem(ns) fora do ar ou inacessível: link perdido junto com a página."})
    noindex = [r for r in active if r["noindex"]]
    if noindex:
        findings.append({"nivel": "INFO", "mensagem": f"{len(noindex)} origem(ns) ativa(s) com noindex: o link tende a valer pouco."})
    commercial = [(a, n) for a, n in anchor_count.most_common()
                  if a and anchor_kind(a, None, brand_terms, target) == "descritiva/palavra-chave"]
    if commercial and all_links:
        top_anchor, top_n = commercial[0]
        share = top_n / len(all_links)
        if top_n >= CONCENTRATION_MIN and share > CONCENTRATION_SHARE:
            findings.append({"nivel": "AVISO", "mensagem": f"A âncora \"{top_anchor}\" aparece em {share:.0%} dos links ativos. Âncora comercial exata em série é sinal de manipulação (heurística)."})
    if all_links and rel_count.get("follow", 0) == len(all_links) and len(all_links) >= 20:
        findings.append({"nivel": "INFO", "mensagem": "Todos os links ativos são follow. Perfis naturais costumam ter uma parcela nofollow/ugc/sponsored; verifique a origem dos links."})
    sponsored = rel_count.get("sponsored", 0) + sum(n for k, n in rel_count.items() if "sponsored" in k and k != "sponsored")
    if sponsored:
        findings.append({"nivel": "INFO", "mensagem": f"{sponsored} link(s) marcados como sponsored: correto para links pagos ou patrocinados (sinaliza ao Google que não é endosso editorial)."})

    return {
        "modo": "origens",
        "dominio": target,
        "verificadas": len(results),
        "ativas": len(active),
        "perdidas": len(lost),
        "fora_do_ar": len(down),
        "dominios_de_referencia_ativos": len({host_key(r["origem"]) for r in active}),
        "rel": dict(rel_count),
        "tipos_de_ancora": dict(kind_count),
        "ancoras_mais_comuns": anchor_count.most_common(10),
        "achados": findings,
        "resultados": results,
    }


def check_targets(rows: List[Dict[str, str]], column: str, site: Optional[str], delay: float) -> Dict[str, Any]:
    links_col = find_column(rows, LINKS_ALIASES)
    sites_col = find_column(rows, SITES_ALIASES)
    if links_col == column:
        links_col = None
    if sites_col in (column, links_col):
        sites_col = None
    entries = []
    for r in rows:
        url = (r.get(column) or "").strip()
        if not url:
            continue
        if not is_url(url) and site:
            url = urllib.parse.urljoin(site.rstrip("/") + "/", url.lstrip("/"))
        if not is_url(url):
            continue
        entries.append({"url": url,
                        "links": to_int(r.get(links_col)) if links_col else None,
                        "sites": to_int(r.get(sites_col)) if sites_col else None})
    entries = list({e["url"]: e for e in entries}.values())
    entries.sort(key=lambda e: (-(e["sites"] or 0), -(e["links"] or 0)))

    findings: List[Dict[str, str]] = []
    for i, e in enumerate(entries):
        if i and delay:
            time.sleep(delay)
        try:
            f = fetch(e["url"], method="HEAD")
            if f.status in (405, 501) or f.status is None:
                f = fetch(e["url"])
        except OSError as err:
            e.update(status=None, final=None, redirects=[], situacao="ERRO", nota=f"inacessível: {err}")
            continue
        e.update(status=f.status, final=f.final_url, redirects=f.redirects)
        weight = f" ({e['sites']} sites)" if e["sites"] else (f" ({e['links']} links)" if e["links"] else "")
        if f.status is None or f.status >= 400:
            e["situacao"] = "ERRO"
            e["nota"] = f"responde {f.status}: crie 301 para a página equivalente{weight}"
        elif any(x.split()[0] in ("302", "307") for x in f.redirects):
            e["situacao"] = "AVISO"
            e["nota"] = "redirect temporário: use 301/308 para consolidar a autoridade"
        elif len(f.redirects) > 1:
            e["situacao"] = "AVISO"
            e["nota"] = f"cadeia de {len(f.redirects)} redirects: aponte direto para o destino final"
        elif f.redirects:
            e["situacao"] = "ok"
            e["nota"] = "301 para " + (f.final_url or "")
        else:
            e["situacao"] = "ok"
            e["nota"] = ""
    errors = [e for e in entries if e.get("situacao") == "ERRO"]
    if errors:
        findings.append({"nivel": "ERRO", "mensagem": f"{len(errors)} página(s) que recebem links estão fora do ar. Cada uma é autoridade desperdiçada: redirecione com 301."})
    warns = [e for e in entries if e.get("situacao") == "AVISO"]
    if warns:
        findings.append({"nivel": "AVISO", "mensagem": f"{len(warns)} página(s) linkadas com redirect temporário ou em cadeia."})
    return {"modo": "destinos", "verificadas": len(entries), "fora_do_ar": len(errors),
            "achados": findings, "resultados": entries}


def md_sources(r: Dict[str, Any]) -> str:
    out = [f"# Backlinks para {r['dominio']}", "",
           "| Indicador | Valor |", "|---|---|",
           f"| Origens verificadas | {r['verificadas']} |",
           f"| Ativas (link encontrado) | {r['ativas']} |",
           f"| Perdidas (página no ar, sem o link) | {r['perdidas']} |",
           f"| Origem fora do ar | {r['fora_do_ar']} |",
           f"| Domínios de referência ativos | {r['dominios_de_referencia_ativos']} |",
           f"| Atributos | {', '.join(f'{k}: {v}' for k, v in r['rel'].items()) or '-'} |",
           f"| Tipos de âncora | {', '.join(f'{k}: {v}' for k, v in r['tipos_de_ancora'].items()) or '-'} |", ""]
    if r["achados"]:
        out += ["## Achados", ""] + [f"- **{a['nivel']}** {a['mensagem']}" for a in r["achados"]] + [""]
    lost = [x for x in r["resultados"] if x["situacao"] == "perdido"]
    if lost:
        out += ["## Links perdidos (pedir de volta)", "", "| Origem |", "|---|"] + [f"| {x['origem']} |" for x in lost] + [""]
    down = [x for x in r["resultados"] if x["situacao"] in ("origem fora do ar", "erro de acesso")]
    if down:
        out += ["## Origens fora do ar", "", "| Origem | Status |", "|---|---|"]
        out += [f"| {x['origem']} | {x['status'] or x.get('erro', '')} |" for x in down] + [""]
    active = [x for x in r["resultados"] if x["situacao"] == "ativo"]
    if active:
        out += ["## Links ativos", "", "| Origem | Alvo | rel | Âncora | Tipo |", "|---|---|---|---|---|"]
        for x in active[:200]:
            for lk in x["links"]:
                note = " (origem noindex)" if x["noindex"] else ""
                out.append(f"| {x['origem']}{note} | {lk['alvo']} | {lk['rel']} | {lk['ancora'][:60]} | {lk['tipo_ancora']} |")
        out.append("")
    if r["ancoras_mais_comuns"]:
        out += ["## Âncoras mais comuns", ""] + [f"- {a or '(vazia)'}: {n}" for a, n in r["ancoras_mais_comuns"]] + [""]
    out.append("_Leitura sem JavaScript: links inseridos por script podem aparecer como perdidos. Confira manualmente antes de cobrar._")
    return "\n".join(out)


def md_targets(r: Dict[str, Any]) -> str:
    out = ["# Páginas do site que recebem links", "",
           f"Verificadas: {r['verificadas']} · Fora do ar: {r['fora_do_ar']}", ""]
    if r["achados"]:
        out += [f"- **{a['nivel']}** {a['mensagem']}" for a in r["achados"]] + [""]
    out += ["| Situação | Página | Status | Sites | Links | Observação |", "|---|---|---|---|---|---|"]
    for e in r["resultados"]:
        out.append(f"| {e.get('situacao')} | {e['url']} | {e.get('status')} | {e['sites'] if e['sites'] is not None else '-'} | "
                   f"{e['links'] if e['links'] is not None else '-'} | {e.get('nota', '')} |")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("modo", choices=["origens", "destinos"])
    ap.add_argument("csv", help="CSV exportado (Search Console, Bing WMT, Ahrefs, Semrush...)")
    ap.add_argument("--dominio", help="(origens) domínio do seu site, ex.: seusite.com.br")
    ap.add_argument("--marca", action="append", default=[], help="(origens) nome da marca para classificar âncoras (pode repetir)")
    ap.add_argument("--coluna", help="nome da coluna de URLs, se a detecção automática errar")
    ap.add_argument("--site", help="(destinos) URL do site para completar caminhos relativos")
    ap.add_argument("--limite", type=int, default=300, help="(origens) máximo de origens verificadas")
    ap.add_argument("--atraso", type=float, default=0.5, help="segundos entre requisições")
    ap.add_argument("--format", choices=["md", "json"], default="md")
    args = ap.parse_args()

    try:
        rows = read_csv(args.csv)
    except OSError as err:
        print(f"erro: {err}", file=sys.stderr)
        sys.exit(2)
    if not rows:
        print("erro: CSV vazio", file=sys.stderr)
        sys.exit(2)

    if args.modo == "origens":
        if not args.dominio:
            print("erro: informe --dominio no modo origens", file=sys.stderr)
            sys.exit(2)
        column = args.coluna or find_column(rows, SOURCE_ALIASES, want_url=True)
        if not column:
            print("erro: não achei a coluna com as URLs de origem; use --coluna", file=sys.stderr)
            sys.exit(2)
        result = check_sources(rows, column, args.dominio, args.marca, args.limite, args.atraso)
        bad = result["perdidas"] > 0
        text = md_sources(result)
    else:
        column = args.coluna or find_column(rows, TARGET_ALIASES, want_url=True)
        if not column:
            print("erro: não achei a coluna com as páginas; use --coluna", file=sys.stderr)
            sys.exit(2)
        result = check_targets(rows, column, args.site, args.atraso)
        bad = result["fora_do_ar"] > 0
        text = md_targets(result)
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.format == "json" else text)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
