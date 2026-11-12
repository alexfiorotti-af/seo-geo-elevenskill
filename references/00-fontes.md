# Fontes e data de referência

Estado do conhecimento desta skill: **novembro de 2026**. Busca muda rápido; antes de afirmar algo
sobre um recurso, política ou número abaixo, confira se não houve atualização. Prefira sempre a
fonte primária (documentação oficial) a blogs.

## Fontes primárias (documentação oficial)

| Tema | Fonte |
|---|---|
| Otimização para recursos de IA generativa do Google (publicado em 15/05/2026; ajuste sobre llms.txt em junho/2026) | https://developers.google.com/search/docs/fundamentals/ai-optimization-guide |
| Relatórios de desempenho de IA generativa no Search Console e controle de exclusão (lançados em junho/2026; controle global desde 31/08/2026) | https://developers.google.com/search/blog/2026/06/gen-ai-performance-reports |
| Title links (como o Google escolhe o título exibido) | https://developers.google.com/search/docs/appearance/title-link |
| Snippets, meta description, `nosnippet`, `max-snippet`, `data-nosnippet` | https://developers.google.com/search/docs/appearance/snippet |
| Políticas de spam do Google | https://developers.google.com/search/docs/essentials/spam-policies |
| Sistemas de ranqueamento do Google | https://developers.google.com/search/docs/appearance/ranking-systems-guide |
| Dados estruturados (galeria de tipos suportados) | https://developers.google.com/search/docs/appearance/structured-data/search-gallery |
| Simplificação da página de resultados (tipos de dados estruturados descontinuados, jun/2025) | https://developers.google.com/search/blog/2025/06/simplifying-search-results |
| Painel de status de atualizações do Google | https://status.search.google.com/ |
| Core Web Vitals | https://web.dev/articles/vitals |
| Sites amigáveis a agentes de IA (web.dev, 2026) | https://web.dev/articles/ai-agent-site-ux |
| Lighthouse, categoria Agentic Browsing (experimental) | https://developer.chrome.com/docs/lighthouse/agentic-browsing |
| Crawlers da OpenAI (OAI-SearchBot, GPTBot, ChatGPT-User, OAI-AdsBot) | https://developers.openai.com/api/docs/bots |
| Crawlers da Anthropic (ClaudeBot, Claude-SearchBot, Claude-User) | https://support.claude.com/en/articles/8896518 |
| Crawlers da Perplexity (PerplexityBot, Perplexity-User) | https://docs.perplexity.ai/docs/resources/perplexity-crawlers |
| IndexNow (protocolo) | https://www.indexnow.org/documentation |
| Sitemaps (protocolo) | https://www.sitemaps.org/protocol.html |
| robots.txt (RFC 9309) | https://www.rfc-editor.org/rfc/rfc9309 |
| Como o Google interpreta o robots.txt (429 tratado como 5xx, limite de 500 KiB, até 5 redirects) | https://developers.google.com/crawling/docs/robots-txt/robots-txt-spec |
| Por dentro do Googlebot: limite de 2 MB por URL, 64 MB para PDF, 15 MB para os demais crawlers (31/03/2026) | https://developers.google.com/search/blog/2026/03/crawler-blog-post |
| Registro de mudanças da documentação de rastreio (Google-Agent em mar/2026, Web Bot Auth em mai/2026, Google-GeminiNotebook em jul/2026, Retry-After em out/2026) | https://developers.google.com/crawling/docs/changelog |
| Atualizações da documentação do Search (fim dos resultados de FAQ em 07/05/2026) | https://developers.google.com/search/updates |
| Política de spam "sequestro do botão Voltar" (13/04/2026, aplicada desde 15/06/2026) | https://developers.google.com/search/blog/2026/04/back-button-hijacking |
| Mudança na política de abuso de reputação de site no EEE (ago/2026) | https://developers.google.com/search/blog/2026/08/update-site-reputation-policy |
| Content Signals (rascunho IETF draft-romm-aipref-contentsignals, chaves search, ai-input, ai-train; expirado em abr/2026) | https://datatracker.ietf.org/doc/draft-romm-aipref-contentsignals/ |
| Formato llms.txt | https://llmstxt.org/ |
| PageSpeed Insights API v5 (CrUX + Lighthouse) | https://developers.google.com/speed/docs/insights/v5/get-started |
| Limiares de Core Web Vitals e TTFB (bom até 0,8 s) | https://web.dev/articles/vitals e https://web.dev/articles/ttfb |
| hreflang e versões localizadas | https://developers.google.com/search/docs/specialty/international/localized-versions |
| Perfil da Empresa no Google: diretrizes de representação | https://support.google.com/business/answer/3038177 |
| Schema.org | https://schema.org/ |
| Universal Commerce Protocol (Google, jan/2026) | https://ucp.dev/ |
| Política de link spam (dentro das políticas de spam: compra/venda, trocas excessivas, automação, publieditorial, diretórios, widgets, fóruns) | https://developers.google.com/search/docs/essentials/spam-policies#link-spam |
| Qualificar links de saída (`sponsored`, `ugc`, `nofollow` como indicações) | https://developers.google.com/search/docs/crawling-indexing/qualify-outbound-links |
| Ferramenta de rejeição de links (quando usar e quando não usar) | https://support.google.com/webmasters/answer/2648487 |
| Apple Business (substituiu o Apple Business Connect em 14/04/2026; gerencia o cartão no Apple Maps) | https://www.apple.com/br/newsroom/2026/03/introducing-apple-business/ |

