#!/usr/bin/env python3
"""Valida dados estruturados JSON-LD (pilar 6) em páginas HTML, URLs ou arquivos .json.

Verifica, para cada nó com @type (inclusive dentro de @graph):
  - JSON válido, @context do schema.org;
  - propriedades obrigatórias e recomendadas dos tipos com resultado enriquecido no Google
    (Article, BreadcrumbList, Product/Offer, LocalBusiness, Organization, Event, JobPosting,
    VideoObject, Recipe, Review/AggregateRating, SoftwareApplication, QAPage, Service, Person...);
  - datas em ISO 8601 e dateModified não anterior a datePublished;
  - URLs absolutas em url, image, logo, item, sameAs, @id...;
  - preço numérico e moeda ISO 4217 em Offer;
  - @id repetido com tipos diferentes (grafo contraditório);
  - avaliações do próprio negócio em LocalBusiness/Organization (o Google não exibe);
  - tipos e recursos que o Google deixou de exibir (FAQ desde 07/05/2026, HowTo, SearchAction
    da caixa de busca de sitelinks, e os tipos descontinuados em jun/2025);
  - texto de modelo não substituído;
  - quando o alvo é HTML: se name/headline/telefone do JSON-LD aparecem no texto visível.

Não substitui o Rich Results Test (que também confere elegibilidade e políticas), mas pega os
erros comuns antes da publicação e roda em lote, sem rede, em arquivos locais.

Uso:
  python3 lint_schema.py https://dominio.com/servicos/limpeza/
  python3 lint_schema.py pagina.html templates/jsonld/service.json
  python3 lint_schema.py https://dominio.com/ --format json

Saída: 0 sem erros, 1 com erros, 2 falha de uso ou de rede.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _seo_common import fetch, find_placeholders, html_to_text, is_url, normalize  # noqa: E402
from audit_page import PageParser  # noqa: E402

ARTICLE = {"Article", "NewsArticle", "BlogPosting", "TechArticle", "Report", "ScholarlyArticle"}
ORG = {"Organization", "Corporation", "NGO", "EducationalOrganization", "GovernmentOrganization",
       "MedicalOrganization", "OnlineBusiness", "OnlineStore", "NewsMediaOrganization", "SportsOrganization"}
LOCAL = {"LocalBusiness", "Dentist", "Physician", "MedicalClinic", "MedicalBusiness", "BeautySalon", "HairSalon",
         "DaySpa", "HealthAndBeautyBusiness", "NailSalon", "TattooParlor", "LegalService", "Attorney", "Notary",
         "Restaurant", "FoodEstablishment", "CafeOrCoffeeShop", "Bakery", "BarOrPub", "FastFoodRestaurant", "Store",
         "AutoRepair", "AutomotiveBusiness", "AutoDealer", "HomeAndConstructionBusiness", "Plumber", "Electrician",
         "HVACBusiness", "RoofingContractor", "GeneralContractor", "HousePainter", "Locksmith", "MovingCompany",
         "RealEstateAgent", "ProfessionalService", "AccountingService", "FinancialService", "InsuranceAgency",
         "VeterinaryCare", "ChildCare", "Hotel", "LodgingBusiness", "ExerciseGym", "SportsActivityLocation",
         "Optician", "Pharmacy", "TravelAgency", "EmploymentAgency", "EntertainmentBusiness", "EducationalOrganization"}

# (obrigatórias, recomendadas). "a|b" = uma das duas basta.
RULES: Dict[str, tuple] = {
    "Article": ([], ["headline", "author", "datePublished", "dateModified", "image"]),
    "BreadcrumbList": (["itemListElement"], []),
    "ListItem": (["position"], ["name|item"]),
    "Product": (["name", "offers|review|aggregateRating"], ["image", "description", "brand", "sku|gtin|gtin13|mpn"]),
    "Offer": (["price|priceSpecification"], ["priceCurrency"]),
    "AggregateOffer": (["lowPrice"], ["priceCurrency", "highPrice", "offerCount"]),
    "LocalBusiness": (["name", "address"], ["telephone", "url", "image", "geo", "openingHoursSpecification|openingHours", "priceRange"]),
    "Organization": ([], ["name", "url", "logo", "sameAs"]),
    "PostalAddress": ([], ["streetAddress", "addressLocality", "addressRegion", "postalCode", "addressCountry"]),
    "Event": (["name", "startDate", "location"], ["eventStatus", "eventAttendanceMode", "image", "description", "offers", "organizer"]),
    "JobPosting": (["title", "description", "datePosted", "hiringOrganization"], ["validThrough", "employmentType", "baseSalary", "identifier"]),
    "VideoObject": (["name", "thumbnailUrl", "uploadDate"], ["description", "duration", "contentUrl|embedUrl"]),
    "Recipe": (["name", "image"], ["author", "recipeIngredient", "recipeInstructions", "totalTime"]),
    "Review": (["itemReviewed|@parent", "author", "reviewRating"], ["datePublished"]),
    "AggregateRating": (["ratingValue", "ratingCount|reviewCount"], []),
    "SoftwareApplication": (["name", "offers|aggregateRating|review"], ["operatingSystem", "applicationCategory"]),
    "QAPage": (["mainEntity"], []),
    "Question": (["name"], ["acceptedAnswer|suggestedAnswer"]),
    "Answer": (["text"], []),
    "Person": (["name"], ["url", "sameAs"]),
    "WebSite": (["name", "url"], []),
    "Service": (["name"], ["provider", "areaServed", "description"]),
    "ImageObject": (["contentUrl|url"], []),
}
RETIRED = {
    "FAQPage": "O Google não exibe mais resultado enriquecido de FAQ para nenhum site desde 07/05/2026. A marcação "
               "pode ficar (ajuda a descrever a página), mas não espere destaque.",
    "HowTo": "Resultado enriquecido de HowTo foi removido pelo Google em 2023.",
    "Course": "Course Info deixou de ser exibido pelo Google em jun/2025.",
    "ClaimReview": "ClaimReview deixou de ser exibido pelo Google em jun/2025.",
    "SpecialAnnouncement": "SpecialAnnouncement deixou de ser exibido pelo Google em jun/2025.",
    "EstimatedSalary": "Estimated Salary deixou de ser exibido pelo Google em jun/2025.",
    "OccupationalExperienceRequirements": "Estimated Salary deixou de ser exibido pelo Google em jun/2025.",
    "Vehicle": "Vehicle Listing deixou de ser exibido pelo Google em jun/2025.",
    "Car": "Vehicle Listing deixou de ser exibido pelo Google em jun/2025.",
    "Book": "Book Actions deixou de ser exibido pelo Google em jun/2025.",
}
DATE_KEYS = {"datePublished", "dateModified", "dateCreated", "uploadDate", "startDate", "endDate", "datePosted",
             "validThrough", "validFrom", "priceValidUntil", "foundingDate", "birthDate"}
URL_KEYS = {"url", "image", "logo", "item", "sameAs", "thumbnailUrl", "contentUrl", "embedUrl", "@id", "mainEntityOfPage"}
ISO_DATE = re.compile(r"^\d{4}(-\d{2})?(-\d{2}([T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?)?)?$")
ISO_DURATION = re.compile(r"^P(?!$)(\d+Y)?(\d+M)?(\d+W)?(\d+D)?(T(?=\d)(\d+H)?(\d+M)?(\d+(\.\d+)?S)?)?$")
CURRENCY = re.compile(r"^[A-Z]{3}$")


def types_of(node: Dict[str, Any]) -> List[str]:
    t = node.get("@type")
    if isinstance(t, str):
        return [t]
    if isinstance(t, list):
        return [str(x) for x in t]
    return []


def family(t: str) -> Optional[str]:
    if t in ARTICLE:
        return "Article"
    if t in LOCAL or t.endswith("Store"):
        return "LocalBusiness"
    if t in ORG:
        return "Organization"
    return t if t in RULES else None


def present(node: Dict[str, Any], spec: str, parent_key: Optional[str]) -> bool:
    for k in spec.split("|"):
        if k == "@parent" and parent_key in ("review",):
            return True
        v = node.get(k)
        if v not in (None, "", [], {}):
            return True
    return False


def walk(node: Any, out: List[tuple], parent_key: Optional[str] = None, path: str = "$") -> None:
    if isinstance(node, dict):
        if "@type" in node:
            out.append((node, parent_key, path))
        for k, v in node.items():
            walk(v, out, k, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            walk(v, out, parent_key, f"{path}[{i}]")


def lint_block(data: Any, label: str, visible: Optional[str], add) -> List[str]:
    nodes: List[tuple] = []
    found_types: List[str] = []
    roots = data if isinstance(data, list) else [data]
    for root in roots:
        if not isinstance(root, dict):
            add("ERRO", label, "Bloco JSON-LD não é um objeto.")
            continue
        ctx = root.get("@context")
        ctx_s = json.dumps(ctx) if ctx is not None else ""
        if "schema.org" not in ctx_s:
            add("ERRO", label, "Sem @context do schema.org (\"@context\": \"https://schema.org\").")
        elif "http://schema.org" in ctx_s:
            add("INFO", label, "@context com http://; prefira https://schema.org.")
        walk(root, nodes)
    ids: Dict[str, set] = defaultdict(set)
    for node, parent_key, path in nodes:
        tps = types_of(node)
        found_types += tps
        where = f"{label} {path} ({'/'.join(tps)})"
        only_ref = set(node.keys()) <= {"@type", "@id"}
        if node.get("@id") and not only_ref:
            ids[str(node["@id"])].update(tps)
        for t in tps:
            if t in RETIRED:
                add("INFO", where, RETIRED[t])
            fam = family(t)
            if fam is None:
                continue
            if t == "LocalBusiness":
                add("INFO", where, "Use o subtipo mais específico de LocalBusiness (Dentist, BeautySalon, LegalService...).")
            if only_ref:
                continue
            required, recommended = RULES[fam]
            for spec in required:
                if not present(node, spec, parent_key):
                    add("ERRO", where, f"Falta propriedade obrigatória: {spec.replace('|', ' ou ')}.")
            for spec in recommended:
                if not present(node, spec, parent_key):
                    add("AVISO", where, f"Falta propriedade recomendada: {spec.replace('|', ' ou ')}.")
            if fam in ("LocalBusiness", "Organization") and (node.get("aggregateRating") or node.get("review")):
                add("AVISO", where, "Avaliações do próprio negócio em LocalBusiness/Organization: o Google não exibe "
                                    "(self-serving). Remova ou mova para Product/Service com avaliações reais e visíveis.")
            if fam == "JobPosting" and not (node.get("jobLocation") or node.get("jobLocationType") == "TELECOMMUTE"):
                add("ERRO", where, "JobPosting sem jobLocation (ou jobLocationType TELECOMMUTE + applicantLocationRequirements).")
            if fam == "Product":
                offers = node.get("offers")
                for o in (offers if isinstance(offers, list) else [offers] if isinstance(offers, dict) else []):
                    if isinstance(o, dict) and not o.get("availability"):
                        add("AVISO", where, "Offer do Product sem availability (https://schema.org/InStock, OutOfStock...).")
                        break
            if fam == "WebSite":
                pa = node.get("potentialAction")
                if pa and "SearchAction" in json.dumps(pa):
                    add("INFO", where, "SearchAction (caixa de busca de sitelinks) não é mais exibida pelo Google desde nov/2024; pode remover.")
            if fam == "Offer" or fam == "AggregateOffer":
                for pk in ("price", "lowPrice", "highPrice"):
                    pv = node.get(pk)
                    if pv is not None and not re.fullmatch(r"\d+(\.\d+)?", str(pv).strip()):
                        add("ERRO", where, f"{pk} \"{pv}\" não é número (use ponto decimal, sem símbolo: \"149.90\").")
                cur = node.get("priceCurrency")
                if cur and not CURRENCY.match(str(cur)):
                    add("ERRO", where, f"priceCurrency \"{cur}\" fora do ISO 4217 (ex.: BRL, USD).")
                av = node.get("availability")
                if av and "schema.org/" not in str(av):
                    add("AVISO", where, f"availability \"{av}\": use a URL do enum (https://schema.org/InStock).")
            if fam == "AggregateRating":
                try:
                    if float(node.get("ratingValue", 0)) > float(node.get("bestRating", 5)):
                        add("ERRO", where, "ratingValue maior que bestRating.")
                except (TypeError, ValueError):
                    add("ERRO", where, "ratingValue/bestRating não numéricos.")
            if fam == "BreadcrumbList":
                items = node.get("itemListElement") or []
                pos = [i.get("position") for i in items if isinstance(i, dict)]
                if pos and [str(p) for p in pos] != [str(i) for i in range(1, len(pos) + 1)]:
                    add("AVISO", where, f"position da BreadcrumbList fora de sequência: {pos}.")
            if visible is not None:
                for key in ("headline", "name"):
                    val = node.get(key)
                    if key == "name" and fam not in ("Article", "Product", "LocalBusiness", "Event", "Service",
                                                     "JobPosting", "Recipe", "SoftwareApplication", "VideoObject"):
                        continue
                    if isinstance(val, str) and len(val) > 3 and normalize(val) not in visible:
                        add("AVISO", where, f"{key} \"{val[:60]}\" não aparece no texto visível (marcação deve descrever o que está na página).")
                        break
                tel = node.get("telephone")
                if isinstance(tel, str):
                    digits = re.sub(r"\D", "", tel)[-8:]
                    if digits and digits not in re.sub(r"\D", "", visible):
                        add("AVISO", where, f"telephone {tel} não aparece no texto visível.")
        # campos de qualquer nó
        dp, dm = node.get("datePublished"), node.get("dateModified")
        for k in DATE_KEYS & set(node.keys()):
            v = node.get(k)
            if isinstance(v, str) and not ISO_DATE.match(v.strip()):
                add("ERRO", where, f"{k} \"{v}\" fora do ISO 8601 (AAAA-MM-DD ou AAAA-MM-DDThh:mm:ss-03:00).")
        if isinstance(dp, str) and isinstance(dm, str) and ISO_DATE.match(dp) and ISO_DATE.match(dm) and dm[:10] < dp[:10]:
            add("ERRO", where, "dateModified anterior a datePublished.")
        for k in ("duration", "totalTime", "cookTime", "prepTime"):
            v = node.get(k)
            if isinstance(v, str) and not ISO_DURATION.match(v):
                add("ERRO", where, f"{k} \"{v}\" fora do formato ISO 8601 de duração (ex.: PT1H30M).")
        for k in URL_KEYS & set(node.keys()):
            vals = node[k] if isinstance(node[k], list) else [node[k]]
            for v in vals:
                if isinstance(v, str) and v and not is_url(v) and not (k == "@id" and v.startswith("#")):
                    add("AVISO", where, f"{k} com URL relativa ou inválida: \"{v[:80]}\" (use URL absoluta).")
                    break
        for k, v in node.items():
            if v == "" or v == []:
                add("AVISO", where, f"{k} vazio.")
    for ref, tps in ids.items():
        fams = {family(t) or t for t in tps}
        if len(fams) > 1:
            add("AVISO", label, f"@id {ref} definido com tipos diferentes ({', '.join(sorted(tps))}): confira se é a mesma entidade.")
    return found_types


def lint_source(source: str) -> Dict[str, Any]:
    findings: List[Dict[str, str]] = []

    def add(level: str, where: str, msg: str) -> None:
        findings.append({"nivel": level, "onde": where, "mensagem": msg})

    f = fetch(source)
    if f.status is not None and f.status >= 400:
        add("ERRO", source, f"Status HTTP {f.status}.")
        return {"alvo": source, "blocos": 0, "tipos": [], "achados": findings, "erros": 1}
    text = f.text()
    blocks: List[str]
    visible: Optional[str] = None
    if source.lower().endswith(".json") or text.lstrip().startswith(("{", "[")):
        blocks = [text]
    else:
        p = PageParser()
        p.feed(text)
        p.close()
        blocks = p.jsonld_raw
        visible = normalize(html_to_text(text))
        if not blocks:
            add("AVISO", source, "Nenhum bloco JSON-LD no HTML do servidor (marcação injetada só por JavaScript pode não ser lida por todos).")
    types: List[str] = []
    for i, raw in enumerate(blocks, 1):
        label = f"bloco {i}"
        ph = find_placeholders(raw)
        if ph:
            add("ERRO", label, f"Texto de modelo não substituído: {', '.join(sorted(set(ph)))}.")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as err:
            add("ERRO", label, f"JSON inválido: {err.msg} (linha {err.lineno}, coluna {err.colno}).")
            continue
        types += lint_block(data, label, visible, add)
    order = {"ERRO": 0, "AVISO": 1, "INFO": 2}
    findings.sort(key=lambda x: order[x["nivel"]])
    return {"alvo": source, "blocos": len(blocks), "tipos": sorted(set(types)), "achados": findings,
            "erros": sum(1 for x in findings if x["nivel"] == "ERRO")}


def to_md(results: List[Dict[str, Any]]) -> str:
    out = ["# Dados estruturados (JSON-LD)", ""]
    for r in results:
        out += [f"## {r['alvo']}", "", f"Blocos: {r['blocos']} · Tipos: {', '.join(r['tipos']) or '(nenhum)'}", ""]
        if not r["achados"]:
            out += ["Nenhum problema encontrado.", ""]
            continue
        out += ["| Nível | Onde | Achado |", "|---|---|---|"]
        out += [f"| {f['nivel']} | {f['onde']} | {f['mensagem']} |" for f in r["achados"]]
        out.append("")
    out.append("_Confirme a elegibilidade no Rich Results Test antes de publicar; este lint não conhece as políticas de cada recurso._")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("alvos", nargs="+", help="URLs, arquivos HTML ou arquivos .json")
    ap.add_argument("--format", choices=["md", "json"], default="md")
    args = ap.parse_args()
    results = []
    for a in args.alvos:
        try:
            results.append(lint_source(a))
        except OSError as err:
            print(f"erro: não foi possível ler {a}: {err}", file=sys.stderr)
            sys.exit(2)
    print(json.dumps(results, ensure_ascii=False, indent=2) if args.format == "json" else to_md(results))
    sys.exit(1 if any(r["erros"] for r in results) else 0)


if __name__ == "__main__":
    main()
