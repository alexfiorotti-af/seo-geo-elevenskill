# Back-end, parte 2: performance e dados estruturados (pilares 5 e 6)

---

## Pilar 5. Performance e servidor

### Metas (Core Web Vitals, percentil 75 de usuários reais, celular e desktop avaliados separadamente)

| Métrica | O que mede | Bom | Precisa melhorar | Ruim |
|---|---|---|---|---|
| **LCP** (Largest Contentful Paint) | Quando o maior elemento visível aparece | ≤ 2,5 s | 2,5 a 4,0 s | > 4,0 s |
| **INP** (Interaction to Next Paint) | Tempo de resposta às interações (substituiu o FID em mar/2024) | ≤ 200 ms | 200 a 500 ms | > 500 ms |
| **CLS** (Cumulative Layout Shift) | Quanto o layout "pula" | ≤ 0,1 | 0,1 a 0,25 | > 0,25 |

Diagnósticos (não são Core Web Vitals, mas explicam o LCP): **TTFB ≤ 0,8 s**, **FCP ≤ 1,8 s**.

O que vale para ranqueamento é o dado de campo (CrUX, relatório de Core Web Vitals do Search
Console), não a nota do Lighthouse. Core Web Vitals funcionam como desempate entre páginas de
relevância parecida; não salvam conteúdo fraco, mas um site lento perde visitas e conversões.
Estabilidade de layout também é auditada pelo Lighthouse na categoria de agentes (pilar 7).

### Back-end primeiro (onde está a maior parte do ganho)
1. **TTFB:** HTML estático ou em cache na borda (CDN). SSR com cache por rota. Banco/API lentos
   não podem estar no caminho crítico da primeira resposta.
2. **CDN** com HTTP/2 ou HTTP/3 e TLS 1.3. Servidor perto do público (região São Paulo para Brasil).
3. **Compressão** Brotli (ou gzip) para HTML, CSS, JS, SVG e JSON.
4. **Cache-Control:** arquivos com hash no nome → `public, max-age=31536000, immutable`;
   HTML → cache curto na borda com revalidação.
5. **Imagens servidas no formato e tamanho certos:** AVIF/WebP, `srcset`/`sizes`, redimensionadas no
   servidor ou pela plataforma de imagens.
6. **Redirects mínimos** na entrada (cada salto custa uma ida e volta).
7. **Scripts de terceiros** (chat, pixels, mapas) carregados depois da interação ou via gerenciador
   de tags com gatilho adiado. São a principal causa de INP ruim.

### Front-end (complementa)
- Imagem do LCP: sem lazy-load, com `fetchpriority="high"`, e pré-carregada se vier do CSS.
- `width`/`height` (ou `aspect-ratio`) em toda imagem, vídeo e iframe; espaço reservado para anúncios e banners de cookie → CLS.
- Fontes: `font-display: swap` ou `optional`, poucas variações, auto-hospedadas, pré-carregar a principal.
- CSS crítico inline, resto adiado. JS dividido por rota; nada de bundle único gigante.
- Handlers de interação leves; tarefas longas quebradas (`scheduler.yield()` ou `setTimeout`) → INP.

### Orçamento de performance sugerido (página de serviço, celular)
| Recurso | Limite |
|---|---|
| HTML | ≤ 50 KB comprimido |
| CSS total | ≤ 60 KB comprimido |
| JS total | ≤ 150 KB comprimido (≤ 70 KB em landing page) |
| Imagem do LCP | ≤ 120 KB |
| Requisições de terceiros antes da interação | 0 a 2 |

---

## Pilar 6. Dados estruturados (JSON-LD) e grafo de entidade

### Para que servem hoje
1. **Entendimento:** dizem sem ambiguidade quem é a entidade (empresa, pessoa, produto), onde fica,
   o que oferece e como as páginas se relacionam.
2. **Resultados enriquecidos:** breadcrumbs, produto (preço, disponibilidade, avaliações reais),
   artigo, vídeo, evento, vagas etc.
3. **Consistência de entidade:** o mesmo nome, endereço, telefone e perfis sociais no site, no
   Perfil da Empresa no Google, no Bing Places e nos diretórios. IAs cruzam essas fontes.

O Google afirma que **não há marcação especial para os recursos de IA**. Use os tipos clássicos,
bem feitos. Não exagere achando que mais schema = mais IA.

