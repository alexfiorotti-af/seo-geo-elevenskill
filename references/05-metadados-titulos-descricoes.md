# Front-end, parte 2: metodologia de títulos, descrições e metatags (pilar 8)

## Como o Google decide o que exibe

**Título (title link):** o Google gera automaticamente a partir de várias fontes: o `<title>`, o
título visual principal (H1), outros headings, `og:title`, texto de destaque, âncoras de links
apontando para a página e o `WebSite` structured data. Ele reescreve quando o `<title>` está
vazio pela metade, desatualizado, impreciso, quase igual ao de outras páginas (micro-boilerplate),
em idioma diferente do conteúdo, ou quando não há título principal claro.

**Snippet:** gerado a partir do conteúdo da página, escolhendo o trecho mais relevante para cada
busca. A meta description é usada quando descreve a página melhor que o texto. Logo, a
description é uma **proposta**: quanto mais precisa e útil, mais vezes é usada.

**Não há limite oficial de caracteres** para nenhum dos dois; o corte acontece pela largura do
dispositivo. Os números abaixo são heurísticas para não ser cortado, não regras do Google.

## Metodologia de title (5 passos)

1. **Intenção:** o que a pessoa quer ao buscar? (saber, comparar, comprar/contratar, chegar a um lugar).
2. **Termo principal:** a forma como o público fala (pilar 9), no início do título quando natural.
3. **Diferencial ou qualificador:** cidade, público, ano (só se o conteúdo for de fato daquele ano),
   formato ("guia", "preços", "passo a passo"), prova ("desde 2012").
4. **Marca no fim,** separada por ` | ` ou ` - `. Curta. Na home, a marca pode abrir o título.
5. **Teste de corte e unicidade:** rode `scripts/lint_meta.py`.

**Heurística de tamanho:** até ~580 px de largura na fonte do resultado (aproximadamente 50 a 60
caracteres). Abaixo de ~30 caracteres costuma faltar contexto.

### Fórmulas por tipo de página
| Tipo | Fórmula | Exemplo (fictício) |
|---|---|---|
| Home (negócio local) | `[Marca]: [o que faz] em [cidade]` | `Clínica Aurora: estética facial em Vitória` |
| Home (marca nacional) | `[Marca] \| [categoria + benefício]` | `Rota Fiscal \| Contabilidade online para MEI` |
| Serviço local | `[Serviço] em [cidade/bairro] \| [Marca]` | `Limpeza de pele em Jardim da Penha \| Clínica Aurora` |
| Serviço sem região | `[Serviço]: [benefício/diferencial] \| [Marca]` | `Gestão de tráfego pago: relatórios semanais \| Agência Norte` |
| Produto | `[Produto + atributo-chave] \| [Marca/Loja]` | `Sérum de vitamina C 30 ml \| Loja Aurora` |
| Categoria | `[Categoria] \| [qualificador] \| [Marca]` | `Séruns faciais \| entrega em todo o Brasil \| Loja Aurora` |
| Artigo "como" | `Como [resultado]: [método/escopo]` | `Como escolher um protetor solar: guia por tipo de pele` |
| Artigo "o que é" | `[Termo]: o que é, [aspecto 1] e [aspecto 2]` | `Peeling químico: o que é, tipos e cuidados` |
| Comparativo | `[A] ou [B]? [critério de decisão]` | `Botox ou preenchimento? Diferenças e indicações` |
| Preço | `Quanto custa [serviço] em [ano/cidade]` | `Quanto custa limpeza de pele em Vitória` |
| Lista | `[N] [itens] para [objetivo]` | `7 cuidados depois do peeling` |
| Contato/Sobre | `[Contato/Sobre] \| [Marca]` | `Contato \| Clínica Aurora` |

### Sites em inglês para o mercado dos EUA
| Tipo | Fórmula | Exemplo (fictício) |
|---|---|---|
| Home (negócio local) | `[Brand] \| [Service] in [City], [ST]` | `Aurora Home Co. \| Kitchen & Bath Remodeling in Orlando, FL` |
| Serviço local | `[Service] in [City], [ST] \| [Brand]` | `Kitchen Remodeling in Orlando, FL \| Aurora Home Co.` |
| Serviço + diferencial | `[Service]: [verifiable benefit] \| [Brand]` | `Bathroom Remodeling: Fixed-Price Quotes \| Aurora Home Co.` |
| Página de preço | `[Service] Cost in [City] ([Year]): [scope]` | `Kitchen Remodel Cost in Orlando (2026): Price Ranges` |
| Artigo "como" | `How to [result]: [scope]` | `How to Choose Bathroom Tile: A Room-by-Room Guide` |
| Comparativo | `[A] vs. [B]: [decision criterion]` | `Quartz vs. Granite Countertops: Cost and Upkeep` |

- Title Case é o padrão americano; sigla do estado (`FL`, `MA`, `TX`) economiza largura.
- Não use "near me" no title: o Google já resolve a proximidade pela localização de quem busca.
- Description: área atendida, prova verificável ("licensed & insured" só se for verdade) e próximo
  passo ("Call for a free estimate").
