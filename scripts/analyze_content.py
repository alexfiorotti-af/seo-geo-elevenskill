#!/usr/bin/env python3
"""Analisa o conteúdo de uma página: citabilidade por seção (GEO), legibilidade em português e
sinais de qualidade (pilares 9 e 10). Lê o HTML do servidor, sem JavaScript.

Citabilidade: motores de resposta extraem TRECHOS. Cada seção (H2/H3) é avaliada como uma
resposta independente:
  - resposta logo na primeira frase (curta, sem depender do texto anterior);
  - trecho autossuficiente (não começa com "Isso", "Além disso", "Ele"...);
  - tamanho de passagem (40 a 300 palavras);
  - dado verificável (número, preço, prazo, porcentagem);
  - fonte (link para fora) quando há afirmação de dado.
Legibilidade: índice de Flesch adaptado ao português (Martins et al., 1996):
  248,835 − 1,015 × (palavras/frase) − 84,6 × (sílabas/palavra). Sílabas são ESTIMADAS.
Qualidade: autor, datas, fontes, tabelas/listas, sinais de experiência própria, repetição,
concentração de palavra (stuffing), conteúdo raso.

As notas são heurísticas para priorizar revisão humana. Não são métricas do Google.

Uso:
  python3 analyze_content.py https://dominio.com/blog/artigo/
  python3 analyze_content.py pagina.html --palavra "limpeza de pele"
  python3 analyze_content.py https://dominio.com/ --format json

Saída: 0 sem erros, 1 com erros (ex.: página sem conteúdo no HTML), 2 falha de uso ou de rede.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _seo_common import DEFAULT_UA, fetch, normalize, same_site  # noqa: E402
from audit_page import PageParser, collect_types  # noqa: E402

SKIP = {"script", "style", "noscript", "template", "svg", "nav", "header", "footer", "aside", "form", "button"}
BLOCKS = {"p", "li", "td", "th", "dd", "dt", "blockquote", "figcaption", "pre"}
ANAPHORA = ("isso", "isto", "esse", "essa", "esses", "essas", "este", "esta", "ele", "ela", "eles", "elas",
            "além disso", "por isso", "assim", "também", "dessa forma", "desse modo", "nesse caso",
            "neste caso", "como dito", "como vimos", "conforme mencionado", "it ", "this ", "these ", "that ")
QUESTION_START = ("como", "qual", "quais", "quanto", "quantos", "quantas", "quando", "onde", "por que", "porque",
                  "o que", "quem", "vale a pena", "é possível", "pode", "posso", "devo", "what", "how", "why",
                  "when", "where", "which", "who", "is ", "can ", "should ", "does ", "do ")
EXPERIENCE = re.compile(r"\b(nós (testamos|atendemos|fizemos|usamos|medimos)|na nossa experiência|em nossa experiência|"
                        r"nossos (clientes|pacientes|alunos)|atendemos|testamos|acompanhamos|nosso time|"
                        r"we tested|in our experience|our clients)\b", re.I)
DATA = re.compile(r"(\d+[.,]?\d*\s*(%|por cento|r\$|us\$|€|reais|dólares|anos|meses|dias|horas|minutos|km|kg|m²|mil|milhões)|"
                  r"r\$\s*\d|\$\s*\d|\b\d{2,}\b)", re.I)
# dado de TERCEIROS (estatística, pesquisa): pede fonte. Preço e prazo do próprio negócio não pedem.
STAT = re.compile(r"(\d+[.,]?\d*\s*(%|por cento)|\b(milh(ão|ões)|bilh(ão|ões))\b|\b(pesquisa|estudo|levantamento|"
                  r"segundo (o|a|os|as)|de acordo com|dados d[aeo]|relatório)\b|according to|survey|study)", re.I)
STOP = set("""a o as os um uma uns umas de da do das dos em no na nos nas por para pra com sem sob sobre
e ou mas que se é são foi ser ter tem têm há ao aos à às como mais menos muito muita muitos muitas seu sua seus
suas nosso nossa nossos nossas the of and to in for is on with this that you your it be are or an at by from
não sim já também até ele ela eles elas isso isto esse essa este esta quando onde qual quais pelo pela pelos
pelas lhe me te nos vos meu minha teu tua dele dela num numa entre após antes depois cada todo toda todos todas""".split())


class ContentParser(HTMLParser):
    """Divide o conteúdo principal em seções por heading e blocos de texto."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.has_main = False
        self.sections: List[Dict[str, Any]] = [{"heading": "(introdução)", "nivel": 1, "blocos": [], "links_ext": [], "fonte_tag": 0}]
        self.tables = 0
        self.lists = 0
        self.times: List[str] = []
        self.author_hint = False
        self._skip = 0
        self._main_depth = 0
        self._buf: Optional[List[str]] = None
        self._heading: Optional[Dict[str, Any]] = None
        self._link: Optional[str] = None

    def handle_starttag(self, tag, attrs_list):
        attrs = {k.lower(): (v or "") for k, v in attrs_list}
        if tag in ("main", "article") or attrs.get("role") == "main":
            self.has_main = True
            self._main_depth += 1
        if tag in SKIP:
            self._skip += 1
            return
        if self._skip:
            return
        cls = (attrs.get("class", "") + " " + attrs.get("itemprop", "") + " " + attrs.get("rel", "")).lower()
        if re.search(r"\b(author|autor|byline)\b", cls):
            self.author_hint = True
        if tag == "time" and attrs.get("datetime"):
            self.times.append(attrs["datetime"])
        if tag == "table":
            self.tables += 1
        if tag in ("ul", "ol"):
            self.lists += 1
        if tag in ("cite",):
            self.sections[-1]["fonte_tag"] += 1
        if re.fullmatch(r"h[1-6]", tag):
            self._heading = {"nivel": int(tag[1]), "texto": []}
        elif tag in BLOCKS:
            self._buf = []
        if tag == "a":
            self._link = attrs.get("href", "")

    def handle_endtag(self, tag):
        if tag in ("main", "article") and self._main_depth:
            self._main_depth -= 1
        if tag in SKIP:
            if self._skip:
                self._skip -= 1
            return
        if self._skip:
            return
        if re.fullmatch(r"h[1-6]", tag) and self._heading is not None:
            text = " ".join("".join(self._heading["texto"]).split())
            level = self._heading["nivel"]
            self._heading = None
            if level in (2, 3) and text:
                self.sections.append({"heading": text, "nivel": level, "blocos": [], "links_ext": [], "fonte_tag": 0})
            elif level == 1 and text:
                self.sections[0]["heading"] = text
        elif tag in BLOCKS and self._buf is not None:
            text = " ".join("".join(self._buf).split())
            if text:
                self.sections[-1]["blocos"].append({"tag": tag, "texto": text, "main": self._main_depth > 0})
            self._buf = None
        elif tag == "a":
            self._link = None

    def handle_data(self, data):
        if self._skip:
            return
        if self._heading is not None:
            self._heading["texto"].append(data)
        elif self._buf is not None:
            self._buf.append(data)
        if self._link and self._buf is not None and data.strip():
            self.sections[-1]["links_ext"].append(self._link)


