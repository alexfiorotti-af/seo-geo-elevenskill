---
name: seo-geo-elevenskill
description: Planeja, implementa e audita SEO e GEO (otimização para buscadores e para motores de resposta com IA como AI Overviews, AI Mode, ChatGPT, Perplexity, Claude e Copilot) em sites, sempre do back-end para o front-end. Usar ao criar ou revisar um site, página, robots.txt, sitemap, llms.txt, dados estruturados, títulos, meta descriptions, metatags, mapa de palavras-chave, arquitetura de conteúdo, citabilidade, Core Web Vitals, visibilidade em IA, backlinks, link building, menções de marca, SEO local e NAP, hreflang e sites multilíngues, SEO de e-commerce, relatório de SEO para cliente, monitoramento após deploy ou ao diagnosticar queda de tráfego orgânico. Also triggers on "SEO audit", "technical SEO", "GEO", "AEO", "AI search visibility", "schema markup", "meta tags", "backlinks", "link building", "site crawl", "local SEO", "hreflang", "ecommerce SEO", "SEO report".
license: MIT
---

# SEO + GEO em 11 pilares (back-end → front-end)

Esta skill transforma um pedido de SEO/GEO em entregáveis concretos (arquivos, código, relatório
priorizado) seguindo uma ordem fixa: **primeiro o que o robô precisa para encontrar, ler e confiar
na página (back-end); depois o que a pessoa e o motor de resposta veem (front-end)**.

A premissa central, confirmada pelo próprio Google em 2026: otimizar para busca com IA continua
sendo SEO. AI Overviews e AI Mode usam o mesmo índice e os mesmos sinais de ranqueamento; ChatGPT,
Perplexity, Claude e Copilot usam índices próprios ou de parceiros, mas premiam as mesmas coisas:
página rastreável, rápida, com conteúdo original, bem estruturado, de uma entidade confiável e
referenciada por outras fontes (links e menções conquistados, nunca fabricados).
Não existe atalho "só para IA" que compense um site tecnicamente fraco.

## Os 11 pilares

| # | Camada | Pilar | Referência |
|---|---|---|---|
| 1 | Back-end | Arquitetura de URLs e de informação | `references/02-backend-rastreio-indexacao.md` |
| 2 | Back-end | Rastreabilidade: robots.txt, sitemaps, IndexNow, crawlers de IA | `references/02-backend-rastreio-indexacao.md` |
| 3 | Back-end | Indexação: status HTTP, redirects, canonical, noindex, hreflang | `references/02-backend-rastreio-indexacao.md` |
| 4 | Back-end | Renderização: HTML entregue pelo servidor, JS e crawlers que não executam JS | `references/02-backend-rastreio-indexacao.md` |
| 5 | Back-end | Performance e servidor: TTFB, cache, CDN, Core Web Vitals | `references/03-backend-performance-dados-estruturados.md` |
| 6 | Back-end | Dados estruturados (JSON-LD) e grafo de entidade | `references/03-backend-performance-dados-estruturados.md` |
| 7 | Front-end | Responsividade, HTML semântico, acessibilidade e site "amigável a agentes" | `references/04-frontend-responsivo-semantico.md` |
| 8 | Front-end | Metadados: title, meta description, robots, Open Graph | `references/05-metadados-titulos-descricoes.md` |
| 9 | Front-end | Palavras-chave, intenção e arquitetura de conteúdo (páginas que movimentam o site) | `references/06-palavras-chave-conteudo.md` |
| 10 | Front-end + fora do site | GEO e autoridade: conteúdo citável, entidade e autoria (10a); links e menções conquistados (10b) | `references/07-geo-motores-de-resposta.md` e `references/10-autoridade-links-mencoes.md` |
| 11 | Transversal | Medição, governança e políticas de spam | `references/08-medicao-governanca.md` |

