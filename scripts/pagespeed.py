#!/usr/bin/env python3
"""Core Web Vitals de campo (CrUX) e laboratório (Lighthouse) pela API do PageSpeed Insights (pilar 5).

Campo = dados reais de usuários do Chrome nos últimos 28 dias (é o que o Google usa); só existe
para páginas/origens com tráfego suficiente. Laboratório = uma execução simulada, útil para achar
a causa. Limiares "bons" no percentil 75: LCP ≤ 2,5 s · INP ≤ 200 ms · CLS ≤ 0,1.

A chave da API é opcional para poucas consultas; para lotes, crie uma no Google Cloud e passe por
variável de ambiente PAGESPEED_API_KEY (nunca no código ou no relatório).

Uso:
  python3 pagespeed.py https://dominio.com/
  python3 pagespeed.py https://dominio.com/ --estrategia desktop --format json
  python3 pagespeed.py --arquivo resposta-psi.json        # lê uma resposta salva (sem rede)

Saída: 0 tudo bom, 1 alguma métrica de campo ruim ou a melhorar, 2 falha de uso ou de rede.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _seo_common import fetch, load_json  # noqa: E402

API = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
FIELD = {  # chave da API → (nome, limiar bom, limiar ruim, divisor, unidade)
    "LARGEST_CONTENTFUL_PAINT_MS": ("LCP", 2500, 4000, 1000, "s"),
    "INTERACTION_TO_NEXT_PAINT": ("INP", 200, 500, 1, "ms"),
    "CUMULATIVE_LAYOUT_SHIFT_SCORE": ("CLS", 10, 25, 100, ""),
    "FIRST_CONTENTFUL_PAINT_MS": ("FCP", 1800, 3000, 1000, "s"),
    "EXPERIMENTAL_TIME_TO_FIRST_BYTE": ("TTFB", 800, 1800, 1000, "s"),
}
CORE = {"LCP", "INP", "CLS"}


def rate(value: float, good: float, poor: float) -> str:
    return "bom" if value <= good else "a melhorar" if value <= poor else "ruim"


def field_metrics(block: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    metrics = (block or {}).get("metrics") or {}
    for key, (name, good, poor, div, unit) in FIELD.items():
        m = metrics.get(key)
        if not m or "percentile" not in m:
            continue
        p75 = m["percentile"]
        out.append({"metrica": name, "p75": round(p75 / div, 3), "unidade": unit, "avaliacao": rate(p75, good, poor)})
    return out


def parse(data: Dict[str, Any]) -> Dict[str, Any]:
    lh = data.get("lighthouseResult") or {}
    audits = lh.get("audits") or {}
    perf = ((lh.get("categories") or {}).get("performance") or {}).get("score")
    lab = {}
    for key, name in (("largest-contentful-paint", "LCP"), ("total-blocking-time", "TBT"),
                      ("cumulative-layout-shift", "CLS"), ("speed-index", "Speed Index")):
        if key in audits:
            lab[name] = audits[key].get("displayValue")
    opps = []
    for key, a in audits.items():
        det = a.get("details") or {}
        saving = det.get("overallSavingsMs") or (a.get("metricSavings") or {}).get("LCP")
        if saving and a.get("score") is not None and a["score"] < 0.9:
            opps.append({"auditoria": a.get("title", key), "economia_ms": round(saving)})
    opps.sort(key=lambda o: -o["economia_ms"])
    page = field_metrics(data.get("loadingExperience"))
    origin = field_metrics(data.get("originLoadingExperience"))
    findings = []
    used = page or origin
    scope = "da página" if page else "da origem (página sem dados próprios)"
    for m in used:
        if m["metrica"] in CORE and m["avaliacao"] != "bom":
            findings.append({"nivel": "ERRO" if m["avaliacao"] == "ruim" else "AVISO", "pilar": "5",
                             "mensagem": f"{m['metrica']} {scope} no p75: {m['p75']}{m['unidade']} ({m['avaliacao']})."})
    if not used:
        findings.append({"nivel": "INFO", "pilar": "5", "mensagem": "Sem dados de campo (CrUX): pouco tráfego no Chrome. Use o laboratório como guia."})
    for o in opps[:5]:
        findings.append({"nivel": "INFO", "pilar": "5", "mensagem": f"Oportunidade de laboratório: {o['auditoria']} (~{o['economia_ms']} ms)."})
    return {"url": data.get("id") or lh.get("finalUrl"), "estrategia": (lh.get("configSettings") or {}).get("formFactor"),
            "cwv": {"pagina": page, "origem": origin}, "laboratorio": {"nota_performance": round(perf * 100) if perf is not None else None, **lab},
            "oportunidades": opps[:10], "achados": findings, "erros": sum(1 for f in findings if f["nivel"] in ("ERRO", "AVISO"))}


def to_md(r: Dict[str, Any]) -> str:
    out = [f"# PageSpeed: {r['url']} ({r['estrategia'] or '-'})", ""]
    for label, rows in (("Campo, página (CrUX p75)", r["cwv"]["pagina"]), ("Campo, origem (CrUX p75)", r["cwv"]["origem"])):
        if rows:
            out += [f"## {label}", "", "| Métrica | p75 | Avaliação |", "|---|---|---|"]
            out += [f"| {m['metrica']} | {m['p75']}{m['unidade']} | {m['avaliacao']} |" for m in rows] + [""]
    lab = r["laboratorio"]
    out += ["## Laboratório (Lighthouse)", "", ", ".join(f"{k}: {v}" for k, v in lab.items() if v is not None), ""]
    out += ["## Achados", ""] + [f"- **{f['nivel']}** {f['mensagem']}" for f in r["achados"]]
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url", nargs="?")
    ap.add_argument("--estrategia", choices=["mobile", "desktop"], default="mobile")
    ap.add_argument("--arquivo", help="resposta JSON da API já salva")
    ap.add_argument("--format", choices=["md", "json"], default="md")
    args = ap.parse_args()
    try:
        if args.arquivo:
            data = load_json(args.arquivo)
        elif args.url:
            q = {"url": args.url, "strategy": args.estrategia, "category": "performance"}
            key = os.environ.get("PAGESPEED_API_KEY")
            if key:
                q["key"] = key
            f = fetch(API + "?" + urllib.parse.urlencode(q))
            if f.status != 200:
                msg = f.text()[:300].replace(key or "\0", "***") if key else f.text()[:300]
                print(f"erro: API respondeu {f.status}: {msg}", file=sys.stderr)
                sys.exit(2)
            data = json.loads(f.text())
        else:
            print("erro: informe a URL ou --arquivo", file=sys.stderr)
            sys.exit(2)
    except (OSError, ValueError) as err:
        print(f"erro: {err}", file=sys.stderr)
        sys.exit(2)
    r = parse(data)
    print(json.dumps(r, ensure_ascii=False, indent=2) if args.format == "json" else to_md(r))
    sys.exit(1 if r["erros"] else 0)


if __name__ == "__main__":
    main()
