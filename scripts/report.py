#!/usr/bin/env python3
"""Junta as saídas JSON dos scripts num relatório único, com nota por pilar (modo H da skill).

Rode os scripts com --format json, salve cada saída num arquivo e passe todos para este script.
Ele reconhece sozinho de qual script veio cada arquivo (audit_page, crawl_site, check_robots,
check_server, check_agents, lint_schema, analyze_content, check_local, drift, llms_txt,
verify_backlinks, pagespeed, gsc_opportunities), agrupa os achados por pilar e gera:
  - HTML pronto para enviar ou imprimir em PDF (A4), com a marca da agência se houver;
  - JSON consolidado, para comparar com o próximo relatório (--anterior).

Nota por pilar (heurística, para acompanhar evolução, não é métrica do Google):
  100 − 15 por ERRO − 5 por AVISO − 1 por INFO, mínimo 0. Pilares sem verificação ficam "não avaliado".

Marca (opcional, fica fora do repositório público): metodologia-local/marca.json com
  {"nome": "...", "cor_primaria": "#0B2A5E", "cor_destaque": "#FD5917", "logo": "caminho/ou/URL", "rodape": "..."}
Modelo: templates/marca.exemplo.json.

Uso:
  python3 report.py relatorios/*.json --site https://dominio.com --saida relatorios/relatorio.html
  python3 report.py relatorios/*.json --site https://dominio.com --anterior relatorios/2026-10.json \\
      --saida relatorios/relatorio.html --json-saida relatorios/2026-11.json
  python3 report.py relatorios/*.json --format md

Saída: 0 ok, 1 se houver ERRO nos achados, 2 falha de uso.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import html
import json
import mimetypes
import os
import re
import sys
from collections import defaultdict
from typing import Any, Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PILLARS = {
    "1": "Arquitetura de URLs e informação", "2": "Rastreabilidade (robots, sitemap, robôs de IA)",
    "3": "Indexação (status, canonical, redirects, hreflang)", "4": "Renderização (HTML do servidor)",
    "5": "Performance e servidor", "6": "Dados estruturados", "7": "Responsividade, semântica, acessibilidade",
    "8": "Metadados (title, description, OG)", "9": "Palavras-chave e conteúdo",
    "10": "GEO e autoridade (citabilidade, entidade, links)", "11": "Medição, governança e spam",
}
WEIGHTS = {"1": 1, "2": 1.5, "3": 1.5, "4": 1.5, "5": 1, "6": 1, "7": 1, "8": 1, "9": 1, "10": 1, "11": 0.5}
PENALTY = {"ERRO": 15, "AVISO": 5, "INFO": 1}
ORDER = {"ERRO": 0, "AVISO": 1, "INFO": 2}


def detect(data: Any) -> str:
    if isinstance(data, list):
        return "lint_schema" if data and isinstance(data[0], dict) and "blocos" in data[0] else "desconhecido"
    if not isinstance(data, dict):
        return "desconhecido"
    keys = set(data)
    checks = [("robots_txt", "check_robots"), ("paginas_rastreadas", "crawl_site"), ("title_px", "audit_page"),
              ("citabilidade", "analyze_content"), ("agentes", "check_agents"), ("mudancas", "drift"),
              ("origem_referencia", "check_local"), ("ttfb_s", "check_server"), ("cwv", "pagespeed"),
              ("oportunidades", "gsc_opportunities")]
    for key, name in checks:
        if key in keys:
            return name
    if "modo" in keys and "resultados" in keys:
        return "verify_backlinks"
    if {"links", "secoes"} <= keys:
        return "llms_txt"
    return "desconhecido"


DEFAULT_PILLAR = {"crawl_site": "3", "check_agents": "2", "lint_schema": "6", "check_local": "10", "drift": "11",
                  "llms_txt": "2", "verify_backlinks": "10", "pagespeed": "5", "gsc_opportunities": "9", "check_robots": "2"}


def normalize_findings(kind: str, data: Any, label: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []

    def push(level: str, pillar: Optional[str], msg: str, items: Optional[List[str]] = None, where: str = "") -> None:
        out.append({"fonte": kind, "arquivo": label, "nivel": level, "pilar": str(pillar or DEFAULT_PILLAR.get(kind, "11")),
                    "mensagem": msg, "itens": list(items or [])[:30], "onde": where})

    if kind == "lint_schema":
        for r in data:
            for f in r.get("achados", []):
                push(f["nivel"], "6", f["mensagem"], where=f"{r.get('alvo')} · {f.get('onde', '')}")
        return out
    if kind == "check_robots":
        for n in data.get("observacoes", []):
            low = n.lower()
            level = "ERRO" if ("busca bloqueados" in low or "urgência" in low or "429" in n or "search=no" in low) else \
                "INFO" if ("treino" in low or "convenção" in low) else "AVISO"
            push(level, "2", n)
        return out
    if kind == "drift":
        for c in data.get("mudancas", []):
            push(c["nivel"], "11", c["mensagem"], where=c.get("url", ""))
        return out
    where = data.get("url") or data.get("inicio") or data.get("alvo") or ""
    for f in data.get("achados", []):
        push(f.get("nivel", "INFO"), f.get("pilar"), f.get("mensagem", ""), f.get("itens"), f.get("onde") or where)
    return out


def score(findings: List[Dict[str, Any]], evaluated: set) -> Dict[str, Any]:
    per: Dict[str, Dict[str, Any]] = {}
    counts: Dict[str, Dict[str, int]] = defaultdict(lambda: {"ERRO": 0, "AVISO": 0, "INFO": 0})
    for f in findings:
        counts[f["pilar"]][f["nivel"]] += 1
    total_w = total = 0.0
    for pid, name in PILLARS.items():
        if pid not in evaluated and pid not in counts:
            per[pid] = {"nome": name, "nota": None, **{k: 0 for k in PENALTY}}
            continue
        c = counts[pid]
        s = max(0, 100 - sum(PENALTY[k] * v for k, v in c.items()))
        per[pid] = {"nome": name, "nota": s, **c}
        total_w += WEIGHTS[pid]
        total += WEIGHTS[pid] * s
    return {"pilares": per, "geral": round(total / total_w) if total_w else None}


EVALUATES = {"audit_page": {"3", "4", "5", "6", "7", "8", "9"}, "crawl_site": {"1", "3", "9"}, "check_robots": {"2"},
             "check_server": {"2", "3", "5"}, "check_agents": {"2", "4"}, "lint_schema": {"6"},
             "analyze_content": {"9", "10"}, "check_local": {"10"}, "drift": {"11"}, "llms_txt": {"2"},
             "verify_backlinks": {"10"}, "pagespeed": {"5"}, "gsc_opportunities": {"9"}}


def key_of(f: Dict[str, Any]) -> str:
    return f"{f['fonte']}|{f['pilar']}|{re.sub(r'[0-9.,]+', '#', f['mensagem'])[:120]}|{f.get('onde', '')}"


def build(files: List[str], site: str, previous: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    findings: List[Dict[str, Any]] = []
    sources: List[Dict[str, str]] = []
    evaluated: set = set()
    for path in files:
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError) as err:
            sources.append({"arquivo": os.path.basename(path), "tipo": f"ignorado ({err})"})
            continue
        kind = detect(data)
        sources.append({"arquivo": os.path.basename(path), "tipo": kind})
        if kind == "desconhecido":
            continue
        evaluated |= EVALUATES.get(kind, set())
        findings += normalize_findings(kind, data, os.path.basename(path))
    findings.sort(key=lambda f: (ORDER.get(f["nivel"], 3), int(f["pilar"]) if f["pilar"].isdigit() else 99))
    sc = score(findings, evaluated)
    rep = {"site": site, "data": dt.date.today().isoformat(), "fontes": sources, "nota_geral": sc["geral"],
           "pilares": sc["pilares"], "achados": findings,
           "totais": {k: sum(1 for f in findings if f["nivel"] == k) for k in PENALTY}}
    if previous:
        old_keys = {key_of(f) for f in previous.get("achados", [])}
        new_keys = {key_of(f) for f in findings}
        rep["comparacao"] = {
            "data_anterior": previous.get("data"), "nota_anterior": previous.get("nota_geral"),
            "resolvidos": sum(1 for k in old_keys - new_keys),
            "novos": sum(1 for k in new_keys - old_keys),
            "pilares": {pid: (previous.get("pilares", {}).get(pid, {}) or {}).get("nota") for pid in PILLARS},
        }
        for f in findings:
            f["novo"] = key_of(f) not in old_keys
    return rep


def load_brand(path: Optional[str]) -> Dict[str, str]:
    candidate = path or os.path.join(ROOT, "metodologia-local", "marca.json")
    brand = {"nome": "", "cor_primaria": "#0B2A5E", "cor_destaque": "#FD5917", "logo": "", "rodape": ""}
    if os.path.exists(candidate):
        try:
            with open(candidate, encoding="utf-8") as fh:
                brand.update({k: str(v) for k, v in json.load(fh).items() if v})
        except (OSError, ValueError):
            pass
    for k in ("cor_primaria", "cor_destaque"):
        if not re.fullmatch(r"#[0-9a-fA-F]{3,8}", brand[k]):
            brand[k] = "#0B2A5E" if k == "cor_primaria" else "#FD5917"
    logo = brand.get("logo", "")
    if logo and not logo.startswith(("http://", "https://", "data:")):
        base = os.path.dirname(candidate)
        lp = logo if os.path.isabs(logo) else os.path.join(base, logo)
        if os.path.exists(lp):
            mime = mimetypes.guess_type(lp)[0] or "image/png"
            with open(lp, "rb") as fh:
                brand["logo"] = f"data:{mime};base64," + base64.b64encode(fh.read()).decode()
        else:
            brand["logo"] = ""
    return brand


def to_html(rep: Dict[str, Any], brand: Dict[str, str]) -> str:
    e = html.escape
    p, a = brand["cor_primaria"], brand["cor_destaque"]
    cmp_ = rep.get("comparacao")

    def bar(n: Optional[int]) -> str:
        if n is None:
            return '<span class="na">não avaliado</span>'
        color = "#1F7A4D" if n >= 80 else "#B7791F" if n >= 50 else "#B42318"
        return (f'<div class="bar"><span style="width:{n}%;background:{color}"></span></div>'
                f'<b>{n}</b>')

    rows = []
    for pid, info in rep["pilares"].items():
        prev = cmp_["pilares"].get(pid) if cmp_ else None
        delta = ""
        if cmp_ and prev is not None and info["nota"] is not None:
            d = info["nota"] - prev
            delta = f' <small class="{"up" if d > 0 else "down" if d < 0 else ""}">{d:+d}</small>' if d else ' <small>=</small>'
        rows.append(f"<tr><td>{pid}</td><td>{e(info['nome'])}</td><td class='score'>{bar(info['nota'])}{delta}</td>"
                    f"<td>{info['ERRO']}</td><td>{info['AVISO']}</td><td>{info['INFO']}</td></tr>")
    items = []
    for f in rep["achados"]:
        if f["nivel"] == "INFO":
            continue
        extra = "".join(f"<li>{e(i)}</li>" for i in f["itens"][:12])
        new = ' <span class="tag new">novo</span>' if f.get("novo") else ""
        items.append(f"<div class='f {f['nivel'].lower()}'><div class='h'><span class='tag'>{f['nivel']}</span>"
                     f"<span class='tag p'>Pilar {e(f['pilar'])}</span>{new}<span class='src'>{e(f['fonte'])}</span></div>"
                     f"<p>{e(f['mensagem'])}</p>" + (f"<p class='w'>{e(f['onde'])}</p>" if f.get("onde") else "")
                     + (f"<ul>{extra}</ul>" if extra else "") + "</div>")
    infos = [f for f in rep["achados"] if f["nivel"] == "INFO"]
    info_html = "".join(f"<li><b>Pilar {e(f['pilar'])}</b> · {e(f['mensagem'])}" + (f" <span class='w'>({e(f['onde'])})</span>" if f.get("onde") else "") + "</li>" for f in infos)
    logo = f"<img src='{e(brand['logo'])}' alt='{e(brand['nome'])}'>" if brand.get("logo") else ""
    comp = ""
    if cmp_:
        comp = (f"<p class='cmp'>Comparado a {e(str(cmp_['data_anterior']))}: nota geral {cmp_['nota_anterior']} → "
                f"{rep['nota_geral']} · {cmp_['resolvidos']} achado(s) resolvido(s) · {cmp_['novos']} novo(s).</p>")
    sources = ", ".join(f"{e(s['arquivo'])} ({e(s['tipo'])})" for s in rep["fontes"])
    t = rep["totais"]
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Relatório SEO e GEO · {e(rep['site'])}</title>
<style>
:root{{--p:{p};--a:{a};--ink:#111827;--mut:#5B6475;--line:#E3E7EE;--bg:#F7F8FB}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif}}
.wrap{{max-width:980px;margin:0 auto;padding:32px 20px}}header{{display:flex;justify-content:space-between;align-items:center;gap:16px;border-bottom:4px solid var(--a);padding-bottom:16px}}
header img{{max-height:56px;max-width:220px}}h1{{margin:0;font-size:26px;color:var(--p)}}h2{{color:var(--p);margin-top:36px}}
.meta{{color:var(--mut)}}.kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:20px}}
.k{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:14px}}.k b{{display:block;font-size:28px;color:var(--p)}}
table{{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line);border-radius:12px;overflow:hidden}}
th,td{{padding:9px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:middle}}th{{background:var(--p);color:#fff;font-weight:600}}
.score{{display:flex;align-items:center;gap:8px;min-width:200px}}.bar{{flex:1;height:8px;background:#EEF1F5;border-radius:4px;overflow:hidden}}.bar span{{display:block;height:100%}}
.na{{color:var(--mut);font-style:italic}}small.up{{color:#1F7A4D}}small.down{{color:#B42318}}
.f{{background:#fff;border:1px solid var(--line);border-left:5px solid #B7791F;border-radius:10px;padding:12px 14px;margin:10px 0;break-inside:avoid}}
.f.erro{{border-left-color:#B42318}}.f p{{margin:6px 0}}.f ul{{margin:4px 0 0 18px;color:var(--mut);font-size:13px}}
.h{{display:flex;gap:6px;align-items:center;flex-wrap:wrap}}.tag{{font-size:12px;font-weight:700;padding:2px 8px;border-radius:99px;background:#FDF0E6;color:#8A3B12}}
.f.erro .tag:first-child{{background:#FDE8E8;color:#B42318}}.tag.p{{background:#EEF2FA;color:var(--p)}}.tag.new{{background:var(--a);color:#fff}}
.src{{margin-left:auto;font-size:12px;color:var(--mut)}}.w{{font-size:13px;color:var(--mut);word-break:break-all}}
.cmp{{background:#fff;border:1px dashed var(--a);padding:10px 14px;border-radius:10px}}footer{{margin-top:40px;color:var(--mut);font-size:13px;border-top:1px solid var(--line);padding-top:12px}}
.tbl{{overflow-x:auto;border-radius:12px}}.f,.f li,footer,ul li,.meta{{overflow-wrap:anywhere}}
@media (max-width:700px){{.kpis{{grid-template-columns:repeat(2,1fr)}}.score{{min-width:110px}}th,td{{padding:7px 6px;font-size:13px}}header{{flex-wrap:wrap}}}}
@media print{{@page{{size:A4;margin:14mm}}body{{background:#fff}}.wrap{{padding:0}}.k,.f,table{{box-shadow:none}}h2{{break-after:avoid}}}}
</style></head><body><div class="wrap">
<header><div><h1>Relatório de SEO e GEO</h1><div class="meta">{e(rep['site'])} · {e(rep['data'])}</div></div>{logo}</header>
<div class="kpis"><div class="k">Nota geral<b>{rep['nota_geral'] if rep['nota_geral'] is not None else '-'}</b></div>
<div class="k">Erros<b>{t['ERRO']}</b></div><div class="k">Avisos<b>{t['AVISO']}</b></div><div class="k">Informativos<b>{t['INFO']}</b></div></div>
{comp}
<h2>Nota por pilar</h2>
<div class="tbl"><table><thead><tr><th>#</th><th>Pilar</th><th>Nota</th><th>Erros</th><th>Avisos</th><th>Info</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<p class="meta">Nota heurística para acompanhar a evolução (100 − 15 por erro − 5 por aviso − 1 por informativo). Não é métrica do Google nem das IAs.</p>
<h2>O que corrigir, por prioridade</h2>
{''.join(items) or '<p>Nenhum erro ou aviso.</p>'}
<h2>Informativos</h2><ul>{info_html or '<li>Nenhum.</li>'}</ul>
<footer>Fontes: {sources}.{(' ' + e(brand['rodape'])) if brand.get('rodape') else ''}</footer>
</div></body></html>"""


