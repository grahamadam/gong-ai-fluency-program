#!/usr/bin/env python3
"""Page test for the AI Fluency page: the checks the Gong brand check does not make.

usage: python3 -I .github/check-page.py [--root <repo>]
       python3 -I .github/check-page.py --hash-name "<code name>"

It fails (exit 1) on any of these:
  - fonts.googleapis.com, fonts.gstatic.com or "Schibsted" in a published file
  - a code name people must never see, anywhere in the repo: the repo and its page are both public. The names
    are kept here only as sha256 hashes (HIDDEN_NAME_SHA256), so this repo never spells them out, and they match
    the way the brand check's hidden-name rule matches: in any case, as whole words
  - a hidden_names entry in .github/brand-check.json, which stays empty because the repo is public
  - a BN Axel font file anywhere in the repo, or BN Axel named in a published file (it is Gong's licensed
    font, so it never goes in this public repo)
  - index.html without <html data-theme="light"> (the page's one theme), or with more than one h1
  - a stylesheet, icon, font, image or script that index.html loads from another site
  - a src or href that starts with "/", which breaks under the /gong-ai-fluency-program/ subpath
  - a relative src or href in index.html that points at no file
  - a gong-brand.css link whose ?v= is not the layer version in gong-brand/VENDOR.json
Published files are what GitHub Pages serves: the repo without its dot folders and dot files (.git,
.github) and without folders and files whose names start with an underscore. Standard library only.
--hash-name prints the hash to add to HIDDEN_NAME_SHA256 for a new code name.
"""
import argparse
import hashlib
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

TEXT_EXT = {".html", ".htm", ".css", ".js", ".mjs", ".json", ".svg", ".txt", ".md", ".xml", ".webmanifest"}
FONT_EXT = {".woff", ".woff2", ".ttf", ".otf", ".eot"}
BN_AXEL_FILE = re.compile(r"bn[\s_-]*axel|axel[\s_-]*grotesk", re.I)
BN_AXEL_TEXT = re.compile(r"\bBN[\s_-]*Axel\b|\bAxel[\s_-]*Grotesk\b", re.I)
GOOGLE_FONTS = re.compile(r"fonts\.googleapis\.com|fonts\.gstatic\.com|schibsted", re.I)
RESOURCE_TAGS = {"link", "script", "img", "source", "iframe", "video", "audio", "embed", "object", "track", "input"}
URL_ATTRS = {"src", "href", "poster", "data"}

# Code names people must never see, as the sha256 of each name in lower case. This repo is public, so the
# names are never written out here, in .github/brand-check.json or in a commit message. The hashes stop a
# reader from seeing the names; they do not make them secret, since anyone who guesses a name can hash it.
HIDDEN_NAME_SHA256 = frozenset({
    "e2e2381d754d62fea454d4ab11bca6ad8bdf556864cc4e8edceaf6f09c4a68ef",
    "68821c49bdb0a231a5e88739b500907154ee0f91941d0c09d1702fd967b0be8a",
})
# A code name is one to four words of letters and digits, joined by one hyphen, underscore, dot or space.
NAME_SHAPE = re.compile(r"[a-z0-9]+(?:[-_. ][a-z0-9]+){0,3}")
NAME_WORDS = 4
WORD = re.compile(r"[a-z0-9]+")
JOINERS = frozenset("-_. ")


def name_hash(name):
    """The HIDDEN_NAME_SHA256 entry for a code name."""
    low = name.strip().lower()
    if not NAME_SHAPE.fullmatch(low):
        raise ValueError("a code name is one to four words of letters and digits, joined by one hyphen, "
                         "underscore, dot or space")
    return hashlib.sha256(low.encode("utf-8")).hexdigest()


def hidden_hits(line, hashes):
    """The 1-based columns where a code name starts in line. Like the brand check's hidden-name rule, a name
    matches in any case, as whole words: a letter or digit on either side ends the match, and anything else
    (a hyphen, a dot, a slash, a space) bounds it, so a name inside a longer hyphenated name or a host counts."""
    low = line.lower()
    runs = [(m.start(), m.end()) for m in WORD.finditer(low)]
    hits = []
    for i, (start, end) in enumerate(runs):
        for j in range(i, min(i + NAME_WORDS, len(runs))):
            if j > i:
                gap = low[runs[j - 1][1]:runs[j][0]]
                if len(gap) != 1 or gap not in JOINERS:
                    break
                end = runs[j][1]
            if hashlib.sha256(low[start:end].encode("utf-8")).hexdigest() in hashes:
                hits.append(start + 1)
                break
    return hits


def published(root):
    """Every file GitHub Pages publishes from root (a legacy Jekyll build skips dot and underscore names)."""
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if any(part.startswith((".", "_")) for part in rel.parts):
            continue
        if path.is_file():
            yield rel, path


def everything(root):
    """Every file in the repo but .git."""
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if rel.parts and rel.parts[0] == ".git":
            continue
        if path.is_file():
            yield rel, path