### Regras
- Formato **JSON-LD** em `<script type="application/ld+json">`, entregue no HTML do servidor.
- **Descreve só o que está visível** na página. Preço, nota, horário e endereço iguais aos do texto.
- **Não marque avaliações do próprio negócio sobre si mesmo** em `LocalBusiness`/`Organization`
  (o Google não exibe e pode tratar como manipulação). Avaliações só se forem de clientes reais e
  estiverem na página.
- Use `@id` estáveis para montar um grafo: a Organization é declarada uma vez
  (`https://dominio/#organization`) e referenciada pelas demais páginas.
- Valide no Rich Results Test e no validador do schema.org antes de publicar.
- Tipos que o Google deixou de exibir (FAQ restrito a sites governamentais e de saúde desde 2023;
  HowTo removido; e, em jun/2025, Book Actions, Course Info, ClaimReview, Estimated Salary,
  Learning Video, Special Announcement e Vehicle Listing) podem permanecer sem prejuízo, mas não
  gaste esforço novo neles esperando resultado enriquecido.

### Qual tipo usar em cada página
| Página | Tipos |
|---|---|
| Todas | `WebSite` (só na home basta), `Organization` ou subtipo (referenciado por `@id`), `BreadcrumbList` (exceto home) |
| Home de negócio local | `LocalBusiness` com o subtipo mais específico (`Dentist`, `BeautySalon`, `LegalService`, `VeterinaryCare`...) |
| Página de serviço | `Service` com `provider` → `@id` da organização, `areaServed`, `offers` se houver preço público |
| Produto | `Product` + `Offer` (preço, moeda, disponibilidade) + `AggregateRating`/`Review` só se reais |
| Artigo/blog | `Article` ou `BlogPosting` com `author` (`Person` com página de autor), `datePublished`, `dateModified`, `image` |
| Sobre/autor | `Person` ou `AboutPage`, com `sameAs` para perfis oficiais |
| Perguntas frequentes | `FAQPage` só para conteúdo de perguntas reais; não esperar resultado enriquecido (ver acima) |
| Evento | `Event` com data, local, status |
| Vídeo | `VideoObject` com `thumbnailUrl`, `uploadDate`, `duration` |

Modelos: `templates/jsonld/`. Substitua todos os valores; não publique campo de exemplo.

### Grafo mínimo (padrão `@graph`)
```json
{
  "@context": "https://schema.org",
  "@graph": [
    { "@type": "Organization", "@id": "https://dominio/#organization", "name": "...", "url": "https://dominio/", "logo": "...", "sameAs": ["..."] },
    { "@type": "WebSite", "@id": "https://dominio/#website", "url": "https://dominio/", "name": "...", "publisher": { "@id": "https://dominio/#organization" }, "inLanguage": "pt-BR" },
    { "@type": "WebPage", "@id": "https://dominio/servicos/x/#webpage", "url": "https://dominio/servicos/x/", "isPartOf": { "@id": "https://dominio/#website" }, "about": { "@id": "https://dominio/#organization" } }
  ]
}
```

### Comércio e agentes
- E-commerce: mantenha o feed do Merchant Center e o `Product` da página sincronizados (preço,
  estoque). O Google recomenda feeds e o Perfil da Empresa atualizados para as experiências de IA.
- Negócio local: Perfil da Empresa no Google e Bing Places completos e com o mesmo NAP do site.
- Padrões de agentes (UCP para checkout em `/.well-known/ucp`, WebMCP para ferramentas no navegador)
  são opcionais e emergentes. Só implemente quando houver demanda clara (loja, agendamento).

---

## Checklist dos pilares 5 e 6
- [ ] LCP ≤ 2,5 s, INP ≤ 200 ms, CLS ≤ 0,1 no campo (p75, celular)
- [ ] TTFB ≤ 0,8 s; HTML em cache na borda; Brotli; HTTP/2+
- [ ] Imagens AVIF/WebP com dimensões; LCP sem lazy-load e com prioridade alta
- [ ] Terceiros adiados; JS dentro do orçamento
- [ ] JSON-LD no HTML do servidor, válido, coerente com o conteúdo visível
- [ ] Organization/LocalBusiness com `@id` único, referenciado nas páginas
- [ ] Nenhuma avaliação ou dado inventado; nenhuma autoavaliação marcada
- [ ] NAP idêntico no site, Perfil da Empresa, Bing Places e diretórios