def to_md(rep: Dict[str, Any]) -> str:
    out = [f"# Relatório SEO e GEO: {rep['site']} ({rep['data']})", "",
           f"Nota geral: **{rep['nota_geral']}** · Erros {rep['totais']['ERRO']} · Avisos {rep['totais']['AVISO']} · Info {rep['totais']['INFO']}", "",
           "| # | Pilar | Nota | Erros | Avisos |", "|---|---|---|---|---|"]
    for pid, i in rep["pilares"].items():
        out.append(f"| {pid} | {i['nome']} | {i['nota'] if i['nota'] is not None else 'não avaliado'} | {i['ERRO']} | {i['AVISO']} |")
    if rep.get("comparacao"):
        c = rep["comparacao"]
        out += ["", f"Comparado a {c['data_anterior']}: nota {c['nota_anterior']} → {rep['nota_geral']}; "
                    f"{c['resolvidos']} resolvido(s), {c['novos']} novo(s)."]
    out += ["", "## Prioridades", ""]
    out += [f"- **{f['nivel']}** (pilar {f['pilar']}, {f['fonte']}) {f['mensagem']}" + (f" · {f['onde']}" if f.get("onde") else "")
            for f in rep["achados"] if f["nivel"] != "INFO"] or ["Nenhum erro ou aviso."]
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("arquivos", nargs="+", help="saídas JSON dos scripts")
    ap.add_argument("--site", default="", help="site do relatório (aparece no título)")
    ap.add_argument("--anterior", help="JSON consolidado do relatório anterior (para comparar)")
    ap.add_argument("--marca", help="arquivo de marca (padrão: metodologia-local/marca.json, se existir)")
    ap.add_argument("--saida", help="arquivo HTML de saída")
    ap.add_argument("--json-saida", help="salva o consolidado em JSON (use como --anterior no próximo mês)")
    ap.add_argument("--format", choices=["md", "json"], default="md", help="o que imprimir no terminal")
    args = ap.parse_args()
    previous = None
    if args.anterior:
        try:
            with open(args.anterior, encoding="utf-8") as fh:
                previous = json.load(fh)
        except (OSError, ValueError) as err:
            print(f"erro: {args.anterior}: {err}", file=sys.stderr)
            sys.exit(2)
    rep = build(args.arquivos, args.site, previous)
    if all(s["tipo"].startswith(("desconhecido", "ignorado")) for s in rep["fontes"]):
        print("erro: nenhum arquivo reconhecido (gere com --format json nos scripts)", file=sys.stderr)
        sys.exit(2)
    if args.saida:
        with open(args.saida, "w", encoding="utf-8") as fh:
            fh.write(to_html(rep, load_brand(args.marca)))
    if args.json_saida:
        with open(args.json_saida, "w", encoding="utf-8") as fh:
            json.dump(rep, fh, ensure_ascii=False, indent=2)
    print(json.dumps(rep, ensure_ascii=False, indent=2) if args.format == "json" else to_md(rep))
    sys.exit(1 if rep["totais"]["ERRO"] else 0)


if __name__ == "__main__":
    main()