def text_of(path):
    """A file's text, or None for a binary file such as a font or an image."""
    data = path.read_bytes()
    if b"\0" in data:
        return None
    return data.decode("utf-8", errors="replace")


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.urls = []  # (line, tag, attr, value)
        self.h1 = 0
        self.html_theme = None
        self.styles = []
        self._in_style = False

    def handle_starttag(self, tag, attrs):
        line = self.getpos()[0]
        values = dict(attrs)
        if tag == "html":
            self.html_theme = values.get("data-theme")
        if tag == "h1":
            self.h1 += 1
        if tag == "style":
            self._in_style = True
        for name, value in attrs:
            if name in URL_ATTRS and value is not None:
                self.urls.append((line, tag, name, value.strip(), values.get("rel", "")))
            if name == "srcset" and value:
                for candidate in value.split(","):
                    first = candidate.strip().split(" ")[0]
                    if first:
                        self.urls.append((line, tag, name, first, values.get("rel", "")))
            if name == "style" and value:
                self.styles.append((line, value))

    handle_startendtag = handle_starttag

    def handle_endtag(self, tag):
        if tag == "style":
            self._in_style = False

    def handle_data(self, data):
        if self._in_style:
            self.styles.append((self.getpos()[0], data))


def check(root, hidden_sha256=HIDDEN_NAME_SHA256):
    problems = []
    config_path = root / ".github" / "brand-check.json"
    if config_path.exists():
        if json.loads(config_path.read_text(encoding="utf-8")).get("hidden_names"):
            problems.append(".github/brand-check.json lists hidden_names; this repo is public, so keep the list "
                            "empty and add each code name to HIDDEN_NAME_SHA256 in .github/check-page.py as a "
                            "hash (--hash-name prints it)")

    for rel, path in published(root):
        if path.suffix.lower() not in TEXT_EXT:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for number, line in enumerate(text.splitlines(), 1):
            if GOOGLE_FONTS.search(line):
                problems.append(f"{rel}:{number} loads or names Google Fonts or Schibsted Grotesk; the page takes its fonts from gong-brand/")
            if BN_AXEL_TEXT.search(line):
                problems.append(f"{rel}:{number} names BN Axel, Gong's licensed font, in a public file")

    for rel, path in everything(root):
        if path.suffix.lower() in FONT_EXT and BN_AXEL_FILE.search(path.name):
            problems.append(f"{rel} is a BN Axel font file; Gong's licensed font never goes in this public repo")
        text = text_of(path)
        if text is None:
            continue
        for number, line in enumerate(text.splitlines(), 1):
            for column in hidden_hits(line, hidden_sha256):
                problems.append(f"{rel}:{number}:{column} names a code name people must never see; this repo and "
                                "its page are public, so take it out")

    index = root / "index.html"
    page = Page()
    page.feed(index.read_text(encoding="utf-8"))
    if page.html_theme != "light":
        problems.append(f"index.html: <html> needs data-theme=\"light\", the page's one theme (found {page.html_theme!r})")
    if page.h1 != 1:
        problems.append(f"index.html: {page.h1} h1 elements; the page has exactly one")

    version = None
    vendor = root / "gong-brand" / "VENDOR.json"
    if vendor.exists():
        version = json.loads(vendor.read_text(encoding="utf-8")).get("layer_version")
    saw_stylesheet = False
    for line, tag, attr, value, rel_attr in page.urls:
        where = f"index.html:{line} <{tag} {attr}=\"{value}\">"
        if not value or value.startswith(("#", "mailto:", "tel:", "data:")):
            continue
        parts = urlsplit(value)
        if parts.scheme or value.startswith("//"):
            if tag in RESOURCE_TAGS:
                problems.append(f"{where} loads from another site; every file the page loads comes from its own site")
            continue
        if value.startswith("/"):
            problems.append(f"{where} starts with '/', which breaks under the /gong-ai-fluency-program/ subpath; use a relative path")
            continue
        target = (index.parent / parts.path).resolve()
        if not parts.path or not target.is_file():
            problems.append(f"{where} points at no file")
        if parts.path == "gong-brand/gong-brand.css":
            saw_stylesheet = True
            query = dict(p.split("=", 1) for p in parts.query.split("&") if "=" in p)
            if version and query.get("v") != version:
                problems.append(f"{where} needs ?v={version}, the vendored layer version, so a cached page never pairs new HTML with an old stylesheet")
    if not saw_stylesheet:
        problems.append("index.html does not link gong-brand/gong-brand.css")

    for line, css in page.styles:
        for m in re.finditer(r"""url\(\s*['"]?([^'")\s]+)|@import\s+['"]([^'"]+)""", css):
            ref = m.group(1) or m.group(2)
            if urlsplit(ref).scheme in ("http", "https") or ref.startswith("//"):
                problems.append(f"index.html:{line} a style loads {ref} from another site")
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    parser.add_argument("--hash-name", metavar="NAME", help="print the HIDDEN_NAME_SHA256 entry for a code name")
    args = parser.parse_args(argv)
    if args.hash_name is not None:
        try:
            print(name_hash(args.hash_name))
        except ValueError as error:
            print(f"check-page: {error}", file=sys.stderr)
            return 2
        return 0
    problems = check(Path(args.root).resolve())
    for problem in problems:
        print(problem)
    print(f"check-page: {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