Especialidades (leia quando o site for desse tipo):
- Negócio local (endereço ou área de atendimento): `references/11-seo-local.md`.
- Vários idiomas ou países: `references/12-internacional-hreflang.md`.
- Loja virtual: `references/13-ecommerce.md`.

Contexto de mercado e de como cada buscador funciona: `references/01-players-e-tecnologias.md`.
Implementação por stack (Next.js, Astro, HTML estático, WordPress): `references/09-stacks.md`.
Fontes com data de consulta: `references/00-fontes.md`.

Leia **só a referência do pilar em que está trabalhando**. Não carregue tudo de uma vez.

**Camada privada:** se existir a pasta `metodologia-local/` ao lado deste arquivo (ela é ignorada
pelo Git e não vai para o repositório público), leia o `README.md` dela antes de começar. O que
estiver lá (padrões da agência, nichos, modelos de cliente) tem precedência sobre as referências
públicas, exceto sobre as "Regras que nunca quebram".

## Escolha o modo de trabalho

Identifique o modo pelo pedido. Se houver dúvida, assuma o mais completo que caiba no pedido e
diga qual assumiu na primeira linha da resposta.

### Modo A: site novo (construção)
1. Levante o mínimo de contexto (ver "Briefing" abaixo).
2. Percorra os pilares **na ordem 1 → 11**. Para cada um, produza o artefato, não só a recomendação:
   árvore de URLs, `robots.txt`, `sitemap.xml` (ou o gerador da stack), regras de redirect/canonical,
   configuração de renderização, orçamento de performance, grafo JSON-LD, `<head>` base,
   mapa de palavras-chave, briefs de conteúdo, plano de medição.
3. Use os modelos de `templates/` como ponto de partida e adapte. Nunca deixe placeholder
   (`example.com`, `SEU-DOMINIO`) no entregável final.
4. Rode os scripts de validação (seção "Ferramentas") sobre o que gerou.

### Modo B: auditoria de site existente
1. Servidor e acesso: `scripts/check_server.py` (https, host, soft 404, compressão, cabeçalhos),
   `scripts/check_robots.py` (o que cada robô pode acessar, Content-Signal, Crawl-delay) e
   `scripts/check_agents.py` (WAF/CDN bloqueando ou servindo outro conteúdo a robôs de IA).
2. Site inteiro: `scripts/crawl_site.py` na home (links quebrados, redirects internos, órfãs,
   sitemap inconsistente, profundidade, titles repetidos, hreflang) e `scripts/validate_sitemap.py`.
3. Páginas-chave (home, uma de serviço/produto, uma de conteúdo, uma local): `scripts/audit_page.py`,
   `scripts/lint_schema.py` e, nas de conteúdo, `scripts/analyze_content.py` (citabilidade,
   legibilidade, autor, datas). Negócio local: `scripts/check_local.py` (NAP). Dados de campo:
   `scripts/pagespeed.py`.
4. Com acesso ao Search Console: `scripts/gsc_opportunities.py` na exportação de Desempenho e
   `scripts/verify_backlinks.py destinos`/`origens` na exportação de Links.
5. Revise os pilares 1 → 11 contra a checklist de cada referência (e a especialidade, se houver).
6. Entregue com `templates/relatorio-auditoria.md` ou gere o relatório consolidado (modo H):
   achados ordenados por **impacto × esforço**, cada um com evidência (URL, trecho, saída do
   script) e correção exata. Bloqueios de indexação e rastreio vêm sempre antes de qualquer
   ajuste de front-end.

### Modo C: página ou conteúdo novo
1. Defina a intenção e a palavra-chave principal (pilar 9). Confira se outra URL já atende
   essa intenção; se sim, melhore a existente em vez de criar outra (evita canibalização).
2. Gere o brief com `templates/brief-de-conteudo.md`.
3. Escreva title, meta description, H1 e slug pela metodologia do pilar 8.
4. Aplique a estrutura citável do pilar 10 e o JSON-LD do tipo certo (pilar 6).
5. Liste os links internos de entrada e de saída (pilar 9) e, ao publicar, atualize sitemap e IndexNow.

