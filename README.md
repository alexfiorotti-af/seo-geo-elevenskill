# seo-geo-elevenskill

Skill open source (formato Agent Skills: `SKILL.md` + referências + scripts) que ensina uma IA a
**planejar, implementar e auditar SEO e GEO** em sites, sempre **do back-end para o front-end**,
em 11 pilares.

> **EN:** An open-source Agent Skill for technical SEO and GEO (Generative Engine Optimization:
> visibility in Google AI Overviews/AI Mode, ChatGPT, Gemini, Claude, Perplexity and Copilot).
> Back-end first (crawling, indexing, rendering, performance, structured data), then front-end
> (responsive/semantic HTML, metadata, keyword architecture, citable content), off-page authority
> (earned links and brand mentions, with a Google-policy traffic light), plus measurement.
> Docs are in Brazilian Portuguese; scripts are dependency-free Python.

## Link building dentro das diretrizes

A referência `10-autoridade-links-mencoes.md` classifica as táticas de backlinks em **verde**
(conquistar por mérito), **amarelo** (depende da execução) e **vermelho** (link spam pela política
do Google: compra, redes de troca de links, automação, PBN, publieditorial pago). A skill nunca
recomenda táticas vermelhas, e trata menções de marca como prioridade para GEO.

## Por que back-end primeiro

Buscadores e motores de resposta seguem a mesma linha de produção:
**descobrir → rastrear → renderizar → indexar → recuperar → ranquear → apresentar**.
Se a página não é rastreável, não chega no HTML do servidor ou não é indexável, nenhum título
bonito ou texto otimizado faz diferença. Por isso os pilares 1 a 6 vêm antes dos 7 a 10.

## Os 11 pilares

| # | Camada | Pilar |
|---|---|---|
| 1 | Back-end | Arquitetura de URLs e de informação |
| 2 | Back-end | Rastreabilidade: robots.txt, sitemaps, IndexNow, crawlers de IA |
| 3 | Back-end | Indexação: status HTTP, redirects, canonical, noindex, hreflang |
| 4 | Back-end | Renderização: conteúdo no HTML do servidor (crawlers de IA não executam JS) |
| 5 | Back-end | Performance e Core Web Vitals |
| 6 | Back-end | Dados estruturados (JSON-LD) e grafo de entidade |
| 7 | Front-end | Responsividade, HTML semântico, acessibilidade, site amigável a agentes |
| 8 | Front-end | Metodologia de títulos, descrições e metatags |
| 9 | Front-end | Palavras-chave, intenção e arquitetura de conteúdo |
| 10 | Front-end + fora do site | GEO e autoridade: conteúdo citável e entidade (10a); links e menções conquistados (10b) |
| 11 | Transversal | Medição, governança, políticas de spam, migração |

## Estrutura

```
SKILL.md                     instruções principais (modos de trabalho, regras, ferramentas)
references/                  um arquivo por grupo de pilares, carregado sob demanda
  00-fontes.md               fontes oficiais e linha do tempo de atualizações (nov/2026)
  01-players-e-tecnologias.md
  02-backend-rastreio-indexacao.md
  03-backend-performance-dados-estruturados.md
  04-frontend-responsivo-semantico.md
  05-metadados-titulos-descricoes.md
  06-palavras-chave-conteudo.md
  07-geo-motores-de-resposta.md
  08-medicao-governanca.md
  09-stacks.md               Next.js, Astro, HTML estático na Vercel, WordPress
  10-autoridade-links-mencoes.md  semáforo de táticas de links, roteiros BR/EUA/SaaS/e-commerce, auditoria de backlinks
  11-seo-local.md            perfis (Google, Apple, Bing), NAP, citações, avaliações, páginas por unidade
  12-internacional-hreflang.md   estrutura por idioma/país, hreflang recíproco, tradução, GEO multilíngue
  13-ecommerce.md            filtros, paginação, ciclo de vida do produto, Product/Offer, feed, compra por agentes
data/atualizacoes-google.json    atualizações do Google (core, spam, políticas, recursos, rastreio) com fonte oficial
templates/                   robots.txt, llms.txt, <head>, JSON-LD, mapa de palavras-chave, brief, relatório,
                             modelos de abordagem (PT/EN), prospecção de links, citações locais,
                             amostragem de IA, marca do relatório (exemplo)
scripts/                     20 ferramentas de auditoria e validação (Python 3.9+, só biblioteca padrão)
tests/                       testes com servidor HTTP local e fixtures fictícios
```

## Ferramentas

