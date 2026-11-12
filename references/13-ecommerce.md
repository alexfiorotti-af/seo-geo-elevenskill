# E-commerce (pilares 1, 3, 6, 9 e 10 para lojas)

Para lojas virtuais próprias (Shopify, VTEX, Nuvemshop, WooCommerce, Magento, headless). Os
problemas típicos de loja são de escala: milhares de URLs geradas por filtros, variações e
paginação, e dados de produto que precisam bater em três lugares (página, JSON-LD e feed).

## 1. Arquitetura e rastreio

- Hierarquia rasa: home → categoria → subcategoria → produto, com breadcrumb (`BreadcrumbList`).
- **Filtros (navegação facetada)** são a maior armadilha de rastreio:
  - Indexe só combinações com demanda de busca real (ex.: "tênis de corrida masculino"), como
    páginas próprias com URL limpa, title, H1 e texto.
  - As demais: bloqueie os parâmetros no robots.txt (ou use fragmento `#`), mantenha ordem fixa de
    parâmetros e devolva 404 para combinação sem produtos. `noindex` não economiza rastreio.
  - Ordenação (`?ordem=preco`) e visualização (`?view=grid`) nunca são indexáveis.
- **Paginação:** cada página (`?page=2`) com canonical para ela mesma e links `<a href>` rastreáveis
  para as próximas. O Google não usa `rel="next/prev"`. "Carregar mais" só em JS esconde produtos.
- Busca interna com `noindex` e fora dos links rastreáveis.
- Rode `crawl_site.py` com `--seguir-parametros` numa cópia de homologação para medir a explosão
  de URLs, e `check_robots.py --path` com URLs de filtro para conferir o bloqueio.

## 2. Ciclo de vida do produto

| Situação | O que fazer |
|---|---|
| Sem estoque, volta depois | Página 200, `availability: OutOfStock` (ou `BackOrder`/`PreOrder`), produtos parecidos visíveis |
| Descontinuado, há substituto | 301 para o substituto ou para a categoria mais próxima |
| Descontinuado, sem substituto e sem links | 404/410 (redirect em massa para a home vira soft 404) |
| Descontinuado com backlinks ou tráfego | Mantenha a página informativa com alternativas, ou 301 para o equivalente |
| Variações (cor, tamanho) | Uma URL principal com seletor, ou URLs por variação com canonical coerente; no JSON-LD, `ProductGroup` com `hasVariant` e `variesBy` |

## 3. Dados estruturados e feed

- `Product` com `name`, `image` (várias, fundo limpo e contexto), `description`, `sku`, `gtin`
  quando existir, `brand` e `offers` (`price` numérico com ponto, `priceCurrency` ISO 4217,
  `availability` com URL do enum, `priceValidUntil` em promoções).
- Frete e devolução: `shippingDetails` (`OfferShippingDetails`) e `hasMerchantReturnPolicy`
  (`MerchantReturnPolicy`) na oferta, ou a política padrão da loja no Search Console/Merchant Center.
- `aggregateRating`/`review` só com avaliações reais de clientes, visíveis na página.
- **Página, JSON-LD e feed do Merchant Center com o mesmo preço e disponibilidade.** Divergência
  reprova itens nas listagens gratuitas e pagas.
- Listagens gratuitas do Google Shopping (Merchant Center) também alimentam a experiência de compra
  do AI Mode (Shopping Graph). Feed completo e atualizado é parte do SEO de loja.
- `lint_schema.py` confere preço, moeda, disponibilidade e obrigatórios; o Rich Results Test
  confere elegibilidade.

## 4. Conteúdo que vende e ranqueia

- **Categoria** é a página que mais ranqueia em loja: texto curto e útil acima ou abaixo da grade
  (como escolher, diferenças entre tipos), perguntas frequentes reais, links para subcategorias e
  guias.
- **Produto:** descrição própria (a do fabricante está em centenas de lojas), especificações em
  tabela, medidas, compatibilidade, cuidados, o que vem na caixa, prazo de entrega, política de troca,
  fotos e vídeo próprios, perguntas e avaliações de clientes.
- **Guias e comparativos** (pilar 9) para a fase de pesquisa, com links para categorias e produtos.
- Avaliações de produto: o sistema de avaliações do Google premia análise com experiência real
  (uso, prós e contras, comparação), não resumo de especificação.

## 5. Performance

Lista de produtos e página de produto são pesadas: imagens responsivas (`srcset`, AVIF/WebP), a
primeira imagem sem `lazy` e com `fetchpriority="high"`, scripts de terceiros (chat, pixels,
reviews) adiados, filtros sem recarregar a página inteira. Meça com `pagespeed.py` (dados de campo).

## 6. GEO e compra assistida por IA

- Assistentes comparam produtos citando lojas, reviews e fóruns: especificações claras em tabela,
  preço visível, política de troca e prazo explícitos aumentam a chance de citação.
- Compra por agentes é um canal emergente: Universal Commerce Protocol (Google, jan/2026) e o
  checkout dentro do ChatGPT (Agentic Commerce Protocol, OpenAI, set/2025) dependem de feed de
  produto estruturado. Avalie a integração da sua plataforma antes de construir algo próprio.
- Robôs de busca de IA liberados também nas páginas de produto e categoria (`check_agents.py`
  pega WAF bloqueando robôs nessas rotas).

## Checklist de loja
- [ ] Filtros sob controle: só combinações com demanda indexáveis; demais bloqueadas no robots.txt
- [ ] Paginação rastreável com canonical própria; busca interna `noindex`
- [ ] Regra clara para sem estoque × descontinuado; nada de redirect em massa para a home
- [ ] `Product`/`Offer` completos, frete e devolução declarados, preço igual na página e no feed
- [ ] Merchant Center com listagens gratuitas ativas e feed sem reprovações
- [ ] Descrições próprias nos produtos principais; categorias com texto e perguntas reais
- [ ] Core Web Vitals de campo "bons" em categoria e produto
