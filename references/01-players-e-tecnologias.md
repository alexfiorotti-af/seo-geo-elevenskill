# Players e tecnologias de busca (visão global, 2026)

Leia quando precisar explicar ao cliente "para quem" o site está sendo otimizado, decidir a política
de crawlers de IA ou justificar uma prioridade.

## 1. Como qualquer buscador funciona (e onde a IA entra)

Todo sistema de busca, clássico ou com IA, passa pelas mesmas etapas. Os pilares desta skill
atacam cada uma delas, nessa ordem:

```
Descoberta → Rastreamento → Renderização → Indexação → Recuperação → Ranqueamento → Apresentação
(links,      (robots.txt,   (HTML do       (canonical,  (palavras,     (relevância,    (title link,
 sitemaps,    status HTTP,   servidor,      noindex,     entidades,     qualidade,      snippet,
 IndexNow)    velocidade)    JS)            duplicação)  embeddings)    experiência)    resposta de IA)
```

Na busca com IA, as quatro primeiras etapas são iguais. O que muda está no fim:

- **RAG (geração aumentada por recuperação):** o modelo não "sabe" seu site; ele recupera trechos
  de um índice no momento da pergunta e escreve a resposta a partir deles, citando as fontes.
  Se a página não está no índice, ou o trecho não é extraível, ela não existe para a IA.
- **Query fan-out:** o AI Mode (e os assistentes em geral) desmembra a pergunta em várias
  subconsultas e busca cada uma. Por isso páginas fora do top 10 da busca original são citadas:
  elas ranqueiam bem para uma das subconsultas. Consequência prática: cobrir bem os
  subtemas de um assunto (em seções claras de poucas páginas fortes) rende mais que
  criar uma página por variação de busca, o que o Google trata como abuso de conteúdo em escala.
- **Seleção de trechos (passages):** o sistema escolhe parágrafos, listas e tabelas que respondem
  diretamente a uma subconsulta. Seções com título claro e resposta logo no início ganham.
- **Recuperação semântica (embeddings):** casa significado, não só palavra exata. Sinônimos e
  reescritas para cada variação de cauda longa não são necessários (o Google diz isso explicitamente).

## 2. Os principais players

### Buscadores com índice próprio

| Player | Peso | O que importa saber |
|---|---|---|
| **Google** (Search, AI Overviews, AI Mode, Discover, Imagens, Maps) | ~90% das buscas no mundo; ~92% no Brasil (out/2026) | Referência principal. AI Overviews e AI Mode usam o índice e os sinais do Search; não há "SEO separado para IA". Controle de exclusão das features de IA no Search Console desde 2026. Sistemas nomeados: link analysis/PageRank, BERT, MUM, RankBrain, neural matching, passage ranking, reviews system, freshness, deduplicação, SpamBrain; o antigo "helpful content" foi incorporado ao core em 2024. |
| **Microsoft Bing** (Bing, Copilot) | ~4% global; ~6,6% no Brasil; peso maior em desktop e no ecossistema Windows/Edge | Índice usado também por outros serviços. Suporta IndexNow. Bing Webmaster Tools tem relatório "AI Performance" com citações no Copilot e as consultas de grounding. Bing Places para negócios locais. |
| **Yandex** | Dominante na Rússia | Suporta IndexNow. Relevante só para público russófono. |
| **Baidu** | Dominante na China continental | Exige hospedagem/ICP e conteúdo em chinês; fora do escopo padrão. |
| **Naver** | Forte na Coreia do Sul | Suporta IndexNow. |
| **Apple** (Applebot: Siri, Spotlight, Safari Suggestions) | Tráfego indireto relevante em iOS | `Applebot-Extended` controla uso em treino de modelos da Apple; bloqueá-lo não afeta a busca da Apple. |
| **Brave Search, DuckDuckGo, Ecosia, Yep, Seznam** | Nicho | Brave tem índice próprio; DuckDuckGo usa majoritariamente fontes parceiras. Seznam e Yep suportam IndexNow. |

### Motores de resposta (assistentes com busca)

