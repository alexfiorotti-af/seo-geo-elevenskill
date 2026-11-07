"""Testes de crawl_site.py e verify_backlinks.py com um servidor HTTP local (sem internet).

Rodar a partir da raiz do repositório:
  python3 -m unittest discover -s tests -v
"""
import functools
import http.server
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
SITE = os.path.join(ROOT, "tests", "fixtures", "site")
sys.path.insert(0, SCRIPTS)

import crawl_site  # noqa: E402
import verify_backlinks  # noqa: E402
from _seo_common import read_csv  # noqa: E402


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):  # silencia o log do servidor nos testes
        pass


class LocalSite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.root = os.path.join(cls.tmp, "site")
        shutil.copytree(SITE, cls.root)
        handler = functools.partial(_QuietHandler, directory=cls.root)
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        with open(os.path.join(cls.root, "robots.txt"), "w", encoding="utf-8") as fh:
            fh.write(f"User-agent: *\nDisallow: /privado/\n\nSitemap: {cls.base}/sitemap.xml\n")
        urls = ["/", "/servicos/", "/servicos", "/servicos/limpeza/", "/orfa/", "/obrigado/"]
        body = "".join(f"<url><loc>{cls.base}{u}</loc><lastmod>2026-11-01</lastmod></url>" for u in urls)
        with open(os.path.join(cls.root, "sitemap.xml"), "w", encoding="utf-8") as fh:
            fh.write(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{body}</urlset>')

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def write_csv(self, name, header, rows):
        path = os.path.join(self.tmp, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(header + "\n" + "\n".join(rows) + "\n")
        return path

    def run_script(self, *args):
        proc = subprocess.run([sys.executable, *args], capture_output=True, text=True)
        return proc.returncode, proc.stdout, proc.stderr


class TestCrawlSite(LocalSite):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.result = crawl_site.crawl(cls.base + "/", max_pages=100, delay=0, follow_params=False)
        cls.text = json.dumps(cls.result["achados"], ensure_ascii=False)

    def finding(self, level, words):
        for f in self.result["achados"]:
            if f["nivel"] == level and words in f["mensagem"]:
                return f
        self.fail(f"achado {level} com '{words}' não encontrado em: {self.text}")

    def test_broken_internal_link(self):
        f = self.finding("ERRO", "quebrado")
        self.assertTrue(any("/nao-existe/" in i and "404" in i for i in f["itens"]))

    def test_link_to_redirect(self):
        f = self.finding("AVISO", "redireciona")
        self.assertTrue(any(i.startswith(f"{self.base}/servicos →") for i in f["itens"]))

    def test_orphans(self):
        f = self.finding("AVISO", "órfã")
        self.assertIn(f"{self.base}/orfa/", f["itens"])
        self.assertNotIn(f"{self.base}/servicos/", f["itens"])

    def test_sitemap_inconsistencies(self):
        f = self.finding("ERRO", "sitemap")
        joined = " ".join(f["itens"])
        self.assertIn("/obrigado/: tem noindex", joined)
        self.assertIn("/servicos: redireciona", joined)

    def test_depth_and_duplicate_titles(self):
        deep = self.finding("AVISO", "cliques")
        self.assertTrue(any("/fundo/" in i for i in deep["itens"]))
        dup = self.finding("AVISO", "title")
        self.assertTrue(any("/blog/" in i and "/servicos/" in i for i in dup["itens"]))

    def test_outside_sitemap_robots_and_params(self):
        missing = self.finding("INFO", "fora do sitemap")
        self.assertIn(f"{self.base}/blog/", missing["itens"])
        self.assertIn(f"{self.base}/privado/", self.finding("INFO", "robots.txt")["itens"])
        self.assertIn(f"{self.base}/busca/?q=pele", self.finding("INFO", "parâmetros")["itens"])
        self.assertNotIn(f"{self.base}/privado/", [p["url"] for p in self.result["paginas"]])

    def test_external_and_mailto_ignored(self):
        urls = [p["url"] for p in self.result["paginas"]]
        self.assertFalse(any("externo.test" in u or u.startswith("mailto") for u in urls))

    def test_cli(self):
        code, out, _ = self.run_script(os.path.join(SCRIPTS, "crawl_site.py"), self.base + "/", "--atraso", "0")
        self.assertEqual(code, 1, out)
        self.assertIn("## Achados", out)

    def test_max_pages_limit(self):
        r = crawl_site.crawl(self.base + "/", max_pages=2, delay=0, follow_params=False)
        self.assertTrue(r["limite_atingido"])
        self.assertLessEqual(len([p for p in r["paginas"] if p["profundidade"] >= 0]), 2)


class TestVerifyBacklinks(LocalSite):
    def test_sources(self):
        csv_path = self.write_csv("links.csv", "Página com link;Último rastreamento", [
            f"{self.base}/parceiros/a.html;2026-10-01",
            f"{self.base}/parceiros/b.html;2026-10-01",
            f"{self.base}/parceiros/c.html;2026-10-01",
            f"{self.base}/parceiros/d.html;2026-10-01",
            f"{self.base}/parceiros/sumiu.html;2026-10-01",
            f"{self.base}/parceiros/a.html;2026-10-02",
        ])
        rows = read_csv(csv_path)
        r = verify_backlinks.check_sources(rows, "Página com link", "clinica-aurora.test", ["Clínica Aurora"], 50, 0)
        by = {x["origem"].rsplit("/", 1)[-1]: x for x in r["resultados"]}
        self.assertEqual(r["verificadas"], 5)                      # duplicada removida
        self.assertEqual(by["a.html"]["situacao"], "ativo")
        self.assertEqual(by["a.html"]["links"][0]["tipo_ancora"], "marca")
        self.assertEqual(by["a.html"]["links"][0]["rel"], "follow")
        self.assertEqual(by["b.html"]["links"][0]["rel"], "nofollow")
        self.assertEqual(len(by["b.html"]["links"]), 1)            # link interno do parceiro ignorado
        self.assertEqual(by["b.html"]["links"][0]["tipo_ancora"], "descritiva/palavra-chave")
        self.assertEqual(by["c.html"]["situacao"], "perdido")
        self.assertEqual(by["d.html"]["links"][0]["rel"], "sponsored")
        self.assertEqual(by["d.html"]["links"][0]["tipo_ancora"], "imagem: marca")
        self.assertTrue(by["d.html"]["noindex"])
        self.assertEqual(by["sumiu.html"]["situacao"], "origem fora do ar")
        self.assertEqual((r["ativas"], r["perdidas"], r["fora_do_ar"]), (3, 1, 1))

    def test_anchor_concentration_warning(self):
        links = "".join('<a href="https://clinica-aurora.test/">limpeza de pele barata</a>' for _ in range(1))
        rows = []
        for i in range(6):
            name = f"spam{i}.html"
            with open(os.path.join(self.root, "parceiros", name), "w", encoding="utf-8") as fh:
                fh.write(f"<html><body>{links}</body></html>")
            rows.append({"source": f"{self.base}/parceiros/{name}"})
        r = verify_backlinks.check_sources(rows, "source", "clinica-aurora.test", [], 50, 0)
        self.assertTrue(any("âncora" in a["mensagem"] for a in r["achados"]))

    def test_targets(self):
        csv_path = self.write_csv("paginas.csv", "Páginas mais linkadas,Links recebidos,Sites com links", [
            f"{self.base}/,120,30",
            f"{self.base}/servicos,15,8",
            f"{self.base}/nao-existe/,40,12",
        ])
        rows = read_csv(csv_path)
        r = verify_backlinks.check_targets(rows, "Páginas mais linkadas", None, 0)
        by = {e["url"].replace(self.base, ""): e for e in r["resultados"]}
        self.assertEqual(by["/"]["situacao"], "ok")
        self.assertEqual(by["/servicos"]["situacao"], "ok")       # 301 único é aceitável
        self.assertIn("301", by["/servicos"]["nota"])
        self.assertEqual(by["/nao-existe/"]["situacao"], "ERRO")
        self.assertEqual(by["/nao-existe/"]["sites"], 12)
        self.assertEqual(r["resultados"][0]["url"], f"{self.base}/")  # ordenado por sites
        self.assertEqual(r["fora_do_ar"], 1)

    def test_cli_column_detection_and_exit_codes(self):
        csv_path = self.write_csv("ahrefs.csv", "Referring page URL,Anchor", [f"{self.base}/parceiros/c.html,x"])
        code, out, _ = self.run_script(os.path.join(SCRIPTS, "verify_backlinks.py"), "origens", csv_path,
                                       "--dominio", "clinica-aurora.test", "--atraso", "0")
        self.assertEqual(code, 1, out)
        self.assertIn("Links perdidos", out)
        code, _, err = self.run_script(os.path.join(SCRIPTS, "verify_backlinks.py"), "origens", csv_path)
        self.assertEqual(code, 2)
        self.assertIn("--dominio", err)
        ok_csv = self.write_csv("ok.csv", "url", [f"{self.base}/"])
        code, out, _ = self.run_script(os.path.join(SCRIPTS, "verify_backlinks.py"), "destinos", ok_csv,
                                       "--atraso", "0", "--format", "json")
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads(out)["fora_do_ar"], 0)


if __name__ == "__main__":
    unittest.main()
