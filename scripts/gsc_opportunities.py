#!/usr/bin/env python3
"""Encontra oportunidades numa exportação de Desempenho do Search Console (pilares 8, 9 e 10).

Funciona offline com o CSV exportado (aba Consultas, aba Páginas ou uma planilha com consulta E
página, como a da API/Looker Studio). Colunas reconhecidas em português ou inglês: consulta/query,
página/page, cliques/clicks, impressões/impressions, CTR, posição/position.

Análises:
  - quase lá: posição média entre 4 e 20 com muitas impressões (melhorar conteúdo e links internos);
  - CTR abaixo do padrão DO PRÓPRIO SITE para a mesma faixa de posição (reescrever title/description);
  - canibalização: a mesma consulta dividida entre duas ou mais páginas (precisa de consulta + página);
  - perguntas e consultas longas (6+ palavras): pauta para seções citáveis (pilar 10);
  - marca × sem marca, se --marca for informado.

Uso:
  python3 gsc_opportunities.py Consultas.csv
  python3 gsc_opportunities.py consultas-paginas.csv --marca "aurora" --min-impressoes 50
  python3 gsc_opportunities.py Consultas.csv --format json

Saída: 0 ok, 2 falha de uso.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
from collections import defaultdict
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _seo_common import find_column, normalize, read_csv  # noqa: E402
from google_updates import parse_number  # noqa: E402

QUESTION = re.compile(r"^(como|qual|quais|quanto|quantos|quantas|quando|onde|por que|porque|o que|quem|"
                      r"vale a pena|pode|posso|devo|what|how|why|when|where|which|who|can|should|is|does)\b", re.I)


def bucket(pos: float) -> str:
    if pos < 1.5:
        return "1"
    if pos < 2.5:
        return "2"
    if pos < 3.5:
        return "3"
    if pos < 5.5:
        return "4-5"
    if pos < 10.5:
        return "6-10"
    if pos < 20.5:
        return "11-20"
    return "21+"


def load(path: str) -> List[Dict[str, Any]]:
    rows = read_csv(path)
    cols = {
        "consulta": find_column(rows, ["consultas principais", "consulta", "query", "top queries", "queries"]),
        "pagina": find_column(rows, ["páginas principais", "pagina", "página", "page", "top pages", "landing page", "url"]),
        "cliques": find_column(rows, ["cliques", "clicks"]),
        "impressoes": find_column(rows, ["impressões", "impressoes", "impressions"]),
        "ctr": find_column(rows, ["ctr"]),
        "posicao": find_column(rows, ["posição", "posicao", "position", "posição média", "average position"]),
    }
    if not cols["impressoes"] or not cols["posicao"] or not (cols["consulta"] or cols["pagina"]):
        raise ValueError("o CSV precisa de impressões, posição e consulta ou página")
    out = []
    for r in rows:
        imp = parse_number(r.get(cols["impressoes"], "")) or 0
        pos = parse_number(r.get(cols["posicao"], ""))
        if not imp or pos is None:
            continue
        clicks = parse_number(r.get(cols["cliques"], "")) if cols["cliques"] else None
        raw_ctr = (r.get(cols["ctr"]) or "") if cols["ctr"] else ""
        ctr = parse_number(raw_ctr) if raw_ctr else None
        if ctr is not None and ("%" in raw_ctr or ctr > 1):
            ctr /= 100
        if ctr is None and clicks is not None:
            ctr = clicks / imp
        out.append({"consulta": (r.get(cols["consulta"]) or "").strip() if cols["consulta"] else "",
                    "pagina": (r.get(cols["pagina"]) or "").strip() if cols["pagina"] else "",
                    "cliques": clicks or 0, "impressoes": imp, "ctr": ctr or 0.0, "posicao": pos})
    return out


def analyze(rows: List[Dict[str, Any]], min_imp: int, brand: List[str], top: int) -> Dict[str, Any]:
    label = "consulta" if any(r["consulta"] for r in rows) else "pagina"
    # padrão de CTR do próprio site por faixa de posição (mediana, só linhas com volume)
    by_bucket: Dict[str, List[float]] = defaultdict(list)
    for r in rows:
        if r["impressoes"] >= min_imp:
            by_bucket[bucket(r["posicao"])].append(r["ctr"])
    baseline = {b: statistics.median(v) for b, v in by_bucket.items() if len(v) >= 5}

    striking = sorted([r for r in rows if 4 <= r["posicao"] <= 20 and r["impressoes"] >= min_imp],
                      key=lambda r: r["impressoes"], reverse=True)[:top]
    low_ctr = []
    for r in rows:
        b = bucket(r["posicao"])
        ref = baseline.get(b)
        if r["posicao"] <= 10.5 and ref and r["impressoes"] >= min_imp and r["ctr"] < ref * 0.5:
            low_ctr.append({**r, "ctr_padrao_do_site": round(ref, 4),
                            "cliques_perdidos_estimados": round(r["impressoes"] * (ref - r["ctr"]))})
    low_ctr.sort(key=lambda r: r["cliques_perdidos_estimados"], reverse=True)

    cannibal = []
    if any(r["consulta"] for r in rows) and any(r["pagina"] for r in rows):
        groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for r in rows:
            if r["consulta"] and r["pagina"]:
                groups[normalize(r["consulta"])].append(r)
        for q, rs in groups.items():
            total = sum(x["impressoes"] for x in rs)
            pages = [x for x in rs if x["impressoes"] >= 0.1 * total]
            if len({x["pagina"] for x in pages}) >= 2 and total >= min_imp:
                cannibal.append({"consulta": rs[0]["consulta"], "impressoes": total,
                                 "paginas": [f"{x['pagina']} (pos. {x['posicao']:.1f}, {int(x['impressoes'])} impr.)"
                                             for x in sorted(pages, key=lambda x: -x["impressoes"])]})
        cannibal.sort(key=lambda c: -c["impressoes"])

    questions = sorted([r for r in rows if r["consulta"] and QUESTION.match(normalize(r["consulta"]))],
                       key=lambda r: -r["impressoes"])[:top]
    long_q = [r for r in rows if r["consulta"] and len(r["consulta"].split()) >= 6]
    brand_split = None
    if brand and any(r["consulta"] for r in rows):
        terms = [normalize(b) for b in brand]
        is_b = lambda q: any(t in normalize(q) for t in terms)  # noqa: E731
        b = [r for r in rows if is_b(r["consulta"])]
        nb = [r for r in rows if r["consulta"] and not is_b(r["consulta"])]
        brand_split = {"marca_cliques": sum(r["cliques"] for r in b), "sem_marca_cliques": sum(r["cliques"] for r in nb),
                       "marca_impressoes": sum(r["impressoes"] for r in b), "sem_marca_impressoes": sum(r["impressoes"] for r in nb)}
    findings = []
    if striking:
        findings.append({"nivel": "AVISO", "pilar": "9", "mensagem": f"{len(striking)} {label}(s) entre as posições 4 e 20 com volume: prioridade de conteúdo e links internos.",
                         "itens": [f"{r[label]} (pos. {r['posicao']:.1f}, {int(r['impressoes'])} impr.)" for r in striking[:20]]})
    if low_ctr:
        findings.append({"nivel": "AVISO", "pilar": "8", "mensagem": f"{len(low_ctr)} {label}(s) com CTR abaixo da metade do padrão do site na mesma posição: revise title e description.",
                         "itens": [f"{r[label]} (pos. {r['posicao']:.1f}, CTR {r['ctr']:.1%} vs {r['ctr_padrao_do_site']:.1%})" for r in low_ctr[:20]]})
    if cannibal:
        findings.append({"nivel": "AVISO", "pilar": "9", "mensagem": f"{len(cannibal)} consulta(s) divididas entre páginas (canibalização): defina a página principal.",
                         "itens": [f"{c['consulta']}: {' | '.join(c['paginas'][:3])}" for c in cannibal[:20]]})
    if questions:
        findings.append({"nivel": "INFO", "pilar": "10", "mensagem": f"{len(questions)} pergunta(s) reais nas consultas: use como H2/H3 com resposta direta.",
                         "itens": [q["consulta"] for q in questions[:20]]})
    return {"linhas": len(rows), "dimensao": label, "ctr_padrao_por_posicao": {k: round(v, 4) for k, v in sorted(baseline.items())},
            "oportunidades": {"quase_la": striking, "ctr_baixo": low_ctr[:top], "canibalizacao": cannibal[:top],
                              "perguntas": questions, "consultas_longas": len(long_q)},
            "marca": brand_split, "achados": findings}


def to_md(r: Dict[str, Any]) -> str:
    out = [f"# Oportunidades no Search Console ({r['linhas']} linhas por {r['dimensao']})", ""]
    if r["ctr_padrao_por_posicao"]:
        out += ["CTR mediano do próprio site por faixa de posição: " +
                ", ".join(f"{k}: {v:.1%}" for k, v in r["ctr_padrao_por_posicao"].items()), ""]
    if r["marca"]:
        m = r["marca"]
        out += [f"Cliques com marca: {int(m['marca_cliques'])} · sem marca: {int(m['sem_marca_cliques'])}", ""]
    for f in r["achados"]:
        out += [f"## {f['nivel']} (pilar {f['pilar']}): {f['mensagem']}", ""] + [f"- {i}" for i in f["itens"]] + [""]
    out.append(f"Consultas com 6+ palavras (tom de conversa, típico de busca com IA): {r['oportunidades']['consultas_longas']}.")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv")
    ap.add_argument("--min-impressoes", type=int, default=100)
    ap.add_argument("--marca", action="append", default=[], help="termo de marca (pode repetir)")
    ap.add_argument("--top", type=int, default=30)
    ap.add_argument("--format", choices=["md", "json"], default="md")
    args = ap.parse_args()
    try:
        rows = load(args.csv)
    except (OSError, ValueError) as err:
        print(f"erro: {err}", file=sys.stderr)
        sys.exit(2)
    r = analyze(rows, args.min_impressoes, args.marca, args.top)
    print(json.dumps(r, ensure_ascii=False, indent=2) if args.format == "json" else to_md(r))


if __name__ == "__main__":
    main()
