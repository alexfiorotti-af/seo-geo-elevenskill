#!/usr/bin/env python3
"""Valida titles e meta descriptions em lote a partir de um CSV (pilar 8).

Colunas reconhecidas (cabeçalho obrigatório; vírgula ou ponto e vírgula):
  url, title, description, palavra_principal (opcional), marca (opcional)
O formato de templates/mapa-de-palavras-chave.csv já serve.

Verifica: ausência, tamanho (caracteres e largura estimada em pixels), duplicados entre
páginas, palavra principal no title e na description, repetição da palavra (stuffing),
marca no meio do title, title em maiúsculas, ano antigo no title, texto de modelo esquecido.

Uso:
  python3 lint_meta.py mapa.csv
  python3 lint_meta.py mapa.csv --format json
  python3 lint_meta.py mapa.csv --max-title-px 600

Saída: 0 sem erros, 1 com erros, 2 falha de uso.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import re
import sys
from collections import defaultdict
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _seo_common import (  # noqa: E402
    DESC_MAX_CHARS, DESC_MIN_CHARS, TITLE_MAX_PX, TITLE_MIN_CHARS,
    find_placeholders, normalize, pixel_width,
)

ALIASES = {
    "title": {"title", "titulo", "título", "seo_title", "meta_title"},
    "description": {"description", "descricao", "descrição", "meta_description", "seo_description"},
    "keyword": {"palavra_principal", "keyword", "palavra-chave", "palavra_chave", "focus_keyword"},
    "brand": {"marca", "brand"},
    "url": {"url", "pagina", "página", "slug"},
}


def pick(row: Dict[str, str], key: str) -> str:
    for col, val in row.items():
        if col and col.strip().lower() in ALIASES[key]:
            return (val or "").strip()
    return ""


def keyword_in(keyword: str, text: str) -> bool:
    """Todas as palavras significativas da palavra-chave aparecem no texto (sem acento/caixa)."""
    stop = {"de", "da", "do", "das", "dos", "em", "e", "a", "o", "para", "com", "no", "na", "the", "of", "in", "for"}
    words = [w for w in re.findall(r"\w+", normalize(keyword)) if w not in stop]
    norm = normalize(text)
    return bool(words) and all(re.search(rf"\b{re.escape(w)}", norm) for w in words)


def lint(rows: List[Dict[str, str]], max_title_px: int) -> List[Dict[str, Any]]:
    results = []
    titles = defaultdict(list)
    descs = defaultdict(list)
    current_year = dt.date.today().year
    for i, row in enumerate(rows, start=2):  # linha 1 = cabeçalho
        url = pick(row, "url") or f"(linha {i})"
        title, desc = pick(row, "title"), pick(row, "description")
        kw, brand = pick(row, "keyword"), pick(row, "brand")
        issues: List[Dict[str, str]] = []

        def add(level: str, msg: str) -> None:
            issues.append({"nivel": level, "mensagem": msg})

        px = pixel_width(title)
        if not title:
            add("ERRO", "Title vazio.")
        else:
            titles[normalize(title)].append(url)
            if px > max_title_px:
                add("AVISO", f"Title ~{px}px ({len(title)} car.): provável corte acima de ~{max_title_px}px.")
            if len(title) < TITLE_MIN_CHARS:
                add("AVISO", f"Title curto ({len(title)} car.).")
            if title.isupper():
                add("AVISO", "Title todo em maiúsculas.")
            if kw:
                if not keyword_in(kw, title):
                    add("AVISO", f"Palavra principal \"{kw}\" não aparece no title.")
                else:
                    first = re.findall(r"\w+", normalize(kw))
                    if first and len(re.findall(rf"\b{re.escape(first[-1])}", normalize(title))) > 2:
                        add("AVISO", "Termo repetido mais de 2 vezes no title (parece keyword stuffing).")
            if brand:
                nb, nt = normalize(brand), normalize(title)
                if nb in nt and not (nt.startswith(nb) or nt.endswith(nb)):
                    add("INFO", "Marca no meio do title; prefira no início (home) ou no fim.")
            for y in re.findall(r"\b(20\d{2})\b", title):
                if int(y) < current_year:
                    add("AVISO", f"Title cita {y}; se o conteúdo foi atualizado, atualize o ano (ou remova).")
        if not desc:
            add("ERRO", "Meta description vazia.")
        else:
            descs[normalize(desc)].append(url)
            if len(desc) < DESC_MIN_CHARS:
                add("AVISO", f"Description curta ({len(desc)} car.).")
            if len(desc) > DESC_MAX_CHARS:
                add("AVISO", f"Description longa ({len(desc)} car.): será cortada; deixe o essencial na primeira frase.")
            if kw and not keyword_in(kw, desc):
                add("INFO", "Palavra principal (ou variação) ausente na description; o Google destaca em negrito os termos buscados.")
            if title and normalize(desc) == normalize(title):
                add("ERRO", "Description igual ao title.")
        ph = find_placeholders(f"{title} {desc}")
        if ph:
            add("ERRO", f"Texto de modelo não substituído: {', '.join(sorted(set(ph)))}.")
        results.append({"url": url, "title": title, "title_px": px, "title_car": len(title),
                        "description_car": len(desc), "achados": issues})

    for norm_title, urls in titles.items():
        if len(urls) > 1:
            for r in results:
                if r["url"] in urls:
                    r["achados"].append({"nivel": "ERRO", "mensagem": f"Title duplicado em {len(urls)} páginas: {', '.join(urls)}."})
    for norm_desc, urls in descs.items():
        if len(urls) > 1:
            for r in results:
                if r["url"] in urls:
                    r["achados"].append({"nivel": "ERRO", "mensagem": f"Description duplicada em {len(urls)} páginas."})
    return results


def read_csv(path: str) -> List[Dict[str, str]]:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        sample = fh.read(4096)
        fh.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        return list(csv.DictReader(fh, dialect=dialect))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", help="arquivo CSV com url, title, description, palavra_principal, marca")
    ap.add_argument("--max-title-px", type=int, default=TITLE_MAX_PX)
    ap.add_argument("--format", choices=["md", "json"], default="md")
    args = ap.parse_args()
    try:
        rows = read_csv(args.csv)
    except OSError as err:
        print(f"erro: {err}", file=sys.stderr)
        sys.exit(2)
    if not rows:
        print("erro: CSV vazio", file=sys.stderr)
        sys.exit(2)
    results = lint(rows, args.max_title_px)
    errors = sum(1 for r in results for a in r["achados"] if a["nivel"] == "ERRO")
    if args.format == "json":
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print("| URL | Title (car. / ~px) | Desc. (car.) | Achados |\n|---|---|---|---|")
        for r in results:
            ach = "<br>".join(f"**{a['nivel']}** {a['mensagem']}" for a in r["achados"]) or "ok"
            print(f"| {r['url']} | {r['title_car']} / {r['title_px']} | {r['description_car']} | {ach} |")
        print(f"\n{len(results)} páginas · {errors} erro(s) · "
              f"{sum(1 for r in results for a in r['achados'] if a['nivel'] == 'AVISO')} aviso(s)")
        print("_Largura em pixels é estimativa (Arial 20px). Nenhum limite é oficial: o Google corta pela largura da tela._")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
