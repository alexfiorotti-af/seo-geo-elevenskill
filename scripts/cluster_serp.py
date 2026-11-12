#!/usr/bin/env python3
"""Agrupa palavras-chave pela sobreposição de resultados no Google (pilar 9).

Se duas buscas mostram as mesmas URLs no top 10, o Google entende que têm a mesma intenção:
devem ser atendidas pela MESMA página. Se mostram resultados diferentes, merecem páginas
diferentes. É o critério mais seguro contra canibalização e contra páginas-porta.

Entrada: CSV com uma linha por (palavra, URL do resultado), exportado de qualquer ferramenta de
SERP (Semrush, Ahrefs, DataForSEO, SerpApi...) ou montado à mão. Colunas: palavra/keyword,
url, posição (opcional; usa só o top 10), volume (opcional, define a palavra principal).

Opcional: --mapa com o seu mapa de palavras-chave (palavra, url da sua página) para apontar
palavras do mesmo grupo em páginas diferentes e grupos diferentes na mesma página.

Uso:
  python3 cluster_serp.py serps.csv
  python3 cluster_serp.py serps.csv --minimo 4 --mapa templates/mapa-de-palavras-chave.csv --format json

Saída: 0 ok, 1 se o --mapa tiver conflitos, 2 falha de uso.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _seo_common import find_column, normalize, read_csv  # noqa: E402
from google_updates import parse_number  # noqa: E402


def clean_url(u: str) -> str:
    u = u.strip().split("#")[0].split("?")[0].rstrip("/").lower()
    return u.replace("https://", "").replace("http://", "").replace("www.", "")


def load_serps(path: str, depth: int) -> Tuple[Dict[str, Set[str]], Dict[str, float], Dict[str, str]]:
    rows = read_csv(path)
    kc = find_column(rows, ["palavra", "palavra-chave", "keyword", "query", "consulta"])
    uc = find_column(rows, ["url", "link", "resultado"], want_url=True)
    pc = find_column(rows, ["posição", "posicao", "position", "rank"])
    vc = find_column(rows, ["volume", "search volume", "buscas"])
    if not kc or not uc:
        raise ValueError("CSV precisa das colunas palavra e url")
    serps: Dict[str, Set[str]] = defaultdict(set)
    volume: Dict[str, float] = {}
    original: Dict[str, str] = {}
    for r in rows:
        k = normalize(r.get(kc, ""))
        u = r.get(uc, "")
        if not k or not u:
            continue
        pos = parse_number(r.get(pc, "")) if pc else None
        if pos is not None and pos > depth:
            continue
        serps[k].add(clean_url(u))
        original.setdefault(k, r.get(kc, "").strip())
        if vc:
            v = parse_number(r.get(vc, ""))
            if v is not None:
                volume[k] = max(volume.get(k, 0), v)
    return serps, volume, original


def cluster(serps: Dict[str, Set[str]], volume: Dict[str, float], minimum: int) -> List[Dict[str, Any]]:
    order = sorted(serps, key=lambda k: (-volume.get(k, 0), k))
    assigned: Dict[str, int] = {}
    groups: List[Dict[str, Any]] = []
    for seed in order:
        if seed in assigned:
            continue
        members = [seed]
        assigned[seed] = len(groups)
        for k in order:
            if k in assigned:
                continue
            if len(serps[seed] & serps[k]) >= minimum:
                members.append(k)
                assigned[k] = len(groups)
        groups.append({"principal": seed, "palavras": members,
                       "volume_total": sum(volume.get(m, 0) for m in members),
                       "urls_em_comum": sorted(set.intersection(*(serps[m] for m in members)))[:10] if len(members) > 1 else []})
    return groups


def check_map(groups: List[Dict[str, Any]], map_rows: List[Dict[str, str]]) -> List[str]:
    kc = find_column(map_rows, ["palavra_principal", "palavra", "keyword", "palavra-chave"])
    uc = find_column(map_rows, ["url", "pagina", "página", "slug"], want_url=True)
    if not kc or not uc:
        return ["--mapa sem colunas palavra e url"]
    page_of = {normalize(r.get(kc, "")): (r.get(uc) or "").strip() for r in map_rows if r.get(kc)}
    conflicts: List[str] = []
    group_of: Dict[str, int] = {}
    for i, g in enumerate(groups):
        for k in g["palavras"]:
            group_of[k] = i
        pages = {page_of[k] for k in g["palavras"] if k in page_of and page_of[k]}
        if len(pages) > 1:
            conflicts.append(f"Mesma intenção em páginas diferentes (canibalização): {', '.join(g['palavras'][:5])} → {', '.join(sorted(pages))}")
    by_page: Dict[str, Set[int]] = defaultdict(set)
    for k, p in page_of.items():
        if k in group_of and p:
            by_page[p].add(group_of[k])
    for p, gs in by_page.items():
        if len(gs) > 1:
            names = [groups[i]["principal"] for i in sorted(gs)]
            conflicts.append(f"Intenções diferentes na mesma página {p}: {', '.join(names)} (considere páginas separadas)")
    return conflicts


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv")
    ap.add_argument("--minimo", type=int, default=3, help="URLs em comum no top 10 para juntar (padrão 3)")
    ap.add_argument("--profundidade", type=int, default=10)
    ap.add_argument("--mapa", help="CSV do seu mapa de palavras-chave (palavra, url)")
    ap.add_argument("--format", choices=["md", "json"], default="md")
    args = ap.parse_args()
    try:
        serps, volume, original = load_serps(args.csv, args.profundidade)
        map_rows: Optional[List[Dict[str, str]]] = read_csv(args.mapa) if args.mapa else None
    except (OSError, ValueError) as err:
        print(f"erro: {err}", file=sys.stderr)
        sys.exit(2)
    groups = cluster(serps, volume, args.minimo)
    conflicts = check_map(groups, map_rows) if map_rows is not None else []  # compara texto normalizado
    for g in groups:
        g["principal"] = original.get(g["principal"], g["principal"])
        g["palavras"] = [original.get(k, k) for k in g["palavras"]]
    res = {"palavras": len(serps), "grupos": groups, "conflitos_com_mapa": conflicts}
    if args.format == "json":
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(f"# Grupos por intenção ({len(serps)} palavras, {len(groups)} grupos, mínimo {args.minimo} URLs em comum)\n")
        print("| Página sugerida para | Palavras do grupo | Volume |\n|---|---|---|")
        for g in sorted(groups, key=lambda g: -g["volume_total"]):
            print(f"| {g['principal']} | {', '.join(g['palavras'])} | {int(g['volume_total']) or '-'} |")
        if conflicts:
            print("\n## Conflitos com o mapa\n")
            print("\n".join(f"- {c}" for c in conflicts))
    sys.exit(1 if conflicts else 0)


if __name__ == "__main__":
    main()