### Modo D: metadados em lote
Monte (ou receba) um CSV no formato de `templates/mapa-de-palavras-chave.csv`, preencha title e
description pela metodologia do pilar 8 e rode `scripts/lint_meta.py` até zerar os erros.

### Modo E: diagnóstico de queda de tráfego
Siga a árvore de decisão de `references/08-medicao-governanca.md` (seção "Queda de tráfego"):
primeiro descarte problema técnico e de medição (`drift.py comparar` se houver foto anterior),
depois cruze com as atualizações do Google (`scripts/google_updates.py cruzar` com a aba "Datas"
do Search Console), só então trate conteúdo.

### Modo F: plano de autoridade (links e menções)
1. Leia `references/10-autoridade-links-mencoes.md`.
2. Diagnóstico: exportações de Links do Search Console + `scripts/verify_backlinks.py` (destinos e
   origens); compare com concorrentes se houver ferramenta paga.
3. Recupere primeiro o que já é seu (páginas linkadas com 404, links perdidos, menções sem link).
4. Monte o plano de 90 dias com o roteiro do tipo de negócio (local BR, local EUA, SaaS,
   e-commerce), só com táticas verdes ou amarelas com os cuidados indicados.
5. Defina um ativo linkável (pilar 9) e use `templates/modelos-de-abordagem.md` e
   `templates/prospeccao-de-links.csv` (listas com contatos reais ficam fora do repositório).
6. Medição mensal pelo pilar 11.

### Modo G: monitoramento contínuo
1. Depois de cada auditoria aprovada, tire a foto das páginas-chave:
   `scripts/drift.py foto --sitemap ... --saida relatorios/<data>.json` (fora do Git).
2. A cada deploy ou semanalmente: `drift.py comparar` (noindex, canonical, title, JSON-LD, texto
   no HTML, redirects). ERRO = corrigir antes de qualquer outra tarefa.
3. Mensal: `gsc_opportunities.py`, amostragem de IA com `templates/amostragem-ia.csv` +
   `scripts/ai_visibility.py`, `crawl_site.py` e `google_updates.py listar --desde <último mês>`.

### Modo H: relatório para cliente
1. Rode os scripts do modo B com `--format json`, salvando em `relatorios/` (ignorada pelo Git).
2. `scripts/report.py relatorios/*.json --site ... --saida relatorios/relatorio.html
   --json-saida relatorios/<mês>.json` (com `--anterior` a partir do segundo mês, para mostrar
   evolução, achados resolvidos e novos).
3. A marca da agência vem de `metodologia-local/marca.json` (modelo em `templates/marca.exemplo.json`).
4. Acrescente o resumo executivo em linguagem simples (3 problemas que mais custam e o ganho
   esperado) e a lista do que depende do cliente. A nota por pilar é heurística: apresente como
   indicador de evolução, nunca como métrica do Google.

### Modo I: SEO local
Leia `references/11-seo-local.md`. Perfis (Google, Apple, Bing) → NAP idêntico (`check_local.py`
com a planilha `templates/citacoes-locais.csv`) → página por unidade com `LocalBusiness` →
avaliações sem incentivo → autoridade local (pilar 10b) → medição com UTM no perfil.

## Briefing mínimo

Pergunte apenas o que não der para descobrir sozinho (no código, no site ou na conversa):
- Domínio (ou "ainda não tem") e stack/hospedagem.
- Negócio, público e região de atuação (local, nacional, internacional; idiomas).
- 3 a 5 serviços/produtos principais e a ação de conversão (WhatsApp, formulário, compra).
- Concorrentes ou referências, se houver.
- Política para crawlers de IA: aparecer em buscas de IA? permitir treino de modelos?
  (o padrão recomendado é aparecer em busca e decidir treino caso a caso; ver pilar 2).

## Regras que nunca quebram