def syllables(word: str) -> int:
    w = normalize(word)
    groups = re.findall(r"[aeiouy]+", w)
    n = len(groups)
    # ditongos decrescentes comuns contam como uma sílaba (já agrupados); hiatos comuns separam
    n += len(re.findall(r"(ia|io|ua|uo|ea|eo|oa)(?=[^aeiouy]|$)", w)) // 2
    return max(1, n)


def split_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?…])\s+(?=[\"“(]?[A-ZÁÉÍÓÚÂÊÔÃÕÀÇ0-9])", text.strip())
    return [p.strip() for p in parts if re.search(r"\w", p)]


def words_of(text: str) -> List[str]:
    return re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9]+(?:[-'][A-Za-zÀ-ÖØ-öø-ÿ]+)*", text)


def flesch_pt(n_words: int, n_sent: int, n_syll: int) -> Optional[float]:
    if not n_words or not n_sent:
        return None
    return round(248.835 - 1.015 * (n_words / n_sent) - 84.6 * (n_syll / n_words), 1)


def flesch_band(score: Optional[float]) -> str:
    if score is None:
        return "sem texto"
    if score >= 75:
        return "muito fácil"
    if score >= 50:
        return "fácil"
    if score >= 25:
        return "difícil"
    return "muito difícil"


def starts_anaphoric(sentence: str) -> bool:
    s = normalize(sentence)[:40] + " "
    return any(s.startswith(a + (" " if not a.endswith(" ") else "")) or s.startswith(a + ",") for a in ANAPHORA)


def is_question(heading: str) -> bool:
    h = normalize(heading)
    return heading.strip().endswith("?") or h.startswith(QUESTION_START)


def score_section(sec: Dict[str, Any], page_url: Optional[str]) -> Dict[str, Any]:
    text = " ".join(b["texto"] for b in sec["blocos"])
    words = words_of(text)
    sentences = split_sentences(text) if text else []
    first = sentences[0] if sentences else ""
    first_len = len(words_of(first))
    ext = [h for h in sec["links_ext"] if h.startswith("http") and not (page_url and same_site(h, page_url))]
    has_data = bool(DATA.search(text))
    has_stat = bool(STAT.search(text))
    checks = {
        "resposta_direta": 8 <= first_len <= 45 and not starts_anaphoric(first),
        "autossuficiente": bool(first) and not starts_anaphoric(first),
        "tamanho_de_passagem": 40 <= len(words) <= 300,
        "dado_verificavel": has_data,
        "fonte": bool(ext) or sec.get("fonte_tag", 0) > 0,
    }
    if not has_stat:  # sem estatística de terceiros, a checagem de fonte não se aplica
        checks["fonte"] = True
    weights = {"resposta_direta": 30, "autossuficiente": 20, "tamanho_de_passagem": 15, "dado_verificavel": 20, "fonte": 15}
    score = sum(weights[k] for k, ok in checks.items() if ok)
    tips = []
    if not checks["resposta_direta"]:
        tips.append("abra com uma frase que responda o título da seção (8 a 45 palavras)")
    if not checks["autossuficiente"]:
        tips.append("não comece com 'Isso', 'Além disso', 'Ele'...: o trecho precisa fazer sentido sozinho")
    if not checks["tamanho_de_passagem"]:
        tips.append("seção curta demais para ser citada" if len(words) < 40 else "seção longa: divida em subtítulos")
    if has_stat and not checks["fonte"]:
        tips.append("estatística sem fonte: link para a origem ou diga de onde veio")
    if not has_data:
        tips.append("inclua um dado concreto (prazo, preço, número, exemplo) se houver")
    return {"heading": sec["heading"], "nivel": sec["nivel"], "pergunta": is_question(sec["heading"]),
            "palavras": len(words), "primeira_frase": first[:160], "checagens": checks, "nota": score,
            "sugestoes": tips}


def analyze(html: str, page_url: Optional[str], keyword: Optional[str] = None) -> Dict[str, Any]:
    meta = PageParser()
    meta.feed(html)
    meta.close()
    cp = ContentParser()
    cp.feed(html)
    cp.close()
    findings: List[Dict[str, str]] = []

    def add(level: str, pillar: str, msg: str) -> None:
        findings.append({"nivel": level, "pilar": pillar, "mensagem": msg})

    if cp.has_main:  # com <main>/<article>, analisa só o conteúdo principal
        for sec in cp.sections:
            sec["blocos"] = [b for b in sec["blocos"] if b["main"]]
    sections = [s for s in cp.sections if s["blocos"] or s["nivel"] > 1]
    all_text = " ".join(b["texto"] for s in cp.sections for b in s["blocos"])
    words = words_of(all_text)
    sentences = [x for s in cp.sections for b in s["blocos"] for x in split_sentences(b["texto"])]
    n_syll = sum(syllables(w) for w in words)
    flesch = flesch_pt(len(words), len(sentences), n_syll)
    long_sent = [x for x in sentences if len(words_of(x)) > 30]
    long_par = [b for s in cp.sections for b in s["blocos"] if b["tag"] == "p" and len(words_of(b["texto"])) > 120]

    if not words:
        add("ERRO", "4", "Nenhum texto de conteúdo no HTML do servidor (conteúdo depende de JavaScript ou está fora de <p>/<li>).")
    elif len(words) < 300:
        add("INFO", "9", f"Conteúdo curto ({len(words)} palavras). Para páginas informativas, cubra os subtemas que a pessoa pergunta em seguida.")
    if flesch is not None and flesch < 25:
        add("AVISO", "9", f"Leitura muito difícil (Flesch pt-BR {flesch}). Frases mais curtas e palavras mais simples.")
    if sentences and len(long_sent) / len(sentences) > 0.25:
        add("AVISO", "9", f"{len(long_sent)} de {len(sentences)} frases com mais de 30 palavras.")
    if long_par:
        add("INFO", "9", f"{len(long_par)} parágrafo(s) com mais de 120 palavras: quebre em blocos de 2 a 4 frases.")

    scored = [score_section(s, page_url) for s in sections if s["nivel"] in (2, 3)]
    if not scored and words:
        add("AVISO", "10", "Sem subtítulos H2/H3: o texto não se divide em trechos que um motor de resposta consiga citar.")
    weak = [s for s in scored if s["nota"] < 50]
    if scored and len(weak) / len(scored) > 0.5:
        add("AVISO", "10", f"{len(weak)} de {len(scored)} seções com citabilidade baixa (ver sugestões por seção).")
    q = [s for s in scored if s["pergunta"]]
    if scored and not q:
        add("INFO", "10", "Nenhum subtítulo em forma de pergunta. Use as perguntas reais do público como H2/H3 quando couber.")

    # --- sinais de qualidade e confiança ---
    jsonld_types: List[str] = []
    jsonld_author = jsonld_dates = False
    for raw in meta.jsonld_raw:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        collect_types(data, jsonld_types)
        blob = json.dumps(data)
        jsonld_author = jsonld_author or '"author"' in blob
        jsonld_dates = jsonld_dates or '"datePublished"' in blob or '"dateModified"' in blob
    meta_author = any(m.get("name", "").lower() == "author" and m.get("content") for m in meta.metas)
    rel_author = any("author" in (a.get("rel") or "").lower().split() for a in meta.anchors) or \
        any("author" in l.get("rel", "").lower().split() for l in meta.links)
    has_author = jsonld_author or meta_author or rel_author or cp.author_hint
    has_dates = jsonld_dates or bool(cp.times)
    ext_links = sorted({h for s in cp.sections for h in s["links_ext"]
                        if h.startswith("http") and not (page_url and same_site(h, page_url))})
    experience = len(EXPERIENCE.findall(all_text))
    article_like = any(t in ("Article", "BlogPosting", "NewsArticle", "TechArticle") for t in jsonld_types) or len(words) >= 600
    if article_like and not has_author:
        add("AVISO", "10", "Sem autor identificável (byline, meta author, rel=author ou author no JSON-LD).")
    if article_like and not has_dates:
        add("AVISO", "10", "Sem data de publicação/atualização (<time datetime> ou datePublished/dateModified).")
    if len(words) >= 600 and not ext_links:
        add("INFO", "10", "Nenhum link para fonte externa. Afirmações com dado ficam mais confiáveis com a origem citada.")
    if len(words) >= 600 and not (cp.tables or cp.lists):
        add("INFO", "10", "Texto longo sem lista nem tabela: comparações e passos ficam mais fáceis de extrair em lista/tabela.")

    norm_sent = Counter(normalize(x) for x in sentences if len(words_of(x)) >= 8)
    repeated = [s for s, c in norm_sent.items() if c > 1]
    if repeated:
        add("AVISO", "11", f"{len(repeated)} frase(s) repetida(s) na mesma página (texto de modelo ou gerado em série).")

    content_words = [normalize(w) for w in words if len(w) > 2 and normalize(w) not in STOP]
    top = Counter(content_words).most_common(8)
    if content_words and top and len(words) >= 200 and top[0][1] / len(words) > 0.04:
        add("AVISO", "11", f"A palavra \"{top[0][0]}\" é {top[0][1] / len(words):.1%} do texto: soa repetitivo (keyword stuffing).")
    kw = None
    if keyword:
        kn = normalize(keyword)
        count = len(re.findall(rf"\b{re.escape(kn)}\b", normalize(all_text)))
        density = count * max(1, len(kn.split())) / max(1, len(words))
        kw = {"palavra": keyword, "ocorrencias": count, "densidade": round(density, 4),
              "no_h1": kn in normalize(" ".join(h["text"] for h in meta.headings if h["level"] == 1)),
              "no_title": kn in normalize(meta.titles[0] if meta.titles else ""),
              "na_introducao": kn in normalize(" ".join(b["texto"] for b in cp.sections[0]["blocos"])[:600])}
        if count == 0:
            add("AVISO", "9", f"A palavra principal \"{keyword}\" não aparece no texto.")
        elif density > 0.03 and count >= 4:
            add("AVISO", "11", f"A palavra principal aparece em {density:.1%} do texto: reduza as repetições.")
        if not kw["no_h1"]:
            add("INFO", "9", "A palavra principal não está no H1.")

    cit = round(sum(s["nota"] for s in scored) / len(scored)) if scored else 0
    order = {"ERRO": 0, "AVISO": 1, "INFO": 2}
    findings.sort(key=lambda f: (order[f["nivel"]], f["pilar"]))
    return {
        "url": page_url,
        "palavras": len(words),
        "frases": len(sentences),
        "palavras_por_frase": round(len(words) / len(sentences), 1) if sentences else 0,
        "silabas_por_palavra": round(n_syll / len(words), 2) if words else 0,
        "flesch_pt": flesch,
        "leitura": flesch_band(flesch),
        "citabilidade": cit,
        "secoes": scored,
        "sinais": {"autor": has_author, "datas": has_dates, "fontes_externas": len(ext_links),
                   "tabelas": cp.tables, "listas": cp.lists, "marcas_de_experiencia": experience,
                   "subtitulos_pergunta": len(q), "jsonld": sorted(set(jsonld_types))},
        "termos_mais_frequentes": top,
        "palavra_principal": kw,
        "achados": findings,
        "erros": sum(1 for f in findings if f["nivel"] == "ERRO"),
    }


def to_md(r: Dict[str, Any]) -> str:
    s = r["sinais"]
    yn = lambda b: "sim" if b else "não"  # noqa: E731
    out = [f"# Conteúdo: {r['url'] or '(arquivo local)'}", "",
           "| Indicador | Valor |", "|---|---|",
           f"| Palavras / frases | {r['palavras']} / {r['frases']} ({r['palavras_por_frase']} palavras por frase) |",
           f"| Legibilidade (Flesch pt-BR) | {r['flesch_pt'] if r['flesch_pt'] is not None else '-'} ({r['leitura']}) |",
           f"| Citabilidade média das seções (0 a 100) | {r['citabilidade']} |",
           f"| Autor / datas | {yn(s['autor'])} / {yn(s['datas'])} |",
           f"| Fontes externas / tabelas / listas | {s['fontes_externas']} / {s['tabelas']} / {s['listas']} |",
           f"| Marcas de experiência própria | {s['marcas_de_experiencia']} |",
           f"| Subtítulos em forma de pergunta | {s['subtitulos_pergunta']} |",
           f"| JSON-LD | {', '.join(s['jsonld']) or '(nenhum)'} |", ""]
    if r["palavra_principal"]:
        k = r["palavra_principal"]
        out += [f"Palavra principal \"{k['palavra']}\": {k['ocorrencias']} ocorrência(s), densidade {k['densidade']:.1%}, "
                f"no title: {yn(k['no_title'])}, no H1: {yn(k['no_h1'])}, na introdução: {yn(k['na_introducao'])}.", ""]
    out += ["## Achados", ""]
    if r["achados"]:
        out += ["| Nível | Pilar | Achado |", "|---|---|---|"] + [f"| {f['nivel']} | {f['pilar']} | {f['mensagem']} |" for f in r["achados"]]
    else:
        out.append("Nenhum problema encontrado pelas verificações automáticas.")
    if r["secoes"]:
        out += ["", "## Citabilidade por seção", "", "| Seção | Palavras | Nota | O que melhorar |", "|---|---|---|---|"]
        for sec in r["secoes"]:
            out.append(f"| {'H' + str(sec['nivel'])} {sec['heading'][:70]} | {sec['palavras']} | {sec['nota']} | "
                       f"{'; '.join(sec['sugestoes']) or 'ok'} |")
    out += ["", "_Notas heurísticas para priorizar revisão humana; não são métricas do Google nem das IAs._"]
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("alvo", help="URL ou arquivo HTML")
    ap.add_argument("--base-url", help="URL pública quando o alvo é arquivo local")
    ap.add_argument("--palavra", help="palavra-chave principal da página (opcional)")
    ap.add_argument("--user-agent", default=DEFAULT_UA)
    ap.add_argument("--format", choices=["md", "json"], default="md")
    args = ap.parse_args()
    try:
        f = fetch(args.alvo, user_agent=args.user_agent)
    except OSError as err:
        print(f"erro: não foi possível ler {args.alvo}: {err}", file=sys.stderr)
        sys.exit(2)
    if f.status is not None and f.status >= 400:
        print(f"erro: {args.alvo} respondeu {f.status}", file=sys.stderr)
        sys.exit(2)
    r = analyze(f.text(), f.final_url or args.base_url, args.palavra)
    print(json.dumps(r, ensure_ascii=False, indent=2) if args.format == "json" else to_md(r))
    sys.exit(1 if r["erros"] else 0)


if __name__ == "__main__":
    main()