## Pesquisas e dados de mercado usados

| Dado | Fonte |
|---|---|
| GEO: citar fontes, incluir citações e estatísticas aumentou a visibilidade em respostas geradas em até ~40% no benchmark (até ~37% no Perplexity) | Aggarwal et al., "GEO: Generative Engine Optimization", arXiv:2311.09735 |
| Só ~38% das URLs citadas em AI Overviews estavam no top 10 da mesma busca (mar/2026), contra ~76% em jul/2025: efeito do query fan-out | Ahrefs, estudos de citações em AI Overviews (2025–2026) |
| ~12% das citações de assistentes de IA (ChatGPT, Gemini, Copilot, Perplexity) estavam no top 10 do Google para o mesmo prompt | Ahrefs, ago/2025 |
| Participação no tráfego web de IA generativa (mai/2026): ChatGPT ~53%, Gemini ~27–28%, Claude ~9% | Similarweb, Generative AI Landscape 2026 |
| Participação de buscadores no Brasil (out/2026): Google ~92%, Bing ~6,6% | StatCounter |
| Bing Webmaster Tools lança relatório "AI Performance" com citações no Copilot (fev/2026) | Bing Webmaster Tools / cobertura especializada |
| Visibilidade de marcas em AI Overviews (75 mil marcas, correlação de Spearman): menções da marca na web 0,664; âncoras com a marca 0,527; volume de busca da marca 0,392; número de backlinks 0,218 | Ahrefs, mai/2025 (atualizado em 2026) |
| Índice de legibilidade de Flesch adaptado ao português: 248,835 − 1,015 × (palavras/frase) − 84,6 × (sílabas/palavra) | Martins, Ghiraldelo, Nunes e Oliveira Jr., 1996 (ICMC-USP) |
| Google (John Mueller, jul/2021): troca sistemática de links é contra as diretrizes "mesmo que seja tematicamente relevante"; se for a maior parte dos links do site, pode gerar ação manual | Search Engine Roundtable, cobertura do Google Search Central Hangout |

## Linha do tempo de atualizações do Google em 2026 (confirmadas)

| Atualização | Período |
|---|---|
| Discover core update | 05/02 a 27/02 |
| Spam update | 24/03 a 25/03 |
| Core update de março | 27/03 a 08/04 |
| Core update de maio | 21/05 a 02/06 |
| Spam update | 24/06 a 26/06 |
| Spam update | 18/08 a 21/08 |
| Spam update | 24/09 a 08/10 |

Core update de maio concluído em 02/06/2026. A lista completa (2024 a 2026, com core, spam,
políticas, recursos e rastreio, cada item com fonte oficial) está em `data/atualizacoes-google.json`
e é usada por `scripts/google_updates.py`. Atualize o arquivo consultando o painel de status do
Google sempre que for diagnosticar variação de tráfego (pilar 11).