1. **Não invente dados.** Nada de estatística, depoimento, avaliação, prêmio, preço ou autoria
   fictícia, nem no texto nem no JSON-LD. Se faltar o dado, deixe marcado como pendência para o
   dono do site.
2. **Não crie páginas-porta.** Uma página por cidade, bairro ou variação de busca só se cada
   uma tiver conteúdo genuinamente diferente e útil. Páginas em massa quase iguais violam a
   política de conteúdo em escala do Google (scaled content abuse) e levam a rebaixamento.
3. **Marcação = conteúdo visível.** Todo dado estruturado descreve algo que a pessoa vê na página.
   Não marque avaliações do próprio negócio sobre si mesmo (LocalBusiness/Organization).
4. **Datas honestas.** Só altere `dateModified`/`lastmod` quando o conteúdo mudar de verdade.
5. **Sem truques para IA.** Nada de texto escondido para LLMs, instruções para robôs dentro da
   página, versões diferentes para crawlers (cloaking) ou menções de marca forjadas.
6. **Segredos fora do repositório.** Chaves (IndexNow, APIs de busca, analytics) vão em variável
   de ambiente; nunca no código, no `llms.txt` ou no relatório.
7. **Link se conquista, não se fabrica.** Nunca recomende comprar links, redes ou plataformas de
   troca de links (inclusive por créditos ou rotação), PBNs, automação de links ou âncora
   comercial em série. Link pago ou patrocinado publicado pelo site leva `rel="sponsored"`.
   Se o cliente já usa algo assim, avise do risco e proponha a alternativa verde.
8. **Recomendação com evidência.** Toda recomendação de auditoria aponta a URL e a prova.
   Toda afirmação sobre "como o Google/IA funciona" deve bater com `references/00-fontes.md`;
   se algo parecer desatualizado, pesquise antes de afirmar.

## Ferramentas (Python 3.9+, só biblioteca padrão)

