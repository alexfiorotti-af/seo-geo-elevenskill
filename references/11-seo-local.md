# SEO local e GEO local (pilares 6, 9 e 10 aplicados a negócios com endereço ou área de atendimento)

Para clínica, escritório, loja, restaurante ou prestador que atende uma região. Leia junto com
`10-autoridade-links-mencoes.md` (roteiros local BR e EUA) e `03-backend-performance-dados-estruturados.md`.

## Como o Google ordena resultados locais

O Google declara três fatores: **relevância** (o perfil e o site correspondem à busca),
**distância** (de quem busca ou do local citado na busca) e **proeminência** (quanto o negócio é
conhecido: avaliações, links, menções, artigos, posição na busca orgânica). Distância não se
otimiza; relevância e proeminência sim. Pagar não melhora o ranking local orgânico.

As respostas de IA para "melhor X em Cidade" cruzam as mesmas fontes: Perfil da Empresa,
avaliações, diretórios, imprensa local, fóruns e o próprio site. Entidade consistente em todas
elas é o que faz a IA ter segurança para citar.

## 1. Perfis de empresa (o "site" que aparece no mapa)

| Plataforma | O que alimenta |
|---|---|
| Perfil da Empresa no Google | Pacote local, Google Maps, AI Overviews/AI Mode para buscas locais |
| Apple Business (substituiu o Apple Business Connect em 14/04/2026) | Apple Maps, Siri, Spotlight |
| Bing Places | Bing, Copilot e parceiros que usam dados do Bing |

Regras que valem para todos:
- **Nome real**, igual ao da fachada e do material impresso. Acrescentar cidade ou serviço ao nome
  ("Clínica Aurora Limpeza de Pele Vitória") viola as diretrizes do Google e pode suspender o perfil.
- Um perfil por endereço físico com atendimento. Escritório virtual, coworking sem equipe ou caixa
  postal não qualificam.
- **Área de atendimento** (quem vai até o cliente): esconda o endereço e informe cidades/bairros.
- Categoria principal a mais específica possível; secundárias só se forem serviços reais.
- Horário, feriados, telefone, site (com UTM: `?utm_source=google&utm_medium=organic&utm_campaign=perfil`),
  fotos reais recentes, serviços/produtos com descrição e preço quando público.
- Link do site aponta para a página da unidade (empresas com várias) ou para a home.

## 2. NAP: nome, endereço, telefone idênticos em toda parte

- Defina a forma oficial uma vez (ex.: "Rua das Flores, 100, Sala 2, Centro, Vitória, ES, 29000-000";
  "+55 27 3000-0000") e use a mesma no site, no JSON-LD, nos perfis e nos diretórios.
- Variações de abreviação ("R." × "Rua") não são o problema; telefone antigo, endereço antigo e
  nome diferente são. Mudou de endereço? Atualize tudo no mesmo mês.
- `scripts/check_local.py` compara o NAP do site (texto visível, `tel:`, JSON-LD) com a referência
  e com uma planilha de citações (`templates/citacoes-locais.csv`).

## 3. Citações (diretórios)

Qualidade vence quantidade. Prioridade:
1. Os três perfis acima.
2. Diretórios e associações do nicho (conselhos profissionais, associações comerciais, guias do setor).
3. Diretórios da cidade com tráfego real e páginas indexadas.
4. Plataformas de avaliação relevantes ao setor (no Brasil, por exemplo, Reclame Aqui para varejo e
   serviços; nos EUA, Yelp, BBB, Nextdoor, Angi conforme o nicho).

Evite pacotes de "500 diretórios": a maioria não é indexada e alguns são redes de spam.

## 4. Avaliações

- Peça a **todos** os clientes, no momento certo (logo após o serviço), com link direto.
- Proibido: filtrar quem pode avaliar (review gating), oferecer desconto ou brinde em troca,
  avaliações de funcionários ou compradas. No Google isso viola a política de conteúdo; nos EUA a
  regra da FTC de 2024 proíbe avaliações falsas e supressão de avaliações negativas.
- Responda todas, inclusive as negativas, com fatos e sem dados pessoais do cliente (LGPD).
- No site: mostre avaliações reais com link para a fonte. Não marque avaliações do próprio negócio
  em `LocalBusiness` (o Google não exibe; ver pilar 6).

## 5. Site

- **Página por unidade** (endereço real): nome, NAP, mapa incorporado, como chegar, estacionamento,
  horário, equipe da unidade, fotos do local, serviços disponíveis, avaliações daquela unidade.
- **Páginas de cidade/bairro** só quando houver conteúdo genuinamente diferente (atendimento,
  preço, prazo, casos locais). Trocar só o nome da cidade é página-porta (`lint_meta.py` acusa
  metadados em série).
- `LocalBusiness` com o subtipo mais específico, `geo`, `openingHoursSpecification`, `areaServed`,
  `sameAs` com o link do Perfil da Empresa; `@id` estável por unidade.
- Telefone clicável (`tel:`) e, no Brasil, link de WhatsApp (`https://wa.me/55...`) visíveis no celular.
- Conteúdo local que só você tem: perguntas reais dos clientes da região, preços médios, prazos,
  bairros atendidos, parceiros locais, eventos e casos.

## 6. Autoridade local (pilar 10b)

Imprensa e blogs da cidade, patrocínio de eventos e times locais (com link quando houver página
real de patrocinadores), parcerias com negócios complementares, palestras, dados locais
originais ("preço médio de X em Vitória em 2026"). Menção sem link também conta para a entidade.

## 7. Medição

- Perfil da Empresa: buscas, visualizações no mapa, cliques no site, ligações, rotas.
- GA4 com a UTM do perfil separa o tráfego do mapa do orgânico comum.
- Ranking local varia por ponto do mapa: use grade de pontos (ferramentas de "local rank grid") em
  vez de uma posição única.
- Amostragem de IA com perguntas locais ("dentista aberto sábado em Vitória") em `templates/amostragem-ia.csv`.

## Checklist local
- [ ] Perfis no Google, Apple e Bing verificados, nome real, categoria certa, horário e fotos
- [ ] NAP idêntico no site, JSON-LD, perfis e diretórios principais (`check_local.py`)
- [ ] Página por unidade com conteúdo próprio; nada de página-porta por cidade
- [ ] `LocalBusiness` (subtipo) com `geo`, horário, `areaServed`, `sameAs`
- [ ] Processo contínuo de pedido e resposta de avaliações, sem incentivo nem filtro
- [ ] Citações de qualidade do nicho e da cidade; menções na imprensa local
- [ ] UTM no link do perfil e medição de ligações/rotas
