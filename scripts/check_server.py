#!/usr/bin/env python3
"""Confere a configuração do servidor que afeta rastreio e confiança (pilares 2, 3 e 5).

Verifica:
  - http → https com 301/308 em um salto; variante www/sem www consolidada no mesmo host;
  - status da página, tempo até o primeiro byte (aprox.) e tamanho do HTML (limite de 2 MB do Googlebot);
  - compressão, Cache-Control e charset do HTML;
  - X-Robots-Tag com noindex/nosnippet no cabeçalho;
  - soft 404 (URL inexistente precisa responder 404/410, não 200 nem redirect para a home);
  - robots.txt (200, texto), sitemap declarado/acessível e llms.txt (opcional);
  - cabeçalhos de segurança (HSTS, nosniff, Referrer-Policy, CSP/frame-ancestors).
    Não são fator de ranqueamento; entram porque um site invadido ou inseguro perde tráfego.

Uso:
  python3 check_server.py https://dominio.com
  python3 check_server.py https://dominio.com --format json

Saída: 0 sem erros, 1 com erros, 2 falha de uso ou de rede.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import sys
import urllib.parse
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _seo_common import GOOGLEBOT_HTML_LIMIT, LOCAL_HOSTS, fetch, fetch_once, host_key, is_url  # noqa: E402

TTFB_GOOD = 0.8   # web.dev: TTFB bom até 0,8 s
TTFB_POOR = 1.8   # ruim acima de 1,8 s


def origin(url: str) -> str:
    p = urllib.parse.urlsplit(url)
    return f"{p.scheme}://{p.netloc}"


def check(start: str) -> Dict[str, Any]:
    findings: List[Dict[str, str]] = []
    data: Dict[str, Any] = {"inicio": start}

    def add(level: str, pillar: str, msg: str) -> None:
        findings.append({"nivel": level, "pilar": pillar, "mensagem": msg})

    parts = urllib.parse.urlsplit(start)
    host = parts.hostname or ""
    local = host in LOCAL_HOSTS

    # --- página inicial (seguindo redirects) ---
    f = fetch(start)
    final = f.final_url or start
    data.update(status=f.status, final=final, redirects=f.redirects, ttfb_s=round(f.elapsed, 3),
                bytes_html=len(f.body), bytes_transferidos=f.raw_size)
    if f.status != 200:
        add("ERRO", "3", f"{start} respondeu {f.status}.")
    if len(f.redirects) > 1:
        add("AVISO", "3", f"{len(f.redirects)} redirects até a página final: " + " | ".join(f.redirects))
    if f.elapsed > TTFB_POOR:
        add("AVISO", "5", f"Tempo até o primeiro byte ~{f.elapsed:.2f} s (ruim acima de 1,8 s): cache de página, CDN ou servidor mais perto do público.")
    elif f.elapsed > TTFB_GOOD:
        add("INFO", "5", f"Tempo até o primeiro byte ~{f.elapsed:.2f} s (bom é até 0,8 s). Medida única, desta máquina: confirme no CrUX/PageSpeed.")
    h = f.headers
    if len(f.body) + sum(len(k) + len(v) + 4 for k, v in h.items()) > GOOGLEBOT_HTML_LIMIT:
        add("ERRO", "4", "HTML acima de 2 MB: o Googlebot ignora o que passa desse limite.")
    if f.status == 200 and len(f.body) > 2048 and not h.get("content-encoding"):
        add("AVISO", "5", "HTML sem compressão (Content-Encoding gzip/br ausente).")
    cc = h.get("cache-control", "")
    if not cc:
        add("INFO", "5", "HTML sem Cache-Control. Defina uma política (ex.: s-maxage na CDN + revalidação).")
    ctype = h.get("content-type", "")
    if "html" in ctype and "charset" not in ctype.lower():
        add("INFO", "4", "Content-Type sem charset; declare charset=utf-8 no cabeçalho ou <meta charset> no início do HTML.")
    xr = h.get("x-robots-tag", "").lower()
    if re.search(r"\b(noindex|none)\b", xr):
        add("ERRO", "3", f"Cabeçalho X-Robots-Tag com noindex na página inicial: \"{h.get('x-robots-tag')}\".")
    elif "nosnippet" in xr:
        add("AVISO", "10", "X-Robots-Tag com nosnippet: sem snippet e fora dos recursos de IA do Google.")

    # --- https e variante de host ---
    final_parts = urllib.parse.urlsplit(final)
    if final_parts.scheme == "https":
        hsts = h.get("strict-transport-security", "")
        if not hsts:
            add("AVISO", "5", "HTTPS sem Strict-Transport-Security (HSTS).")
        try:
            r = fetch_once(f"http://{final_parts.netloc}/")
            data["http_para_https"] = f"{r.status} → {r.headers.get('location', '')}"
            loc = r.headers.get("location", "")
            if r.status == 200:
                add("ERRO", "3", "http:// responde 200 sem redirecionar para https:// (duas versões do site).")
            elif r.status in (302, 307):
                add("AVISO", "3", f"http → https com redirect temporário {r.status}; use 301 ou 308.")
            elif r.status in (301, 308) and not loc.startswith("https://"):
                add("AVISO", "3", f"http:// redireciona para {loc}, não direto para https://.")
        except OSError:
            data["http_para_https"] = "porta 80 inacessível"
    elif not local:
        add("ERRO", "5", "O site termina em http:// (sem HTTPS).")
    if not local:
        alt_host = final_parts.hostname[4:] if (final_parts.hostname or "").startswith("www.") else "www." + (final_parts.hostname or "")
        alt = f"{final_parts.scheme}://{alt_host}/"
        try:
            r = fetch_once(alt)
            loc = r.headers.get("location", "")
            data["variante_de_host"] = f"{alt} → {r.status} {loc}"
            if r.status == 200:
                add("ERRO", "3", f"{alt} também responde 200: duas versões do site. Redirecione com 301 para {origin(final)}/.")
            elif r.status in (301, 308) and host_key(loc or alt) != host_key(final):
                add("AVISO", "3", f"{alt} redireciona para outro host ({loc}).")
            elif r.status in (302, 307):
                add("AVISO", "3", f"{alt} usa redirect temporário {r.status}; use 301.")
        except OSError:
            data["variante_de_host"] = f"{alt} não resolve (ok se não for usada)"

    # --- soft 404 ---
    probe = f"{origin(final)}/{secrets.token_hex(6)}-pagina-inexistente/"
    try:
        r = fetch_once(probe)
        data["url_inexistente"] = f"{r.status} {r.headers.get('location', '')}".strip()
        if r.status == 200:
            add("ERRO", "3", "URL inexistente responde 200 (soft 404). Páginas de erro precisam de status 404 ou 410.")
        elif r.status in (301, 302, 307, 308):
            add("AVISO", "3", f"URL inexistente redireciona ({r.status} → {r.headers.get('location', '')}); o Google trata como soft 404. Responda 404.")
    except OSError:
        pass

    # --- robots.txt, sitemap, llms.txt ---
    sitemaps: List[str] = []
    try:
        r = fetch(f"{origin(final)}/robots.txt")
        data["robots_txt"] = r.status
        if r.status == 200:
            if "text/plain" not in r.headers.get("content-type", "text/plain"):
                add("AVISO", "2", f"robots.txt servido como {r.headers.get('content-type')}; use text/plain.")
            sitemaps = re.findall(r"(?im)^\s*sitemap:\s*(\S+)", r.text())
        elif r.status == 429 or r.status >= 500:
            add("ERRO", "2", f"robots.txt respondeu {r.status}: o Google pode pausar o rastreio do site.")
        else:
            add("INFO", "2", f"robots.txt respondeu {r.status} (tudo liberado). Crie um para declarar o sitemap.")
    except OSError:
        pass
    sm = urllib.parse.urljoin(origin(final) + "/", sitemaps[0]) if sitemaps else f"{origin(final)}/sitemap.xml"
    if sitemaps and not is_url(sitemaps[0]):
        add("AVISO", "2", f"Sitemap declarado com URL relativa ({sitemaps[0]}); use URL absoluta no robots.txt.")
    try:
        r = fetch(sm)
        data["sitemap"] = f"{sm} → {r.status}"
        if r.status != 200:
            add("AVISO", "2", f"Sitemap {sm} respondeu {r.status}.")
    except OSError:
        add("AVISO", "2", f"Sitemap {sm} inacessível.")
    try:
        r = fetch_once(f"{origin(final)}/llms.txt")
        data["llms_txt"] = r.status
        if r.status == 200 and "html" in r.headers.get("content-type", ""):
            add("AVISO", "2", "/llms.txt devolve HTML (provavelmente a página de erro com status 200).")
    except OSError:
        pass

    # --- segurança (confiança) ---
    if not h.get("x-content-type-options"):
        add("INFO", "5", "Sem X-Content-Type-Options: nosniff.")
    if not h.get("referrer-policy"):
        add("INFO", "5", "Sem Referrer-Policy (ex.: strict-origin-when-cross-origin).")
    csp = h.get("content-security-policy", "")
    if not csp and not h.get("x-frame-options"):
        add("INFO", "5", "Sem Content-Security-Policy nem X-Frame-Options (proteção contra clickjacking).")

    order = {"ERRO": 0, "AVISO": 1, "INFO": 2}
    findings.sort(key=lambda x: (order[x["nivel"]], x["pilar"]))
    data["achados"] = findings
    data["erros"] = sum(1 for x in findings if x["nivel"] == "ERRO")
    return data


def to_md(r: Dict[str, Any]) -> str:
    rows = [("Status", r.get("status")), ("URL final", r.get("final")), ("Tempo até o 1º byte (s)", r.get("ttfb_s")),
            ("HTML (bytes descompactados / transferidos)", f"{r.get('bytes_html')} / {r.get('bytes_transferidos')}"),
            ("http → https", r.get("http_para_https", "-")), ("Variante de host", r.get("variante_de_host", "-")),
            ("URL inexistente", r.get("url_inexistente", "-")), ("robots.txt", r.get("robots_txt", "-")),
            ("Sitemap", r.get("sitemap", "-")), ("llms.txt", r.get("llms_txt", "-"))]
    out = [f"# Servidor: {r['inicio']}", "", "| Item | Resultado |", "|---|---|"]
    out += [f"| {k} | {v} |" for k, v in rows]
    out += ["", "## Achados", ""]
    if r["achados"]:
        out += ["| Nível | Pilar | Achado |", "|---|---|---|"] + [f"| {f['nivel']} | {f['pilar']} | {f['mensagem']} |" for f in r["achados"]]
    else:
        out.append("Nenhum problema encontrado.")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inicio", help="URL do site (normalmente a home)")
    ap.add_argument("--format", choices=["md", "json"], default="md")
    args = ap.parse_args()
    start = args.inicio if is_url(args.inicio) else "https://" + args.inicio
    try:
        r = check(start)
    except OSError as err:
        print(f"erro: não foi possível acessar {start}: {err}", file=sys.stderr)
        sys.exit(2)
    print(json.dumps(r, ensure_ascii=False, indent=2) if args.format == "json" else to_md(r))
    sys.exit(1 if r["erros"] else 0)


if __name__ == "__main__":
    main()