| Script | Para quê | Exemplo |
|---|---|---|
| `scripts/audit_page.py` | Audita uma página (arquivo HTML ou URL): title, description, canonical, robots, H1/hierarquia, lang, viewport, Open Graph, JSON-LD, imagens sem alt, links | `python3 scripts/audit_page.py https://dominio.com/ --format md` |
| `scripts/check_robots.py` | Mostra o que cada robô (Google, Bing, OpenAI, Anthropic, Perplexity, Apple...) pode acessar e quais sitemaps estão declarados | `python3 scripts/check_robots.py https://dominio.com --path /blog/` |
| `scripts/validate_sitemap.py` | Valida sitemap ou índice de sitemaps: URLs absolutas, mesmo host, `lastmod` em ISO 8601, limites de 50 mil URLs/50 MB | `python3 scripts/validate_sitemap.py https://dominio.com/sitemap.xml` |
| `scripts/lint_meta.py` | Valida titles e descriptions em lote (CSV): tamanho em caracteres e largura estimada em pixels, duplicados, palavra-chave, marca | `python3 scripts/lint_meta.py mapa.csv` |
| `scripts/crawl_site.py` | Rastreia o site pelos links internos (sem JS, respeitando o robots.txt): links quebrados, links para redirects, órfãs, sitemap inconsistente, profundidade, titles repetidos | `python3 scripts/crawl_site.py https://dominio.com --max-paginas 500` |
| `scripts/verify_backlinks.py` | `origens`: confere se os backlinks ainda existem, com qual `rel` e âncora. `destinos`: confere se as páginas que recebem links respondem 200 | `python3 scripts/verify_backlinks.py destinos paginas-mais-linkadas.csv` |
| `scripts/indexnow_submit.py` | Envia URLs novas/alteradas ao IndexNow (Bing, Yandex, Naver, Seznam, Yep). Chave via `INDEXNOW_KEY` | `INDEXNOW_KEY=... python3 scripts/indexnow_submit.py --host dominio.com urls.txt` |
| `scripts/check_server.py` | Servidor: http→https, www, soft 404, tempo até o 1º byte, tamanho (2 MB), compressão, cache, X-Robots-Tag, robots/sitemap/llms.txt, cabeçalhos de segurança | `python3 scripts/check_server.py https://dominio.com` |
| `scripts/check_agents.py` | Compara o que navegador e cada robô (Googlebot, Bingbot, OAI-SearchBot, ClaudeBot, PerplexityBot...) recebem: bloqueio de WAF, desafio, conteúdo diferente | `python3 scripts/check_agents.py https://dominio.com/` |
| `scripts/lint_schema.py` | Valida JSON-LD: obrigatórios/recomendados por tipo, datas, preço, URLs, `@id`, avaliação própria, tipos aposentados (FAQ, HowTo, SearchAction), coerência com o texto visível | `python3 scripts/lint_schema.py https://dominio.com/servicos/x/` |
| `scripts/analyze_content.py` | Citabilidade por seção (resposta direta, trecho autossuficiente, dado, fonte), legibilidade pt-BR, autor, datas, repetição, stuffing | `python3 scripts/analyze_content.py URL --palavra "termo"` |
| `scripts/check_local.py` | NAP do site × referência × planilha de citações; horário, geo, `areaServed`, mapa, `tel:` | `python3 scripts/check_local.py URL1 URL2 --citacoes citacoes.csv` |
| `scripts/llms_txt.py` | `validar` (formato, links, instruções para IA) e `gerar` (rascunho a partir do sitemap) | `python3 scripts/llms_txt.py gerar https://dominio.com > llms.txt` |
| `scripts/drift.py` | `foto` e `comparar`: detecta noindex, canonical, title, JSON-LD e texto que mudaram entre duas datas | `python3 scripts/drift.py comparar relatorios/antes.json` |
| `scripts/google_updates.py` | `listar` atualizações do Google (data/atualizacoes-google.json) e `cruzar` com a série diária do Search Console | `python3 scripts/google_updates.py cruzar datas.csv` |
| `scripts/gsc_opportunities.py` | Exportação do Search Console: quase lá (4 a 20), CTR abaixo do padrão do site, canibalização, perguntas, marca × sem marca | `python3 scripts/gsc_opportunities.py Consultas.csv --marca aurora` |
| `scripts/cluster_serp.py` | Agrupa palavras pela sobreposição de URLs no top 10 (mesma intenção = mesma página) e confere o mapa | `python3 scripts/cluster_serp.py serps.csv --mapa mapa.csv` |
| `scripts/ai_visibility.py` | Resume a amostragem manual de IA: taxa de citação por plataforma/mês, concorrentes, domínios-fonte | `python3 scripts/ai_visibility.py amostragem.csv` |
| `scripts/pagespeed.py` | Core Web Vitals de campo (CrUX) e laboratório pela API do PageSpeed. Chave opcional via `PAGESPEED_API_KEY` | `python3 scripts/pagespeed.py https://dominio.com/` |
| `scripts/report.py` | Junta as saídas JSON num relatório HTML (imprimível em PDF) com nota por pilar e comparação com o mês anterior | `python3 scripts/report.py relatorios/*.json --saida relatorio.html` |

Todos aceitam `--help` e `--format json` (quando geram relatório). Códigos de saída: `0` sem erros,
`1` com erros, `2` falha de uso/rede. Saídas com dados de clientes vão para `relatorios/` ou
`clientes/` (ignoradas pelo Git).
Quando não houver acesso à rede, rode sobre arquivos locais (os scripts aceitam caminho de arquivo).

## Formato da entrega

- Arquivos prontos para uso (com o domínio real), não só texto explicando o que fazer.
- Para auditorias: o relatório no modelo de `templates/relatorio-auditoria.md`.
- Ao final, uma lista curta do que depende do dono do site (dados reais, acessos ao
  Search Console/Bing Webmaster Tools, aprovação de política de IA) e a próxima verificação
  recomendada (normalmente 2 a 4 semanas após publicar, ou após a próxima atualização do Google).