```bash
python3 scripts/audit_page.py https://seusite.com.br/pagina/          # auditoria de página (HTML sem JS)
python3 scripts/check_robots.py https://seusite.com.br --path /servicos/  # o que cada robô de busca/IA pode acessar
python3 scripts/validate_sitemap.py https://seusite.com.br/sitemap.xml    # validação de sitemap
python3 scripts/crawl_site.py https://seusite.com.br                       # rastreio: links quebrados, órfãs, sitemap
python3 scripts/verify_backlinks.py destinos paginas-mais-linkadas.csv     # páginas com backlinks fora do ar
python3 scripts/verify_backlinks.py origens links.csv --dominio seusite.com.br  # links perdidos, rel, âncoras
python3 scripts/lint_meta.py mapa.csv                                      # titles e descriptions em lote
INDEXNOW_KEY=... python3 scripts/indexnow_submit.py --host seusite.com.br urls.txt

# servidor, robôs e IA
python3 scripts/check_server.py https://seusite.com.br                    # https, www, soft 404, 2 MB, compressão, segurança
python3 scripts/check_agents.py https://seusite.com.br/                   # o que navegador × robôs de IA recebem (WAF, cloaking)
python3 scripts/llms_txt.py gerar https://seusite.com.br > llms.txt        # rascunho do llms.txt a partir do sitemap
python3 scripts/llms_txt.py validar https://seusite.com.br --verificar-links

# dados estruturados, conteúdo e local
python3 scripts/lint_schema.py https://seusite.com.br/servicos/x/         # JSON-LD: obrigatórios, datas, preço, tipos aposentados
python3 scripts/analyze_content.py https://seusite.com.br/blog/x/ --palavra "termo"  # citabilidade e legibilidade pt-BR
python3 scripts/check_local.py https://seusite.com.br/ --citacoes citacoes.csv       # consistência de NAP
python3 scripts/pagespeed.py https://seusite.com.br/                      # Core Web Vitals de campo e laboratório

# dados do Search Console, palavras-chave e IA (offline, a partir de CSV)
python3 scripts/gsc_opportunities.py Consultas.csv --marca "suamarca"     # quase lá, CTR baixo, canibalização
python3 scripts/cluster_serp.py serps.csv --mapa mapa.csv                  # agrupar palavras por intenção (SERP)
python3 scripts/ai_visibility.py amostragem.csv                            # taxa de citação da marca nas IAs
python3 scripts/google_updates.py cruzar datas.csv                         # quedas × atualizações do Google

# monitoramento e relatório
python3 scripts/drift.py foto --sitemap https://seusite.com.br/sitemap.xml --saida relatorios/antes.json
python3 scripts/drift.py comparar relatorios/antes.json                    # o que mudou desde a foto
python3 scripts/report.py relatorios/*.json --site https://seusite.com.br --saida relatorios/relatorio.html

python3 -m unittest discover -s tests                                      # testes
```

## Instalação

- **Claude Code:** copie (ou clone) esta pasta para `~/.claude/skills/seo-geo-elevenskill/`
  (todas as sessões) ou `.claude/skills/seo-geo-elevenskill/` dentro de um projeto.
- **Claude (app):** compacte a pasta em `.zip` e adicione como skill personalizada nas
  configurações de skills da sua conta.
- **Outras IAs e agentes:** o `SKILL.md` é Markdown puro; use-o como instrução de sistema e
  disponibilize a pasta `references/` para consulta.

## Privacidade e segurança

Este repositório é público e foi escrito para não conter nada sensível:
- Nenhum dado de cliente, credencial, chave de API, ID de analytics, pixel ou contato pessoal.
- Exemplos usam domínios reservados para teste (`.test`) e uma marca fictícia ("Clínica Aurora").
- Scripts leem chaves só de variáveis de ambiente (`INDEXNOW_KEY`) e mascaram a chave na saída.
- O `.gitignore` bloqueia `.env`, `metodologia-local/`, `clientes/`, `prospeccao/` e arquivos `*.local.*`.
- Listas de prospecção de links com contatos reais são dados pessoais: ficam nessas pastas, nunca no repositório.

### Camada privada (sua metodologia, fora do Git)
Crie `metodologia-local/README.md` ao lado do `SKILL.md` com seus padrões próprios (nichos,
modelos de proposta, checklists internos, dados de clientes). A skill lê essa pasta primeiro
quando ela existe, e o Git nunca a envia para o repositório público.

## Atualização

Busca muda rápido. As afirmações sobre o Google e as IAs estão datadas em
`references/00-fontes.md` (estado de novembro de 2026). Ao atualizar, cite a fonte primária e
a data, e rode os testes.

## Referências e inspiração

A cobertura de servidor, robôs de IA, citabilidade, schema, SEO local, hreflang, monitoramento e
relatórios foi ampliada depois de comparar esta skill com dois projetos abertos (MIT) que valem a
visita: [claude-seo](https://github.com/AgriciDaniel/claude-seo) e
[geo-seo-claude](https://github.com/zubair-trabzada/geo-seo-claude). Nenhum código foi copiado:
as ferramentas daqui seguem o padrão desta skill (sem dependências, sem chamadas a serviços pagos,
documentação em pt-BR e fontes oficiais datadas).

## Contribuindo

Issues e pull requests são bem-vindos. Regras: fonte primária para qualquer afirmação sobre
como um buscador funciona; nenhum dado real de cliente nos exemplos; scripts sem dependências
externas e com teste.

## Licença

MIT. Veja `LICENSE`.
