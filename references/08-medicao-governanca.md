# Medição, governança e políticas de spam (pilar 11)

## 1. Instrumentação mínima (todo site)

| Ferramenta | Configurar | Olhar com frequência |
|---|---|---|
| **Google Search Console** | Propriedade de domínio (verificação por DNS); envio do sitemap | Desempenho (consultas, páginas, CTR), Indexação de páginas, Core Web Vitals, relatório de IA generativa, Links (exportar mensalmente), Ações manuais, Segurança |
| **Bing Webmaster Tools** | Importar do Search Console; sitemap; IndexNow | AI Performance (citações no Copilot, consultas de grounding), Search Performance, Site Scan |
| **GA4** (ou analytics equivalente com consentimento) | Grupo de canais "IA" (abaixo); conversões (WhatsApp, formulário, compra) | Sessões e conversões orgânicas e de IA por página de entrada |
| **Perfil da Empresa no Google / Bing Places** | Mesmo NAP do site | Ligações, rotas, cliques no site |
| **Logs do servidor / CDN** | Retenção de pelo menos 30 dias | Hits por robô, status 4xx/5xx para robôs, URLs mais rastreadas |

### Grupo de canais "IA" no GA4 (regex de origem)
```
.*(chatgpt\.com|chat\.openai\.com|perplexity\.ai|gemini\.google\.com|claude\.ai|copilot\.microsoft\.com|meta\.ai|you\.com|grok\.com).*
```
Coloque esse canal **acima** de "Referral" na ordem do grupo. Parte do tráfego de IA chega sem
referenciador (aparece como direto); trate o número como piso.

### Robôs nos logs (padrões de user-agent)
`Googlebot`, `bingbot`, `OAI-SearchBot`, `ChatGPT-User`, `GPTBot`, `Claude-SearchBot`, `Claude-User`,
`ClaudeBot`, `PerplexityBot`, `Perplexity-User`, `Applebot`, `Meta-ExternalAgent`, `CCBot`.
User-agent pode ser falsificado: para decisões de bloqueio, confira o IP contra as faixas que cada
empresa publica (OpenAI, Perplexity e Google publicam as suas; Anthropic também lista as suas).

## 2. KPIs por fase

| Fase | KPI principal | KPI de apoio |
|---|---|---|
| 0 a 4 semanas após publicar | Páginas indexadas / páginas no sitemap | Erros de rastreio, Core Web Vitals |
| 1 a 3 meses | Impressões e posição média das consultas-alvo | Impressões em recursos de IA, citações no Bing |
| 3 meses em diante | Cliques e **conversões** orgânicas e de IA | CTR por página, menções em amostragem de IA |
| Contínuo (autoridade) | Domínios de referência **relevantes** conquistados por mês | Links perdidos e recuperados, páginas linkadas com 404, menções da marca com e sem link, tráfego de referência e conversões vindas de links, distribuição de âncoras e atributos |

Com respostas de IA ocupando o topo, impressões podem subir enquanto cliques caem. Por isso o KPI
final é conversão (contato, venda), não clique.

Para autoridade, conte **domínios relevantes**, não links brutos: dez links de um mesmo diretório
valem menos que um de um jornal da cidade. Detalhes em `10-autoridade-links-mencoes.md`.

## 3. Políticas de spam do Google (o que derruba um site)

Atualizações de spam em 2026 (março, junho, agosto e setembro) reforçaram a aplicação destas
políticas, sem criar novas:
- **Abuso de conteúdo em escala:** muitas páginas geradas (por IA ou não) para manipular ranking,
  sem valor próprio. Inclui criar uma página para cada variação de busca do fan-out.
- **Abuso de reputação de site:** conteúdo de terceiros hospedado para aproveitar a autoridade do domínio.
- **Abuso de domínio expirado:** comprar domínio com histórico para publicar conteúdo sem relação.
- **Páginas-porta (doorway):** páginas criadas só para capturar buscas e mandar para outro lugar.
- **Spam de links:** compra/venda de links que passam autoridade, troca excessiva, PBNs.
- **Cloaking, texto oculto, redirecionamento enganoso, keyword stuffing.**
- **Conteúdo copiado ou "espremido" de outras fontes sem valor adicional.**

Links pagos ou patrocinados são permitidos com `rel="sponsored"` (e `rel="ugc"` para conteúdo de usuário).

