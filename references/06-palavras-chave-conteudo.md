# Front-end, parte 3: palavras-chave, intenção e arquitetura de conteúdo (pilar 9)

Este pilar define **quais páginas existem e por quê**. É também o motor que "movimenta" o site:
páginas novas e atualizadas, ligadas entre si, mostram aos buscadores que o site está vivo e
cobrem os subtemas que o query fan-out das IAs procura.

## 1. Pesquisa de palavras-chave (processo)

### Fontes gratuitas (sempre disponíveis)
- **Search Console → Desempenho:** consultas que já trazem impressões. Ouro para sites existentes.
- **Sugestões do Google** (autocomplete), "As pessoas também perguntam" e "Pesquisas relacionadas".
- **Google Trends:** sazonalidade e comparação de termos por região.
- **Perguntas reais do público:** WhatsApp, e-mails, avaliações, atendimento, comentários. A
  linguagem do cliente vale mais que a do fornecedor.
- **Concorrentes:** que páginas eles têm, quais temas cobrem e você não.
- **Assistentes de IA:** pergunte ao ChatGPT/Gemini/Perplexity sobre o tema e veja quais
  subperguntas e fontes aparecem (indica o fan-out e quem já é citado).

### Ferramentas pagas (se o projeto tiver)
Volume, dificuldade e lacunas de concorrentes (Semrush, Ahrefs, Similarweb e afins). Use como
apoio; volume estimado de cauda longa local costuma ser zero nas ferramentas e mesmo assim converter.

### Classificação de intenção
| Intenção | Sinal na busca | Página que atende |
|---|---|---|
| Informacional | "o que é", "como", "por que", "vale a pena" | Artigo, guia, glossário |
| Comparativa/investigação | "melhor", "vs", "ou", "preço", "avaliação" | Comparativo, página de preço, cases |
| Transacional | "contratar", "agendar", "comprar", "orçamento" | Página de serviço/produto |
| Local | "perto de mim", "em [cidade]", "[bairro]" | Página de serviço local + Perfil da Empresa |
| Navegacional | nome da marca | Home, contato |

**Regra:** olhe a primeira página do Google para o termo. O tipo de página que ranqueia ali
(artigo, loja, mapa, vídeo) é o tipo que o Google entende como certo para aquela intenção.

## 2. Mapa de palavras-chave (documento central)

Uma linha por URL. Modelo em `templates/mapa-de-palavras-chave.csv`. Campos:
`url, tipo, intencao, palavra_principal, secundarias, title, description, h1, status, links_de_entrada`.

Regras do mapa:
- **Uma palavra principal por URL, uma URL por palavra principal.**
- Variações com a mesma intenção (singular/plural, sinônimos, ordem diferente) ficam na mesma URL.
- Se duas URLs disputam a mesma intenção: funda (301) ou diferencie a intenção de cada uma.
- Quando o Search Console mostra duas URLs alternando para a mesma consulta, é canibalização.

## 3. Clusters (hub e satélites)

```
                 [Página-pilar / hub]
         /servicos/limpeza-de-pele/  (transacional)
           ↑↓            ↑↓             ↑↓
 /blog/limpeza-de-pele-  /blog/cravos-   /blog/cuidados-depois-
 doi/  (informacional)   e-espinhas/     da-limpeza-de-pele/
```
- A pilar cobre o tema amplo e linka para cada satélite; cada satélite aprofunda uma subpergunta
  e linka de volta para a pilar com âncora descritiva.
- Satélites linkam entre si quando houver relação real.
- O conjunto cobre as subperguntas que o fan-out gera, sem criar páginas quase iguais.

## 4. Links internos
- Cada página nova recebe **pelo menos 2 a 3 links de entrada** de páginas já indexadas e relevantes
  (incluindo da pilar). Página sem link de entrada demora a ser descoberta e tem pouca autoridade.
- Âncora descritiva e variada ("limpeza de pele para pele oleosa"), nunca "clique aqui".
- Links no corpo do texto pesam mais que em menu e rodapé.
- Breadcrumbs em todas as páginas internas (com `BreadcrumbList`).
- Revise páginas antigas ao publicar: acrescente links para o conteúdo novo.

## 5. Páginas que movimentam o site

| Tipo | Para quê | Cuidado |
|---|---|---|
| **Páginas de serviço/produto fortes** | Converter; ranquear para intenção transacional | Conteúdo próprio: processo, preço/faixa, prazos, FAQ real, prova |
| **Artigos que respondem dúvidas reais** | Atrair quem ainda está pesquisando; alimentar IAs | Resposta direta no início; experiência própria |
| **Comparativos e páginas de preço** | Capturar a fase de decisão; muito citadas por IAs | Critérios honestos; datar preços |
| **Estudos de caso** | Prova e informação original (difícil de copiar) | Com autorização do cliente; números reais |
| **Glossário** | Definições curtas linkadas aos serviços | Só termos que o público usa |
| **Páginas locais** | Uma por cidade/bairro atendido de verdade | Conteúdo realmente local (equipe, endereço, casos, particularidades). Sem troca só do nome da cidade |
| **Página "Sobre" e de autores** | Confiança e autoria (E-E-A-T) | Credenciais verificáveis, foto real, links oficiais |
| **Atualização de conteúdo (refresh)** | Manter posições e frescor | Atualizar fatos, exemplos e data; não só trocar a data |
| **Poda (pruning)** | Remover peso morto | Páginas sem tráfego nem valor: melhorar, fundir (301) ou remover (404/410) |

### Cadência sugerida (negócio local ou PME)
- Mês 1: páginas de serviço e pilares completas.
- Depois: 2 a 4 conteúdos novos por mês + 1 a 2 atualizações de conteúdo existente.
- Trimestral: revisão do mapa de palavras-chave com dados do Search Console e poda.
- Publicar pouco e bem supera publicar muito e raso. Volume gerado em massa sem revisão humana
  é exatamente o que as atualizações de spam de 2026 combateram.

## 6. Qualidade: o que os sistemas premiam (E-E-A-T)
- **Experiência:** relato em primeira mão, fotos próprias, dados do próprio negócio.
- **Especialidade:** autor identificado com credenciais relevantes.
- **Autoridade:** reconhecimento externo (citações, menções, links de sites do setor e da região).
- **Confiabilidade:** informações corretas, fontes citadas, contato claro, política de privacidade, HTTPS.

O Google pede conteúdo "não commodity", com ponto de vista próprio. Texto genérico reescrito de
outros sites (por pessoa ou IA) não traz nada que justifique ranquear ou ser citado.

## Checklist do pilar 9
- [ ] Mapa de palavras-chave com uma intenção por URL e sem canibalização
- [ ] Intenção de cada página confere com o tipo de página que ranqueia hoje
- [ ] Clusters definidos (pilar + satélites) com links nos dois sentidos
- [ ] Cada página com 2+ links internos de entrada e breadcrumbs
- [ ] Páginas locais só onde há conteúdo local real
- [ ] Calendário de publicação e de atualização definido
- [ ] Autor identificado e página "Sobre" com credenciais reais