- Negócio de brasileiros nos EUA com site bilíngue: URLs separadas por idioma, com
  `hreflang="en-US"` e `hreflang="pt-US"` (português para quem está nos EUA), recíprocos (pilar 3).

### Erros que fazem o Google reescrever
- Title genérico ("Início", "Serviços", "Página 2").
- Mesmo title em várias páginas, ou mudando só um detalhe.
- Lista de palavras-chave ("Estética, Clínica de Estética, Estética Vitória...").
- Ano desatualizado no title enquanto a página mostra outro.
- Title em inglês com conteúdo em português (ou vice-versa).
- Marca longa repetida em todas as páginas.
- H1 diferente do assunto do title.

## Metodologia de meta description (4 passos)

1. **Responda o que a página entrega** na primeira frase (o resumo que o Google procuraria no texto).
2. **Detalhe concreto:** preço a partir de, prazo, autor, data, especificação, região atendida.
3. **Motivo para clicar:** diferencial verificável ou próximo passo ("veja a tabela", "agende pelo WhatsApp").
4. **Única por página,** escrita para pessoas, com o termo principal ou sinônimo de forma natural
   (o Google destaca em negrito termos da busca).

**Heurística de tamanho:** ~120 a 155 caracteres (até ~920 px no desktop). No celular aparecem mais
linhas, mas a primeira frase precisa se sustentar sozinha.

**Exemplo (fictício):** `Limpeza de pele profunda em Jardim da Penha com esteticista habilitada.
Sessões de 60 min, a partir de R$ 180. Agende pelo WhatsApp.`

Para sites grandes (catálogo), gere descriptions programaticamente a partir dos atributos, desde
que o resultado seja legível e varie entre páginas.

## H1 e slug
- **H1:** pode ser mais longo e conversacional que o title; mesmo assunto, mesma intenção.
- **Slug:** a palavra principal, curta, sem stopwords desnecessárias (`/servicos/limpeza-de-pele/`).

## Metatags essenciais no `<head>` (ordem recomendada)

```html
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Limpeza de pele em Jardim da Penha | Clínica Aurora</title>
<meta name="description" content="…">
<link rel="canonical" href="https://dominio/servicos/limpeza-de-pele/">
<meta name="robots" content="index, follow, max-image-preview:large">
<!-- hreflang, se houver versões em outros idiomas -->
<link rel="alternate" hreflang="pt-BR" href="https://dominio/servicos/limpeza-de-pele/">
<!-- Open Graph / redes sociais e apps de mensagem (WhatsApp usa OG) -->
<meta property="og:type" content="website">
<meta property="og:site_name" content="Clínica Aurora">
<meta property="og:title" content="Limpeza de pele em Jardim da Penha">
<meta property="og:description" content="…">
<meta property="og:url" content="https://dominio/servicos/limpeza-de-pele/">
<meta property="og:image" content="https://dominio/og/limpeza-de-pele.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:locale" content="pt_BR">
<meta name="twitter:card" content="summary_large_image">
<!-- Ícones -->
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="icon" href="/icon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta name="theme-color" content="#ffffff">
<!-- JSON-LD (pilar 6) -->
<script type="application/ld+json">…</script>
```

Notas:
- `og:image` sempre com **URL absoluta**, 1200×630, menos de ~300 KB, texto legível em miniatura.
- `max-image-preview:large` permite imagem grande em Discover e resultados; útil para conteúdo.
- Favicon: múltiplo de 48×48 px, estável, representando a marca (aparece no resultado do Google).
  O nome do site exibido vem do `WebSite` structured data (`name`) e do conteúdo da home.
- `<meta name="keywords">`: **não use**. O Google ignora; não traz benefício e expõe a estratégia.
- Controles de snippet para casos especiais: `nosnippet`, `max-snippet:[n]`, `data-nosnippet` em
  trechos (ex.: aviso legal que não deve virar snippet). Eles também limitam o uso do conteúdo nos
  recursos de IA do Google.

## Palavras-chave nos metadados (como usar hoje)
"Palavra-chave" hoje é o **mapa intenção → página** (pilar 9), não uma metatag. Nos metadados:
- Termo principal no title (de preferência no início) e no H1, de forma natural.
- Termo principal ou sinônimo na description, sem repetição forçada.
- Termos secundários vão nos H2, no corpo e nos textos-âncora de links internos, não no title.
- Nunca use o mesmo termo principal como foco de duas páginas.

## Checklist do pilar 8
- [ ] Todo title único, descritivo, com termo principal, marca curta no fim, sem corte (lint ok)
- [ ] Toda description única, resume a página, tem detalhe concreto e próximo passo
- [ ] H1 coerente com o title; slug curto e descritivo
- [ ] Canonical, robots, viewport, lang e charset presentes
- [ ] Open Graph completo com imagem absoluta 1200×630
- [ ] Favicon nos tamanhos corretos e `WebSite` com `name` na home
- [ ] Sem meta keywords; sem metadados alterados só via JavaScript
