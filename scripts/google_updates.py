#!/usr/bin/env python3
"""Cruza a série diária de tráfego com as atualizações do Google (pilar 11, modo E da skill).

Usa data/atualizacoes-google.json (core, spam, políticas, recursos e rastreio, com fonte oficial).

  listar   mostra as atualizações num período (filtra por tipo)
  cruzar   lê um CSV diário (ex.: Search Console → Desempenho → Exportar → aba "Datas") e mede,
           para cada atualização de ranqueamento, a média de 14 dias antes do início contra a
           média de 14 dias depois do fim (ou do início + 14 dias, se não houver fim). Também lista as
           maiores quedas semanais e a atualização mais próxima de cada uma.

Correlação não é causa: confira primeiro medição e problemas técnicos (árvore do pilar 11).

Uso:
  python3 google_updates.py listar --desde 2026-01-01
  python3 google_updates.py listar --tipo core --tipo spam
  python3 google_updates.py cruzar datas.csv
  python3 google_updates.py cruzar datas.csv --coluna Impressões --limiar 0.2 --format json

Saída: 0 ok; 1 (cruzar) se alguma atualização coincide com variação acima do limiar; 2 falha.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _seo_common import find_column, load_json, read_csv  # noqa: E402

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "atualizacoes-google.json")
RANKING = {"core", "spam", "discover", "helpful", "reviews"}
WINDOW = 14


def parse_date(value: str) -> Optional[dt.date]:
    v = (value or "").strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return dt.datetime.strptime(v[:10], fmt).date()
        except ValueError:
            continue
    return None


def parse_number(value: str) -> Optional[float]:
    v = (value or "").strip().replace("%", "")
    if not v:
        return None
    if re.fullmatch(r"-?\d{1,3}(\.\d{3})+(,\d+)?", v):        # 1.234,5 (pt-BR)
        v = v.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"-?\d{1,3}(,\d{3})+(\.\d+)?", v):      # 1,234.5 (en)
        v = v.replace(",", "")
    else:
        v = v.replace(",", ".")
    try:
        return float(v)
    except ValueError:
        return None


def load_events(path: str = DATA) -> List[Dict[str, Any]]:
    return load_json(path)["eventos"]


def mean(values: List[float]) -> Optional[float]:
    return sum(values) / len(values) if values else None


def cross(series: Dict[dt.date, float], events: List[Dict[str, Any]], threshold: float) -> Dict[str, Any]:
    days = sorted(series)
    first, last = days[0], days[-1]
    rows: List[Dict[str, Any]] = []
    for ev in events:
        if ev["tipo"] not in RANKING:
            continue
        start = dt.date.fromisoformat(ev["inicio"])
        end = dt.date.fromisoformat(ev["fim"]) if ev.get("fim") else start + dt.timedelta(days=WINDOW)
        if end < first or start > last:
            continue
        before = [series[d] for d in days if start - dt.timedelta(days=WINDOW) <= d < start]
        after = [series[d] for d in days if end < d <= end + dt.timedelta(days=WINDOW)]
        mb, ma = mean(before), mean(after)
        change = (ma - mb) / mb if mb and ma is not None else None
        rows.append({"evento": ev["nome"], "tipo": ev["tipo"], "inicio": ev["inicio"], "fim": ev.get("fim"),
                     "media_antes": round(mb, 1) if mb is not None else None,
                     "media_depois": round(ma, 1) if ma is not None else None,
                     "variacao": round(change, 3) if change is not None else None,
                     "completo": len(before) >= WINDOW // 2 and len(after) >= WINDOW // 2,
                     "alerta": change is not None and abs(change) >= threshold,
                     "fonte": ev.get("fonte")})
    # quedas semanais (semana contra a anterior)
    weekly: List[Tuple[dt.date, float]] = []
    for i in range(14, len(days) + 1, 7):
        cur = [series[d] for d in days[i - 7:i]]
        prev = [series[d] for d in days[i - 14:i - 7]]
        if mean(prev):
            weekly.append((days[i - 7], (mean(cur) - mean(prev)) / mean(prev)))
    drops = sorted([w for w in weekly if w[1] <= -threshold], key=lambda w: w[1])[:5]
    nearest = []
    for week_start, change in drops:
        best = None
        for ev in events:
            s = dt.date.fromisoformat(ev["inicio"])
            dist = abs((s - week_start).days)
            if dist <= 10 and (best is None or dist < best[0]):
                best = (dist, ev)
        nearest.append({"semana": week_start.isoformat(), "variacao": round(change, 3),
                        "atualizacao_proxima": f"{best[1]['nome']} ({best[1]['inicio']})" if best else None})
    return {"periodo": [first.isoformat(), last.isoformat()], "dias": len(days), "atualizacoes": rows,
            "maiores_quedas_semanais": nearest, "alertas": sum(1 for r in rows if r["alerta"])}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    ls = sub.add_parser("listar")
    ls.add_argument("--desde")
    ls.add_argument("--ate")
    ls.add_argument("--tipo", action="append", help="core, spam, discover, politica, recurso, rastreio")
    ls.add_argument("--format", choices=["md", "json"], default="md")
    cr = sub.add_parser("cruzar")
    cr.add_argument("csv", help="CSV diário com uma coluna de data e uma métrica")
    cr.add_argument("--coluna", help="métrica (padrão: Cliques/Clicks)")
    cr.add_argument("--limiar", type=float, default=0.15, help="variação que gera alerta (0.15 = 15%%)")
    cr.add_argument("--format", choices=["md", "json"], default="md")
    for p in (ls, cr):
        p.add_argument("--dados", default=DATA, help="arquivo de atualizações (padrão: data/atualizacoes-google.json)")
    args = ap.parse_args()
    try:
        events = load_events(args.dados)
    except (OSError, ValueError, KeyError) as err:
        print(f"erro: não foi possível ler {args.dados}: {err}", file=sys.stderr)
        sys.exit(2)

    if args.cmd == "listar":
        sel = [e for e in events if (not args.desde or (e.get("fim") or e["inicio"]) >= args.desde)
               and (not args.ate or e["inicio"] <= args.ate) and (not args.tipo or e["tipo"] in args.tipo)]
        if args.format == "json":
            print(json.dumps(sel, ensure_ascii=False, indent=2))
        else:
            print("| Início | Fim | Tipo | Atualização | Fonte |\n|---|---|---|---|---|")
            for e in sel:
                print(f"| {e['inicio']} | {e.get('fim') or '-'} | {e['tipo']} | {e['nome']} | {e.get('fonte', '')} |")
            print("\n_Antes de diagnosticar, confira se o painel de status registrou algo depois desta lista._")
        return

    try:
        rows = read_csv(args.csv)
    except (OSError, UnicodeDecodeError) as err:
        print(f"erro: {err}", file=sys.stderr)
        sys.exit(2)
    date_col = find_column(rows, ["data", "date", "dia", "day"])
    metric_col = find_column(rows, [args.coluna] if args.coluna else ["cliques", "clicks", "sessões", "sessions", "impressões", "impressions"])
    if not date_col or not metric_col:
        print("erro: CSV precisa de uma coluna de data e uma de métrica (use --coluna)", file=sys.stderr)
        sys.exit(2)
    series: Dict[dt.date, float] = {}
    for r in rows:
        d, v = parse_date(r.get(date_col, "")), parse_number(r.get(metric_col, ""))
        if d and v is not None:
            series[d] = series.get(d, 0) + v
    if len(series) < 21:
        print("erro: a série precisa de pelo menos 21 dias", file=sys.stderr)
        sys.exit(2)
    res = cross(series, events, args.limiar)
    res["metrica"] = metric_col
    if args.format == "json":
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(f"# {metric_col} × atualizações do Google ({res['periodo'][0]} a {res['periodo'][1]})\n")
        print(f"Janela: {WINDOW} dias antes do início × {WINDOW} dias depois do fim. Limiar de alerta: {args.limiar:.0%}.\n")
        print("| Atualização | Período | Média antes | Média depois | Variação | Alerta |\n|---|---|---|---|---|---|")
        for r in res["atualizacoes"]:
            var = f"{r['variacao']:+.1%}" if r["variacao"] is not None else "-"
            flag = "**sim**" if r["alerta"] else ("dados parciais" if not r["completo"] else "não")
            print(f"| {r['evento']} | {r['inicio']} a {r['fim'] or '?'} | {r['media_antes']} | {r['media_depois']} | {var} | {flag} |")
        if res["maiores_quedas_semanais"]:
            print("\n## Maiores quedas semanais\n")
            for q in res["maiores_quedas_semanais"]:
                print(f"- Semana de {q['semana']}: {q['variacao']:+.1%}" + (f" · perto de: {q['atualizacao_proxima']}" if q["atualizacao_proxima"] else " · nenhuma atualização a até 10 dias"))
        print("\n_Coincidência de datas não prova causa. Descarte medição e problema técnico antes (pilar 11)._")
    sys.exit(1 if res["alertas"] else 0)


if __name__ == "__main__":
    main()
