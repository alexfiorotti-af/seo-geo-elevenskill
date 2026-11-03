# Modelos de JSON-LD

| Arquivo | Página |
|---|---|
| `home-localbusiness.json` | Home de negócio local (troque `BeautySalon` pelo subtipo certo de `LocalBusiness`) |
| `organization.json` | Home de empresa sem atendimento local |
| `service.json` | Página de serviço (inclui `BreadcrumbList`) |
| `article.json` | Artigo de blog com autor (`Person`) |
| `product.json` | Produto com oferta |
| `faqpage.json` | Perguntas frequentes reais (o Google exibe resultado enriquecido só para sites governamentais e de saúde) |

Regras: valores reais e visíveis na página; `@id` estáveis (`https://dominio/#organization`);
remova campos que não se aplicam em vez de deixá-los com texto de exemplo; valide no
Rich Results Test e em validator.schema.org; o `scripts/audit_page.py` acusa placeholders esquecidos.