## 4. Rotina de governança

| Quando | O quê |
|---|---|
| A cada publicação | Title/description no lint; JSON-LD validado; links internos de entrada; sitemap atualizado; IndexNow enviado; pedido de indexação no GSC para páginas importantes |
| Semanal | Erros novos no GSC (indexação, ações manuais, segurança) |
| Mensal | Desempenho por cluster; páginas com impressões e CTR baixo (revisar title/description); amostragem de IA; `crawl_site.py` (links quebrados, órfãs); exportar Links do Search Console e rodar `verify_backlinks.py destinos` e `origens`; alertas de menção da marca |
| Trimestral | Revisão do mapa de palavras-chave, canibalização, poda e atualização de conteúdo; auditoria completa com os scripts; revisão do plano de autoridade (o que trouxe links e menções, o que não trouxe) |
| Após atualização do Google | Esperar a conclusão do rollout + 1 semana antes de concluir algo; comparar períodos equivalentes |

## 5. Queda de tráfego: árvore de diagnóstico

1. **É real ou é medição?** Mudou tag, consentimento de cookies, filtro, domínio da propriedade?
   Compare GA4 com GSC. Se só um caiu, é medição.
2. **É técnico?** Verifique em ordem: robots.txt (mudou? 5xx?), `noindex` acidental (deploy recente),
   canonical apontando errado, redirects quebrados, sitemap vazio, servidor lento/5xx para robôs,
   conteúdo sumindo do HTML do servidor (mudança para CSR). Rode os scripts nas páginas que caíram.
3. **Foi uma página, um cluster ou o site todo?** Página isolada → concorrência ou intenção mudou.
   Site todo → técnico, ação manual ou atualização do Google.
4. **Coincide com atualização?** Compare as datas com o painel de status do Google (`00-fontes.md`).
   - Core update: reavaliação de qualidade/relevância. Não há conserto técnico; melhore o
     conteúdo das páginas afetadas (originalidade, experiência, utilidade) e espere a próxima.
   - Spam update: revise as políticas acima com honestidade.
5. **Ação manual?** Search Console → Ações manuais. Se houver, corrija e peça reconsideração.
   Ação por "links não naturais" pede limpeza do perfil (remover links, e só então rejeitar o que
   sobrar; ver `10-autoridade-links-mencoes.md`, seção 7).
6. **Perdeu links importantes?** Compare a exportação de Links do Search Console com a anterior e
   rode `verify_backlinks.py`: páginas linkadas que passaram a dar 404 (deploy, migração) e
   parcerias encerradas explicam quedas graduais em páginas específicas.
7. **Mudou o resultado da busca?** Pesquise os termos: entrou AI Overview, mapa, vídeo ou
   concorrente novo? Se a resposta passou a aparecer na própria busca, ajuste o objetivo para
   ser citado (pilar 10) e trabalhe a fase de decisão (comparativos, preço, cases).

## 6. Migração de site (troca de plataforma, domínio ou estrutura)

Antes:
- Rastreie o site antigo e exporte todas as URLs indexadas (GSC + sitemap + crawler + analytics).
- Mapa de redirects 1:1 (URL antiga → URL nova equivalente), nunca tudo para a home.
- Preserve titles, descriptions, H1, conteúdo e JSON-LD das páginas que trazem tráfego.
- Baixe dados de referência (90 dias de GSC por página) para comparar depois.
- Exporte "Páginas mais linkadas" do Search Console: **toda página com backlink precisa de
  redirect** para a equivalente, mesmo que não tenha tráfego.

No dia:
- Redirects 301 ativos, sitemap novo enviado, robots.txt de produção (não o de homologação),
  `noindex` de homologação removido, IndexNow das URLs novas.
- Se mudou de domínio: ferramenta "Mudança de endereço" no Search Console; mantenha o domínio
  antigo e os redirects por no mínimo 1 ano.

Depois (4 a 8 semanas):
- Acompanhe indexação e 404 no GSC diariamente na primeira semana.
- Compare impressões e cliques por página com a referência; corrija redirects faltantes.
- Rode `verify_backlinks.py destinos` com a exportação feita antes da migração (URLs antigas):
  nenhuma pode responder 404. Rode `crawl_site.py` no site novo para links internos antigos.
