# Back-end, parte 1: arquitetura, rastreio, indexação e renderização (pilares 1 a 4)

Estes quatro pilares decidem se a página **existe** para buscadores e IAs. Nada no front-end
compensa um erro aqui. Em auditoria, qualquer achado destes pilares tem prioridade máxima.

---

## Pilar 1. Arquitetura de URLs e de informação

### Princípios
- **Uma intenção de busca = uma URL.** Duas páginas disputando a mesma intenção se canibalizam.
- **Profundidade rasa:** páginas importantes a no máximo 3 cliques da home.
- **Hierarquia que espelha o negócio:** `/servicos/<servico>/`, `/blog/<artigo>/`,
  `/<cidade>/<servico>/` só quando houver conteúdo local real (ver pilar 9).
- **Toda página indexável recebe ao menos um link interno** de página relevante (sem páginas órfãs).

### Padrão de URL
- Minúsculas, palavras separadas por hífen, sem acento nem caractere especial:
  `/servicos/limpeza-de-pele/` (não `/Servicos/Limpeza_de_Pele` nem `/servicos/limpeza-de-pele-em-vitoria-es-melhor-preco`).
- Curta e descritiva; palavra principal presente, sem repetir.
- Sem datas no slug de conteúdo perene (impede atualizar sem mudar a URL).
- Sem IDs de sessão ou parâmetros de rastreamento em links internos (UTM só em links externos de campanha).
- Escolha **uma** convenção de barra final e de `www`/sem `www` e redirecione o resto com 301.
- URL é permanente. Mudou? Redirect 301 da antiga para a nova, atualize links internos e sitemap.

### Modelo de árvore para site de serviço local
```
/                         home: entidade, serviços principais, prova, região, CTA
/servicos/                hub de serviços (links para todos)
/servicos/<servico>/      uma página forte por serviço (intenção transacional)
/sobre/                   quem é, equipe, credenciais (sinal de autoria/confiança)
/contato/                 NAP (nome, endereço, telefone) idêntico ao Perfil da Empresa
/blog/                    hub de conteúdo
/blog/<artigo>/           dúvidas reais do público (intenção informacional), ligadas aos serviços
/perguntas-frequentes/    só se as perguntas forem reais e não repetirem as páginas de serviço
/politica-de-privacidade/ obrigatória (LGPD); noindex opcional, mas mantenha rastreável
```

---

## Pilar 2. Rastreabilidade

### robots.txt
- Fica em `https://dominio/robots.txt`, um por host (subdomínio tem o seu). Resposta 200 em texto.
- **Bloquear no robots.txt não tira a página do índice**; só impede o rastreio. Para tirar do
  índice use `noindex` (e deixe rastrear, senão o robô não vê o `noindex`).
- Nunca bloqueie CSS, JS ou imagens necessários para renderizar a página.
- Declare os sitemaps: `Sitemap: https://dominio/sitemap.xml` (URL absoluta).
- Erro 5xx no robots.txt faz o Google pausar o rastreio do site. Monitore.

### Política para crawlers de IA (decisão do dono do site)

Separe **busca** (aparecer e ser citado em respostas) de **treino** (seu conteúdo alimentar
modelos). O padrão recomendado para negócios que querem clientes:

| Robô | Empresa | Função | Padrão recomendado |
|---|---|---|---|
| Googlebot | Google | Busca, AI Overviews, AI Mode | **Permitir** |
| Google-Extended | Google | Treino do Gemini e grounding no app Gemini/Vertex (não afeta Search) | Decisão do dono |
| Bingbot | Microsoft | Busca e Copilot | **Permitir** |
| OAI-SearchBot | OpenAI | Resultados do ChatGPT Search | **Permitir** |
| ChatGPT-User | OpenAI | Acesso quando o usuário pede (pode não seguir robots.txt) | Permitir |
| GPTBot | OpenAI | Treino de modelos | Decisão do dono |
| Claude-SearchBot | Anthropic | Índice de busca do Claude | **Permitir** |
| Claude-User | Anthropic | Acesso quando o usuário pede | Permitir |
| ClaudeBot | Anthropic | Treino de modelos | Decisão do dono |
| PerplexityBot | Perplexity | Índice de busca (não é treino) | **Permitir** |
| Perplexity-User | Perplexity | Acesso sob demanda (em geral ignora robots.txt) | Permitir |
| Applebot | Apple | Siri, Spotlight | Permitir |
| Applebot-Extended | Apple | Treino (não afeta busca da Apple) | Decisão do dono |
| Meta-ExternalAgent | Meta | Treino e recursos de IA da Meta | Decisão do dono |
| CCBot | Common Crawl | Base aberta usada por muitos treinos | Decisão do dono |

