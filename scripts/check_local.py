#!/usr/bin/env python3
"""Confere a consistência de NAP (nome, endereço, telefone) para SEO local (pilares 6 e 10).

IAs e o Google cruzam o site, o Perfil da Empresa, Apple Business, Bing Places e diretórios.
Dados divergentes enfraquecem a entidade. Este script compara:
  - o NAP de referência (informado, ou o do JSON-LD da primeira página);
  - o JSON-LD LocalBusiness/Organization de cada página;
  - os telefones e o endereço visíveis no HTML (e links tel:);
  - opcionalmente, uma planilha de citações (diretórios) exportada ou preenchida à mão.
Também aponta o que falta para o negócio local: horário, geo, link do mapa, sameAs, areaServed.

Uso:
  python3 check_local.py https://dominio.com/ https://dominio.com/contato/
  python3 check_local.py https://dominio.com/ --nome "Clínica Aurora" --telefone "+55 27 3000-0000" \\
      --endereco "Rua das Flores, 100, Vitória, ES, 29000-000"
  python3 check_local.py https://dominio.com/ --citacoes citacoes.csv --format json

Planilha de citações: colunas diretorio, url, nome, telefone, endereco (vírgula ou ponto e vírgula).
Modelo: templates/citacoes-locais.csv.

Saída: 0 consistente, 1 com divergência de NAP (ERRO), 2 falha de uso ou de rede.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _seo_common import fetch, find_column, html_to_text, normalize, read_csv  # noqa: E402
from audit_page import PageParser  # noqa: E402
from lint_schema import LOCAL, ORG, types_of, walk  # noqa: E402

PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s.-]?)?\(?\d{2,3}\)?[\s.-]?\d{4,5}[\s.-]?\d{4}")
MAPS_RE = re.compile(r"(google\.[a-z.]+/maps|maps\.app\.goo\.gl|goo\.gl/maps|g\.page/|maps\.apple\.com|bing\.com/maps)", re.I)
SUFFIX = re.compile(r"\b(ltda|me|epp|eireli|s\.?a\.?|llc|inc|corp|co|ltd)\b\.?", re.I)
ABBR = {"r": "rua", "av": "avenida", "al": "alameda", "trav": "travessa", "rod": "rodovia", "pc": "praca",
        "pca": "praca", "est": "estrada", "st": "street", "ave": "avenue", "rd": "road", "blvd": "boulevard",
        "dr": "drive", "ste": "suite", "n": "numero", "no": "numero", "nº": "numero", "apto": "apartamento",
        "sl": "sala", "cj": "conjunto", "bl": "bloco"}


def phone_key(value: str) -> str:
    d = re.sub(r"\D", "", value or "")
    return d[-10:] if len(d) > 10 else d  # compara DDD + número (ignora código do país)


def phone_match(a: str, b: str) -> bool:
    ka, kb = phone_key(a), phone_key(b)
    if not ka or not kb:
        return False
    return ka == kb or ka[-8:] == kb[-8:] and (len(ka) < 10 or len(kb) < 10 or ka[:2] == kb[:2])


def name_key(value: str) -> str:
    return re.sub(r"\s+", " ", SUFFIX.sub(" ", normalize(value)).replace("&", " e ")).strip(" .,-")


def addr_tokens(value: str) -> List[str]:
    toks = re.findall(r"[a-z0-9]+", normalize(value))
    return [ABBR.get(t, t) for t in toks if t not in ("de", "da", "do", "das", "dos", "e")]


def postal(value: str) -> str:
    m = re.search(r"\b\d{5}-?\d{3}\b", value or "") or re.search(r"\b\d{5}(?:-\d{4})?\b", value or "")
    return re.sub(r"\D", "", m.group(0)) if m else ""


def addr_match(a: str, b: str) -> bool:
    if not a or not b:
        return False
    pa, pb = postal(a), postal(b)
    if pa and pb and pa[:5] != pb[:5]:
        return False
    ta, tb = set(addr_tokens(a)), set(addr_tokens(b))
    if not ta or not tb:
        return False
    return len(ta & tb) / min(len(ta), len(tb)) >= 0.7


def address_text(addr: Any) -> str:
    if isinstance(addr, str):
        return addr
    if isinstance(addr, dict):
        keys = ("streetAddress", "addressLocality", "addressRegion", "postalCode", "addressCountry")
        return ", ".join(str(addr.get(k)) for k in keys if addr.get(k) and not isinstance(addr.get(k), dict))
    if isinstance(addr, list) and addr:
        return address_text(addr[0])
    return ""


def business_nodes(jsonld_raw: List[str]) -> List[Dict[str, Any]]:
    out = []
    for raw in jsonld_raw:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        nodes: List[tuple] = []
        walk(data, nodes)
        for node, _parent, _path in nodes:
            tps = types_of(node)
            if any(t in LOCAL or t in ORG or t.endswith("Store") for t in tps) and (node.get("name") or node.get("address")):
                out.append(node)
    # LocalBusiness primeiro
    out.sort(key=lambda n: 0 if any(t in LOCAL or t.endswith("Store") for t in types_of(n)) else 1)
    return out


def inspect(source: str) -> Dict[str, Any]:
    f = fetch(source)
    html = f.text()
    p = PageParser()
    p.feed(html)
    p.close()
    text = html_to_text(html)
    nodes = business_nodes(p.jsonld_raw)
    node = nodes[0] if nodes else {}
    tel_links = [a["href"][4:] for a in p.anchors if (a.get("href") or "").lower().startswith("tel:")]
    phones = sorted({m.group(0).strip() for m in PHONE_RE.finditer(text) if len(re.sub(r"\D", "", m.group(0))) >= 10})
    links = " ".join((a.get("href") or "") for a in p.anchors) + " " + " ".join(re.findall(r"<iframe[^>]+src=[\"']([^\"']+)", html, re.I))
    same_as = node.get("sameAs") or []
    same_as = same_as if isinstance(same_as, list) else [same_as]
    return {"url": source, "status": f.status, "texto": normalize(text), "tipos": types_of(node) if node else [],
            "nome": node.get("name") or "", "telefone": node.get("telephone") or "",
            "endereco": address_text(node.get("address")), "horario": bool(node.get("openingHoursSpecification") or node.get("openingHours")),
            "geo": bool(node.get("geo")), "area_atendida": bool(node.get("areaServed")),
            "same_as": same_as, "telefones_visiveis": phones, "links_tel": tel_links,
            "link_mapa": bool(MAPS_RE.search(links)), "tem_jsonld_negocio": bool(nodes)}


def check(sources: List[str], ref: Dict[str, str], citations: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
    findings: List[Dict[str, str]] = []

    def add(level: str, where: str, msg: str) -> None:
        findings.append({"nivel": level, "onde": where, "mensagem": msg})

    pages = [inspect(s) for s in sources]
    ref = dict(ref)
    first = next((pg for pg in pages if pg["tem_jsonld_negocio"]), None)
    origin = "informado"
    if first and not (ref.get("nome") and ref.get("telefone") and ref.get("endereco")):
        origin = f"JSON-LD de {first['url']}" if not any(ref.values()) else "informado + JSON-LD"
        ref["nome"] = ref.get("nome") or first["nome"]
        ref["telefone"] = ref.get("telefone") or first["telefone"]
        ref["endereco"] = ref.get("endereco") or first["endereco"]
    if not any(ref.values()):
        add("ERRO", "referência", "Sem NAP de referência: informe --nome/--telefone/--endereco ou publique LocalBusiness no JSON-LD.")
    for pg in pages:
        w = pg["url"]
        if pg["status"] not in (None, 200):
            add("ERRO", w, f"Status {pg['status']}.")
            continue
        if not pg["tem_jsonld_negocio"]:
            add("AVISO", w, "Sem LocalBusiness/Organization no JSON-LD.")
        else:
            if ref.get("nome") and pg["nome"] and name_key(pg["nome"]) != name_key(ref["nome"]):
                add("AVISO", w, f"Nome no JSON-LD \"{pg['nome']}\" difere da referência \"{ref['nome']}\".")
            if ref.get("telefone") and pg["telefone"] and not phone_match(pg["telefone"], ref["telefone"]):
                add("ERRO", w, f"Telefone no JSON-LD {pg['telefone']} difere da referência {ref['telefone']}.")
            if ref.get("endereco") and pg["endereco"] and not addr_match(pg["endereco"], ref["endereco"]):
                add("ERRO", w, f"Endereço no JSON-LD \"{pg['endereco']}\" difere da referência \"{ref['endereco']}\".")
            if pg["tipos"] and not any(t in LOCAL or t.endswith("Store") for t in pg["tipos"]):
                add("INFO", w, f"Tipo {', '.join(pg['tipos'])}: para negócio com endereço, use um subtipo de LocalBusiness.")
            if not pg["horario"]:
                add("INFO", w, "JSON-LD sem horário (openingHoursSpecification).")
            if not pg["geo"]:
                add("INFO", w, "JSON-LD sem geo (latitude/longitude).")
            if not pg["area_atendida"]:
                add("INFO", w, "JSON-LD sem areaServed (cidades/bairros atendidos).")
            if not any(MAPS_RE.search(str(s)) for s in pg["same_as"]):
                add("INFO", w, "sameAs sem o link do Perfil da Empresa/mapa.")
        if ref.get("telefone"):
            if not any(phone_match(x, ref["telefone"]) for x in pg["telefones_visiveis"] + pg["links_tel"]):
                add("AVISO", w, f"Telefone de referência {ref['telefone']} não aparece no texto da página.")
            other = [x for x in pg["telefones_visiveis"] if not phone_match(x, ref["telefone"])]
            if other:
                add("INFO", w, f"Outros telefones visíveis: {', '.join(other[:4])} (confirme se são oficiais e iguais nos diretórios).")
        if pg["telefones_visiveis"] and not pg["links_tel"]:
            add("INFO", w, "Telefone sem link tel: (no celular, tocar para ligar).")
        if ref.get("endereco"):
            pc = postal(ref["endereco"])
            street = " ".join(addr_tokens(ref["endereco"])[:3])
            if not ((pc and pc in re.sub(r"\D", "", pg["texto"])) or (street and street in " ".join(addr_tokens(pg["texto"])))):
                add("INFO", w, "Endereço de referência não aparece no texto desta página (ok se não for a página de contato).")
    if pages and not any(pg["link_mapa"] for pg in pages):
        add("INFO", "site", "Nenhuma página verificada tem link ou mapa incorporado do Google/Apple/Bing Maps.")

    cit_rows: List[Dict[str, Any]] = []
    if citations:
        cols = {k: find_column(citations, al) for k, al in {
            "diretorio": ["diretorio", "diretório", "fonte", "site", "directory"],
            "url": ["url", "link"], "nome": ["nome", "name", "empresa"],
            "telefone": ["telefone", "phone", "fone"], "endereco": ["endereco", "endereço", "address"]}.items()}
        for row in citations:
            g = lambda k: (row.get(cols[k]) or "").strip() if cols[k] else ""  # noqa: E731
            res = {"diretorio": g("diretorio") or g("url"), "url": g("url"), "problemas": []}
            if g("nome") and ref.get("nome") and name_key(g("nome")) != name_key(ref["nome"]):
                res["problemas"].append(f"nome \"{g('nome')}\"")
            if g("telefone") and ref.get("telefone") and not phone_match(g("telefone"), ref["telefone"]):
                res["problemas"].append(f"telefone {g('telefone')}")
            if g("endereco") and ref.get("endereco") and not addr_match(g("endereco"), ref["endereco"]):
                res["problemas"].append(f"endereço \"{g('endereco')}\"")
            res["situacao"] = "divergente" if res["problemas"] else "ok"
            cit_rows.append(res)
        bad = [c for c in cit_rows if c["problemas"]]
        if bad:
            add("ERRO", "citações", f"{len(bad)} de {len(cit_rows)} citação(ões) com NAP divergente: "
                + "; ".join(f"{c['diretorio']} ({', '.join(c['problemas'])})" for c in bad[:10]))
    order = {"ERRO": 0, "AVISO": 1, "INFO": 2}
    findings.sort(key=lambda x: order[x["nivel"]])
    for pg in pages:
        pg.pop("texto", None)
    return {"referencia": ref, "origem_referencia": origin, "paginas": pages, "citacoes": cit_rows,
            "achados": findings, "erros": sum(1 for x in findings if x["nivel"] == "ERRO")}


def to_md(r: Dict[str, Any]) -> str:
    ref = r["referencia"]
    out = ["# Consistência de NAP (SEO local)", "",
           f"Referência ({r['origem_referencia']}): **{ref.get('nome') or '?'}** · {ref.get('telefone') or '?'} · {ref.get('endereco') or '?'}", "",
           "| Página | JSON-LD | Telefones visíveis | tel: | Mapa |", "|---|---|---|---|---|"]
    for pg in r["paginas"]:
        out.append(f"| {pg['url']} | {', '.join(pg['tipos']) or '-'} | {', '.join(pg['telefones_visiveis'][:3]) or '-'} | "
                   f"{'sim' if pg['links_tel'] else 'não'} | {'sim' if pg['link_mapa'] else 'não'} |")
    if r["citacoes"]:
        out += ["", "## Citações", "", "| Diretório | Situação | Divergências |", "|---|---|---|"]
        out += [f"| {c['diretorio']} | {c['situacao']} | {', '.join(c['problemas']) or '-'} |" for c in r["citacoes"]]
    out += ["", "## Achados", ""]
    out += [f"- **{f['nivel']}** ({f['onde']}) {f['mensagem']}" for f in r["achados"]] or ["NAP consistente."]
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paginas", nargs="+", help="URLs ou arquivos HTML (home, contato, unidades)")
    ap.add_argument("--nome")
    ap.add_argument("--telefone")
    ap.add_argument("--endereco")
    ap.add_argument("--citacoes", help="CSV com diretorio, url, nome, telefone, endereco")
    ap.add_argument("--format", choices=["md", "json"], default="md")
    args = ap.parse_args()
    ref = {k: v for k, v in {"nome": args.nome, "telefone": args.telefone, "endereco": args.endereco}.items() if v}
    try:
        cits = read_csv(args.citacoes) if args.citacoes else None
        r = check(args.paginas, ref, cits)
    except OSError as err:
        print(f"erro: {err}", file=sys.stderr)
        sys.exit(2)
    print(json.dumps(r, ensure_ascii=False, indent=2) if args.format == "json" else to_md(r))
    sys.exit(1 if r["erros"] else 0)


if __name__ == "__main__":
    main()
