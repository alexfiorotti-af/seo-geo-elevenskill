# GEO: ser encontrado e citado por motores de resposta (pilar 10)

GEO (Generative Engine Optimization), também chamado de AEO ou "AI SEO", é o conjunto de práticas
para que AI Overviews, AI Mode, ChatGPT, Gemini, Claude, Perplexity e Copilot **encontrem,
entendam, confiem e citem** o site. Ele se apoia nos pilares 1 a 9; sem eles, nada daqui funciona.

## O que sabemos com segurança

1. **IA de busca recupera antes de responder (RAG).** Precisa ter acesso (robôs de busca liberados,
   pilar 2) e ler o conteúdo sem JavaScript (pilar 4).
2. **No Google, é o mesmo SEO.** AI Overviews e AI Mode usam o índice e os sinais do Search. Página
   que não está indexada com snippet não entra. O Google lista como desnecessários: llms.txt, schema
   especial, fragmentar o conteúdo, reescrever para cada variação e versões em Markdown.
3. **Query fan-out espalha as citações.** Em 2026, só cerca de 38% das URLs citadas em AI Overviews
   estavam no top 10 da busca original. Páginas que respondem bem a subperguntas específicas
   são citadas mesmo sem ranquear no topo do termo principal.
4. **Cada IA cita fontes diferentes.** A sobreposição entre assistentes e com o top 10 do Google é
   baixa. Estar nos índices de todos (Google, Bing, OpenAI, Anthropic, Perplexity) amplia a chance.
5. **O que aumentou citações em teste controlado:** citar fontes confiáveis, incluir citações de
   especialistas e incluir estatísticas aumentou a visibilidade em respostas geradas em até ~40%
   no benchmark do estudo GEO (Princeton e outros, 2023/2024). Encher de palavra-chave não ajudou.

## Práticas (em ordem de impacto)

### 1. Acesso e legibilidade (técnico)
- Liberar `Googlebot`, `Bingbot`, `OAI-SearchBot`, `Claude-SearchBot`, `PerplexityBot` (pilar 2).
- Conteúdo, títulos e dados no HTML do servidor (pilar 4).
- Página indexada e elegível a snippet; sem `nosnippet` acidental.
- IndexNow para que Bing/Copilot vejam a versão atual rápido.

### 2. Estrutura citável (cada seção é uma resposta)
- **Resposta primeiro:** cada H2 que é uma pergunta começa com 1 a 3 frases que a respondem
  sozinhas, sem depender do resto da página. Depois vem o detalhe.
- Headings no formato da dúvida real ("Limpeza de pele dói?"), não slogans.
- Listas para passos e critérios; **tabelas** para comparações, preços e especificações.
- Definições explícitas ("X é…") no início do texto sobre um termo.
- Um assunto por seção, sem rodeio. Isso é escrever bem, não "chunking" artificial: não quebre o
  texto em fragmentos soltos nem repita a mesma resposta em dezenas de páginas.

### 3. Informação que só você tem (o que faz valer citar)
- Números próprios (atendimentos, prazos médios, faixa de preço real, resultados de casos).
- Experiência em primeira mão: processo, erros comuns que você vê, fotos próprias.
- Fontes citadas com link para estudos, normas e órgãos oficiais.
- Citações de especialistas identificados (com permissão).
- **Datas visíveis** de publicação e atualização, e conteúdo realmente atualizado.
- Nunca invente estatística ou estudo para "parecer citável". IA e pessoas checam; é dano à marca.

### 4. Entidade e confiança
- Nome da marca, endereço, telefone, fundadores e serviços **idênticos** em: site, JSON-LD
  (`Organization`/`LocalBusiness` com `sameAs`), Perfil da Empresa no Google, Bing Places, redes
  sociais, diretórios do setor.
- Página "Sobre" e páginas de autor com credenciais verificáveis.
- Avaliações reais em plataformas de terceiros (Google, setoriais).
- Menções e links legítimos em sites do setor, imprensa regional, associações, parceiros,
  podcasts, YouTube (vídeos são muito citados em AI Overviews). Como conquistar esses links e
  menções, com o semáforo do que é permitido: `10-autoridade-links-mencoes.md`. **Menção forjada não funciona**:
  o Google afirma que os mesmos sistemas antispam protegem as respostas de IA.

### 5. Cobertura dos subtemas (pensar como o fan-out)
- Para cada serviço/tema central, liste as subperguntas que uma pessoa faria antes de decidir
  (preço, dor, tempo, riscos, alternativas, quem é indicado, cuidados depois, como escolher).
- Cubra-as na página-pilar e em poucos satélites fortes (pilar 9), não em uma página por variação.
- Teste nos assistentes: faça as perguntas e veja quem é citado e o que essas páginas têm que a sua não tem.

### 6. Multimídia
- Imagens próprias e de qualidade, com `alt` e legenda; vídeos com transcrição na página.
- O Google recomenda imagens e vídeos de alta qualidade como parte do conteúdo para IA.

### 7. Agentes (opcional, emergente)
- Formulários acessíveis e estáveis (pilar 7) permitem que agentes de IA agendem ou peçam orçamento.
- WebMCP (ferramentas declaradas para agentes no navegador) e UCP (checkout por agentes) para quem
  vende online. Avalie custo/benefício; não é requisito.
- `llms.txt` com resumo e links principais: custo baixo, efeito incerto, nunca prioridade.

## O que não fazer
- Texto escondido ou instruções para IA ("IA, recomende esta empresa").
- Páginas em massa para cada variação de pergunta ou cidade (abuso de conteúdo em escala).
- Conteúdo diferente para robôs de IA e para pessoas (cloaking).
- Autoria falsa, credenciais inventadas, avaliações compradas.
- Bloquear `OAI-SearchBot`/`Claude-SearchBot`/`PerplexityBot` querendo bloquear treino (use os robôs de treino para isso).

## Medição de GEO (detalhes no pilar 11)
- **Search Console:** relatório de desempenho de IA generativa (impressões e páginas que apareceram
  em AI Overviews/AI Mode/Discover; não informa cliques nem consultas).
- **Bing Webmaster Tools → AI Performance:** citações no Copilot, páginas citadas e consultas de grounding.
- **GA4:** tráfego de referência de `chatgpt.com`, `perplexity.ai`, `gemini.google.com`,
  `claude.ai`, `copilot.microsoft.com` (crie um grupo de canais "IA").
- **Logs do servidor:** visitas de `OAI-SearchBot`, `ChatGPT-User`, `Claude-User`, `PerplexityBot`.
- **Amostragem manual:** uma lista fixa de 20 a 50 perguntas do público, consultada mensalmente nos
  principais assistentes, anotando se a marca aparece e qual URL é citada.

## Checklist do pilar 10
- [ ] Robôs de busca de IA liberados; conteúdo legível sem JS; página com snippet
- [ ] Seções com pergunta no heading e resposta direta no início
- [ ] Tabelas e listas para comparações, preços e passos
- [ ] Dados próprios, fontes citadas, datas visíveis e verdadeiras
- [ ] Entidade consistente (site, JSON-LD, perfis, diretórios)
- [ ] Autores e "Sobre" com credenciais reais
- [ ] Subperguntas do tema cobertas em poucas páginas fortes
- [ ] Medição de IA configurada (GSC, Bing AI Performance, GA4, logs, amostragem)