Modelo pronto: `templates/robots.txt`. Mudanças em robots.txt levam até ~24 h para valer
para OpenAI e Perplexity. Verifique com `scripts/check_robots.py`.

**Sair dos recursos de IA do Google** (decisão rara para quem vende serviço): o
`Google-Extended` não faz isso. As opções são o controle "Search generative AI" no Search
Console (disponível para todos os sites desde 31/08/2026) ou `nosnippet`/`max-snippet:0`, que
também removem o snippet da busca comum.

### Sitemaps XML
- Só URLs **canônicas, indexáveis e com status 200**. Nada de redirect, 404, `noindex` ou URL com parâmetro.
- `lastmod` em ISO 8601 (`2026-11-03` ou `2026-11-03T14:00:00-03:00`) e **verdadeiro**:
  o Google usa `lastmod` quando ele é consistentemente confiável. `changefreq` e `priority` são ignorados pelo Google.
- Limite: 50.000 URLs ou 50 MB (descompactado) por arquivo; acima disso, índice de sitemaps.
- Separe por tipo em sites maiores (`sitemap-paginas.xml`, `sitemap-blog.xml`) para diagnosticar indexação por seção.
- Gere automaticamente a partir das rotas/CMS. Sitemap escrito à mão desatualiza.
- Envie no Search Console e no Bing Webmaster Tools. Valide com `scripts/validate_sitemap.py`.

### IndexNow
- Protocolo aberto: o site avisa que uma URL foi criada, alterada ou removida, e Bing, Yandex,
  Naver, Seznam e Yep recebem na hora (o aviso é compartilhado entre eles). O Google não participa.
- Como implementar:
  1. Gere uma chave (8 a 128 caracteres: letras, números, hífen).
  2. Publique o arquivo `https://dominio/<chave>.txt` contendo só a chave.
  3. A cada publicação/alteração, envie as URLs (`scripts/indexnow_submit.py` ou integração da plataforma).
- A chave é pública por natureza (está no arquivo), mas **guarde-a em variável de ambiente** no
  projeto para não espalhá-la em código e facilitar trocar.
- Envie só URLs que mudaram de fato. Reenviar tudo sem mudança é desperdício e pode ser ignorado.

### llms.txt (opcional, prioridade baixa)
- Arquivo Markdown em `/llms.txt` com um resumo do site e links para as páginas principais.
- O Google declarou que **não usa** e que ele não ajuda nem prejudica o ranqueamento. Alguns agentes
  e a categoria experimental "Agentic Browsing" do Lighthouse verificam a presença.
- Faça só depois que os pilares 1 a 6 estiverem resolvidos. Modelo: `templates/llms.txt`.
- O conteúdo deve ser o mesmo que está no site. Nada de instruções para IAs nem afirmações que a página não sustenta.

### Orçamento de rastreio (sites grandes, acima de ~10 mil URLs ou atualização diária)
- Elimine armadilhas: filtros e ordenações que geram URLs infinitas, calendários, busca interna indexável.
- Bloqueie no robots.txt combinações de parâmetros sem valor de busca.
- Mantenha o servidor rápido: o Google reduz o ritmo de rastreio quando o servidor fica lento ou responde 5xx/429.
- Logs do servidor mostram onde os robôs gastam tempo (pilar 11).

---

## Pilar 3. Indexação

### Status HTTP corretos
| Situação | Resposta |
|---|---|
| Página existe | 200 |
| Mudou de endereço para sempre | 301 (ou 308) direto para o destino final, **sem cadeia** |
| Mudança temporária (manutenção, teste) | 302/307 |
| Não existe mais e não tem substituta | 404 ou 410 |
| Página de "não encontrado" | **status 404 de verdade** (soft 404, página de erro com status 200, é erro comum em SPA) |
| Servidor indisponível temporariamente | 503 com `Retry-After` |

- Não redirecione todas as páginas removidas para a home: o Google trata como soft 404.
- Redirecione `http→https` e a variante de host (`www`) com 301, em um único salto.

### Canonical
- Toda página indexável tem `<link rel="canonical" href="URL-absoluta-de-si-mesma">`.
- Variações (parâmetros de rastreamento, ordenação, versão de impressão) apontam o canonical para a principal.
- O canonical precisa ser coerente com: sitemap, links internos, hreflang e redirects. Sinais
  contraditórios fazem o Google escolher outra URL.
