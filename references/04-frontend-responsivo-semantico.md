# Front-end, parte 1: responsividade, HTML semântico e site amigável a agentes (pilar 7)

O Google indexa a versão de celular (mobile-first indexing). Agentes de IA leem o site por três
vias: captura de tela, HTML bruto e a **árvore de acessibilidade**. O que é bom para leitor de tela
é bom para robô, e vice-versa.

## Responsividade (mobile-first)
- `<meta name="viewport" content="width=device-width, initial-scale=1">` em todas as páginas.
  Não bloqueie zoom (`user-scalable=no`, `maximum-scale=1`).
- **Mesmo conteúdo no celular e no desktop.** Texto, links, imagens e JSON-LD que existem só no
  desktop não são indexados.
- Layout fluido (grid/flex, `clamp()` para tipografia), sem rolagem horizontal em 360 px.
- Áreas de toque ≥ 24×24 px (ideal 44×44) com espaço entre elas.
- Fonte base ≥ 16 px; contraste de texto ≥ 4,5:1.
- Sem intersticial que cubra o conteúdo ao chegar da busca (aviso de cookies discreto é aceitável).
- Imagens com `srcset`/`sizes`; a versão móvel não pode ser a do desktop reduzida por CSS.

## HTML semântico
```html
<html lang="pt-BR">
<body>
  <header> … <nav aria-label="Principal"> <a href="/servicos/">Serviços</a> … </nav> </header>
  <main>
    <nav aria-label="Trilha"> breadcrumbs com <a href> </nav>
    <article>
      <h1>Um único H1 que diz do que a página trata</h1>
      <p>Resposta direta em 1 a 3 frases.</p>
      <section> <h2>Subtema</h2> … <h3>Detalhe</h3> … </section>
    </article>
  </main>
  <footer> NAP, links institucionais </footer>
</body>
</html>
```
- **Um H1 por página**, coerente com o title. Hierarquia sem pular níveis (H2 → H3, não H2 → H4).
- Títulos de seção descritivos ("Quanto custa uma limpeza de pele", não "Saiba mais").
- Links com `<a href="...">` e texto-âncora descritivo. Nada de "clique aqui".
- Botões com `<button>`; não `<div onclick>`.
- Listas com `<ul>/<ol>`, tabelas de dados com `<table>`, `<th>` e `<caption>`: são os formatos
  que motores de resposta mais extraem.
- `<time datetime="2026-11-03">` em datas de publicação/atualização.
- Imagens com `alt` que descreve o conteúdo (vazio, `alt=""`, só para imagem decorativa). Nome de
  arquivo descritivo (`limpeza-de-pele-antes-depois.webp`).
- Texto em imagem não é lido como texto. Títulos e preços sempre em HTML.

## Site amigável a agentes (diretrizes do web.dev, 2026)
- Elementos interativos com nome acessível (texto, `aria-label` ou `<label for>` ligado ao campo).
- Formulários com `<label>` associado, `type` correto (`email`, `tel`), `autocomplete`, mensagens de erro em texto.
- Layout estável: sem elementos que mudam de lugar no hover ou ao carregar (o CLS também é auditado
  pelo Lighthouse na categoria "Agentic Browsing").
- `cursor: pointer` em clicáveis; foco visível no teclado.
- Não esconda conteúdo interativo da árvore de acessibilidade (`aria-hidden` em elemento focável é erro).
- Opcional e emergente: WebMCP (ferramentas declaradas para agentes, em origin trial no Chrome) para
  formulários de agendamento ou orçamento. Registre só ações que o site realmente executa.

## Checklist do pilar 7
- [ ] Viewport correto, sem bloqueio de zoom, sem rolagem horizontal em 360 px
- [ ] Mesmo conteúdo e mesmos dados estruturados no celular e no desktop
- [ ] `lang` correto, um H1, hierarquia de headings sem saltos
- [ ] Links `<a href>` com âncora descritiva; botões `<button>`
- [ ] Imagens com `alt` útil, dimensões e nome de arquivo descritivo
- [ ] Formulários com `<label>`, `type` e `autocomplete`
- [ ] Contraste ≥ 4,5:1, alvos de toque adequados, foco visível
- [ ] Lighthouse: Acessibilidade ≥ 90; Agentic Browsing sem falhas em nomes, rótulos e estabilidade
