"""Tests for .github/check-page.py, run in CI: python3 -I -B -m unittest discover -s .github/tests

Each test copies the repo (without .git) to a temporary folder, plants one problem and runs the page test on
the copy. The code-name tests use a made-up name, because this repo is public and never spells out a real one.
"""
import hashlib
import importlib.util
import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("check_page", REPO / ".github" / "check-page.py")
check_page = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check_page)

MADE_UP = "zebra-console"
MADE_UP_HASHES = frozenset({hashlib.sha256(MADE_UP.encode("utf-8")).hexdigest()})


def _ignore(directory, names):
    """Leave out .git, bytecode and these tests, which spell out the made-up name."""
    skip = {".git", "__pycache__"}
    if Path(directory).resolve() == (REPO / ".github").resolve():
        skip.add("tests")
    return [name for name in names if name in skip]


class PageTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "repo"
        shutil.copytree(REPO, self.root, ignore=_ignore)
        self.index = self.root / "index.html"

    def tearDown(self):
        self._tmp.cleanup()

    def problems(self, hashes=MADE_UP_HASHES):
        return check_page.check(self.root, hashes)

    def edit(self, path, old, new):
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text, f"{path.name} no longer holds the text this test edits")
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def assertOneProblem(self, needle):
        found = self.problems()
        self.assertTrue(any(needle in p for p in found), f"no problem mentions {needle!r}: {found}")


class TheRepoPasses(PageTest):
    def test_the_repo_as_committed_passes(self):
        self.assertEqual(check_page.check(self.root), [])

    def test_the_repo_passes_the_made_up_name_too(self):
        self.assertEqual(self.problems(), [])


class CodeNames(PageTest):
    def test_a_code_name_in_the_page_text_fails(self):
        self.edit(self.index, "The program practices exactly what it teaches.",
                  "The program practices exactly what it teaches. Zebra-Console runs it.")
        found = self.problems()
        self.assertEqual(len(found), 1, found)
        self.assertTrue(found[0].startswith("index.html:"), found)
        self.assertNotIn("ebra", found[0].lower(), "the message must not repeat the name")

    def test_a_code_name_anywhere_in_the_repo_fails(self):
        workflow = self.root / ".github" / "workflows" / "brand-check.yml"
        workflow.write_text(workflow.read_text(encoding="utf-8") + "# zebra-console\n", encoding="utf-8")
        (self.root / "notes").mkdir()
        (self.root / "notes" / "todo.txt").write_text("ask about ZEBRA-CONSOLE\n", encoding="utf-8")
        found = self.problems()
        self.assertEqual(len(found), 2, found)
        self.assertTrue(any(p.startswith(".github/workflows/brand-check.yml:") for p in found), found)
        self.assertTrue(any(p.startswith("notes/todo.txt:1:") for p in found), found)

    def test_whole_word_matches(self):
        for text in ["Zebra-Console", "ZEBRA-CONSOLE", "https://zebra-console.gong.io/x", "the zebra-console-uat service",
                     "my-zebra-console", "(zebra-console)", "zebra-console_db"]:
            with self.subTest(text=text):
                self.assertEqual(len(check_page.hidden_hits(text, MADE_UP_HASHES)), 1)

    def test_near_misses_pass(self):
        for text in ["zebra-consoles", "zebraconsole", "zebra--console", "xzebra-console", "zebra console", "zebra",
                     "console", "zebra-console2"]:
            with self.subTest(text=text):
                self.assertEqual(check_page.hidden_hits(text, MADE_UP_HASHES), [])

    def test_hidden_names_in_the_config_fail_without_repeating_them(self):
        config = self.root / ".github" / "brand-check.json"
        data = json.loads(config.read_text(encoding="utf-8"))
        data["hidden_names"] = ["Quokka"]
        config.write_text(json.dumps(data), encoding="utf-8")
        found = self.problems()
        self.assertEqual(len(found), 1, found)
        self.assertIn("hidden_names", found[0])
        self.assertNotIn("quokka", found[0].lower())

    def test_the_hash_list_holds_only_hashes(self):
        self.assertTrue(check_page.HIDDEN_NAME_SHA256)
        for entry in check_page.HIDDEN_NAME_SHA256:
            self.assertRegex(entry, r"\A[0-9a-f]{64}\Z")

    def test_hash_name_prints_the_entry(self):
        self.assertEqual(check_page.name_hash("Zebra-Console"), next(iter(MADE_UP_HASHES)))
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(check_page.main(["--hash-name", "Zebra-Console"]), 0)
        self.assertEqual(out.getvalue().strip(), next(iter(MADE_UP_HASHES)))
        with self.assertRaises(ValueError):
            check_page.name_hash("not/a name")


class PageRules(PageTest):
    def test_google_fonts_fail(self):
        self.edit(self.index, "<head>",
                  '<head>\n<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter">')
        self.assertOneProblem("Google Fonts")
        self.assertOneProblem("loads from another site")

    def test_a_bn_axel_file_fails(self):
        (self.root / "gong-brand" / "fonts" / "bn-axel-grotesk-bold.woff").write_bytes(b"wOFF\0")
        self.assertOneProblem("BN Axel font file")

    def test_another_theme_fails(self):
        self.edit(self.index, '<html lang="en" data-theme="light">', '<html lang="en" data-theme="dark">')
        self.assertOneProblem("data-theme")

    def test_a_second_h1_fails(self):
        self.edit(self.index, "</h1>", "</h1>\n<h1>Second</h1>")
        self.assertOneProblem("2 h1 elements")

    def test_a_root_path_fails(self):
        self.edit(self.index, 'href="gong-brand/gong-brand.css?v=', 'href="/gong-brand/gong-brand.css?v=')
        self.assertOneProblem("starts with '/'")

    def test_a_missing_file_fails(self):
        self.edit(self.index, 'src="gong-brand/logos/gong-logo-dark-ink.png"', 'src="gong-brand/logos/missing.png"')
        self.assertOneProblem("points at no file")

    def test_a_stale_version_query_fails(self):
        version = json.loads((self.root / "gong-brand" / "VENDOR.json").read_text(encoding="utf-8"))["layer_version"]
        self.edit(self.index, f"gong-brand.css?v={version}", "gong-brand.css?v=0.0.1")
        self.assertOneProblem(f"needs ?v={version}")


if __name__ == "__main__":
    unittest.main()
