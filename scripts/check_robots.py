#!/usr/bin/env python3
"""Mostra o que cada robô de busca e de IA pode rastrear segundo o robots.txt (RFC 9309).

Implementa a correspondência do padrão: grupo mais específico por user-agent, regra de
caminho mais longa vence, Allow vence empate, curingas * e $.

Uso:
  python3 check_robots.py https://dominio.com
  python3 check_robots.py https://dominio.com --path / --path /blog/artigo/
  python3 check_robots.py robots.txt --path /servicos/
  python3 check_robots.py https://dominio.com --format json

Saída: 0 se os robôs de busca podem rastrear todos os caminhos testados;
       1 se algum robô de busca/IA de busca está bloqueado ou o robots.txt responde 5xx;
       2 falha de uso ou de rede.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.parse
from typing import List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _seo_common import fetch, is_url  # noqa: E402

# (token do user-agent, empresa, função, categoria)
# categoria: "busca" = precisa estar liberado para aparecer; "sob-demanda" = acesso pedido pelo usuário;
#            "treino" = decisão do dono do site.
BOTS: List[Tuple[str, str, str, str]] = [
    ("Googlebot", "Google", "Search, AI Overviews, AI Mode", "busca"),
    ("Bingbot", "Microsoft", "Bing e Copilot", "busca"),
    ("OAI-SearchBot", "OpenAI", "ChatGPT Search", "busca"),
    ("Claude-SearchBot", "Anthropic", "Busca do Claude", "busca"),
    ("PerplexityBot", "Perplexity", "Índice do Perplexity", "busca"),
    ("Applebot", "Apple", "Siri, Spotlight", "busca"),
    ("DuckDuckBot", "DuckDuckGo", "DuckDuckGo", "busca"),
    ("YandexBot", "Yandex", "Yandex", "busca"),
    ("ChatGPT-User", "OpenAI", "Acesso pedido pelo usuário", "sob-demanda"),
    ("Claude-User", "Anthropic", "Acesso pedido pelo usuário", "sob-demanda"),
    ("Perplexity-User", "Perplexity", "Acesso pedido pelo usuário (costuma ignorar robots.txt)", "sob-demanda"),
    ("GPTBot", "OpenAI", "Treino de modelos", "treino"),
    ("ClaudeBot", "Anthropic", "Treino de modelos", "treino"),
    ("Google-Extended", "Google", "Treino Gemini / grounding do app (não afeta Search)", "treino"),
    ("Applebot-Extended", "Apple", "Treino (não afeta busca da Apple)", "treino"),
    ("Meta-ExternalAgent", "Meta", "Treino e IA da Meta", "treino"),
    ("CCBot", "Common Crawl", "Base aberta usada em treinos", "treino"),
]
CRITICAL = {"Googlebot", "Bingbot", "OAI-SearchBot", "Claude-SearchBot", "PerplexityBot"}


class Group:
    def __init__(self) -> None:
        self.agents: List[str] = []
        self.rules: List[Tuple[bool, str]] = []  # (allow?, padrão)


def parse_robots(text: str) -> Tuple[List[Group], List[str]]:
    groups: List[Group] = []
    sitemaps: List[str] = []
    current: Optional[Group] = None
    last_was_agent = False
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
        if key == "user-agent":
            if current is None or not last_was_agent:
                current = Group()
                groups.append(current)
            current.agents.append(value.lower())
            last_was_agent = True
        elif key in ("allow", "disallow"):
            last_was_agent = False
            if current is None:
                continue
            if key == "disallow" and value == "":
                continue  # Disallow vazio = permite tudo
            current.rules.append((key == "allow", value))
        elif key == "sitemap":
            sitemaps.append(value)
            last_was_agent = False
        else:
            last_was_agent = False
    return groups, sitemaps


def select_group(groups: List[Group], bot: str) -> Optional[List[Tuple[bool, str]]]:
    """Junta os grupos cujo user-agent casa com o token do robô; senão, os grupos '*'."""
    token = bot.lower()
    specific = [g for g in groups if any(a != "*" and token.startswith(a) for a in g.agents)]
    if specific:
        # o token mais longo que casa vence (ex.: 'googlebot-image' vs 'googlebot')
        best = max(len(a) for g in specific for a in g.agents if a != "*" and token.startswith(a))
        chosen = [g for g in specific if any(a != "*" and token.startswith(a) and len(a) == best for a in g.agents)]
    else:
        chosen = [g for g in groups if "*" in g.agents]
    if not chosen:
        return None
    rules: List[Tuple[bool, str]] = []
    for g in chosen:
        rules.extend(g.rules)
    return rules


def _pattern_to_regex(pattern: str) -> re.Pattern:
    anchored = pattern.endswith("$")
    body = pattern[:-1] if anchored else pattern
    regex = "".join(".*" if ch == "*" else re.escape(ch) for ch in body)
    return re.compile("^" + regex + ("$" if anchored else ""))


def is_allowed(rules: Optional[List[Tuple[bool, str]]], path: str) -> Tuple[bool, Optional[str]]:
    if not rules:
        return True, None
    path = path or "/"
    best: Optional[Tuple[int, bool, str]] = None
    for allow, pattern in rules:
        if _pattern_to_regex(pattern).match(path):
            length = len(pattern)
            if best is None or length > best[0] or (length == best[0] and allow and not best[1]):
                best = (length, allow, pattern)
    if best is None:
        return True, None
    return best[1], f"{'Allow' if best[1] else 'Disallow'}: {best[2]}"


def robots_url(target: str) -> str:
    parts = urllib.parse.urlsplit(target if "://" in target else "https://" + target)
    return f"{parts.scheme}://{parts.netloc}/robots.txt"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("alvo", help="domínio/URL do site ou caminho de um robots.txt local")
    ap.add_argument("--path", action="append", help="caminho que DEVE estar liberado para busca (pode repetir). Padrão: /")
    ap.add_argument("--format", choices=["md", "json"], default="md")
    args = ap.parse_args()
    paths = args.path or ["/"]

    local = os.path.exists(args.alvo) and not is_url(args.alvo)
    source = args.alvo if local else robots_url(args.alvo)
    try:
        f = fetch(source)
    except OSError as err:
        print(f"erro: não foi possível ler {source}: {err}", file=sys.stderr)
        sys.exit(2)

    notes: List[str] = []
    exit_code = 0
    text = ""
    if f.status is None or f.status == 200:
        text = f.text()
    elif 400 <= f.status < 500:
        notes.append(f"robots.txt respondeu {f.status}: os robôs tratam como 'tudo liberado'.")
    else:
        notes.append(f"robots.txt respondeu {f.status}: o Google pode pausar o rastreio do site inteiro. Corrija com urgência.")
        exit_code = 1

    groups, sitemaps = parse_robots(text)
    rows = []
    for token, company, role, category in BOTS:
        rules = select_group(groups, token)
        results = {}
        for path in paths:
            ok, rule = is_allowed(rules, path)
            results[path] = {"permitido": ok, "regra": rule}
            if not ok and token in CRITICAL:
                exit_code = 1
        rows.append({"robo": token, "empresa": company, "funcao": role, "categoria": category, "caminhos": results})

    if not sitemaps and text:
        notes.append("Nenhuma linha 'Sitemap:' no robots.txt; declare a URL absoluta do sitemap.")
    for s in sitemaps:
        if not is_url(s):
            notes.append(f"Sitemap com URL relativa ({s}); use URL absoluta.")
    blocked_search = [r["robo"] for r in rows if r["robo"] in CRITICAL and not all(v["permitido"] for v in r["caminhos"].values())]
    if blocked_search:
        notes.append("Robôs de BUSCA bloqueados: " + ", ".join(blocked_search) + ". O site some desses buscadores/IAs nesses caminhos.")
    training_blocked = [r["robo"] for r in rows if r["categoria"] == "treino" and not r["caminhos"][paths[0]]["permitido"]]
    if training_blocked:
        notes.append("Robôs de treino bloqueados (decisão do dono, não afeta busca): " + ", ".join(training_blocked) + ".")

    result = {"robots_txt": source, "status": f.status, "sitemaps": sitemaps, "robos": rows, "observacoes": notes}
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"# robots.txt: {source}\n")
        print(f"Status: {f.status if f.status is not None else 'arquivo local'} · Sitemaps declarados: {', '.join(sitemaps) or 'nenhum'}\n")
        header = "| Robô | Empresa | Função | Categoria | " + " | ".join(paths) + " |"
        print(header)
        print("|" + "---|" * (4 + len(paths)))
        for r in rows:
            cells = []
            for p in paths:
                v = r["caminhos"][p]
                cells.append(("permitido" if v["permitido"] else "**bloqueado**") + (f" ({v['regra']})" if v["regra"] else ""))
            print(f"| {r['robo']} | {r['empresa']} | {r['funcao']} | {r['categoria']} | " + " | ".join(cells) + " |")
        if notes:
            print("\n## Observações\n")
            for n in notes:
                print(f"- {n}")
        print("\n_Perplexity-User e ChatGPT-User podem não seguir robots.txt por serem acessos pedidos pelo usuário._")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