- Canonical é sugestão, não ordem. Conteúdo muito diferente entre página e canonical é ignorado.
- Nunca aponte canonical de todas as páginas paginadas para a página 1: cada página da paginação é canônica de si mesma.

### noindex
- `<meta name="robots" content="noindex">` ou cabeçalho `X-Robots-Tag: noindex` (útil para PDF e arquivos).
- Use em: resultados de busca interna, páginas de obrigado, carrinho, área logada, filtros sem valor.
- Não combine `noindex` com bloqueio no robots.txt (o robô não verá o `noindex`).
- Ambientes de homologação: proteja com senha/autenticação. `noindex` sozinho deixa vazar.

### Internacionalização (hreflang)
- Para o mesmo conteúdo em idiomas/regiões diferentes: `pt-BR`, `en-US`, `es` etc.
- Cada versão lista **todas** as versões, incluindo ela mesma, e as declarações são recíprocas.
- Inclua `x-default` para a página de seleção ou versão padrão.
- Use URLs separadas por idioma (`/en/`, subdomínio ou domínio). Nunca troque idioma por cookie ou IP na mesma URL.
- `<html lang="pt-BR">` em todas as páginas.

### Conteúdo duplicado
- Consolide páginas quase iguais (301 + mescla do melhor conteúdo).
- Paginação com links rastreáveis (`<a href>`), não só botão "carregar mais" em JavaScript.
- Descrições de produto copiadas do fabricante: reescreva as dos itens principais.

---

## Pilar 4. Renderização

### Regra de ouro
**O conteúdo principal, os links internos, o title, a meta description, o canonical e o JSON-LD
precisam estar no HTML que o servidor entrega**, sem depender de JavaScript no navegador.

Por quê: o Googlebot renderiza JavaScript (com atraso e custo), mas a maioria dos crawlers de IA
(OpenAI, Anthropic, Perplexity e outros) lê só o HTML bruto. Uma SPA que monta o texto no cliente
aparece vazia para eles. O Google também diz que processa JS "a menos que bloqueado"; não conte
com isso para o essencial.

### Escolha da estratégia
| Estratégia | Quando usar | Observação |
|---|---|---|
| **SSG** (geração estática) | Sites institucionais, landing pages, blogs | Melhor custo/benefício; HTML pronto na CDN |
| **ISR** / revalidação | Catálogos e blogs que mudam com frequência | Estático com atualização periódica |
| **SSR** (renderização no servidor) | Conteúdo personalizado ou muito dinâmico | Cuidar do TTFB (pilar 5) |
| **CSR** (só no cliente) | Áreas logadas e painéis | **Nunca** para página que precisa ranquear |

### Teste rápido
```bash
curl -sL -A "Mozilla/5.0 (compatible; OAI-SearchBot/1.3)" https://dominio/pagina/ | grep -i "<h1"
```
Se o H1 e o texto principal não aparecem no HTML bruto, a página está invisível para IAs.
`scripts/audit_page.py` faz essa leitura sem executar JavaScript, exatamente como esses robôs.

### Armadilhas comuns
- Links feitos com `onclick` ou `<div>` em vez de `<a href>`: robôs não seguem.
- Conteúdo em abas/accordions carregado só após clique (via fetch): não é indexado. Conteúdo
  presente no HTML e apenas oculto visualmente por CSS é indexado normalmente.
- Lazy-load de texto ou de imagens acima da dobra.
- Rotas com `#` (hash routing): a parte após `#` não é URL indexável.
- `<title>` e meta tags alterados só no cliente (o HTML inicial chega genérico).
- Popups intersticiais cobrindo o conteúdo no celular.

---

## Checklist dos pilares 1 a 4
- [ ] Árvore de URLs definida, uma intenção por URL, nenhuma página indexável órfã
- [ ] Convenção única de host, protocolo e barra final, com 301 de um salto
- [ ] robots.txt 200, declara sitemap, não bloqueia recursos de renderização
- [ ] Política de crawlers de IA decidida e aplicada (busca liberada)
- [ ] Sitemap automático, só URLs canônicas 200, `lastmod` real, enviado ao GSC e Bing WMT
- [ ] IndexNow configurado com chave em variável de ambiente
- [ ] 404 real para página inexistente; sem soft 404; sem cadeias de redirect
- [ ] Canonical absoluto e coerente com sitemap, links e hreflang
- [ ] `noindex` nas páginas sem valor de busca; homologação protegida por senha
- [ ] `lang` e hreflang corretos quando houver mais de um idioma
- [ ] HTML do servidor contém conteúdo, links, metadados e JSON-LD (teste sem JS)
