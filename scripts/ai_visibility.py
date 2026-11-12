#!/usr/bin/env python3
"""Resume a amostragem manual de visibilidade em IA (pilares 10 e 11).

Não existe painel oficial de "posição no ChatGPT". O método confiável e barato: uma lista fixa de
perguntas reais do público, feitas todo mês nas mesmas plataformas, anotadas numa planilha
(templates/amostragem-ia.csv). Este script transforma a planilha em indicadores:
  - taxa de citação da marca por plataforma e por mês (share of voice nas respostas);
  - páginas do site que aparecem como fonte;
  - concorrentes citados e quantas vezes;
  - domínios mais usados como fonte pelas IAs (alvos de menção e de link, pilar 10b);
  - perguntas em que a marca nunca aparece (pauta de conteúdo).

Colunas: data, plataforma, prompt, marca_citada (sim/não), url_citada, posicao_marca,
concorrentes_citados (separados por ;), fontes_citadas (URLs ou domínios separados por ;),
sentimento (positivo/neutro/negativo), observacoes.

Uso:
  python3 ai_visibility.py amostragem.csv
  python3 ai_visibility.py amostragem.csv --format json

Saída: 0 ok, 2 falha de uso.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _seo_common import find_column, host_key, normalize, read_csv  # noqa: E402
from google_updates import parse_date  # noqa: E402

YES = {"sim", "s", "yes", "y", "1", "true", "x"}


def split(v: str) -> List[str]:
    return [x.strip() for x in re.split(r"[;|\n]", v or "") if x.strip()]


def summarize(rows: List[Dict[str, str]]) -> Dict[str, Any]:
    c = {k: find_column(rows, al) for k, al in {
        "data": ["data", "date", "mes", "mês"], "plataforma": ["plataforma", "platform", "ia", "motor"],
        "prompt": ["prompt", "pergunta", "consulta"], "marca": ["marca_citada", "marca citada", "citada", "brand_mentioned"],
        "url": ["url_citada", "url citada", "pagina_citada"], "posicao": ["posicao_marca", "posição", "posicao"],
        "conc": ["concorrentes_citados", "concorrentes"], "fontes": ["fontes_citadas", "fontes", "sources"],
        "sent": ["sentimento", "sentiment"]}.items()}
    if not c["plataforma"] or not c["prompt"] or not c["marca"]:
        raise ValueError("a planilha precisa das colunas plataforma, prompt e marca_citada")
    g = lambda r, k: (r.get(c[k]) or "").strip() if c[k] else ""  # noqa: E731
    by_plat: Dict[str, List[int]] = defaultdict(lambda: [0, 0])
    by_month: Dict[str, List[int]] = defaultdict(lambda: [0, 0])
    prompts: Dict[str, List[int]] = defaultdict(lambda: [0, 0])
    urls, comps, domains, sents = Counter(), Counter(), Counter(), Counter()
    for r in rows:
        if not g(r, "prompt"):
            continue
        cited = normalize(g(r, "marca")) in YES
        plat = g(r, "plataforma") or "(sem plataforma)"
        d = parse_date(g(r, "data"))
        month = d.strftime("%Y-%m") if d else (g(r, "data")[:7] or "(sem data)")
        for bucket in (by_plat[plat], by_month[month], prompts[g(r, "prompt")]):
            bucket[0] += int(cited)
            bucket[1] += 1
        if g(r, "url"):
            urls[g(r, "url")] += 1
        for x in split(g(r, "conc")):
            comps[x] += 1
        for x in split(g(r, "fontes")):
            domains[host_key(x) if "." in x else x] += 1
        if cited and g(r, "sent"):
            sents[normalize(g(r, "sent"))] += 1
    total = sum(v[1] for v in by_plat.values())
    cited_total = sum(v[0] for v in by_plat.values())
    never = sorted(p for p, v in prompts.items() if v[0] == 0)
    rate = lambda v: round(v[0] / v[1], 3) if v[1] else 0  # noqa: E731
    return {
        "respostas": total, "citacoes_da_marca": cited_total, "taxa_geral": round(cited_total / total, 3) if total else 0,
        "por_plataforma": {k: {"citada": v[0], "respostas": v[1], "taxa": rate(v)} for k, v in sorted(by_plat.items())},
        "por_mes": {k: {"citada": v[0], "respostas": v[1], "taxa": rate(v)} for k, v in sorted(by_month.items())},
        "paginas_citadas": urls.most_common(15), "concorrentes": comps.most_common(15),
        "dominios_fonte": domains.most_common(20), "sentimento": dict(sents),
        "perguntas_sem_a_marca": never,
    }


def to_md(r: Dict[str, Any]) -> str:
    out = ["# Visibilidade em IA (amostragem manual)", "",
           f"Respostas analisadas: {r['respostas']} · Marca citada em {r['citacoes_da_marca']} ({r['taxa_geral']:.0%})", "",
           "| Plataforma | Citada / respostas | Taxa |", "|---|---|---|"]
    out += [f"| {k} | {v['citada']} / {v['respostas']} | {v['taxa']:.0%} |" for k, v in r["por_plataforma"].items()]
    if len(r["por_mes"]) > 1:
        out += ["", "| Mês | Citada / respostas | Taxa |", "|---|---|---|"]
        out += [f"| {k} | {v['citada']} / {v['respostas']} | {v['taxa']:.0%} |" for k, v in r["por_mes"].items()]
    if r["concorrentes"]:
        out += ["", "## Concorrentes citados", ""] + [f"- {n}: {q}" for n, q in r["concorrentes"]]
    if r["paginas_citadas"]:
        out += ["", "## Páginas do site citadas como fonte", ""] + [f"- {u}: {q}" for u, q in r["paginas_citadas"]]
    if r["dominios_fonte"]:
        out += ["", "## Domínios que as IAs usam como fonte (alvos de menção e link)", ""] + [f"- {d}: {q}" for d, q in r["dominios_fonte"]]
    if r["perguntas_sem_a_marca"]:
        out += ["", "## Perguntas em que a marca nunca aparece (pauta)", ""] + [f"- {p}" for p in r["perguntas_sem_a_marca"]]
    out += ["", "_Respostas de IA variam a cada execução: compare tendências mensais com a mesma lista de perguntas, não respostas isoladas._"]
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv")
    ap.add_argument("--format", choices=["md", "json"], default="md")
    args = ap.parse_args()
    try:
        r = summarize(read_csv(args.csv))
    except (OSError, ValueError) as err:
        print(f"erro: {err}", file=sys.stderr)
        sys.exit(2)
    print(json.dumps(r, ensure_ascii=False, indent=2) if args.format == "json" else to_md(r))


if __name__ == "__main__":
    main()
