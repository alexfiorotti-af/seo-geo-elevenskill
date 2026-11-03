#!/usr/bin/env python3
"""Envia URLs novas, alteradas ou removidas ao IndexNow (Bing, Yandex, Naver, Seznam, Yep).

A chave NUNCA fica no código: passe por --key ou pela variável de ambiente INDEXNOW_KEY.
O arquivo https://<host>/<chave>.txt (contendo só a chave) precisa estar publicado antes.
O Google não participa do IndexNow; para ele, use sitemap + Search Console.

Uso:
  INDEXNOW_KEY=xxxx python3 indexnow_submit.py --host dominio.com urls.txt
  git diff --name-only ... | gerar-urls | python3 indexnow_submit.py --host dominio.com -
  python3 indexnow_submit.py --host dominio.com urls.txt --dry-run

urls.txt: uma URL absoluta por linha (linhas vazias e iniciadas com # são ignoradas).
Saída: 0 aceito (200/202), 1 recusado pelo endpoint, 2 erro de uso ou rede.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _seo_common import DEFAULT_UA, env_or  # noqa: E402

ENDPOINT = "https://api.indexnow.org/indexnow"
MAX_URLS = 10_000
KEY_RE = re.compile(r"^[A-Za-z0-9-]{8,128}$")
MEANING = {
    200: "OK: URLs recebidas.",
    202: "Aceito: recebido, chave ainda em validação.",
    400: "Requisição inválida (formato).",
    403: "Chave inválida: o arquivo da chave não foi encontrado ou não confere.",
    422: "URLs não pertencem ao host ou a chave não corresponde ao esquema.",
    429: "Muitas requisições: reduza a frequência (possível spam).",
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("arquivo", help="arquivo com URLs (uma por linha) ou - para ler da entrada padrão")
    ap.add_argument("--host", required=True, help="host do site, ex.: dominio.com")
    ap.add_argument("--key", help="chave IndexNow (preferível: variável INDEXNOW_KEY)")
    ap.add_argument("--key-location", help="URL do arquivo da chave, se não estiver na raiz")
    ap.add_argument("--endpoint", default=ENDPOINT)
    ap.add_argument("--dry-run", action="store_true", help="mostra o que seria enviado, sem enviar")
    args = ap.parse_args()

    key = env_or(args.key, "INDEXNOW_KEY")
    if not key:
        print("erro: informe a chave em INDEXNOW_KEY (ou --key).", file=sys.stderr)
        sys.exit(2)
    if not KEY_RE.match(key):
        print("erro: chave deve ter 8 a 128 caracteres: letras, números ou hífen.", file=sys.stderr)
        sys.exit(2)

    stream = sys.stdin if args.arquivo == "-" else open(args.arquivo, encoding="utf-8")
    with stream:
        urls = [ln.strip() for ln in stream if ln.strip() and not ln.strip().startswith("#")]
    host = args.host.lower().removeprefix("https://").removeprefix("http://").strip("/")
    valid = []
    for u in dict.fromkeys(urls):  # remove duplicadas mantendo a ordem
        parts = urllib.parse.urlsplit(u)
        if parts.scheme in ("http", "https") and (parts.hostname or "").lower() == host:
            valid.append(u)
        else:
            print(f"ignorada (não é URL absoluta de {host}): {u}", file=sys.stderr)
    if not valid:
        print("erro: nenhuma URL válida para enviar.", file=sys.stderr)
        sys.exit(2)
    if len(valid) > MAX_URLS:
        print(f"aviso: {len(valid)} URLs; enviando as primeiras {MAX_URLS} (limite por requisição).", file=sys.stderr)
        valid = valid[:MAX_URLS]

    payload = {"host": host, "key": key, "urlList": valid}
    if args.key_location:
        payload["keyLocation"] = args.key_location
    if args.dry_run:
        shown = dict(payload, key=key[:4] + "…" + key[-2:])
        print(json.dumps(shown, ensure_ascii=False, indent=2))
        print(f"\n(dry-run) {len(valid)} URL(s) seriam enviadas para {args.endpoint}")
        sys.exit(0)

    req = urllib.request.Request(
        args.endpoint, data=json.dumps(payload).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": DEFAULT_UA},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            code = resp.status
    except urllib.error.HTTPError as err:
        code = err.code
    except OSError as err:
        print(f"erro de rede: {err}", file=sys.stderr)
        sys.exit(2)
    print(f"{code}: {MEANING.get(code, 'resposta inesperada')} ({len(valid)} URL(s))")
    sys.exit(0 if code in (200, 202) else 1)


if __name__ == "__main__":
    main()
