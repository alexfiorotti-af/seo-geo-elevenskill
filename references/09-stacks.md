# Implementação por stack

Exemplos mínimos para aplicar os pilares 2 a 8. Troque `https://dominio.com` pelo domínio real e
confira a documentação da versão em uso antes de copiar.

## Next.js (App Router)

### Metadados globais e por página (pilar 8)
```tsx
// app/layout.tsx
import type { Metadata } from 'next';

export const metadata: Metadata = {
  metadataBase: new URL('https://dominio.com'),
  title: { default: 'Marca: o que faz em Cidade', template: '%s | Marca' },
  description: 'Descrição da home…',
  alternates: { canonical: '/' },
  openGraph: { type: 'website', siteName: 'Marca', locale: 'pt_BR', images: ['/og/home.jpg'] },
  twitter: { card: 'summary_large_image' },
  robots: { index: true, follow: true, 'max-image-preview': 'large' },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="pt-BR"><body>{children}</body></html>;
}
```
```tsx
// app/servicos/[slug]/page.tsx
export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const s = await getServico(slug);              // sua fonte de dados
  return {
    title: s.seoTitle,                            // vira "s.seoTitle | Marca" pelo template
    description: s.seoDescription,
    alternates: { canonical: `/servicos/${slug}/` },
    openGraph: { title: s.seoTitle, description: s.seoDescription, images: [s.ogImage] },
  };
}
```
Com `title.template`, o title da página não deve repetir a marca. Para `params` síncrono em
versões antigas do Next.js, remova o `await`.

### robots e sitemap (pilar 2)
```ts
// app/robots.ts
import type { MetadataRoute } from 'next';
export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      { userAgent: '*', allow: '/', disallow: ['/api/', '/obrigado/'] },
      { userAgent: ['GPTBot', 'ClaudeBot', 'CCBot', 'Google-Extended'], disallow: '/' }, // só se o dono optar por bloquear treino
    ],
    sitemap: 'https://dominio.com/sitemap.xml',
  };
}
```
```ts
// app/sitemap.ts
import type { MetadataRoute } from 'next';
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const servicos = await listarServicos();
  return [
    { url: 'https://dominio.com/', lastModified: new Date('2026-11-01') },
    ...servicos.map((s) => ({ url: `https://dominio.com/servicos/${s.slug}/`, lastModified: s.atualizadoEm })),
  ];
}
```
Use a data real de alteração (`atualizadoEm`), não `new Date()` em toda requisição.

### JSON-LD (pilar 6) e renderização (pilar 4)
```tsx
<script
  type="application/ld+json"
  dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd).replace(/</g, '\\u003c') }}
/>
```
- Páginas públicas como Server Components com `generateStaticParams` (SSG) ou revalidação (ISR).
- `next/image` com carregamento prioritário na imagem do LCP (`priority` ou a propriedade
  equivalente da sua versão; o nome mudou entre versões, confira a documentação) e `sizes` sempre.
- `trailingSlash: true` em `next.config` se a convenção do site usar barra final; redirects 301 em `redirects()`.
- Página 404: `app/not-found.tsx` (retorna status 404 real).

## Astro
- Saída estática por padrão (ótimo para os pilares 4 e 5).
- `site: 'https://dominio.com'` no `astro.config.mjs` + integração `@astrojs/sitemap`.
- Componente `<SEOHead>` recebendo `title`, `description`, `canonical`, `ogImage`, `jsonLd` e usado
  em todos os layouts. `trailingSlash: 'always'` ou `'never'`, de forma consistente.
- `public/robots.txt` a partir de `templates/robots.txt`.

## HTML estático na Vercel
```json
// vercel.json
{
  "cleanUrls": true,
  "trailingSlash": false,
  "redirects": [
    { "source": "/pagina-antiga", "destination": "/pagina-nova", "permanent": true }
  ],
  "headers": [
    { "source": "/assets/(.*)", "headers": [{ "key": "Cache-Control", "value": "public, max-age=31536000, immutable" }] },
    { "source": "/obrigado", "headers": [{ "key": "X-Robots-Tag", "value": "noindex" }] }
  ]
}
```
- `permanent: true` gera 308 (equivalente ao 301 para buscadores).
- Previews da Vercel recebem `X-Robots-Tag: noindex` automaticamente; confira se o domínio de
  produção não herdou nada parecido.
- `404.html` na raiz para status 404 real.
- `<head>` de cada página a partir de `templates/head.html`; sitemap gerado por script no build.

## WordPress
- Um único plugin de SEO (Yoast, Rank Math, SEOPress ou similar) para title/description/canonical,
  sitemap e schema básico. Desative recursos duplicados do tema.
- Configure: base de URL (`/%postname%/`), arquivos de tag/autor/data sem valor → `noindex`,
  anexos redirecionados ao post.
- Cache de página + CDN + otimização de imagem (AVIF/WebP) para os Core Web Vitals; limite plugins
  que injetam JS em todas as páginas.
- IndexNow: plugins de SEO populares ou o plugin oficial IndexNow.
- Ao migrar de WordPress para outra stack, siga a seção "Migração" do pilar 11.
