# Sites em vários idiomas ou países (pilares 1, 3 e 9)

Para quem atende mais de um idioma ou país (ex.: empresa brasileira com operação nos EUA, site em
pt-BR, en-US e es). Complementa a seção "Internacionalização" de `02-backend-rastreio-indexacao.md`.

## 1. Estrutura de URL

| Opção | Exemplo | Prós | Contras |
|---|---|---|---|
| Subpasta | `dominio.com/en/` | Herda a autoridade do domínio; uma só infraestrutura | Sinal geográfico mais fraco que ccTLD |
| Subdomínio | `en.dominio.com` | Separação técnica | Autoridade mais dividida; mais manutenção |
| Domínio por país (ccTLD) | `dominio.com.br`, `dominio.com` | Sinal geográfico forte; confiança local | Autoridade separada por domínio; custo maior |
| Parâmetro | `?lang=en` | Nenhum relevante | Não recomendado |

Padrão recomendado para PME: **subpastas** por idioma (`/en/`, `/es/`) ou por idioma-país
(`/en-us/`) quando preço, moeda ou oferta mudam por país.

Nunca: trocar idioma por cookie, cabeçalho `Accept-Language` ou IP **na mesma URL**, nem
redirecionar automaticamente pelo IP (o Googlebot rastreia principalmente dos EUA e veria só uma
versão). Mostre um aviso/seletor de idioma e deixe a pessoa escolher.

## 2. hreflang

- Declare no `<head>` (`<link rel="alternate" hreflang="en-us" href="...">`), no cabeçalho HTTP
  (útil para PDF) **ou** no sitemap (`xhtml:link`). Escolha um método; misturar aumenta o risco de
  contradição.
- Cada versão lista **todas** as versões, incluindo ela mesma (autorreferência), com URL absoluta.
- **Reciprocidade:** se A aponta para B, B precisa apontar para A. Par sem retorno é ignorado.
- `x-default` para o seletor de idioma ou a versão padrão.
- Códigos: idioma ISO 639-1, região ISO 3166-1 opcional. `pt-BR`, `pt-PT`, `en-US`, `en-GB`
  (nunca `en-UK`), `es-419` (América Latina), `ja` (nunca `jp`), `zh-Hans`/`zh-Hant` para escrita.
  Região sozinha (`-BR`) não vale.
- Cada URL do hreflang responde **200, é indexável e canônica de si mesma**. Apontar para URL com
  redirect, `noindex` ou canonical para outra quebra o conjunto.
- **Canonical de cada idioma aponta para ele mesmo**, nunca para a versão original em outro idioma.
- Mesmo idioma com conteúdo igual para vários países (ex.: um só texto em espanhol): use `es` e
  não crie cópias por país sem diferença real.
- `scripts/crawl_site.py` verifica reciprocidade, autorreferência, códigos inválidos, alvos não
  indexáveis e falta de `x-default` em todo o site.

Exemplo no sitemap:
```xml
<url>
  <loc>https://dominio.com/servicos/</loc>
  <xhtml:link rel="alternate" hreflang="pt-BR" href="https://dominio.com/servicos/"/>
  <xhtml:link rel="alternate" hreflang="en-US" href="https://dominio.com/en/services/"/>
  <xhtml:link rel="alternate" hreflang="x-default" href="https://dominio.com/servicos/"/>
</url>
```
(o `<urlset>` precisa declarar `xmlns:xhtml="http://www.w3.org/1999/xhtml"`; repita o bloco para
cada URL do conjunto).

## 3. Outros sinais

- `<html lang="pt-BR">` em cada versão. O Bing recomenda declarar o idioma também em
  `<html lang>` e na meta `content-language`; o Google não usa a meta, mas ela não atrapalha.
- O relatório de segmentação internacional do Search Console foi descontinuado em 2022: o país vem
  de ccTLD, hreflang, conteúdo local (moeda, telefone, endereço) e links locais.
- Traduza **tudo**: title, description, slug, `alt`, JSON-LD (`inLanguage`), menus, formulários e
  mensagens de erro. Metadados no idioma errado são causa comum de títulos reescritos.
- Moeda, unidades, formato de data e telefone do país. Preço em BRL na página em inglês para os EUA
  sinaliza a versão errada.

## 4. Conteúdo: tradução não é cópia

- Tradução automática sem revisão, publicada em massa, entra em "conteúdo em escala" se não
  agregar valor. Revise com falante nativo, adapte exemplos, termos de busca e provas locais.
- Pesquisa de palavras-chave por idioma e país (pilar 9): o termo traduzido nem sempre é o termo
  buscado ("limpeza de pele" × "facial" nos EUA).
- Autoridade é por mercado: links e menções de sites do país da versão (pilar 10b, roteiros BR e EUA).

## 5. GEO multilíngue

Assistentes respondem no idioma da pergunta e tendem a citar fontes nesse idioma. Uma versão
traduzida bem estruturada (respostas diretas, dados locais, entidade consistente) é o que permite
ser citado no outro mercado. `sameAs` e o mesmo `@id` de organização em todas as versões mantêm
uma única entidade.

## Checklist internacional
- [ ] URL própria por idioma/país; sem redirect por IP nem troca por cookie
- [ ] hreflang completo, recíproco, com autorreferência e `x-default` (`crawl_site.py` sem erros)
- [ ] Canonical de cada versão para ela mesma; todas 200 e indexáveis
- [ ] `lang` correto e tudo traduzido (metadados, slug, JSON-LD, interface)
- [ ] Palavras-chave pesquisadas por mercado; revisão nativa
- [ ] Moeda, telefone, endereço e provas do país de cada versão
