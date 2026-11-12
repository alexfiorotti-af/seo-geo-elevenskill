#!/usr/bin/env python3
"""Compara o que o servidor entrega para navegadores e para robôs de busca e de IA (pilares 2, 4 e 10).

Faz a mesma requisição com o user-agent de cada robô e de um navegador e compara status,
tamanho, title, H1, quantidade de palavras e JSON-LD. Encontra:
  - WAF/CDN bloqueando robôs de IA que você quer na busca (403, 429, desafio "Just a moment");
  - conteúdo diferente por robô (cloaking acidental, versão "leve" para bots, prerender quebrado);
  - página que só tem conteúdo no navegador (o HTML de todos é magro: depende de JavaScript).

Limitação honesta: o servidor vê o NOME do robô, não o IP verificado. Um WAF que confere o IP
pode bloquear este teste e liberar o robô real (ou o contrário). Confirme nos logs (pilar 11).

Uso:
  python3 check_agents.py https://dominio.com/
  python3 check_agents.py https://dominio.com/servicos/ --robo GPTBot --robo PerplexityBot
  python3 check_agents.py https://dominio.com/ --format json

Saída: 0 sem diferenças relevantes, 1 com robô de busca bloqueado ou conteúdo divergente, 2 falha.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _seo_common import fetch, html_to_text  # noqa: E402
from audit_page import PageParser, collect_types  # noqa: E402

BROWSER = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
AGENTS: Dict[str, str] = {
    "Navegador": BROWSER,
    "Googlebot": "Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 (KHTML, like Gecko) "
                 "Chrome/130.0 Mobile Safari/537.36 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Bingbot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm) Chrome/130.0 Safari/537.36",
    "OAI-SearchBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; OAI-SearchBot/1.3; +https://openai.com/searchbot)",
    "ChatGPT-User": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; ChatGPT-User/1.0; +https://openai.com/bot",
    "GPTBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; GPTBot/1.3; +https://openai.com/gptbot)",
    "Claude-SearchBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Claude-SearchBot/1.0; +https://www.anthropic.com)",
    "ClaudeBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; ClaudeBot/1.0; +claudebot@anthropic.com)",
    "PerplexityBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; PerplexityBot/1.0; +https://perplexity.ai/perplexitybot)",
    "Applebot": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15 (Applebot/0.1; +http://www.apple.com/go/applebot)",
}
SEARCH = {"Googlebot", "Bingbot", "OAI-SearchBot", "Claude-SearchBot", "PerplexityBot", "Applebot"}
CHALLENGE = re.compile(r"(just a moment|checking your browser|attention required|cf-challenge|captcha|"
                       r"access denied|acesso negado|enable javascript and cookies|ddos protection)", re.I)


def snapshot(url: str, ua: str) -> Dict[str, Any]:
    try:
        f = fetch(url, user_agent=ua)
    except OSError as err:
        return {"status": None, "erro": str(err)}
    html = f.text() if f.body else ""
    p = PageParser()
    try:
        p.feed(html)
        p.close()
    except Exception:  # noqa: BLE001 - HTML muito quebrado não deve derrubar a comparação
        pass
    types: List[str] = []
    for raw in p.jsonld_raw:
        try:
            collect_types(json.loads(raw), types)
        except json.JSONDecodeError:
            pass
    text = html_to_text(html)
    return {"status": f.status, "final": f.final_url, "bytes": len(f.body),
            "title": p.titles[0] if p.titles else "",
            "h1": next((h["text"] for h in p.headings if h["level"] == 1), ""),
            "palavras": len(re.findall(r"\w+", text)), "jsonld": sorted(set(types)),
            "desafio": bool(CHALLENGE.search(html[:20000])) and len(re.findall(r"\w+", text)) < 400,
            "noindex": bool(re.search(r"noindex", f.headers.get("x-robots-tag", ""), re.I))}


def compare(url: str, agents: Dict[str, str], delay: float = 0.5) -> Dict[str, Any]:
    results: Dict[str, Dict[str, Any]] = {}
    for i, (name, ua) in enumerate(agents.items()):
        if i and delay:
            time.sleep(delay)
        results[name] = snapshot(url, ua)
    findings: List[Dict[str, str]] = []

    def add(level: str, msg: str) -> None:
        findings.append({"nivel": level, "mensagem": msg})

    base = results.get("Navegador") or next(iter(results.values()))
    for name, r in results.items():
        if name == "Navegador":
            continue
        level = "ERRO" if name in SEARCH else "AVISO"
        if r.get("status") is None:
            add(level, f"{name}: sem resposta ({r.get('erro')}).")
            continue
        if r["status"] in (401, 403, 429, 503) or r["desafio"]:
            why = "página de desafio/bloqueio" if r["desafio"] else f"status {r['status']}"
            add(level, f"{name} recebe {why} (navegador recebe {base.get('status')}). Libere no WAF/CDN se quiser aparecer nessa plataforma.")
            continue
        if r["status"] != base.get("status"):
            add(level, f"{name} recebe status {r['status']}; navegador recebe {base.get('status')}.")
        if base.get("title") and r["title"] != base["title"]:
            add("AVISO", f"{name} recebe outro title: \"{r['title'][:70]}\" (navegador: \"{base['title'][:70]}\").")
        if base.get("h1") and r["h1"] != base["h1"]:
            add("AVISO", f"{name} recebe outro H1: \"{r['h1'][:70]}\".")
        bw = base.get("palavras") or 0
        if bw >= 100 and r["palavras"] < bw * 0.6:
            add(level, f"{name} recebe {r['palavras']} palavras; navegador recebe {bw}. Conteúdo diferente por robô.")
        if set(base.get("jsonld", [])) - set(r["jsonld"]):
            add("AVISO", f"{name} não recebe o JSON-LD {', '.join(sorted(set(base['jsonld']) - set(r['jsonld'])))}.")
        if r["noindex"] and not base.get("noindex"):
            add("ERRO", f"{name} recebe X-Robots-Tag noindex que o navegador não recebe.")
    if base.get("status") == 200 and (base.get("palavras") or 0) < 150:
        add("AVISO", f"Mesmo o navegador (sem JavaScript) recebe só {base.get('palavras')} palavras: o conteúdo depende de JS (pilar 4).")
    order = {"ERRO": 0, "AVISO": 1, "INFO": 2}
    findings.sort(key=lambda x: order[x["nivel"]])
    return {"url": url, "agentes": results, "achados": findings, "erros": sum(1 for x in findings if x["nivel"] == "ERRO")}


def to_md(r: Dict[str, Any]) -> str:
    out = [f"# O que cada robô recebe: {r['url']}", "", "| Agente | Status | Bytes | Palavras | Title | JSON-LD |", "|---|---|---|---|---|---|"]
    for name, a in r["agentes"].items():
        status = a.get("status") if a.get("status") is not None else "erro"
        if a.get("desafio"):
            status = f"{status} (desafio)"
        out.append(f"| {name} | {status} | {a.get('bytes', '-')} | {a.get('palavras', '-')} | {(a.get('title') or '')[:50]} | {', '.join(a.get('jsonld', [])) or '-'} |")
    out += ["", "## Achados", ""]
    out += [f"- **{f['nivel']}** {f['mensagem']}" for f in r["achados"]] or ["Todos recebem o mesmo conteúdo."]
    out += ["", "_O teste usa só o user-agent; WAFs que verificam IP podem tratar o robô real de outro jeito. Confirme nos logs._"]
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url")
    ap.add_argument("--robo", action="append", help=f"limitar a estes robôs (pode repetir): {', '.join(a for a in AGENTS if a != 'Navegador')}")
    ap.add_argument("--atraso", type=float, default=0.5)
    ap.add_argument("--format", choices=["md", "json"], default="md")
    args = ap.parse_args()
    agents = AGENTS
    if args.robo:
        unknown = [x for x in args.robo if x not in AGENTS]
        if unknown:
            print(f"erro: robô desconhecido: {', '.join(unknown)}", file=sys.stderr)
            sys.exit(2)
        agents = {"Navegador": BROWSER, **{x: AGENTS[x] for x in args.robo}}
    r = compare(args.url, agents, args.atraso)
    if all(a.get("status") is None for a in r["agentes"].values()):
        print("erro: nenhuma resposta (rede ou URL incorreta)", file=sys.stderr)
        sys.exit(2)
    print(json.dumps(r, ensure_ascii=False, indent=2) if args.format == "json" else to_md(r))
    sys.exit(1 if r["erros"] else 0)


if __name__ == "__main__":
    main()
