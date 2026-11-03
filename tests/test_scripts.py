"""Testes dos scripts da skill (só biblioteca padrão, sem rede).

Rodar a partir da raiz do repositório:
  python3 -m unittest discover -s tests -v
"""
import json
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
FIX = os.path.join(ROOT, "tests", "fixtures")
sys.path.insert(0, SCRIPTS)

import audit_page  # noqa: E402
import check_robots  # noqa: E402
import lint_meta  # noqa: E402
import validate_sitemap  # noqa: E402
from _seo_common import find_placeholders, normalize, pixel_width  # noqa: E402


def run(script, *args, env=None):
    proc = subprocess.run([sys.executable, os.path.join(SCRIPTS, script), *args],
                          capture_output=True, text=True, env=env)
    return proc.returncode, proc.stdout, proc.stderr


def read(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as fh:
        return fh.read()


class TestCommon(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(normalize("  Estética   FACIAL "), "estetica facial")

    def test_pixel_width_grows(self):
        self.assertLess(pixel_width("iiii"), pixel_width("MMMM"))
        self.assertGreater(pixel_width("x" * 70), 580)

    def test_placeholders(self):
        self.assertTrue(find_placeholders("https://dominio.com/x"))
        self.assertFalse(find_placeholders("https://clinica-aurora.test/"))


class TestAuditPage(unittest.TestCase):
    def test_good_page_has_no_findings(self):
        r = audit_page.audit(read("pagina_boa.html"), "https://clinica-aurora.test/servicos/limpeza-de-pele/")
        self.assertEqual(r["erros"], 0)
        self.assertEqual(r["achados"], [])
        self.assertIn("Service", r["jsonld_types"])
        self.assertEqual(r["h1"], ["Limpeza de pele profunda em Vitória"])

    def test_csr_page_flags_core_problems(self):
        r = audit_page.audit(read("pagina_csr.html"), "https://clinica-aurora.test/app/")
        msgs = " ".join(f["mensagem"] for f in r["achados"])
        for expected in ("noindex", "JSON-LD inválido", "texto de modelo", "viewport", "Sem H1", "JavaScript"):
            self.assertIn(expected, msgs)
        self.assertGreater(r["erros"], 3)

    def test_x_robots_header_and_nosnippet(self):
        html = read("pagina_boa.html")
        r = audit_page.audit(html, "https://clinica-aurora.test/servicos/limpeza-de-pele/",
                             status=200, headers={"x-robots-tag": "nosnippet"})
        self.assertTrue(any("nosnippet" in f["mensagem"] for f in r["achados"]))

    def test_error_status_short_circuits(self):
        r = audit_page.audit("<html></html>", "https://x.test/", status=404)
        self.assertEqual(r["erros"], 1)
        self.assertEqual(len(r["achados"]), 2)

    def test_cli_exit_codes(self):
        code, out, _ = run("audit_page.py", os.path.join(FIX, "pagina_boa.html"),
                           "--base-url", "https://clinica-aurora.test/servicos/limpeza-de-pele/")
        self.assertEqual(code, 0, out)
        code, out, _ = run("audit_page.py", os.path.join(FIX, "pagina_csr.html"), "--format", "json")
        self.assertEqual(code, 1)
        self.assertGreater(json.loads(out)["erros"], 0)


class TestRobots(unittest.TestCase):
    def setUp(self):
        self.groups, self.sitemaps = check_robots.parse_robots(read("robots_exemplo.txt"))

    def allowed(self, bot, path):
        return check_robots.is_allowed(check_robots.select_group(self.groups, bot), path)[0]

    def test_sitemap_parsed(self):
        self.assertEqual(self.sitemaps, ["https://clinica-aurora.test/sitemap.xml"])

    def test_general_rules(self):
        self.assertTrue(self.allowed("Googlebot", "/"))
        self.assertFalse(self.allowed("Googlebot", "/busca?q=x"))
        self.assertTrue(self.allowed("Googlebot", "/busca/ajuda"))      # Allow com $ mais longo vence
        self.assertFalse(self.allowed("Googlebot", "/busca/ajuda/x"))   # $ ancora o fim
        self.assertFalse(self.allowed("Googlebot", "/servicos/?utm_source=ig"))

    def test_grouped_user_agents(self):
        self.assertFalse(self.allowed("GPTBot", "/"))
        self.assertFalse(self.allowed("ClaudeBot", "/blog/"))
        self.assertTrue(self.allowed("Claude-SearchBot", "/blog/"))     # não herda o grupo do ClaudeBot

    def test_specific_group_replaces_star(self):
        self.assertTrue(self.allowed("PerplexityBot", "/busca"))        # grupo próprio ignora o '*'
        self.assertFalse(self.allowed("PerplexityBot", "/privado/x"))
        self.assertTrue(self.allowed("PerplexityBot", "/privado/publico/x"))

    def test_cli_flags_blocked_search_bots(self):
        code, out, _ = run("check_robots.py", os.path.join(FIX, "robots_bloqueia_busca.txt"))
        self.assertEqual(code, 1)
        self.assertIn("Robôs de BUSCA bloqueados", out)
        code, _, _ = run("check_robots.py", os.path.join(FIX, "robots_exemplo.txt"))
        self.assertEqual(code, 0)

    def test_template_robots_keeps_search_open(self):
        code, out, _ = run("check_robots.py", os.path.join(ROOT, "templates", "robots.txt"),
                           "--path", "/", "--path", "/servicos/x/")
        self.assertEqual(code, 0, out)


class TestSitemap(unittest.TestCase):
    def test_good(self):
        with open(os.path.join(FIX, "sitemap_bom.xml"), "rb") as fh:
            r = validate_sitemap.validate(fh.read(), "sitemap_bom.xml", "https://clinica-aurora.test")
        self.assertEqual(r["erros"], 0)
        self.assertEqual(r["total"], 3)

    def test_bad(self):
        with open(os.path.join(FIX, "sitemap_ruim.xml"), "rb") as fh:
            r = validate_sitemap.validate(fh.read(), "sitemap_ruim.xml", "https://clinica-aurora.test")
        msgs = " ".join(a["mensagem"] for a in r["achados"])
        for expected in ("relativa", "outro host", "duplicada", "fragmento", "W3C", "futuro"):
            self.assertIn(expected, msgs)

    def test_invalid_xml(self):
        r = validate_sitemap.validate(b"<urlset><url>", "x.xml", None)
        self.assertEqual(r["erros"], 1)


class TestLintMeta(unittest.TestCase):
    def test_batch(self):
        rows = lint_meta.read_csv(os.path.join(FIX, "meta_lote.csv"))
        res = {r["url"]: r for r in lint_meta.lint(rows, 580)}
        ok = res["/servicos/limpeza-de-pele/"]["achados"]
        self.assertEqual([a for a in ok if a["nivel"] != "INFO"], [])
        dup = " ".join(a["mensagem"] for a in res["/servicos/botox/"]["achados"])
        self.assertIn("duplicado", dup)
        guia = " ".join(a["mensagem"] for a in res["/blog/guia/"]["achados"])
        for expected in ("corte", "stuffing", "2023", "modelo"):
            self.assertIn(expected, guia)

    def test_keyword_match_ignores_accents(self):
        self.assertTrue(lint_meta.keyword_in("estética facial", "Estetica Facial em Vitória"))
        self.assertFalse(lint_meta.keyword_in("peeling químico", "Serviços"))

    def test_template_is_clean(self):
        code, out, _ = run("lint_meta.py", os.path.join(ROOT, "templates", "mapa-de-palavras-chave.csv"))
        self.assertEqual(code, 0, out)


class TestIndexNow(unittest.TestCase):
    def test_requires_key(self):
        env = {k: v for k, v in os.environ.items() if k != "INDEXNOW_KEY"}
        code, _, err = run("indexnow_submit.py", "--host", "x.test", os.devnull, env=env)
        self.assertEqual(code, 2)
        self.assertIn("INDEXNOW_KEY", err)

    def test_dry_run_masks_key_and_filters_hosts(self):
        urls = os.path.join(FIX, "_urls.txt")
        with open(urls, "w", encoding="utf-8") as fh:
            fh.write("https://clinica-aurora.test/a/\nhttps://outro.test/b/\n# comentario\n")
        try:
            env = dict(os.environ, INDEXNOW_KEY="abcd1234efgh5678")
            code, out, _ = run("indexnow_submit.py", "--host", "clinica-aurora.test", urls, "--dry-run", env=env)
        finally:
            os.remove(urls)
        self.assertEqual(code, 0)
        self.assertNotIn("abcd1234efgh5678", out)
        self.assertIn("https://clinica-aurora.test/a/", out)
        self.assertNotIn("outro.test", out)


class TestTemplates(unittest.TestCase):
    def test_jsonld_templates_are_valid_json(self):
        folder = os.path.join(ROOT, "templates", "jsonld")
        for name in os.listdir(folder):
            if name.endswith(".json"):
                with open(os.path.join(folder, name), encoding="utf-8") as fh:
                    json.load(fh)


if __name__ == "__main__":
    unittest.main()
