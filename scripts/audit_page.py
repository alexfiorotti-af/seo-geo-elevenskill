#!/usr/bin/env python3
"""Audita SEO/GEO de uma página a partir do HTML bruto (sem executar JavaScript).

Lê o HTML exatamente como a maioria dos crawlers de IA lê: o que o servidor entrega.
Se o conteúdo só aparece depois do JavaScript, este relatório vai mostrar a página vazia,
e é exatamente esse o problema a corrigir (pilar 4).

Uso:
  python3 audit_page.py https://dominio.com/pagina/
  python3 audit_page.py pagina.html --base-url https://dominio.com/pagina/
  python3 audit_page.py https://dominio.com/ --format json
  python3 audit_page.py https://dominio.com/ --user-agent "OAI-SearchBot/1.3"

Saída: 0 sem erros, 1 com erros, 2 falha de uso ou de rede.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.parse
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _seo_common import (  # noqa: E402
    DEFAULT_UA, DESC_MAX_CHARS, DESC_MIN_CHARS, GOOGLEBOT_HTML_LIMIT, TITLE_MAX_PX, TITLE_MIN_CHARS,
    fetch, find_placeholders, is_url, pixel_width, same_site,
)

GENERIC_ANCHORS = {"clique aqui", "saiba mais", "leia mais", "aqui", "veja mais", "click here",
                   "read more", "learn more", "mais", "link"}
SKIP_TEXT_TAGS = {"script", "style", "noscript", "template", "svg"}


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.html_lang: Optional[str] = None
        self.base_href: Optional[str] = None
        self.titles: List[str] = []
        self.metas: List[Dict[str, str]] = []
        self.links: List[Dict[str, str]] = []
        self.headings: List[Dict[str, Any]] = []
        self.images: List[Dict[str, Optional[str]]] = []
        self.anchors: List[Dict[str, Any]] = []
        self.jsonld_raw: List[str] = []
        self.text_chunks: List[str] = []
        self._stack: List[str] = []
        self._in_title = False
        self._title_buf: List[str] = []
        self._heading: Optional[Dict[str, Any]] = None
        self._anchor: Optional[Dict[str, Any]] = None
        self._in_jsonld = False
        self._jsonld_buf: List[str] = []
        self._skip_depth = 0
        self._in_body = False

    def handle_starttag(self, tag: str, attrs_list):  # noqa: C901
        attrs = {k.lower(): (v if v is not None else "") for k, v in attrs_list}
        if tag == "html":
            self.html_lang = attrs.get("lang")
        elif tag == "body":
            self._in_body = True
        elif tag == "title" and not self._in_body and "svg" not in self._stack:
            self._in_title = True
            self._title_buf = []
        elif tag == "meta":
            self.metas.append(attrs)
        elif tag == "link":
            self.links.append(attrs)
        elif re.fullmatch(r"h[1-6]", tag):
            self._heading = {"level": int(tag[1]), "text": []}
        elif tag == "img":
            self.images.append({k: attrs.get(k) if k in attrs else None
                                for k in ("src", "alt", "width", "height", "loading", "fetchpriority")})
            if self._anchor is not None:
                self._anchor["img_alt"] = attrs.get("alt", "")
        elif tag == "base" and "href" in attrs:
            self.base_href = attrs.get("href")
        elif tag == "a":
            self._anchor = {"href": attrs.get("href") if "href" in attrs else None,
                            "rel": attrs.get("rel", ""), "text": [],
                            "aria": attrs.get("aria-label", "")}
        elif tag == "script" and attrs.get("type", "").lower() == "application/ld+json":
            self._in_jsonld = True
            self._jsonld_buf = []
        if tag in SKIP_TEXT_TAGS:
            self._skip_depth += 1
        if tag not in {"meta", "link", "img", "br", "hr", "input", "source"}:
            self._stack.append(tag)

    def handle_endtag(self, tag: str):
        if tag == "title" and self._in_title:
            self.titles.append(" ".join("".join(self._title_buf).split()))
            self._in_title = False
        elif re.fullmatch(r"h[1-6]", tag) and self._heading is not None:
            self._heading["text"] = " ".join("".join(self._heading["text"]).split())
            self.headings.append(self._heading)
            self._heading = None
        elif tag == "a" and self._anchor is not None:
            self._anchor["text"] = " ".join("".join(self._anchor["text"]).split())
            self.anchors.append(self._anchor)
            self._anchor = None
        elif tag == "script" and self._in_jsonld:
            self.jsonld_raw.append("".join(self._jsonld_buf))
            self._in_jsonld = False
        if tag in SKIP_TEXT_TAGS and self._skip_depth:
            self._skip_depth -= 1
        if tag in self._stack:
            while self._stack and self._stack.pop() != tag:
                pass

    def handle_data(self, data: str):
        if self._in_title:
            self._title_buf.append(data)
        if self._in_jsonld:
            self._jsonld_buf.append(data)
            return
        if self._skip_depth:
            return
        if self._heading is not None:
            self._heading["text"].append(data)
        if self._anchor is not None:
            self._anchor["text"].append(data)
        if self._in_body:
            self.text_chunks.append(data)


def meta_content(metas: List[Dict[str, str]], *, name: str = "", prop: str = "") -> List[str]:
    out = []
    for m in metas:
        if name and m.get("name", "").lower() == name:
            out.append(m.get("content", ""))
        if prop and m.get("property", "").lower() == prop:
            out.append(m.get("content", ""))
    return out


def collect_types(node: Any, acc: List[str]) -> None:
    if isinstance(node, dict):
        t = node.get("@type")
        if isinstance(t, str):
            acc.append(t)
        elif isinstance(t, list):
            acc.extend(str(x) for x in t)
        for v in node.values():
            collect_types(v, acc)
    elif isinstance(node, list):
        for v in node:
            collect_types(v, acc)


def audit(html: str, page_url: Optional[str], status: Optional[int] = None,
          headers: Optional[Dict[str, str]] = None, redirects: Optional[List[str]] = None,
          size_bytes: Optional[int] = None) -> Dict[str, Any]:
    headers = headers or {}
    if size_bytes is None:
        size_bytes = len(html.encode("utf-8"))
    p = PageParser()
    p.feed(html)
    p.close()
    findings: List[Dict[str, str]] = []

    def add(level: str, pillar: str, msg: str) -> None:
        findings.append({"nivel": level, "pilar": pillar, "mensagem": msg})

    # --- HTTP (pilares 3 e 4) ---
    if status is not None and status != 200:
        add("ERRO", "3", f"Status HTTP {status}. Páginas que devem ranquear precisam responder 200.")
    if status is not None and status >= 400:
        add("INFO", "3", "Demais verificações suspensas: o HTML recebido é uma página de erro. "
                         "Se o site bloqueia este user-agent, teste com --user-agent ou salve o HTML e audite o arquivo.")
        return {"url": page_url, "status": status, "redirects": redirects or [], "title": "", "title_px": 0,
                "description": "", "canonical": None, "robots": None, "lang": None, "h1": [], "headings": [],
                "jsonld_types": [], "palavras": 0, "links_internos": 0, "links_externos": 0, "imagens": 0,
                "achados": findings, "erros": 1}
    if redirects:
        if len(redirects) > 1:
            add("AVISO", "3", f"Cadeia de {len(redirects)} redirects; aponte direto para o destino final.")
        for r in redirects:
            if r.startswith("302") or r.startswith("307"):
                add("AVISO", "3", f"Redirect temporário ({r.split()[0]}); use 301/308 se a mudança for permanente.")

    # --- Tamanho (pilar 4): o Googlebot lê só os primeiros 2 MB de cada URL (inclui cabeçalhos) ---
    header_bytes = sum(len(k) + len(v) + 4 for k, v in headers.items())
    total = size_bytes + header_bytes
    if total > GOOGLEBOT_HTML_LIMIT:
        add("ERRO", "4", f"HTML com {total / 1048576:.1f} MB: o Googlebot para de ler em 2 MB (cabeçalhos incluídos) "
                         "e ignora o resto. Tire CSS/JS/SVG/JSON embutidos e mova o conteúdo principal para o início.")
    elif total > GOOGLEBOT_HTML_LIMIT * 0.75:
        add("AVISO", "4", f"HTML com {total / 1048576:.1f} MB, perto do limite de 2 MB do Googlebot.")

    # --- Robots ---
    robots_meta = " ".join(meta_content(p.metas, name="robots") + meta_content(p.metas, name="googlebot")).lower()
    x_robots = headers.get("x-robots-tag", "").lower()
    robots_all = f"{robots_meta} {x_robots}"
    if re.search(r"\b(noindex|none)\b", robots_all):
        add("ERRO", "3", "Página com noindex (meta robots ou X-Robots-Tag). Se não for intencional, remova.")
    if "nosnippet" in robots_all or re.search(r"max-snippet:\s*0\b", robots_all):
        add("AVISO", "10", "nosnippet/max-snippet:0 ativo: a página não terá snippet nem aparecerá em AI Overviews/AI Mode.")

    # --- Title (pilar 8) ---
    title = p.titles[0] if p.titles else ""
    if not p.titles or not title:
        add("ERRO", "8", "Sem <title> no HTML do servidor.")
    else:
        if len(p.titles) > 1:
            add("AVISO", "8", f"{len(p.titles)} elementos <title>; mantenha só um.")
        px = pixel_width(title)
        if px > TITLE_MAX_PX:
            add("AVISO", "8", f"Title com ~{px}px ({len(title)} caracteres): provável corte acima de ~{TITLE_MAX_PX}px.")
        if len(title) < TITLE_MIN_CHARS:
            add("AVISO", "8", f"Title curto ({len(title)} caracteres): falta contexto (serviço, qualificador, marca).")
        if title.isupper():
            add("AVISO", "8", "Title todo em maiúsculas.")

    # --- Description ---
    descs = meta_content(p.metas, name="description")
    desc = descs[0].strip() if descs else ""
    if not desc:
        add("AVISO", "8", "Sem meta description: o Google vai montar o snippet só com o texto da página.")
    else:
        if len(descs) > 1:
            add("AVISO", "8", "Mais de uma meta description.")
        if len(desc) < DESC_MIN_CHARS:
            add("AVISO", "8", f"Meta description curta ({len(desc)} caracteres).")
        if len(desc) > DESC_MAX_CHARS:
            add("INFO", "8", f"Meta description longa ({len(desc)} caracteres): pode ser cortada; a primeira frase deve se sustentar sozinha.")
        if title and desc.strip().lower() == title.strip().lower():
            add("AVISO", "8", "Meta description igual ao title.")
    if meta_content(p.metas, name="keywords"):
        add("INFO", "8", "meta keywords presente: o Google ignora; pode remover.")

    # --- Canonical ---
    canon = [l.get("href", "") for l in p.links if "canonical" in l.get("rel", "").lower().split()]
    if not canon:
        add("AVISO", "3", "Sem link rel=canonical.")
    else:
        if len(canon) > 1:
            add("ERRO", "3", f"{len(canon)} canonicals diferentes; o Google pode ignorar todos.")
        c = canon[0]
        if not is_url(c):
            add("AVISO", "3", f"Canonical relativo ({c}); use URL absoluta.")
        elif page_url and is_url(page_url):
            norm = lambda u: u.split("#")[0]  # noqa: E731
            if norm(c) != norm(page_url):
                add("INFO", "3", f"Canonical aponta para outra URL: {c}. Confirme que é intencional.")

    # --- hreflang ---
    alternates = [l for l in p.links if "alternate" in l.get("rel", "").lower().split() and l.get("hreflang")]
    if alternates:
        hrefs = [a.get("href", "") for a in alternates]
        langs = [a.get("hreflang", "").lower() for a in alternates]
        if canon and canon[0] not in hrefs:
            add("AVISO", "3", "hreflang sem autorreferência (a página não lista a si mesma).")
        if "x-default" not in langs:
            add("INFO", "3", "hreflang sem x-default.")

    # --- lang / viewport (pilar 7) ---
    if not p.html_lang:
        add("AVISO", "7", "<html> sem atributo lang.")
    viewport = meta_content(p.metas, name="viewport")
    if not viewport:
        add("ERRO", "7", "Sem meta viewport: a página não é responsiva para o índice mobile-first.")
    elif re.search(r"user-scalable\s*=\s*(no|0)|maximum-scale\s*=\s*1(\.0)?\b", viewport[0], re.I):
        add("AVISO", "7", "Viewport bloqueia zoom (acessibilidade).")

    # --- Headings ---
    h1s = [h for h in p.headings if h["level"] == 1]
    if not h1s:
        add("ERRO", "7", "Sem H1 no HTML do servidor (ou só aparece após JavaScript).")
    elif len(h1s) > 1:
        add("AVISO", "7", f"{len(h1s)} H1; use um único H1 com o assunto da página.")
    prev = 0
    for h in p.headings:
        if prev and h["level"] > prev + 1:
            add("AVISO", "7", f"Hierarquia pula de H{prev} para H{h['level']} em \"{h['text'][:60]}\".")
            break
        prev = h["level"]
    empty_h = [h for h in p.headings if not h["text"]]
    if empty_h:
        add("AVISO", "7", f"{len(empty_h)} heading(s) vazio(s).")

    # --- Imagens ---
    no_alt = [i for i in p.images if i.get("alt") is None]
    if no_alt:
        add("AVISO", "7", f"{len(no_alt)} imagem(ns) sem atributo alt (use alt=\"\" só para decorativas).")
    no_dim = [i for i in p.images if not (i.get("width") and i.get("height"))]
    if no_dim:
        add("INFO", "5", f"{len(no_dim)} imagem(ns) sem width/height no HTML (risco de CLS se o CSS não reservar espaço).")
    if p.images and (p.images[0].get("loading") or "").lower() == "lazy":
        add("AVISO", "5", "A primeira imagem da página usa loading=lazy; se for a imagem do LCP, remova o lazy.")

    # --- Links ---
    internal = external = 0
    generic = 0
    no_href = 0
    for a in p.anchors:
        href = a["href"]
        if href is None or href.strip() in ("", "#") or href.lower().startswith("javascript:"):
            no_href += 1
            continue
        absolute = urllib.parse.urljoin(page_url or "", href) if page_url else href
        if href.startswith(("mailto:", "tel:")):
            continue
        if page_url and is_url(absolute) and same_site(absolute, page_url):
            internal += 1
        elif is_url(absolute):
            external += 1
        else:
            internal += 1
        if (a["text"] or "").strip().lower() in GENERIC_ANCHORS and not a["aria"]:
            generic += 1
    if no_href:
        add("AVISO", "4", f"{no_href} link(s) sem href rastreável (href vazio, # ou javascript:). Robôs não seguem.")
    if generic:
        add("INFO", "9", f"{generic} link(s) com âncora genérica (\"saiba mais\", \"clique aqui\"); prefira texto descritivo.")
    if internal == 0:
        add("AVISO", "9", "Nenhum link interno no HTML do servidor.")

    # --- Open Graph ---
    for prop in ("og:title", "og:description", "og:image"):
        if not meta_content(p.metas, prop=prop):
            add("AVISO", "8", f"Sem {prop} (afeta compartilhamento em WhatsApp e redes).")
    og_img = meta_content(p.metas, prop="og:image")
    if og_img and not is_url(og_img[0]):
        add("AVISO", "8", "og:image com URL relativa; use URL absoluta.")

    # --- JSON-LD (pilar 6) ---
    types: List[str] = []
    for raw in p.jsonld_raw:
        try:
            collect_types(json.loads(raw), types)
        except json.JSONDecodeError as err:
            add("ERRO", "6", f"JSON-LD inválido: {err.msg} (linha {err.lineno}).")
        ph = find_placeholders(raw)
        if ph:
            add("ERRO", "6", f"JSON-LD com texto de modelo não substituído: {', '.join(sorted(set(ph)))}.")
    if not p.jsonld_raw:
        add("AVISO", "6", "Sem dados estruturados JSON-LD no HTML do servidor.")

    # --- Conteúdo / renderização ---
    body_text = " ".join(" ".join(p.text_chunks).split())
    words = len(re.findall(r"\w+", body_text))
    if words < 150:
        add("AVISO", "4", f"Só {words} palavras no HTML do servidor. Se a página mostra mais no navegador, o conteúdo depende de JavaScript e fica invisível para crawlers de IA.")
    if page_url and page_url.startswith("https://"):
        mixed = [i.get("src") for i in p.images if (i.get("src") or "").startswith("http://")]
        mixed += re.findall(r"""<(?:script|iframe)[^>]+src=["'](http://[^"']+)""", html, re.I)
        if mixed:
            add("AVISO", "5", f"{len(mixed)} recurso(s) carregado(s) por http:// em página https (conteúdo misto; o navegador bloqueia).")
    if re.search(r"history\.(pushState|replaceState)\s*\(", html) and re.search(r"popstate", html):
        add("INFO", "11", "Script no HTML manipula o histórico (pushState/replaceState + popstate). É normal em SPA, "
                          "mas confira se o botão Voltar leva à página anterior: sequestro do Voltar é spam no Google desde 15/06/2026.")
    head_values = " ".join([title, desc, *canon, *(m.get("content", "") for m in p.metas if m.get("property", "").startswith("og:"))])
    ph_page = find_placeholders(head_values)
    if ph_page:
        add("ERRO", "8", f"Metadados com texto de modelo não substituído: {', '.join(sorted(set(ph_page)))}.")

    order = {"ERRO": 0, "AVISO": 1, "INFO": 2}
    findings.sort(key=lambda f: (order[f["nivel"]], f["pilar"]))
    return {
        "url": page_url,
        "status": status,
        "redirects": redirects or [],
        "title": title,
        "title_px": pixel_width(title) if title else 0,
        "description": desc,
        "canonical": canon[0] if canon else None,
        "robots": robots_all.strip() or None,
        "lang": p.html_lang,
        "h1": [h["text"] for h in h1s],
        "headings": [f"H{h['level']} {h['text']}" for h in p.headings][:40],
        "jsonld_types": sorted(set(types)),
        "palavras": words,
        "links_internos": internal,
        "links_externos": external,
        "imagens": len(p.images),
        "bytes_html": size_bytes,
        "achados": findings,
        "erros": sum(1 for f in findings if f["nivel"] == "ERRO"),
    }


def to_markdown(r: Dict[str, Any]) -> str:
    lines = [f"# Auditoria de página: {r['url'] or '(arquivo local)'}", ""]
    lines += [
        "| Campo | Valor |", "|---|---|",
        f"| Status | {r['status'] if r['status'] is not None else 'arquivo local'} |",
        f"| Title | {r['title'] or '(ausente)'} (~{r['title_px']}px) |",
        f"| Description | {r['description'] or '(ausente)'} ({len(r['description'])} car.) |",
        f"| Canonical | {r['canonical'] or '(ausente)'} |",
        f"| Robots | {r['robots'] or 'padrão (index, follow)'} |",
        f"| lang | {r['lang'] or '(ausente)'} |",
        f"| H1 | {' / '.join(r['h1']) or '(ausente)'} |",
        f"| JSON-LD | {', '.join(r['jsonld_types']) or '(nenhum)'} |",
        f"| Palavras no HTML do servidor | {r['palavras']} |",
        f"| Links internos / externos | {r['links_internos']} / {r['links_externos']} |",
        f"| Imagens | {r['imagens']} |",
        "",
    ]
    if r["redirects"]:
        lines += ["**Redirects:**", *[f"- {x}" for x in r["redirects"]], ""]
    lines += ["## Achados", ""]
    if not r["achados"]:
        lines.append("Nenhum problema encontrado pelas verificações automáticas.")
    else:
        lines += ["| Nível | Pilar | Achado |", "|---|---|---|"]
        lines += [f"| {f['nivel']} | {f['pilar']} | {f['mensagem']} |" for f in r["achados"]]
    lines += ["", "## Estrutura de headings", ""]
    lines += [f"- {h}" for h in r["headings"]] or ["(nenhum)"]
    lines += ["", "_Verificação automática. Não substitui a revisão de conteúdo, intenção e GEO dos pilares 9 e 10._"]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("alvo", help="URL ou caminho de um arquivo HTML")
    ap.add_argument("--base-url", help="URL pública da página quando o alvo é um arquivo local")
    ap.add_argument("--format", choices=["md", "json"], default="md")
    ap.add_argument("--user-agent", default=DEFAULT_UA)
    args = ap.parse_args()
    try:
        f = fetch(args.alvo, user_agent=args.user_agent)
    except OSError as err:
        print(f"erro: não foi possível ler {args.alvo}: {err}", file=sys.stderr)
        sys.exit(2)
    page_url = f.final_url or args.base_url
    result = audit(f.text(), page_url, f.status, f.headers, f.redirects, size_bytes=len(f.body))
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.format == "json" else to_markdown(result))
    sys.exit(1 if result["erros"] else 0)


if __name__ == "__main__":
    main()
