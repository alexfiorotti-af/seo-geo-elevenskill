#!/usr/bin/env python3
"""Mostra o que cada robô de busca e de IA pode rastrear segundo o robots.txt (RFC 9309).

Implementa a correspondência do padrão: grupo mais específico por user-agent, regra de
caminho mais longa vence, Allow vence empate, curingas * e $.

Também mostra, por robô: Crawl-delay (o Google ignora; Bing e Yandex respeitam) e a linha
Content-Signal (convenção da Cloudflare com as chaves search, ai-input e ai-train), lembrando
que um robô com grupo próprio NÃO herda o que está no grupo '*'. Detecta o bloco gerenciado da
Cloudflare, robots.txt acima de 500 KiB (o Google ignora o excedente) e trata 429 como 5xx,
como o Google faz.

Uso:
  python3 check_robots.py https://dominio.com
  python3 check_robots.py https://dominio.com --path / --path /blog/artigo/
  python3 check_robots.py robots.txt --path /servicos/
  python3 check_robots.py https://dominio.com --format json

Saída: 0 se os robôs de busca podem rastrear todos os caminhos testados;
       1 se algum robô de busca/IA de busca está bloqueado ou o robots.txt responde 5xx/429;
       2 falha de uso ou de rede.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.parse
from typing import Dict, List, Optional, Tuple

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
    ("DuckAssistBot", "DuckDuckGo", "Respostas com IA do DuckDuckGo", "busca"),
    ("YandexBot", "Yandex", "Yandex", "busca"),
    ("ChatGPT-User", "OpenAI", "Acesso pedido pelo usuário", "sob-demanda"),
    ("Claude-User", "Anthropic", "Acesso pedido pelo usuário", "sob-demanda"),
    ("Perplexity-User", "Perplexity", "Acesso pedido pelo usuário (costuma ignorar robots.txt)", "sob-demanda"),
    ("Google-Agent", "Google", "Agentes do Google agindo a pedido do usuário (desde mar/2026)", "sob-demanda"),
    ("Google-GeminiNotebook", "Google", "Gemini Notebook, ex-NotebookLM (nome novo desde jul/2026)", "sob-demanda"),
    ("Meta-ExternalFetcher", "Meta", "Acesso pedido pelo usuário", "sob-demanda"),
    ("MistralAI-User", "Mistral", "Acesso pedido pelo usuário (Le Chat)", "sob-demanda"),
    ("GPTBot", "OpenAI", "Treino de modelos", "treino"),
    ("ClaudeBot", "Anthropic", "Treino de modelos", "treino"),
    ("Google-Extended", "Google", "Treino Gemini / grounding do app (não afeta Search)", "treino"),
    ("Applebot-Extended", "Apple", "Treino (não afeta busca da Apple)", "treino"),
    ("Meta-ExternalAgent", "Meta", "Treino e IA da Meta", "treino"),
    ("Amazonbot", "Amazon", "Serviços e IA da Amazon (Alexa); pode treinar modelos", "treino"),
    ("Bytespider", "ByteDance", "Treino de modelos", "treino"),
    ("CCBot", "Common Crawl", "Base aberta usada em treinos", "treino"),
]
# Robôs acionados pelo usuário costumam não seguir o robots.txt (o Google documenta isso para os
# fetchers "user-triggered"). O resultado deles abaixo é o que o arquivo PEDE, não o que acontece.
USER_TRIGGERED_NOTE = ("Robôs 'sob-demanda' (ChatGPT-User, Claude-User, Perplexity-User, Google-Agent, "
                       "Google-GeminiNotebook...) agem a pedido de uma pessoa e podem não seguir o robots.txt.")
GOOGLE_MAX_BYTES = 500 * 1024
SIGNAL_KEYS = ("search", "ai-input", "ai-train")
CRITICAL = {"Googlebot", "Bingbot", "OAI-SearchBot", "Claude-SearchBot", "PerplexityBot"}


class Group:
    def __init__(self) -> None:
        self.agents: List[str] = []
        self.rules: List[Tuple[bool, str]] = []  # (allow?, padrão)
        self.signals: Dict[str, str] = {}        # Content-Signal: search=yes, ai-train=no
        self.crawl_delay: Optional[str] = None


def parse_signals(value: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for part in value.split(","):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip().lower()] = v.strip().lower()
    return out


def parse_robots(text: str) -> Tuple[List[Group], List[str]]:
    groups: List[Group] = []
    sitemaps: List[str] = []
    current: Optional[Group] = None
    last_was_agent = False
    global_signals: Dict[str, str] = {}
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
        elif key == "content-signal":
            last_was_agent = False
            if current is None:
                global_signals.update(parse_signals(value))
            else:
                current.signals.update(parse_signals(value))
        elif key == "crawl-delay":
            last_was_agent = False
            if current is not None:
                current.crawl_delay = value
        else:
            last_was_agent = False
    if global_signals:  # Content-Signal fora de grupo: vale para o grupo '*'
        star = [g for g in groups if "*" in g.agents]
        for g in star or []:
            for k, v in global_signals.items():
                g.signals.setdefault(k, v)
        if not star:
            g = Group()
            g.agents.append("*")
            g.signals.update(global_signals)
            groups.append(g)
    return groups, sitemaps


def matching_groups(groups: List[Group], bot: str) -> List[Group]:
    """Grupos que valem para o robô: os do token mais longo que casa; senão, os grupos '*'."""
    token = bot.lower()
    specific = [g for g in groups if any(a != "*" and token.startswith(a) for a in g.agents)]
    if specific:
        # o token mais longo que casa vence (ex.: 'googlebot-image' vs 'googlebot')
        best = max(len(a) for g in specific for a in g.agents if a != "*" and token.startswith(a))
        return [g for g in specific if any(a != "*" and token.startswith(a) and len(a) == best for a in g.agents)]
    return [g for g in groups if "*" in g.agents]


def select_group(groups: List[Group], bot: str) -> Optional[List[Tuple[bool, str]]]:
    """Junta as regras dos grupos que valem para o robô (None se nenhum grupo se aplica)."""
    chosen = matching_groups(groups, bot)
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
    elif f.status == 429:
        notes.append("robots.txt respondeu 429 (excesso de requisições): o Google trata como erro de servidor "
                     "e pode pausar o rastreio do site. Libere o robots.txt no limite de taxa/WAF.")
        exit_code = 1
    elif 400 <= f.status < 500:
        notes.append(f"robots.txt respondeu {f.status}: os robôs tratam como 'tudo liberado'.")
    else:
        notes.append(f"robots.txt respondeu {f.status}: o Google pode pausar o rastreio do site inteiro. Corrija com urgência.")
        exit_code = 1
    if len(f.body) > GOOGLE_MAX_BYTES:
        notes.append(f"robots.txt com {len(f.body) // 1024} KiB: o Google ignora o que passa de 500 KiB. Simplifique as regras.")
    if len(f.redirects) > 5:
        notes.append(f"robots.txt passa por {len(f.redirects)} redirects; o Google segue no máximo 5.")
    if "cloudflare managed" in text.lower():
        notes.append("Bloco gerenciado da Cloudflare detectado no robots.txt (Content-Signal e bloqueio de robôs de IA). "
                     "Confira se ele bate com a política de IA do site; ele é editado no painel da Cloudflare, não no servidor.")

    groups, sitemaps = parse_robots(text)
    rows = []
    for token, company, role, category in BOTS:
        rules = select_group(groups, token)
        chosen = matching_groups(groups, token)
        signals: Dict[str, str] = {}
        delay: Optional[str] = None
        for g in chosen:
            signals.update(g.signals)
            delay = delay or g.crawl_delay
        results = {}
        for path in paths:
            ok, rule = is_allowed(rules, path)
            results[path] = {"permitido": ok, "regra": rule}
            if not ok and token in CRITICAL:
                exit_code = 1
        named = any(a != "*" for g in chosen for a in g.agents)
        rows.append({"robo": token, "empresa": company, "funcao": role, "categoria": category, "caminhos": results,
                     "grupo": "próprio" if named else ("*" if chosen else "nenhum"),
                     "content_signal": signals, "crawl_delay": delay})

    star_signals = any(g.signals for g in groups if "*" in g.agents)
    if star_signals:
        orphan = [r["robo"] for r in rows if r["grupo"] == "próprio" and not r["content_signal"]]
        if orphan:
            notes.append("Content-Signal está no grupo '*', mas estes robôs têm grupo próprio e não herdam o sinal: "
                         + ", ".join(orphan) + ". Repita a linha Content-Signal nesses grupos se quiser que valha para eles.")
        notes.append("Content-Signal é uma convenção (proposta da Cloudflare; o rascunho no IETF expirou em abr/2026): "
                     "expressa preferência, não bloqueia. Quem decide o acesso continua sendo Allow/Disallow.")
    for r in rows:
        bad = {k: v for k, v in r["content_signal"].items() if k not in SIGNAL_KEYS or v not in ("yes", "no")}
        if bad:
            notes.append(f"Content-Signal com chave/valor fora do padrão para {r['robo']}: {bad} (use search, ai-input, ai-train = yes/no).")
            break
    for r in rows:
        if r["robo"] in CRITICAL and r["content_signal"].get("search") == "no":
            notes.append(f"{r['robo']} recebe Content-Signal search=no: contradiz o objetivo de aparecer na busca.")
    delays = sorted({r["crawl_delay"] for r in rows if r["crawl_delay"]})
    if delays:
        notes.append(f"Crawl-delay declarado ({', '.join(delays)} s): o Google ignora; Bing e Yandex respeitam. "
                     "Valores altos atrasam a descoberta de páginas novas no Bing/Copilot.")

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

    result = {"robots_txt": source, "status": f.status, "tamanho_bytes": len(f.body), "sitemaps": sitemaps,
              "robos": rows, "observacoes": notes}
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
        extras = [r for r in rows if r["content_signal"] or r["crawl_delay"]]
        if extras:
            print("\n## Sinais por robô\n")
            print("| Robô | Grupo aplicado | Content-Signal | Crawl-delay |")
            print("|---|---|---|---|")
            for r in extras:
                sig = ", ".join(f"{k}={v}" for k, v in r["content_signal"].items()) or "(nenhum)"
                print(f"| {r['robo']} | {r['grupo']} | {sig} | {r['crawl_delay'] or '-'} |")
        if notes:
            print("\n## Observações\n")
            for n in notes:
                print(f"- {n}")
        print(f"\n_{USER_TRIGGERED_NOTE}_")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