| Player | Peso (tráfego web de IA, mai/2026) | Robô que precisa acessar o site para você aparecer |
|---|---|---|
| **ChatGPT** (OpenAI) | ~53% | `OAI-SearchBot` (resultados do ChatGPT Search). `ChatGPT-User` busca páginas quando o usuário pede. `GPTBot` é só treino. |
| **Gemini** (Google) | ~27–28% | Googlebot (busca). `Google-Extended` controla treino e grounding do app Gemini/Vertex, **não** afeta AI Overviews nem AI Mode. |
| **Claude** (Anthropic) | ~9% | `Claude-SearchBot` (índice de busca). `Claude-User` busca quando o usuário pede. `ClaudeBot` é treino. |
| **Perplexity** | menor, porém cita muito | `PerplexityBot` (índice). `Perplexity-User` busca sob demanda e em geral ignora robots.txt. |
| **Copilot** (Microsoft) | integrado ao Windows/Edge/Office | Bingbot. |
| **Meta AI** | grande base de usuários em apps | `Meta-ExternalAgent` / `Meta-ExternalFetcher`. |

Números de participação mudam rápido; ver `00-fontes.md` e atualizar antes de citar a cliente.

**Leitura estratégica:** a sobreposição entre o que cada IA cita é baixa (estudos de 2025–2026
mostram que só cerca de 12% das citações de assistentes coincidem com o top 10 do Google para o
mesmo prompt). Não dá para "otimizar para uma IA". O que funciona para todas: estar no índice delas
(liberar os robôs de busca), entregar o conteúdo em HTML legível sem JavaScript, e ser a fonte mais
clara e confiável sobre o assunto.

## 3. Tecnologias que movem o sistema (o que o site precisa suportar)

| Tecnologia | Papel | Pilar |
|---|---|---|
| HTTP/2 ou HTTP/3, HTTPS, compressão (Brotli/gzip) | Rastreio eficiente e velocidade | 5 |
| robots.txt (RFC 9309), meta robots, `X-Robots-Tag` | Controle de rastreio e indexação | 2, 3 |
| Sitemaps XML (+ imagens, vídeo, hreflang) | Descoberta e sinal de atualização | 2 |
| IndexNow | Notificação instantânea de URL nova/alterada (Bing, Yandex, Naver, Seznam, Yep; o Google não participa) | 2 |
| `rel=canonical`, redirects 301/308, `hreflang` | Consolidação de sinais e idiomas | 3 |
| SSR/SSG/ISR (renderização no servidor) | Conteúdo legível por robôs que não executam JS | 4 |
| Core Web Vitals (LCP, INP, CLS) | Experiência de página, desempate de ranqueamento | 5 |
| Schema.org em JSON-LD | Entendimento de entidades e resultados enriquecidos | 6 |
| Árvore de acessibilidade, HTML semântico | Leitura por agentes de IA e por leitores de tela | 7 |
| `llms.txt` | Resumo em Markdown para agentes; o Google não usa, alguns agentes e o Lighthouse (categoria experimental) verificam | 2 |
| WebMCP e UCP | Padrões emergentes para agentes executarem ações (formulários, compras). Opcional, para e-commerce e serviços com agendamento | 7 |
| Search Console, Bing Webmaster Tools, logs do servidor | Medição | 11 |

## 4. O que NÃO move mais o ponteiro (desmistificar com o cliente)

- **Meta keywords:** o Google ignora há mais de uma década. Não use.
- **Densidade de palavra-chave:** não existe número mágico; repetição artificial é spam.
- **Tamanho ideal de texto:** o Google afirma que não há tamanho ideal de página.
- **"Fragmentar" o conteúdo para IA (chunking) ou reescrever para cada variação:** o Google lista
  como desnecessário.
- **Schema "especial para IA" ou versão Markdown da página:** não é requisito para os recursos de
  IA do Google. Dados estruturados continuam úteis pelos motivos clássicos (pilar 6).
- **llms.txt como fator de ranqueamento:** não ajuda nem atrapalha o Google; pode ser útil para
  outros agentes. Custo baixo, prioridade baixa.
