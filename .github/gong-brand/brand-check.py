#!/usr/bin/env python3
"""Gong brand check: the drift and rules check apps run in CI.

usage:
  python3 brand-check.py --root <repo> [--config <repo>/brand-check.json] [--new-only]
                         [--baseline-ref <file> | --baseline-ref git:<ref>]
                         [--update-baseline [--allow-raise]]

The config (JSON) names the vendored layer folder, the source globs to scan, the files to skip,
the app's theme names and the baseline file. See brand-check.example.json. Keys:
  layer                the vendored layer folder, such as client/public/gong-brand (null: none yet)
  scan, skip           globs of the files to check and the files to leave out (** spans folders)
  themes               the app's theme names; pair-contrast checks each one
  display_selectors    regexes for selectors and elements that hold BN Axel display text
  baseline             the baseline file, next to the config
  theme_files          globs of the files that may define layer token names, such as a Girly Pop theme
  flavour              [{"glob", "rules", "reason"}]: findings kept on purpose ("rules" left out: all rules)
  allowed_identifiers  ["name"] or [{"name", "glob"}]: identifiers people never see that env-name lets through
  acronyms             words people type in capitals on purpose, added to the built-in list
  names                product, team and people names typed in Title Case, which title-case-heading ignores
  hidden_names         code names people must never see, such as a project's internal name; they match in any
                       case, as whole words

Rules (rule id, severity):
  layer-intact         error  the vendored layer matches VERSION.json (and VENDOR.json when present), holds no
                              extra files, and inlined <style> or <script> copies match their fingerprint
  tools-intact         error  this check matches the TOOLS.json written next to it by generate.py --tools
  baseline-raised      error  the committed baseline holds more than the --baseline-ref reference
  retired-value        error  retired palette values and Poppins, anywhere in scanned sources
  font-family          error  font families other than the four brand typefaces and fallbacks: font-family,
                              the font shorthand, custom properties used as fonts (any name), SVG font-family
                              attributes and Google Fonts links or @imports (only Inter, Inter Tight, IBM Plex Mono);
                              Inter Variable and Inter Tight Variable pass, and BN Axel fails in the public profile
  raw-color            error  hex, rgb() or hsl() colour literals in app styles, var() hex fallbacks included
  token-redefined      error  an app style defines a layer token name (or the layer's own --gb- names)
                              outside theme_files
  theme-os             error  any use of prefers-color-scheme (a favicon swap counts too)
  theme-default        error  a theme default other than light
  theme-unknown        error  a theme name the config does not list for this app
  uppercase            error  capitals by text-transform outside BN Axel display text
  letter-spacing       warn   letter-spacing above 0.02em outside display text
  middle-dot           error  the middle dot in text people see
  env-name             error  'uat', '-uat', 'UAT' or 'run.app' in text or links people see (server-only strings
                              pass: an environment variable's id, database or project fallback, OAuth return addresses)
  hidden-name          error  a config hidden_names entry, in any case, in text, links or attributes people see
  card-shadow          warn   an elevation shadow on anything but a floating layer (dialog, drawer, menu,
                              popover, toast and the like, or a class the same file places with position fixed
                              or absolute and a z-index, or gives a ::backdrop, unless it names a control or card)
  gradient-fill        error  a linear-, radial- or conic-gradient that blends colours; var(--gradient-*) glows
                              and hard-stop shapes (a select caret, stripes, a pie) pass
  accent-bar           error  a border of 2px or more on one side of a box, or an inset shadow bar, in a
                              colour that is not neutral, in CSS or a JS style object. The quote's 4px Lavendar
                              rule, a 2px edge on a selected or current item (the tab underline), focus styles,
                              a link's bottom underline and an empty element drawn as a connector line pass.
  focus-removed        error  outline none or 0 with no replacement focus style for that element (a script focus
                              target such as a main, status or live region may drop it on :focus)
  control-shape        warn   corners under 16px on buttons, fields, tags, chips and badges (pills in the
                              layer) and under 12px on multi-line fields (radius-2xl in the layer); a button that
                              is a row or card, or sits in a nav, menu, tree, list, tab row or sidebar, and a
                              chip drawn as an icon square pass
  graphic-text         error  Teal, Pink or Blue as a text colour, outside BN Axel display text and icons
  emoji-icon           error  emoji or Unicode pictographs used as icons (warn in content files such as .md);
                              arrows and the multiplication sign pass in running text, not alone in a button or
                              link; RegExp sources are code
  small-text           error  font-size under 12px (px, pt and rem at 16px; em and % are skipped), except glyphs
                              such as carets and icons
  typed-caps           error  two or more capital words, or one with a number (STEP 1), typed in text people
                              see: HTML and JSX text, markup written in JS strings, and the attributes people
                              read (warn for one word of 4 letters or more alone); acronyms, a capital word the
                              app never writes in lowercase, code and BN Axel display elements pass
  color-mix            error  color-mix() makes colours outside the system
  logo-filter          error  a CSS filter on a logo, lockup, wordmark or burst image, on an image in a brand,
                              masthead or header, or read from a custom property named for a logo
  runtime-origin-link  warn   share or copy links built from location.origin or window.location
  display-face-case    warn   BN Axel (a display font variable counts when it holds BN Axel) on a rule with no
                              capitals and no display class, or on an eyebrow
  text-opacity         warn   opacity below 1 on a rule that sets text (glyphs, decoration and elements the markup
                              marks aria-hidden pass)
  title-case-heading   warn   an h1 to h6 typed in Title Case (three or more capitalised words; Gong's and Google
                              Cloud's product names pass)
  pair-contrast        error  a rule that sets both its text colour and its background below 4.5:1, or 3:1 for
                              text of 24px or 18.66px at 600 or more, in any of the config's themes
  flavour-marker       warn   a gb-flavour marker with no reason, which does not count

Baseline. --update-baseline writes today's findings the first time. After that it only lowers counts and
drops fixed keys (a key is the file, the rule and the finding's key); it refuses to raise a count or add a
key, prints what would rise and exits 1, unless --allow-raise is passed. --baseline-ref <file> or
--baseline-ref git:<ref> (the baseline file at that commit, read with git show) compares with a reference:
an error above the reference count fails as a new error, and a committed baseline that holds more than
the reference fails as baseline-raised. Warnings never fail. layer-intact, tools-intact and
baseline-raised are never baselined.

Flavour. A comment "gb-flavour: <reason>" on a finding's line, on a line of its own just before it, or as
the first comment inside or just before a CSS rule keeps the finding as flavour (CSS, HTML, JS and JSX
comments); so do the config's flavour entries. Kept findings are listed with their reason, never fail and
are never baselined, and the summary lists each reason once. A marker with no reason does not count.

Display text is a rule that sets BN Axel or a display font variable (--font-display, --<prefix>-font-display
or --display), a display_selectors match, the layer's BN Axel classes (gb-hero-h1, gb-accent-*,
gb-stat__value), or a class the app's own CSS sets in the display face. Eyebrows (eyebrow, kicker and overline
classes) are never display text, as the system says. When the vendored layer (or the copied check) is the
public profile there is no BN Axel, so no text is display text and BN Axel itself is a font-family finding.
Token values come from the vendored layer's gong-brand.tokens.css, else from a verified pasted copy of a layer
sheet in a page, else from the tokens.json generate.py --tools copies next to this file; a third theme such as
Girly Pop reads the token values its theme rules set.

Output: one line per finding (file:line rule severity: message), then a summary. Exit 0 when there is no
new error, 1 when there is one (or a refused raise), 2 when the check cannot run (a bad config or
reference). Standard library only, Python 3.9 or later.

Where the rules come from: Light by default, a saved pick kept, nothing following the computer's own
setting, White navigation in Light and Midnight in Dark, logos swapped by file and never recoloured, no
environment or code names where people see them, short links for every link a tool shares, and the
flavour kept on purpose are Graham's decisions. The other rules are the Gong Design System's tool-screen
rules. Every threshold, word list and exemption written in this file is Claude's default and can change.
"""
import argparse
import ast
import bisect
import collections
import hashlib
import html as html_lib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote_plus

HERE = Path(__file__).resolve().parent

SEVERITY = {
    "layer-intact": "error",
    "tools-intact": "error",
    "baseline-raised": "error",
    "retired-value": "error",
    "font-family": "error",
    "raw-color": "error",
    "token-redefined": "error",
    "theme-os": "error",
    "theme-default": "error",
    "theme-unknown": "error",
    "uppercase": "error",
    "letter-spacing": "warn",
    "middle-dot": "error",
    "env-name": "error",
    "hidden-name": "error",
    "card-shadow": "warn",
    "gradient-fill": "error",
    "accent-bar": "error",
    "focus-removed": "error",
    "control-shape": "warn",
    "graphic-text": "error",
    "emoji-icon": "error",
    "small-text": "error",
    "typed-caps": "error",
    "color-mix": "error",
    "logo-filter": "error",
    "runtime-origin-link": "warn",
    "display-face-case": "warn",
    "text-opacity": "warn",
    "title-case-heading": "warn",
    "pair-contrast": "error",
    "flavour-marker": "warn",
}
NEVER_BASELINED = frozenset({"layer-intact", "tools-intact", "baseline-raised"})
NEVER_FLAVOUR = NEVER_BASELINED | {"flavour-marker"}

DEFAULT_CONFIG = {
    "layer": None,
    "scan": ["**/*.css", "**/*.html", "**/*.js", "**/*.jsx", "**/*.ts", "**/*.tsx"],
    "skip": [],
    "themes": ["light", "dark"],
    "display_selectors": [],
    "baseline": "brand-check.baseline.json",
    "theme_files": [],
    "flavour": [],
    "allowed_identifiers": [],
    "acronyms": [],
    "names": [],
    "hidden_names": [],
}
PRUNE_DIRS = {"node_modules", ".git", "__pycache__", ".venv", "venv", ".next", ".cache"}
MAX_BYTES = 2_000_000

CSS_EXT = {".css", ".scss", ".less"}
HTML_EXT = {".html", ".htm", ".vue", ".svelte"}
JS_EXT = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
JSX_EXT = {".js", ".jsx", ".tsx"}  # .ts files cannot hold JSX, and <Type>value there is a type assertion

# The four brand faces, and the names the variable-font packages give Inter and Inter Tight.
BRAND_FAMILIES = {"bn axel grotesk", "inter tight", "inter", "ibm plex mono", "inter variable", "inter tight variable"}
# BN Axel under every name the design system publishes: "BNAxel Grotesk Bold" in its tokens.css,
# "BN Axel Grotesk Bold" in its README and "BN Axel Grotesk" in tokens.json and this layer.
BN_AXEL = re.compile(r"bn ?axel(?: grotesk)?(?: bold)?")
FALLBACK_FAMILIES = {
    "serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui", "ui-sans-serif",
    "ui-serif", "ui-monospace", "ui-rounded", "math", "emoji", "fangsong", "-apple-system",
    "blinkmacsystemfont", "segoe ui", "roboto", "helvetica neue", "helvetica", "arial",
    "noto sans", "menlo", "monaco", "consolas", "liberation mono", "courier new",
    "sfmono-regular", "apple color emoji", "segoe ui emoji", "segoe ui symbol", "noto color emoji",
}
FONT_KEYWORDS = {"inherit", "initial", "unset", "revert", "revert-layer"}
# Families a custom property can name that are never brand faces (Claude's default list of common web fonts).
KNOWN_NON_BRAND = {
    "archivo", "schibsted grotesk", "poppins", "montserrat", "lato", "open sans", "source sans pro", "source sans 3",
    "nunito", "nunito sans", "raleway", "work sans", "dm sans", "manrope", "plus jakarta sans", "space grotesk",
    "space mono", "ibm plex sans", "ibm plex serif", "fira code", "fira sans", "fira mono", "jetbrains mono",
    "roboto mono", "source code pro", "playfair display", "merriweather", "georgia", "times new roman", "times",
    "comic sans ms", "ubuntu", "oswald", "pt sans", "libre franklin", "karla", "rubik", "outfit", "sora", "geist",
    "geist mono", "lora", "barlow", "mulish", "quicksand", "josefin sans", "cabin", "figtree", "public sans",
    "red hat display", "red hat text", "overpass", "heebo", "assistant", "noto serif", "courier", "sf pro",
    "sf pro display", "sf pro text", "sf mono", "avenir", "avenir next", "futura", "gill sans", "proxima nova",
}
GOOGLE_FONT_FAMILIES = {"inter", "inter tight", "ibm plex mono"}

RETIRED = re.compile(r"#(ff2370|4cfec8|ffe03f|997ced|eef4fe|1d0b4e)(?:[0-9a-f]{2})?(?![0-9a-z])", re.I)
POPPINS = re.compile(r"\bpoppins\b", re.I)
HEX_COLOR = re.compile(r"(?<![\w&#])#(?:[0-9a-f]{8}|[0-9a-f]{6}|[0-9a-f]{4}|[0-9a-f]{3})(?![\w-])", re.I)
FUNC_COLOR = re.compile(r"(?<![\w-])(?:rgba?|hsla?)\(", re.I)
MIDDLE_DOT = re.compile(r"\u00b7|&middot;|&centerdot;|&#0*183;|&#x0*b7;|\\u00b7|\\u\{0*b7\}|\\xb7|\\0*b7(?![0-9a-f])", re.I)
ENV_NAME = re.compile(r"(?<![a-z0-9])uat(?![a-z0-9])|run\.app", re.I)
PREFERS = re.compile(r"prefers-color-scheme", re.I)
# Display text: BN Axel, or any display font variable (--font-display, --cine-font-display, --display).
DISPLAY_VAR = r"--(?:[\w-]+-)?font-display(?![\w-])|--display(?![\w-])"
DISPLAY_FONT = re.compile(r"(?<![\w-])font(?:-family)?\s*:[^;]*(?:bn\s*axel|" + DISPLAY_VAR + ")", re.I)
DISPLAY_JS = re.compile(r"bn\s*axel|font-?display|" + DISPLAY_VAR, re.I)
# The layer's classes set in BN Axel. The gb-display-* classes are Inter Tight headings in their own case.
BN_AXEL_CLASS = re.compile(r"\.gb-(?:hero-h1|accent-[\w-]+|stat__value)(?![\w-])")
CAPS_DISPLAY_CLASS = re.compile(r"gb-(?:hero-h1|accent-[\w-]+|stat__value)")
# Eyebrows are never BN Axel and stay sentence case (the system's tool-screen rules), whatever face a rule sets.
EYEBROW = re.compile(r"eyebrow|kicker|overline", re.I)
CARD_LIKE = re.compile(r"card|tile|panel|\bbox\b|-box\b|well|surface", re.I)
FLOATING = re.compile(
    r"dialog|(?<![a-z])dlg(?![a-z])|modal|menu|popover|popup|pop-up|toast|snackbar|drawer|dropdown|tooltip|overlay|sheet|gongy|floating"
    r"|flyout|lightbox|listbox|autocomplete|suggest|combobox|palette|cmdk|hovercard|tippy|(?<![a-z])tips?(?![a-z])|:focus"
    r"|\[role=.?(?:dialog|menu|listbox|tooltip)",
    re.I)
FOCUS_MARK = re.compile(r":focus(?:-visible|-within)?(?![\w-])|\.is-focus(?![\w-])|\.focus-visible(?![\w-])|\.focused(?![\w-])"
                        r"|\[data-focus[\w-]*(?:[~|^$*]?=[^\]]*)?\]", re.I)
SELECTED_MARK = re.compile(
    r"\[aria-(?:selected|current|pressed|checked)\b|:checked\b|\[selected\]|:target\b|\[data-(?:state|active|selected|current)\b"
    r"|[.\-_](?:is-|has-)?(?:active|selected|current|checked|chosen|picked)(?![\w-])|\.(?:is-)?on(?![\w-])", re.I)
DISABLED_MARK = re.compile(r":disabled|\[disabled|\[aria-disabled|\.(?:is-)?disabled(?![\w-])|placeholder", re.I)
SPINNER = re.compile(r"spin|loader|loading|throbber|drag|drop-?(?:target|zone|over|line|indicator)", re.I)
# Elements a script focuses to move the reading position: no ring is expected on them (Claude's default).
NON_INTERACTIVE = re.compile(r"^(?:h[1-6]|main|section|article|dialog|body|html)(?![\w-])|\[tabindex\s*=\s*[\"']?-1"
                             r"|\[role\s*=\s*[\"']?(?:dialog|region|main|alert|status)", re.I)
# Class and id words that mark such a script focus target, when the outline goes on :focus, not :focus-visible.
FOCUS_TARGET_WORDS = {"main", "content", "status", "alert", "region", "live", "announcer"}
# Class words of a control that stays a control even when it is placed like a floating layer (card-shadow).
CONTROL_WORDS = re.compile(r"btn|button|switch|toggle|chip|tile|card", re.I)
# Subjects that hold a glyph or decoration, not text people read (small-text, text-opacity, graphic-text).
GLYPH_WORDS = re.compile(r"(?:^|[-_])(?:caret|chevron|arrow|ext|icons?|ico|glyph|monogram|watermark)(?:$|[-_])", re.I)
# Selector words of a list, menu or navigation whose buttons are rows, not pill buttons (control-shape).
ROW_CONTAINER = re.compile(r"(?<![a-z])(?:nav|navbar|navigation|sidenav|menu|menubar|tree|treeview|list|tabs?|tablist"
                           r"|sidebar)(?![a-z])", re.I)
# Common page elements: a string holding one of them with attributes, or closed, is markup the app writes into the
# page. Placeholders in prompts (<user_request>, <slot>, <one line>) are not (Claude's default).
UI_TAGS = set("""
a abbr article aside b blockquote br button caption code col colgroup dd details dialog div dl dt em fieldset figcaption
figure footer form g h1 h2 h3 h4 h5 h6 header hr i iframe img input kbd label legend li line main mark meter nav ol option
p path picture polygon polyline pre progress rect section select small source span strong sub summary sup svg table tbody td
text textarea tfoot th thead time tr tspan u ul use video circle canvas
""".split())
HTML_FRAGMENT = re.compile(r"<(/?)([A-Za-z][\w-]*)(\s[^<>]*)?/?>")


def looks_like_markup(value):
    """True when a string holds HTML: a common element with attributes, a closing tag, or a br, hr, img or input."""
    if "<" not in value:
        return False
    for tag in HTML_FRAGMENT.finditer(value):
        name = tag.group(2).lower()
        if name in UI_TAGS and (tag.group(1) or (tag.group(3) and "=" in tag.group(3)) or name in ("br", "hr", "img", "input")):
            return True
    return False
STYLE_COLOR_KEY = re.compile(r"(?:color|background\w*|border\w*|outline\w*|fill|stroke|boxShadow|textShadow|caretColor|accentColor"
                             r"|stopColor|textDecoration\w*|columnRule\w*)", re.I)
TYPOGRAPHIC_OK = {"\u25e6"}  # the white bullet of a nested list
QUOTE_SEL = re.compile(r"quote|testimonial|\bcite\b", re.I)
LOGO_WORDS = re.compile(r"logo|lockup|wordmark|burst", re.I)
# url(#id) points at an SVG filter, mask or gradient by id; the #id is not a colour.
FRAGMENT_URL = re.compile(r"""url\(\s*(["']?)#[^"')\s]*\1\s*\)""", re.I)
# A JS string is read as CSS only when it sets a property the rules read.
CSS_COLOR_PROP = re.compile(
    r"(?:^|[;{\s])(?:-(?:webkit|moz|ms)-)?(?:color|background(?:-color|-image)?|border(?:-[a-z-]+)?|outline(?:-color)?"
    r"|fill|stroke|box-shadow|text-shadow|text-decoration(?:-color)?|caret-color|accent-color|column-rule(?:-color)?"
    r"|stop-color|flood-color|lighting-color|scrollbar-color|filter)\s*:", re.I)
CSS_TEXT_PROP = re.compile(
    r"(?:^|[;{\s])(?:-(?:webkit|moz)-)?(?:color|background(?:-color|-image)?|border(?:-(?:left|right|top|bottom|inline-start|inline-end"
    r"|block-start|block-end))?|border-radius|outline|font(?:-family|-size)?|opacity|filter|box-shadow|text-transform|letter-spacing"
    r"|--[\w-]+)\s*:\s*[^;{}]+(?:;|$)", re.I)
# Strings that fully match a hex colour but are a selector, an anchor or a hash, not a colour.
SELECTOR_USE = re.compile(
    r"(?:\b(?:querySelector(?:All)?|closest|matches|getElementById|scrollIntoView|jQuery)|\$|\b(?:history|router)\.(?:push|replace)(?:State)?)"
    r"\s*\((?:[^()]*,)?\s*$|(?:\bhash|\bhref|\bto|\bid|\bselector|\banchor|\bfragment)\s*(?:[!=]==?|=|:)\s*$|\bcase\s*$", re.I)
# Strings compared, matched or looked up in code are not shown to anyone.
LOOKUP_BEFORE = re.compile(
    r"(?:[!=]==?|\bcase|\bin|\b(?:includes|startsWith|endsWith|indexOf|lastIndexOf|match|matchAll|test|search|has|get"
    r"|getItem|setItem|removeItem|getAttribute|hasAttribute|contains|require|import|RegExp)\s*\()\s*$|(?:\bfrom|\bimport)\s*$")
# Server identifiers people never see: the fallback of an environment variable that names an id, a database or a
# project (process.env.LMS_DATABASE_ID || "lms-uat"), and OAuth return addresses, which must match a registration.
SERVER_ID_BEFORE = re.compile(r"process\.env\.[A-Za-z0-9_]*(?:_ID|_DB|DATABASE|PROJECT)\s*(?:\|\||\?\?)\s*$"
                              r"|\b(?:redirect|callback)\w*\s*[:=]\s*$", re.I)
SERVER_ID_OBJECT = re.compile(r"([A-Za-z_$][\w$]*)\s*[:=]\s*(?:Object\.freeze\(\s*)?$")
SERVER_ID_NAME = re.compile(r"redirect|callback", re.I)
LOOKUP_AFTER = re.compile(r"\s*(?:[!=]==?|\bin\b)")
# Strings written to a log are read by developers, never by the people using the tool.
LOG_CALL = re.compile(r"\b(?:console|logger|log)\s*\.\s*(?:log|info|warn|error|debug|trace)\s*\((?:[^()]*,)?\s*$|\bdebug\s*\((?:[^()]*,)?\s*$")
# JSX attributes people never see; every other attribute and prop counts as visible text.
UNSEEN_ATTRS = {
    "classname", "class", "id", "key", "ref", "style", "htmlfor", "for", "name", "type", "rel", "role", "src", "srcset",
    "target", "method", "action", "enctype", "autocomplete", "inputmode", "variant", "size", "as", "lang", "dir", "slot",
    "form", "xmlns", "viewbox", "d", "fill", "stroke", "testid", "aria-hidden", "aria-controls", "aria-describedby",
    "aria-labelledby", "aria-owns", "aria-live", "aria-current", "aria-expanded", "aria-haspopup", "integrity",
    "crossorigin", "loading", "decoding", "sizes", "media", "mode", "theme", "icon", "fontfamily", "fontsize",
    "fontweight", "textanchor", "stopcolor", "strokewidth", "transform", "points", "x", "y", "cx", "cy", "r", "rx", "ry",
    "width", "height", "offset", "gradientunits", "preserveaspectratio",
}
CLASS_ATTRS = {"classname", "class"}
# Attributes whose text people read, for typed capitals.
CAPS_ATTRS = {"title", "alt", "placeholder", "aria-label", "label", "value", "tooltip", "message", "heading", "text"}
# HTML attributes people see or copy; text between tags counts too.
SHOWN_HTML_ATTRS = {"title", "alt", "placeholder", "aria-label", "aria-description", "aria-roledescription",
                    "aria-placeholder", "aria-valuetext", "value", "content", "label"}
HTML_LINK_TAGS = {"a", "area"}
HTML_TAG = re.compile(r"""<(/?)([A-Za-z][\w:.-]*)((?:[^<>"']|"[^"]*"|'[^']*')*)>""", re.S)
HTML_ATTR = re.compile(r"""([^\s"'=<>`/]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+)))?""")
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
CODE_TAGS = {"code", "pre", "kbd", "samp", "var", "abbr", "script", "style", "textarea"}
HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
SVG_TEXT_TAGS = {"text", "tspan", "textpath"}
JUNK_NAME = re.compile(r"\.DS_Store|Thumbs\.db|desktop\.ini|\._.*", re.I)
GOOGLE_FONTS = re.compile(r"fonts\.googleapis\.com/css2?\?([^\"'\s)<>`]*)", re.I)
LAYER_HEADER = re.compile(
    r"[ \t\r\n]*/\* Gong brand layer (\S+?), generated from the Gong Design System \(tokens sha256 [0-9a-f]{12}\)\. "
    r"fingerprint sha256:([0-9a-f]{64})\. Do not edit: regenerate\. \*/[ \t]*\n")
FLAVOUR_MARK = re.compile(r"gb-flavour\s*:([^\n]*)", re.I)
GRADIENT = re.compile(r"(?<![\w-])(?:repeating-)?(?:linear|radial|conic)-gradient\(", re.I)
KEYFRAME_STOP = re.compile(r"(?:from|to|\d+(?:\.\d+)?%)(?:\s*,\s*(?:from|to|\d+(?:\.\d+)?%))*", re.I)
VAR_NAME = re.compile(r"var\(\s*--([\w-]+)")

# Colours that are graphic only: Teal, Pink and Blue (their tokens resolve to these).
GRAPHIC = {"#6dffec": "Teal", "#fd63fe": "Pink", "#3caff2": "Blue"}
# The tokens that are those colours by name, known without a vendored layer (cta is the Pink fill).
GRAPHIC_TOKENS = {"Teal": "Teal", "teal-500": "Teal", "Pink": "Pink", "pink-500": "Pink", "cta": "Pink", "Blue": "Blue", "blue-500": "Blue"}
LAVENDAR = "#9069e7"
# Token roles that are neutral edges or grounds for accent-bar (Claude's default).
NEUTRAL_TOKENS = {"border", "control-border", "field-border", "text-body", "text-gray", "doc-ink", "doc-muted", "doc-rule",
                  "White", "text-on-dark", "text-on-dark-muted", "scrim"}
ACCENT_NAME = re.compile(
    r"accent|brand|primary|violet|purple|pink|magenta|teal|cyan|aqua|blue|lavend|lilac|mauve|indigo|success|warning|warn|error"
    r"|danger|info|green|red|orange|yellow|amber|gold|cta|highlight|chart|kind|role|category|(?:^|-)ai(?:-|$)|coral|lime", re.I)
NEUTRAL_NAME = re.compile(
    r"border|line|divider|separator|rule|hairline|neutral|gr[ae]y|muted|subtle|surface|bg|paper|ink|text|fg|edge|stroke|outline|shade", re.I)
TEXT_PROPS = {"color", "font", "line-height", "letter-spacing", "-webkit-text-fill-color", "white-space", "word-spacing"}
NON_TEXT_TAGS = {"img", "svg", "hr", "video", "canvas", "iframe", "progress", "meter", "picture", "audio", "object", "embed"}

# Word lists (Claude's defaults; the config adds to them).
BUILTIN_ACRONYMS = frozenset("""
AI GTM RFP RFI RFQ LMS KPI OKR CRM SFDC API SSO IT UI UX ROI ARR MRR NRR GRR ACV TCV PDF CSV URL ID FAQ FY Q1 Q2 Q3 Q4
H1 H2 AE SDR BDR CSM RA SE SC VP SVP EVP AVP RVP CEO CRO CMO CFO COO CTO CPO CIO CISO CHRO HR US USA UK EU EMEA APAC
AMER LATAM ANZ DACH NA NAMER PM UTC PST PDT PT ET EST EDT CT CST MT MST GMT CET BST IST OK MEDDIC MEDDICC MEDDICCC
MEDDPICC SKO QBR EBR NPS CSAT SLA SOW MSA NDA POC POV MVP SMB MM ENT GM BU CX CS PS ICP ABM MQL SQL SAL TAM SAM CAC
LTV GPT LLM RAG MCP ML NLP OS HTML CSS JS TS JSON XML YAML SDK CLI CI CD QA DNS IP VPN MFA OTP PII PHI GDPR SOC HIPAA
CCPA ISO PCI NIST USD EUR GBP CAD AUD JPY INR PNG JPG JPEG GIF SVG MP3 MP4 DOCX XLSX PPTX ZIP SCORM XAPI CMS CPQ ERP
HRIS ATS BI ETL CDP GCP AWS IAM IAP SAML HTTP HTTPS REST TBD TBA FYI ASAP AKA DM PTO OOO EOD EOW EOQ EOY ETA YTD QTD
MTD YOY QOQ TLDR IPO ESG DEI ERG KB TOC PIN AB NYC SF LA SLC TLV RSVP AM PM NB ASR STT TTS ARIA WCAG DOM RGB HSL
DPI CDN NPM
""".split())
PRODUCT_NAMES = ("Gong Data Cloud", "Revenue AI OS", "Gong Foundation", "Gong Forecast", "Gong Engage", "Gong Enable",
                 "AI Fluency", "Data Cloud", "Gong Labs", "Revenue AI", "Gongy", "Gong")
# Google Cloud products the apps describe, written as the products are named.
CLOUD_NAMES = ("Workload Identity Federation", "Identity-Aware Proxy", "Cloud Run Jobs", "Cloud Run", "Cloud Scheduler",
               "Cloud Logging", "Cloud Monitoring", "Secret Manager", "Artifact Registry", "Vertex AI")
# The internal apps. generate.py --tools --profile public writes this one line as an empty tuple.
INTERNAL_NAMES = ()  # left out of a public copy
BUILTIN_NAMES = PRODUCT_NAMES + CLOUD_NAMES + INTERNAL_NAMES
SHORT_WORDS = {"a", "an", "the", "and", "or", "nor", "but", "of", "to", "in", "on", "at", "by", "for", "with", "from", "as",
               "vs", "via", "per", "up", "into", "onto", "off", "out", "over", "is", "if", "so", "yet"}

# Characters that stand in for icons. Arrows, the multiplication sign and keyboard symbols are ordinary
# text in running text and count only when they stand alone in a button or link (Claude's default).
ICON_CHAR = re.compile(
    "[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\u2300-\u23FF\u25A0-\u25FF\u2460-\u24FF\u2190-\u21FF\u2900-\u297F"
    "\u3030\u303D\u3297\u3299\u2139\u00D7]|[0-9#*]\uFE0F?\u20E3")
FLEXIBLE_CHARS = set(chr(c) for c in range(0x2190, 0x2200)) | set(chr(c) for c in range(0x2900, 0x2980)) | {
    "\u00D7", "\u2318", "\u2325", "\u2303", "\u23CE", "\u232B", "\u2326", "\u238B", "\u21E7"}

CssRule = collections.namedtuple("CssRule", "selector decls start sel_start end parents")
JsParts = collections.namedtuple("JsParts", "code nocomment strings jsx_text comments")


class CheckError(Exception):
    """The check cannot run: a bad config or baseline reference (exit 2)."""


class Finding:
    __slots__ = ("file", "line", "rule", "message", "key", "offset", "level", "baselined", "flavour")

    def __init__(self, file, line, rule, message, key, offset=0, level=None):
        self.file, self.line, self.rule, self.message, self.key = file, line, rule, message, key
        self.offset = offset
        self.level = level or SEVERITY[rule]
        self.baselined = False
        self.flavour = None

    @property
    def severity(self):
        return self.level

    def format(self):
        if self.flavour:
            tail = f" (kept flavour: {self.flavour})"
        elif self.baselined:
            tail = " (baseline)"
        else:
            tail = ""
        return f"{self.file}:{self.line} {self.rule} {self.severity}: {self.message}{tail}"


def sha256(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def canonical(record):
    return json.dumps(record, sort_keys=True, separators=(",", ":"))


# ------------------------------------------------------------------ config and files

def glob_regex(pattern):
    """A glob where ** spans folders and * stays inside one folder."""
    out, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out, i = out + "(?:.*/)?", i + 3
        elif pattern.startswith("**", i):
            out, i = out + ".*", i + 2
        elif pattern[i] == "*":
            out, i = out + "[^/]*", i + 1
        elif pattern[i] == "?":
            out, i = out + "[^/]", i + 1
        else:
            out, i = out + re.escape(pattern[i]), i + 1
    return re.compile(out + r"\Z")


def load_config(root, path):
    config = dict(DEFAULT_CONFIG)
    if path is None:
        path = root / "brand-check.json"
        if not path.exists():
            return config, None
    try:
        loaded = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise CheckError(f"cannot read the config {path}: {error}") from None
    if not isinstance(loaded, dict):
        raise CheckError(f"the config {path} must be a JSON object")
    for key in DEFAULT_CONFIG:
        if key in loaded:
            config[key] = loaded[key]
    return config, Path(path)


def discover(root, config):
    scan = [glob_regex(p) for p in config["scan"]]
    skip = [glob_regex(p) for p in config["skip"]]
    layer = (root / config["layer"]).resolve() if config.get("layer") else None
    files, too_big = [], []
    for folder, dirs, names in os.walk(root):
        folder_path = Path(folder)
        dirs[:] = sorted(d for d in dirs if d not in PRUNE_DIRS
                         and not (layer and (folder_path / d).resolve() == layer))
        for name in sorted(names):
            path = folder_path / name
            rel = path.relative_to(root).as_posix()
            if not any(r.match(rel) for r in scan) or any(r.match(rel) for r in skip):
                continue
            if layer and layer in path.resolve().parents:
                continue
            try:
                size = path.stat().st_size
            except OSError:
                continue
            if size > MAX_BYTES:
                too_big.append(rel)
                continue
            files.append((rel, path))
    return files, too_big


# ------------------------------------------------------------------ splitting sources

def blank(text, start, end):
    """Spaces for every character of text[start:end] except newlines, so offsets keep their lines."""
    return "".join("\n" if c == "\n" else " " for c in text[start:end])


def strip_css_comments(text):
    return re.sub(r"/\*.*?(?:\*/|\Z)", lambda m: blank(m.group(0), 0, len(m.group(0))), text, flags=re.S)


REGEX_BEFORE = set("(,=:[!&|?{};+-*%~^")
JSX_AFTER = set("(,=:?[{};!&|>")
JSX_KEYWORDS = {"return", "yield", "await", "case", "default", "else", "do", "in", "of", "typeof", "void", "delete", "throw"}
JSX_NAME = re.compile(r"[A-Za-z][\w.:-]*")


def word_before(text, i):
    j = i
    while j > 0 and text[j - 1].isspace():
        j -= 1
    k = j
    while k > 0 and (text[k - 1].isalnum() or text[k - 1] in "_$"):
        k -= 1
    return text[k:j]


def jsx_tag_end(text, i):
    """Where a JSX tag starting at text[i] == '<' ends (just after its '>'), or None when it is
    not a tag: '<' takes a name (or '>' for a fragment), then a space, '/', '>' or '{', and the
    tag closes before any ';' or '<' outside braces."""
    n = len(text)
    j = i + 1
    if j < n and text[j] == "/":
        j += 1
    m = JSX_NAME.match(text, j)
    if m:
        j = m.end()
    elif not (j < n and text[j] == ">"):
        return None
    if j < n and not (text[j].isspace() or text[j] in "/>{"):
        return None
    depth, quote, limit = 0, "", min(n, i + 4000)
    while j < limit:
        c = text[j]
        if quote:
            if c == "\\":
                j += 2
                continue
            if c == quote:
                quote = ""
        elif c in "'\"`":
            quote = c
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth < 0:
                return None
        elif depth == 0:
            if c == ">":
                return j + 1
            if c in ";<":
                return None
        j += 1
    return None


def template_end(text, at):
    """Where the template literal that opens at text[at] == '`' closes: ${...} expressions are skipped,
    with the strings and nested template literals inside them."""
    n, j = len(text), at + 1
    while j < n:
        c = text[j]
        if c == "\\":
            j += 2
            continue
        if c == "`":
            return j
        if c == "$" and text.startswith("${", j):
            j = expression_end(text, j + 2)
            continue
        j += 1
    return n


def expression_end(text, j):
    """Just after the } that closes a ${ expression whose body starts at j."""
    n, depth = len(text), 1
    while j < n:
        c = text[j]
        if c == "\\":
            j += 2
            continue
        if c in "'\"":
            k = j + 1
            while k < n and text[k] != c and text[k] != "\n":
                k += 2 if text[k] == "\\" else 1
            j = k + 1
            continue
        if c == "`":
            j = template_end(text, j) + 1
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return j + 1
        j += 1
    return n


def template_hole_spans(value):
    """[(start, end)] of the body of every ${...} expression in a template literal's contents."""
    spans, i, n = [], 0, len(value)
    while i < n:
        if value[i] == "\\":
            i += 2
            continue
        if value.startswith("${", i):
            end = expression_end(value, i + 2)
            spans.append((i + 2, max(i + 2, end - 1)))
            i = end
            continue
        i += 1
    return spans


def template_holes(value):
    """value with every ${...} expression blanked (newlines kept), so markup in a template literal reads alone."""
    out, i, n = list(value), 0, len(value)
    while i < n:
        if value[i] == "\\":
            i += 2
            continue
        if value.startswith("${", i):
            end = expression_end(value, i + 2)
            for k in range(i, min(end, n)):
                if out[k] != "\n":
                    out[k] = " "
            i = end
            continue
        i += 1
    return "".join(out)


def new_tag(text, at):
    m = JSX_NAME.match(text, at)
    return {"name": m.group(0) if m else "", "attrs": {}, "classes": []}


def make_element(info, uid):
    """(tag, classes, role, uid) for an element: what the text rules need to know about it."""
    return (info["name"], " ".join(info["classes"]), str(info["attrs"].get("role", "")), uid)


def split_js(text, jsx=False):
    """Tokenize JavaScript, and JSX when jsx is true. Returns JsParts:
    code       the text with comments, strings, regex literals and JSX text blanked
    nocomment  the text with only comments blanked
    strings    [(offset, contents, attribute, stack, tag)] for every string literal: attribute names the
               JSX attribute a string sets (None for a plain string, and className inside className={...}),
               stack the enclosing JSX elements and tag the element whose attribute it is
    jsx_text   [(start, end, stack)] for each run of JSX text
    comments   [(start, end)] for every comment
    Inside JSX text, quotes and // are ordinary characters."""
    code, nocomment = list(text), list(text)
    strings, jsx_text, comments = [], [], []
    n = len(text)
    frames = [["js", 0, None]]  # [mode, braces, info]: js, expr (code in {} inside JSX), tag, close, children
    i, last, run = 0, "", None
    uid = 0

    def wipe(a, b, comment=False):
        if comment:
            comments.append((a, b))
        for k in range(a, b):
            if text[k] != "\n":
                code[k] = " "
                if comment:
                    nocomment[k] = " "

    def comment_end(at):
        if text.startswith("//", at):
            end = text.find("\n", at)
            return n if end == -1 else end
        if text.startswith("/*", at):
            end = text.find("*/", at + 2)
            return n if end == -1 else end + 2
        return None

    def stack():
        return tuple(f[2] for f in frames if f[0] == "children")

    def read_string(at, quote, attribute=None, tag=None):
        j = template_end(text, at) if quote == "`" else at + 1
        while quote != "`" and j < n:
            if text[j] == "\\":
                j += 2
                continue
            if text[j] == quote or text[j] == "\n":
                break
            j += 1
        strings.append((at + 1, text[at + 1:j], attribute, stack(), tag))
        if quote == "`" and "${" in text[at + 1:j]:
            # The strings inside ${...} are strings too (a label, a mark, a nested template).
            for hole_start, hole_end in template_hole_spans(text[at + 1:j]):
                inner = split_js(text[at + 1 + hole_start:at + 1 + hole_end], jsx)
                shift = at + 1 + hole_start
                strings.extend((shift + o, v, None, stack(), None) for o, v, a, s, t in inner.strings)
        wipe(at + 1, min(j, n))
        return j + 1

    while i < n:
        mode = frames[-1][0]
        c = text[i]
        if mode in ("js", "expr"):
            end = comment_end(i) if c == "/" else None
            if end is not None and text.startswith("//", i) and i >= 2 and text[i - 1] == ":" and text[i - 2].isalpha():
                end = None  # the // of a URL scheme such as https://, not a comment
            if end is not None:
                wipe(i, end, comment=True)
                i = end
                continue
            if c in "'\"`":
                attribute = frames[-1][2] if mode == "expr" and frames[-1][2] in CLASS_ATTRS else None
                i = read_string(i, c, attribute)
                if attribute and len(frames) > 1 and frames[-2][0] == "tag" and frames[-2][2]:
                    frames[-2][2]["classes"].append(strings[-1][1])
                last = c
                continue
            if c == "/" and (last == "" or last in REGEX_BEFORE):
                j, in_class = i + 1, False
                while j < n and text[j] != "\n":
                    if text[j] == "\\":
                        j += 2
                        continue
                    if text[j] == "[":
                        in_class = True
                    elif text[j] == "]":
                        in_class = False
                    elif text[j] == "/" and not in_class:
                        break
                    j += 1
                if j < n and text[j] == "/":
                    wipe(i, j + 1)
                    i = j + 1
                    last = "/"
                    continue
            if jsx and c == "<" and not text.startswith("</", i) \
                    and (last == "" or last in JSX_AFTER or word_before(text, i) in JSX_KEYWORDS) \
                    and jsx_tag_end(text, i):
                frames.append(["tag", 0, new_tag(text, i + 1)])
                i += 1
                continue
            if c == "{":
                frames[-1][1] += 1
            elif c == "}":
                if mode == "expr" and frames[-1][1] == 0:
                    frames.pop()
                    i += 1
                    last = ")"
                    continue
                frames[-1][1] -= 1
            if not c.isspace():
                last = c
            i += 1
            continue
        if mode in ("tag", "close"):
            end = comment_end(i) if c == "/" and text[i + 1:i + 2] in ("/", "*") else None
            if end is not None:
                wipe(i, end, comment=True)
                i = end
                continue
            if c in "'\"":
                m = re.search(r"([\w:.-]+)\s*=\s*$", text[max(0, i - 80):i])
                attribute = m.group(1).lower() if m else ""
                info = frames[-1][2]
                i = read_string(i, c, attribute, info["name"] if info else None)
                if info is not None and attribute:
                    info["attrs"][attribute] = strings[-1][1]
                    if attribute in CLASS_ATTRS:
                        info["classes"].append(strings[-1][1])
                continue
            if c == "{":
                m = re.search(r"([\w:.-]+)\s*=\s*$", text[max(0, i - 80):i])
                frames.append(["expr", 0, m.group(1).lower() if m else None])
                i += 1
                continue
            if c == ">" or text.startswith("/>", i):
                closing = mode == "close"
                info = frames.pop()[2]
                if c == ">" and not closing:
                    uid += 1
                    frames.append(["children", 0, make_element(info, uid)])
                elif closing and len(frames) > 1 and frames[-1][0] == "children":
                    frames.pop()
                i += 1 if c == ">" else 2
                if frames[-1][0] != "children":
                    last = ")"  # a JSX element is a value in the code around it
                continue
            i += 1
            continue
        # children: JSX text up to the next tag or {expression}
        if c == "<" and i + 1 < n and (text[i + 1] in "/>" or text[i + 1].isalpha()):
            if run is not None:
                jsx_text.append((run, i, stack()))
                wipe(run, i)
                run = None
            closing = text[i + 1] == "/"
            frames.append(["close", 0, None] if closing else ["tag", 0, new_tag(text, i + 1)])
            i += 2 if closing else 1
            continue
        if c == "{":
            if run is not None:
                jsx_text.append((run, i, stack()))
                wipe(run, i)
                run = None
            frames.append(["expr", 0, None])
            i += 1
            continue
        if run is None:
            run = i
        i += 1
    if run is not None:
        jsx_text.append((run, n, stack()))
        wipe(run, n)
    return JsParts("".join(code), "".join(nocomment), strings, jsx_text, comments)


SCRIPT_BLOCK = re.compile(r"(<script\b([^>]*)>)(.*?)(</script\s*>)", re.I | re.S)
STYLE_BLOCK = re.compile(r"(<style\b[^>]*>)(.*?)(</style\s*>)", re.I | re.S)


def layer_copy_ok(body):
    """None when body does not start with the layer's header line; else (ok, version): ok is True when
    everything after the header matches its fingerprint, apart from whitespace at the very end."""
    m = LAYER_HEADER.match(body)
    if not m:
        return None
    rest, fingerprint = body[m.end():], m.group(2)
    core = rest.rstrip()
    ok = sha256(rest) == fingerprint or any(sha256(core + tail) == fingerprint for tail in ("\n", "", "\r\n", "\n\n"))
    return ok, m.group(1)


def split_html(text):
    """Return (remainder, css_parts, js_parts, layer_parts): comments blanked; style and script contents
    moved into their own parts, css as (offset, text) and js as (offset, text, jsx); JSON and template
    script bodies blanked; style and script blocks that carry the layer's header verified and set aside
    as layer_parts (offset, ok, version, kind, body), kind "css" or "js"."""
    rest = re.sub(r"<!--.*?(?:-->|\Z)", lambda m: blank(m.group(0), 0, len(m.group(0))), text, flags=re.S)
    css_parts, js_parts, data_parts, layer_parts = [], [], [], []
    for match in SCRIPT_BLOCK.finditer(rest):
        attrs = match.group(2).lower()
        start, end = match.start(3), match.end(3)
        kind = re.search(r"""type\s*=\s*["']?([^"'\s>]+)""", attrs)
        kind = kind.group(1) if kind else "text/javascript"
        copy = layer_copy_ok(text[start:end])
        if copy is not None:
            layer_parts.append((start, copy[0], copy[1], "js", text[start:end]))
            data_parts.append((start, rest[start:end]))
            continue
        if "json" in kind or "template" in kind:
            data_parts.append((start, rest[start:end]))
            continue
        js_parts.append((start, rest[start:end], "babel" in kind or "jsx" in kind))
    for match in STYLE_BLOCK.finditer(rest):
        start, end = match.start(2), match.end(2)
        copy = layer_copy_ok(text[start:end])
        if copy is not None:
            layer_parts.append((start, copy[0], copy[1], "css", text[start:end]))
            data_parts.append((start, rest[start:end]))
            continue
        css_parts.append((start, rest[start:end]))
    pieces = list(rest)
    for part in js_parts + css_parts + data_parts:
        start, body = part[0], part[1]
        for k in range(start, start + len(body)):
            if pieces[k] != "\n":
                pieces[k] = " "
    for m in re.finditer(r"<![^>]*>|<\?[^>]*>", rest):
        for k in range(m.start(), m.end()):
            if pieces[k] != "\n":
                pieces[k] = " "
    return "".join(pieces), css_parts, js_parts, layer_parts


def visible_html(remainder):
    """The remainder with only what people see or copy left in place: the text between tags,
    and the values of the attributes in SHOWN_HTML_ATTRS (and href on links)."""
    out = list(remainder)
    for m in HTML_TAG.finditer(remainder):
        name, attrs_at = m.group(2).lower(), m.start(3)
        keep = []
        for a in HTML_ATTR.finditer(m.group(3)):
            attr = a.group(1).lower()
            if attr in SHOWN_HTML_ATTRS or (attr == "href" and name in HTML_LINK_TAGS):
                for g in (2, 3, 4):
                    if a.group(g) is not None:
                        keep.append((attrs_at + a.start(g), attrs_at + a.end(g)))
        for k in range(m.start(), m.end()):
            if out[k] != "\n":
                out[k] = " "
        for s, e in keep:
            out[s:e] = remainder[s:e]
    return "".join(out)


def html_attrs(m):
    """[(name, value, start, end)] for the attributes of an HTML_TAG match, with absolute value offsets."""
    out, at = [], m.start(3)
    for a in HTML_ATTR.finditer(m.group(3)):
        for g in (2, 3, 4):
            if a.group(g) is not None:
                out.append((a.group(1).lower(), a.group(g), at + a.start(g), at + a.end(g)))
                break
        else:
            out.append((a.group(1).lower(), "", at + a.end(1), at + a.end(1)))
    return out


def html_structure(remainder):
    """Walk the tags of an HTML remainder. Returns (tags, texts): tags is [(name, attrs, start, end, stack)]
    for every start tag, texts is [(start, end, stack)] for every run of text between tags, and stack is
    the tuple of open elements (tag, classes, role, uid) around each."""
    tags, texts, open_elements, pos, uid = [], [], [], 0, 0
    for m in HTML_TAG.finditer(remainder):
        if m.start() > pos:
            texts.append((pos, m.start(), tuple(open_elements)))
        pos = m.end()
        name = m.group(2).lower()
        if m.group(1):
            for k in range(len(open_elements) - 1, -1, -1):
                if open_elements[k][0] == name:
                    del open_elements[k:]
                    break
            continue
        attrs = html_attrs(m)
        tags.append((name, attrs, m.start(), m.end(), tuple(open_elements)))
        if name not in VOID_TAGS and not m.group(3).rstrip().endswith("/"):
            uid += 1
            values = {a[0]: a[1] for a in attrs}
            open_elements.append((name, values.get("class", ""), values.get("role", ""), uid))
    if pos < len(remainder):
        texts.append((pos, len(remainder), tuple(open_elements)))
    return tags, texts


def css_rules(text):
    """[CssRule(selector, own declarations, offset of the declarations, selector offset, end, parents)]
    for every {} block. Text must already have its comments blanked. Nested blocks are blanked out of
    the parent, and parents names the enclosing at-rules and selectors."""
    rules, stack = [], []
    boundary, i, n, quote = 0, 0, len(text), ""
    while i < n:
        c = text[i]
        if quote:
            if c == "\\":
                i += 2
                continue
            if c == quote:
                quote = ""
        elif c in "'\"":
            quote = c
        elif c == "{":
            raw = text[boundary:i]
            stack.append([raw.strip(), i + 1, [], boundary + len(raw) - len(raw.lstrip())])
            boundary = i + 1
        elif c == "}":
            if stack:
                selector, start, children, sel_start = stack.pop()
                if children:
                    own = list(text[start:i])
                    for child_start, child_end in children:
                        for k in range(max(child_start, start) - start, min(child_end, i) - start):
                            if own[k] != "\n":
                                own[k] = " "
                    own = "".join(own)
                else:
                    own = text[start:i]
                rules.append(CssRule(selector, own, start, sel_start, i + 1, tuple(s[0] for s in stack)))
                if stack:
                    stack[-1][2].append((sel_start, i + 1))
            boundary = i + 1
        elif c == ";":
            boundary = i + 1
        i += 1
    return rules


DECL_PROP = re.compile(r"-?-?[A-Za-z_][\w-]*")


def parse_decls(decls, base=0):
    """[(prop, value, offset)] for each declaration in a block's own text. prop is lower case (custom
    properties keep their case), value has !important removed, offset points at the property."""
    out = []
    n, depth, quote, start, i = len(decls), 0, "", 0, 0
    while i <= n:
        c = decls[i] if i < n else ";"
        if quote:
            if c == "\\":
                i += 2
                continue
            if c == quote:
                quote = ""
        elif c in "'\"":
            quote = c
        elif c == "(":
            depth += 1
        elif c == ")":
            depth = max(0, depth - 1)
        elif c in ";{}" and depth == 0:
            chunk = decls[start:i]
            colon = chunk.find(":")
            if colon > 0:
                prop = chunk[:colon].strip()
                if DECL_PROP.fullmatch(prop):
                    lead = len(chunk) - len(chunk.lstrip())
                    value = re.sub(r"\s*!\s*important\s*$", "", chunk[colon + 1:].strip(), flags=re.I)
                    out.append((prop if prop.startswith("--") else prop.lower(), value, base + start + lead))
            start = i + 1
        i += 1
    return out


def split_top(value, sep=","):
    """value split on sep (',' or whitespace when sep is None) outside parentheses and quotes."""
    out, depth, quote, current = [], 0, "", ""
    for c in value:
        if quote:
            current += c
            if c == quote:
                quote = ""
            continue
        if c in "'\"":
            quote = c
        elif c == "(":
            depth += 1
        elif c == ")":
            depth = max(0, depth - 1)
        if depth == 0 and ((sep is None and c.isspace()) or c == sep):
            if current.strip():
                out.append(current.strip())
            current = ""
            continue
        current += c
    if current.strip():
        out.append(current.strip())
    return out


def split_selectors(selector):
    """A selector list split on its top-level commas (commas inside :is() or [] stay)."""
    parts, depth, current = [], 0, ""
    for c in selector:
        if c in "([":
            depth += 1
        elif c in ")]":
            depth = max(0, depth - 1)
        if c == "," and depth == 0:
            parts.append(current)
            current = ""
        else:
            current += c
    parts.append(current)
    return [p.strip() for p in parts if p.strip()]


def compounds(part):
    """The compound selectors of one selector, split on combinators outside () and []."""
    out, depth, current = [], 0, ""
    for c in part:
        if c in "([":
            depth += 1
        elif c in ")]":
            depth = max(0, depth - 1)
        if depth == 0 and (c.isspace() or c in ">+~"):
            if current:
                out.append(current)
            current = ""
            continue
        current += c
    if current:
        out.append(current)
    return out


def subject(part):
    found = compounds(part)
    return found[-1] if found else ""


def classes_of(compound):
    return re.findall(r"\.([\w-]+)", re.sub(r":not\([^)]*\)", "", compound))


def tag_of(compound):
    m = re.match(r"[A-Za-z][\w-]*", compound)
    return m.group(0).lower() if m else ""


def selector_theme_sets(selector):
    """(themes the selector applies to, themes it leaves out) from its data-theme attributes and the
    layer's dark scope classes (.gb-dark, gb-band and gb-panel sections)."""
    inc, exc = set(), set()
    for m in re.finditer(r"""(:not\(\s*)?\[\s*data-theme\s*[~|^$*]?=\s*["']?([\w-]+)""", selector):
        (exc if m.group(1) else inc).add(m.group(2))
    if not inc and re.search(r"\.gb-(?:dark|band|panel)(?![\w-])", selector):
        inc.add("dark")
    return inc, exc


def short(selector):
    selector = " ".join(selector.split())
    return selector[:80] if selector else "inline style"


def is_brand_family(name):
    return name in BRAND_FAMILIES or bool(BN_AXEL.fullmatch(name))


def enclosing_braces(code, pos):
    """(start, end) of the innermost {} block around pos in code (strings already blanked),
    so a style object split over several lines is read as one; the whole line when there is none."""
    depth, lo = 0, None
    for k in range(pos - 1, max(-1, pos - 6000), -1):
        if code[k] == "}":
            depth += 1
        elif code[k] == "{":
            if depth == 0:
                lo = k
                break
            depth -= 1
    if lo is None:
        lo = code.rfind("\n", 0, pos) + 1
        hi = code.find("\n", pos)
        return lo, len(code) if hi == -1 else hi
    depth = 0
    for k in range(lo + 1, min(len(code), lo + 6000)):
        if code[k] == "{":
            depth += 1
        elif code[k] == "}":
            if depth == 0:
                return lo, k + 1
            depth -= 1
    return lo, min(len(code), lo + 6000)


THEMEISH = re.compile(r"theme|colou?r-?scheme|colou?r-?mode", re.I)
EXPLICIT_DEFAULT = re.compile(r"^(?:default|initial|start|starting|fallback)|(?:default|initial)$", re.I)


def starting_theme_name(name):
    """True for a name that holds the starting theme: theme, defaultTheme, initialTheme,
    currentTheme, THEME_DEFAULT, colorMode and the like. Not DARK_THEME, themeKey or themes."""
    flat = name.replace("_", "").replace("$", "").lower()
    if flat in ("colormode", "colorscheme", "defaultcolormode", "initialcolormode", "defaultcolorscheme"):
        return True
    flat = re.sub(r"^(?:default|initial|current|start|starting|fallback|app|ui|site|page)", "", flat)
    flat = re.sub(r"(?:mode|name|value|default|initial)$", "", flat)
    return flat == "theme"


def left_operand(before):
    """The operand just left of a || or ?? whose left side ends before: a name, a member chain
    or a call, such as localStorage.getItem('app:theme') or h."""
    s = before.rstrip()
    i, depth = len(s), 0
    while i > 0:
        c = s[i - 1]
        if c in ")]":
            depth += 1
        elif c in "([":
            if depth == 0:
                break
            depth -= 1
        elif depth == 0 and not (c.isalnum() or c in "_$." or (c == "?" and s[i:i + 1] == ".")):
            break
        i -= 1
    return s[i:]


def assignment_target(before):
    """The name a value on this line is assigned to (const theme = ...), or ''."""
    m = re.search(r"([A-Za-z_$][\w$.]*)\s*(?<![=!<>])=(?![=>])[^=]*$", before)
    return m.group(1) if m else ""


def string_shown(code, offset, length, attribute):
    """Whether people can see a string: a JSX attribute other than the unseen ones (className,
    id, key, src and the like), or a plain string that is not compared, matched, imported,
    looked up, logged or used as an object key."""
    if attribute is not None:
        return not (attribute in UNSEEN_ATTRS or attribute.startswith("data-") or attribute.startswith("on"))
    before = code[max(0, offset - 121):max(0, offset - 1)]
    after = code[offset + length + 1:offset + length + 61]
    if LOOKUP_BEFORE.search(before) or LOOKUP_AFTER.match(after) or LOG_CALL.search(before):
        return False
    if re.match(r"\s*:", after) and re.search(r"[{,]\s*$", before):
        return False
    return True


def too_wide(number, unit):
    try:
        value = float(number)
    except ValueError:
        return False
    unit = (unit or "px").lower()
    return value > (0.32 if unit == "px" else 0.02) + 1e-9


def parse_families(value):
    value = re.sub(r"!important", "", value, flags=re.I).strip()
    out, current, depth, quote = [], "", 0, ""
    for c in value:
        if quote:
            if c == quote:
                quote = ""
            else:
                current += c
            continue
        if c in "'\"":
            quote = c
        elif c == "(":
            depth += 1
            current += c
        elif c == ")":
            depth -= 1
            current += c
        elif c == "," and depth == 0:
            out.append(current)
            current = ""
        else:
            current += c
    out.append(current)
    return [" ".join(x.split()).lower() for x in out if x.strip()]


def looks_like_families(value):
    """True when a custom property's value reads as a font stack, not a size or a var()."""
    names = parse_families(value)
    if not names:
        return False
    return all(re.fullmatch(r"-?[a-z][a-z0-9 -]*", n) for n in names if not n.startswith("var("))


SIZE_TOKEN = r"(?:\d*\.?\d+(?:px|em|rem|%|pt|vw|vh|ch|ex)|xx-small|x-small|small|medium|large|x-large|xx-large|smaller|larger)"


def shorthand_families(value):
    value = value.strip()
    if value.lower().startswith("var(") or value.lower() in FONT_KEYWORDS:
        return ""
    m = re.search(r"(?:^|\s)" + SIZE_TOKEN + r"(?:\s*/\s*[\w.%-]+)?\s+(.+)$", value, re.I)
    return m.group(1) if m else ""


def shorthand_size(value):
    m = re.search(r"(?:^|\s)(" + SIZE_TOKEN + r"|var\([^)]*\)|calc\([^)]*\)|max\([^)]*\)|min\([^)]*\)|clamp\([^)]*\))"
                  r"(?:\s*/\s*[\w.%()-]+)?\s+\S", value.strip(), re.I)
    return m.group(1) if m else None


# ------------------------------------------------------------------ colours and lengths

NAMED_COLOURS = {
    "white": (1.0, 1.0, 1.0, 1.0), "black": (0.0, 0.0, 0.0, 1.0), "transparent": (0.0, 0.0, 0.0, 0.0),
    "gray": (0.502, 0.502, 0.502, 1.0), "grey": (0.502, 0.502, 0.502, 1.0), "silver": (0.753, 0.753, 0.753, 1.0),
    "lightgray": (0.827, 0.827, 0.827, 1.0), "lightgrey": (0.827, 0.827, 0.827, 1.0),
    "darkgray": (0.663, 0.663, 0.663, 1.0), "darkgrey": (0.663, 0.663, 0.663, 1.0),
    "gainsboro": (0.863, 0.863, 0.863, 1.0), "whitesmoke": (0.961, 0.961, 0.961, 1.0),
    "dimgray": (0.412, 0.412, 0.412, 1.0), "dimgrey": (0.412, 0.412, 0.412, 1.0),
}
COLOUR_WORDS = {"red", "blue", "green", "purple", "orange", "yellow", "pink", "teal", "navy", "violet", "magenta", "cyan",
                "aqua", "lime", "gold", "coral", "tomato", "crimson", "indigo", "fuchsia", "maroon", "olive", "salmon", "orchid"}


def parse_colour(value):
    """(r, g, b, a) in 0..1 for a hex, rgb(), hsl() or a few named colours; None otherwise."""
    v = value.strip().lower()
    if v.startswith("#"):
        h = v[1:]
        if not re.fullmatch(r"[0-9a-f]{3}|[0-9a-f]{4}|[0-9a-f]{6}|[0-9a-f]{8}", h):
            return None
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h)
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
        return (r, g, b, int(h[6:8], 16) / 255 if len(h) == 8 else 1.0)
    m = re.fullmatch(r"(rgba?|hsla?)\((.*)\)", v, re.S)
    if m:
        parts = [p for p in re.split(r"[\s,/]+", m.group(2).strip()) if p]
        if len(parts) not in (3, 4):
            return None
        try:
            def number(p, scale):
                return float(p[:-1]) / 100 if p.endswith("%") else float(p) / scale
            alpha = number(parts[3], 1) if len(parts) == 4 else 1.0
            if m.group(1).startswith("rgb"):
                return (number(parts[0], 255), number(parts[1], 255), number(parts[2], 255), alpha)
            hue = float(re.sub(r"deg$", "", parts[0])) % 360 / 360
            sat, light = number(parts[1], 100), number(parts[2], 100)
        except ValueError:
            return None
        import colorsys
        r, g, b = colorsys.hls_to_rgb(hue, light, sat)
        return (r, g, b, alpha)
    return NAMED_COLOURS.get(v)


def hex6(colour):
    return "#" + "".join(f"{max(0, min(255, round(x * 255))):02x}" for x in colour[:3])


def luminance(c):
    def channel(x):
        return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4
    return 0.2126 * channel(c[0]) + 0.7152 * channel(c[1]) + 0.0722 * channel(c[2])


def over(fg, bg):
    a = fg[3]
    return (fg[0] * a + bg[0] * (1 - a), fg[1] * a + bg[1] * (1 - a), fg[2] * a + bg[2] * (1 - a), 1.0)


def contrast_ratio(fg, bg, page):
    if bg[3] < 1:
        bg = over(bg, page)
    if fg[3] < 1:
        fg = over(fg, bg)
    l1, l2 = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def chroma(colour):
    return max(colour[:3]) - min(colour[:3])


GRADIENT_POSITION = re.compile(r"-?\d*\.?\d+(?:%|px|r?em|vw|vh|ch|deg|rad|grad|turn)?|(?:calc|min|max|clamp)\(.*\)", re.I | re.S)
GRADIENT_SHAPE = re.compile(r"^(?:to\s|from\s|at\s|circle|ellipse|closest-|farthest-|-?\d*\.?\d+(?:deg|rad|grad|turn)\b)", re.I)


def call_body(value, start):
    """The text inside the parentheses of a call whose '(' ends just before value[start], or None if unclosed."""
    depth, j = 1, start
    while j < len(value) and depth:
        if value[j] == "(":
            depth += 1
        elif value[j] == ")":
            depth -= 1
        j += 1
    return value[start:j - 1] if depth == 0 else None


def hard_stops_only(args):
    """True when a gradient's colour changes only at hard stops (each stop ends where the next starts), so it draws a
    shape such as a select caret, a pie or stripes, not a blended fill (Claude's default)."""
    stops = []
    for index, item in enumerate(split_top(args)):
        if index == 0 and GRADIENT_SHAPE.match(item.strip()):
            continue
        tokens = split_top(item, None)
        positions = [t for t in tokens if GRADIENT_POSITION.fullmatch(t)]
        colour = " ".join(t for t in tokens if not GRADIENT_POSITION.fullmatch(t)).lower()
        if not colour:
            return False  # a bare position is a transition hint: a blend
        stops.append((colour, positions))
    if len(stops) < 2:
        return False

    def number(token):
        m = re.fullmatch(r"(-?\d*\.?\d+)(%|px|r?em|vw|vh|ch|deg|rad|grad|turn)?", token.lower())
        return (float(m.group(1)), m.group(2) or "") if m else None

    for (colour_a, at_a), (colour_b, at_b) in zip(stops, stops[1:]):
        if colour_a == colour_b:
            continue
        if not at_a or not at_b:
            return False
        end, start = at_a[-1].lower(), at_b[0].lower()
        if end == start:
            continue
        a, b = number(end), number(start)
        if a and b and (a[1] == b[1] or 0 in (a[0], b[0])) and b[0] <= a[0]:
            continue  # a stop placed before the last one is moved up to it: still a hard stop
        return False
    return True


def blended_gradient(value):
    """True when value holds a gradient that blends colours (any gradient that is not hard stops only)."""
    for m in GRADIENT.finditer(value):
        body = call_body(value, m.end())
        if body is None or not hard_stops_only(body):
            return True
    return False


WIDTH_KEYWORDS = {"thin": 1.0, "medium": 3.0, "thick": 5.0}
BORDER_STYLES = {"none", "hidden", "dotted", "dashed", "solid", "double", "groove", "ridge", "inset", "outset"}
SIDES = {"left": "left", "right": "right", "top": "top", "bottom": "bottom",
         "inline-start": "left", "inline-end": "right", "block-start": "top", "block-end": "bottom"}
SIDE_LONGHAND = re.compile(r"border-(left|right|top|bottom|inline-start|inline-end|block-start|block-end)(?:-(width|color|style))?")
LENGTH = re.compile(r"(-?\d*\.?\d+)(px|rem|em|pt)?")


def safe_arithmetic(expression):
    """The value of + - * / arithmetic on plain numbers, or None."""
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError:
        return None

    def walk(node):
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            value = walk(node.operand)
            return None if value is None else (-value if isinstance(node.op, ast.USub) else value)
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            a, b = walk(node.left), walk(node.right)
            if a is None or b is None or (isinstance(node.op, ast.Div) and b == 0):
                return None
            return {ast.Add: a + b, ast.Sub: a - b, ast.Mult: a * b}.get(type(node.op), a / b if b else None)
        return None
    return walk(tree)


# ------------------------------------------------------------------ the layer's tokens and the run's context

def sheet_theme(selector):
    """The theme a token block sets: a data-theme name, light for :root, dark for .gb-dark; None otherwise."""
    parts = split_selectors(selector)
    for part in parts:
        m = re.search(r"""\[\s*data-theme\s*=\s*["']?([\w-]+)""", part)
        if m and ":not(" not in part:
            return m.group(1)
    if any(p in (":root", "html") for p in parts):
        return "light"
    if any(p == ".gb-dark" for p in parts):
        return "dark"
    return None


class Context:
    """What every file's rules share: the config, the layer's token values per theme, the names an app must
    not redefine, the app's own custom properties, the classes its CSS sets in display type, and so on."""

    def __init__(self, root, config):
        self.root, self.config = root, config
        self.notes = []
        self.themes = [t for t in (config.get("themes") or []) if isinstance(t, str)] or ["light"]
        self.layer_values = {}
        self.gb_values = {}
        self.token_names = None
        self.gb_names = set()
        self.app_values = {}
        self.theme_values = {}
        self.display_classes = set()
        self.font_var_uses = set()
        self.inline_ok = 0
        self.token_source = None       # where the token values came from: "layer", "inline" or "tokens.json"
        self.layer_sheet_read = False  # the vendored gong-brand.css gave the layer's own --gb- names
        self.inline_read = set()       # fingerprints of the pasted layer copies already read
        self.profile = None            # the vendored layer's profile (full, slim or public), else the copied check's
        self.public = False
        # What the scanned markup shows about each class: the tags it sits on, whether its text has lowercase
        # letters, and how often it sits on an empty or an aria-hidden element.
        self.class_info = {}
        self.lower_words = set()       # words the app writes in lowercase or sentence case somewhere
        self._redefinable = None
        self._colour_themes = None
        self.display_res = [re.compile(p) for p in config.get("display_selectors") or []]
        self.theme_file_res = [glob_regex(p) for p in config.get("theme_files") or [] if isinstance(p, str)]
        self.flavour_entries = []
        for entry in config.get("flavour") or []:
            if not isinstance(entry, dict) or not isinstance(entry.get("glob"), str):
                self.notes.append(f"a flavour entry needs a glob: {entry!r} does not count")
                continue
            reason = " ".join(str(entry.get("reason") or "").split())
            if not reason:
                self.notes.append(f"the flavour entry for {entry['glob']} has no reason, so it does not count")
                continue
            rules = entry.get("rules")
            rules = None if not rules or rules == "*" or "*" in rules else set(rules)
            self.flavour_entries.append((glob_regex(entry["glob"]), rules, reason))
        self.allowed = []
        for entry in config.get("allowed_identifiers") or []:
            if isinstance(entry, str):
                self.allowed.append((None, entry.lower()))
            elif isinstance(entry, dict) and isinstance(entry.get("name"), str):
                glob = entry.get("glob")
                self.allowed.append((glob_regex(glob) if isinstance(glob, str) else None, entry["name"].lower()))
        self.acronyms = BUILTIN_ACRONYMS | {str(a).upper() for a in config.get("acronyms") or []}
        names = [str(n) for n in config.get("names") or [] if str(n).strip()] + list(BUILTIN_NAMES)
        self.names = sorted(set(names), key=len, reverse=True)
        # Code names match in any case (slugs and links are lower case); a finding keeps the config's spelling as its key.
        hidden = sorted({str(n) for n in config.get("hidden_names") or [] if str(n).strip()}, key=len, reverse=True)
        self.hidden_spelling = {n.lower(): n for n in reversed(hidden)}
        self.hidden = re.compile("(?<![A-Za-z0-9])(?:" + "|".join(re.escape(n) for n in hidden) + ")(?![A-Za-z0-9])",
                                 re.I) if hidden else None
        self.load_layer()

    # -- the layer's own values

    def load_layer(self):
        layer = self.config.get("layer")
        folder = (self.root / layer) if layer else None
        sheet = folder / "gong-brand.tokens.css" if folder else None
        if sheet is not None and sheet.is_file():
            self.read_token_sheet(sheet.read_text(encoding="utf-8", errors="replace"))
            self.token_source = "layer"
        elif (HERE / "tokens.json").is_file():
            try:
                self.read_tokens_json(json.loads((HERE / "tokens.json").read_text(encoding="utf-8")))
                self.token_source = "tokens.json"
            except (OSError, ValueError, KeyError, TypeError, AttributeError):
                self.layer_values, self.token_names = {}, None
        full = folder / "gong-brand.css" if folder else None
        if full is not None and full.is_file():
            self.read_layer_sheet(full.read_text(encoding="utf-8", errors="replace"))
            self.layer_sheet_read = True
        for record_path in ([folder / "VERSION.json"] if folder else []) + [HERE / "TOOLS.json"]:
            try:
                profile = json.loads(record_path.read_text(encoding="utf-8")).get("profile")
            except (OSError, ValueError, AttributeError):
                continue
            if isinstance(profile, str):
                self.profile = profile
                break
        self.public = self.profile == "public"
        if self.public:
            self.notes.append("the public profile has no BN Axel: display text is Inter Tight in its own case, so no "
                              "text counts as BN Axel display text")

    def token_notes(self):
        """The note for a run whose token names stay unknown after every file was prepared."""
        if self.token_names is None:
            self.notes.append("token-redefined is skipped: no gong-brand.tokens.css in the vendored layer, no pasted copy "
                              "of a layer sheet and no tokens.json next to the check, so the layer's token names are unknown")

    def read_token_sheet(self, text, merge=False):
        names = set(self.token_names or ()) if merge else set()
        for rule in css_rules(strip_css_comments(text)):
            theme = sheet_theme(rule.selector)
            if theme is None:
                continue
            table = self.layer_values.setdefault(theme, {})
            for prop, value, _ in parse_decls(rule.decls):
                if prop.startswith("--"):
                    names.add(prop[2:])
                    if merge:
                        table.setdefault(prop[2:], value)
                    else:
                        table[prop[2:]] = value
        self.token_names = names

    def add_inline_layer(self, text, fingerprint):
        """A verified pasted copy of a layer sheet (a single-file page) is the layer that page runs: its token values
        and --gb- names count when the vendored layer has none, ahead of a tokens.json next to the check."""
        if fingerprint in self.inline_read:
            return
        self.inline_read.add(fingerprint)
        # Only a sheet that holds the token block counts (the tokens, fonts-inline, inline or full sheet): the names an
        # alias sheet declares are not layer tokens.
        if self.token_source != "layer" and re.search(r"(?:^|[{;\s])--text-heading\s*:", text):
            if self.token_source != "inline":
                self.layer_values, self.token_names = {}, None
            self.read_token_sheet(text[:text.find("/* ==== src/")] if "/* ==== src/" in text else text, merge=True)
            self.token_names = {n for n in self.token_names if not n.startswith("gb-")}
            self.token_source = "inline"
        if not self.layer_sheet_read and re.search(r"\.gb-btn(?![\w-])", text):
            self.read_layer_sheet(text, merge=bool(self.gb_names))
        self._redefinable = self._colour_themes = None

    def read_tokens_json(self, data):
        themes = [t["id"] for t in data["color"]["themes"] if isinstance(t, dict) and isinstance(t.get("id"), str)]
        colours = {t["name"]: t["value"] for t in data["color"]["tokens"]
                   if isinstance(t, dict) and isinstance(t.get("name"), str) and isinstance(t.get("value"), dict)}

        def resolve(name, theme, depth=0):
            if depth > 20 or name not in colours:
                return None
            value = colours[name]
            expr = str(value.get(theme, value.get("light", ""))).strip()
            alias = re.fullmatch(r"\{([^{}]+)\}", expr)
            return resolve(alias.group(1).strip(), theme, depth + 1) if alias else expr.lower()

        names = set(colours)
        light = self.layer_values.setdefault("light", {})
        for theme in themes:
            table = self.layer_values.setdefault(theme, {})
            for name, value in colours.items():
                if theme == "light" or theme in value:
                    resolved = resolve(name, theme)
                    if resolved:
                        table[name] = resolved
        for family, block in data.items():
            if family in ("version", "color", "type") or not isinstance(block, dict):
                continue
            for token in block.get("tokens", []):
                if isinstance(token, dict) and isinstance(token.get("name"), str):
                    names.add(token["name"])
                    light[token["name"]] = str(token.get("value", "")).strip()
        type_block = data.get("type", {}) if isinstance(data.get("type"), dict) else {}
        for key, stack in (type_block.get("families") or {}).items():
            names.add(f"font-{key}")
            light[f"font-{key}"] = str(stack)
        for group in type_block.get("groups") or []:
            for style in (group.get("styles") or []) if isinstance(group, dict) else []:
                if not isinstance(style, dict) or not isinstance(style.get("name"), str):
                    continue
                for field, suffix in (("fontSize", "font-size"), ("lineHeight", "line-height"),
                                      ("fontWeight", "font-weight"), ("letterSpacing", "letter-spacing")):
                    name = f"{style['name']}-{suffix}"
                    names.add(name)
                    light[name] = str(style.get(field, "normal"))
        if "motion" not in data:
            names.update({"motion-color", "motion-accordion", "motion-dialog"})
        self.token_names = names

    def read_layer_sheet(self, text, merge=False):
        stripped = strip_css_comments(text)
        declared = set()
        for rule in css_rules(stripped):
            theme = sheet_theme(rule.selector)
            for prop, value, _ in parse_decls(rule.decls):
                if prop.startswith("--gb-"):
                    declared.add(prop[2:])
                    if theme:
                        self.gb_values.setdefault(theme, {}).setdefault(prop[2:], value)
        inputs = {m.group(1) for m in re.finditer(r"var\(\s*--(gb-[\w-]+)\s*,", stripped)}
        self.gb_names = (declared - inputs) | (self.gb_names if merge else set())

    def redefine_names(self):
        if self.token_names is None:
            return None
        if self._redefinable is None:
            self._redefinable = frozenset(self.token_names | self.gb_names)
        return self._redefinable

    def is_layer_token(self, name):
        return any(name in table for table in self.layer_values.values())

    # -- resolving values

    def lookup(self, name, theme="light", app=True):
        """What --name holds in theme. With app, the app's own definitions come first, because app styles load
        after the layer; without it, only the layer's tokens count (and a third theme's own token values)."""
        if app:
            tables = [self.theme_values.get(theme), self.app_values]
        elif theme not in self.layer_values and theme not in ("light", "dark") and self.is_layer_token(name):
            tables = [self.theme_values.get(theme)]  # a third theme such as Girly Pop sets layer tokens in its own file
        else:
            tables = []
        tables += [self.layer_values.get(theme), self.layer_values.get("light"),
                   self.gb_values.get(theme), self.gb_values.get("light")]
        for table in tables:
            if table and name in table:
                return table[name]
        return None

    def resolve(self, value, theme="light", app=True, depth=0):
        """value with every var() replaced by what it stands for in theme, or None when one is unknown."""
        if depth > 16:
            return None
        i = value.find("var(")
        if i < 0:
            return value
        j, level = i + 4, 1
        while j < len(value) and level:
            if value[j] == "(":
                level += 1
            elif value[j] == ")":
                level -= 1
            j += 1
        if level:
            return None
        inner = value[i + 4:j - 1]
        name, comma, fallback = inner.partition(",")
        name = name.strip()
        found = self.lookup(name[2:], theme, app) if name.startswith("--") else None
        if found is None:
            if not comma:
                return None
            found = fallback.strip()
        found = self.resolve(found, theme, app, depth + 1)
        if found is None:
            return None
        rest = self.resolve(value[j:], theme, app, depth)
        return None if rest is None else value[:i] + found + rest

    def colour(self, value, theme="light", app=True):
        v = value.strip()
        if "var(" in v:
            v = self.resolve(v, theme, app)
            if v is None:
                return None
        return parse_colour(v)

    def length(self, value, theme="light"):
        """A length in px (rem and em at 16px), or None."""
        v = value.strip()
        if "var(" in v:
            v = self.resolve(v, theme)
            if v is None:
                return None
        v = v.strip().lower()
        if v in WIDTH_KEYWORDS:
            return WIDTH_KEYWORDS[v]
        m = LENGTH.fullmatch(v)
        if m:
            number, unit = float(m.group(1)), m.group(2) or ""
            if unit == "px":
                return number
            if unit in ("rem", "em"):
                return number * 16
            if unit == "pt":
                return number * 4 / 3
            return 0.0 if number == 0 else None
        calc = re.fullmatch(r"calc\((.*)\)", v, re.S)
        if calc:
            expression = re.sub(r"(-?\d*\.?\d+)(px|rem|em)\b",
                                lambda x: str(float(x.group(1)) * (16 if x.group(2) != "px" else 1)), calc.group(1))
            if re.fullmatch(r"[\d.\s+*/()-]+", expression):
                return safe_arithmetic(expression)
        return None

    def colour_themes(self):
        if self._colour_themes is None:
            self._colour_themes = list(dict.fromkeys(["light"] + self.themes + list(self.layer_values)))
        return self._colour_themes

    def env_allowed(self, rel_regex_names, text, a, b):
        for name in rel_regex_names:
            lo = max(0, a - len(name))
            window = text[lo:b + len(name)].lower()
            k = window.find(name)
            while k != -1:
                if lo + k <= a and lo + k + len(name) >= b:
                    return True
                k = window.find(name, k + 1)
        return False


# ------------------------------------------------------------------ text helpers

ENTITY = re.compile(r"&(?:#\d+|#x[0-9a-f]+|[a-z][a-z0-9]*);", re.I)
CAPS_STRIP = "()[]{}<>\"'\u201c\u201d\u2018\u2019\u00ab\u00bb,.;:!?\u2026*_~`|"
LETTERS = re.compile(r"[A-Za-z\u00c0-\u00d6\u00d8-\u00f6\u00f8-\u00ff]")


def entities_blank(text):
    return ENTITY.sub(lambda m: " " * len(m.group(0)), text)


def caps_runs(text, acronyms):
    """[(start, end, capital words)] for each run of capital words typed in text. Acronyms, numbers and codes
    sit inside a run without counting; any other word ends it."""
    runs, current = [], []

    def flush():
        if current:
            words = [w for w in current if w[3]]
            if words:
                runs.append((current[0][0], current[-1][1], [w[2] for w in words]))
            current.clear()

    for m in re.finditer(r"\S+", text):
        core = m.group(0).strip(CAPS_STRIP)
        if not core or re.search(r"[^\w'\u2019&-]", core) or "_" in core:
            flush()
            continue
        start = m.start() + m.group(0).find(core)
        for piece in re.finditer(r"[^-]+", core):
            word = piece.group(0)
            letters = "".join(LETTERS.findall(word))
            if re.search(r"\d", word) or "&" in word:
                current.append((start + piece.start(), start + piece.end(), word, False))
            elif len(letters) >= 2 and letters.isupper():
                is_word = letters not in acronyms and word.upper() not in acronyms
                current.append((start + piece.start(), start + piece.end(), word, is_word))
            else:
                flush()
    flush()
    return runs


def title_case(text, names, acronyms):
    """True when text reads as Title Case: three or more words, each capitalised, with no lowercase word
    other than the short ones (a, of, the and the like). Names and acronyms are left out."""
    for name in names:
        text = text.replace(name, " ")
    considered = []
    for m in re.finditer(r"\S+", text):
        word = m.group(0).strip(CAPS_STRIP + "-=+&/")
        if not word or not LETTERS.match(word):
            continue
        if re.search(r"\d", word) or word.upper() in acronyms or (len(word) > 1 and word.isupper()) \
                or (len(word) > 2 and word.endswith("s") and word[:-1].isupper()):
            continue
        if word.lower() in SHORT_WORDS and word[0].islower():
            continue
        considered.append(word)
    return len(considered) >= 3 and all(w[0].isupper() for w in considered)


def decode_escapes(value, css=False):
    """A string with its \\uXXXX, \\u{...} and \\xXX escapes (or CSS \\hex escapes) decoded. An escaped
    backslash stays as it is, so the \\\\u2600 a RegExp source string holds is not read as the character."""
    def safe_chr(number):
        try:
            return chr(number) if number < 0x110000 else ""
        except ValueError:
            return ""
    if css:
        return re.sub(r"\\\\|\\([0-9a-fA-F]{1,6})\s?",
                      lambda m: m.group(0) if m.group(1) is None else safe_chr(int(m.group(1), 16)), value)

    def one(m):
        if m.group(1) is not None:
            high, low = int(m.group(1), 16), int(m.group(2), 16)
            return safe_chr(0x10000 + ((high - 0xD800) << 10) + (low - 0xDC00))
        number = m.group(3) or m.group(4) or m.group(5)
        return m.group(0) if number is None else safe_chr(int(number, 16))
    return re.sub(r"\\\\|\\u([dD][89abAB][0-9a-fA-F]{2})\\u([dD][c-fC-F][0-9a-fA-F]{2})"
                  r"|\\u\{([0-9a-fA-F]+)\}|\\u([0-9a-fA-F]{4})|\\x([0-9a-fA-F]{2})", one, value)


def in_control(stack):
    for tag, classes, role, uid in stack:
        low = tag.lower()
        if low in ("a", "button", "summary") or re.search(r"(?:button|link)$", low) or role.lower() in ("button", "link", "tab", "menuitem"):
            return True
    return False


# ------------------------------------------------------------------ the scanner

class Scan:
    def __init__(self, rel, text, ctx):
        self.rel, self.text, self.ctx = rel, text, ctx
        self.config = ctx.config
        self.starts = [0] + [m.end() for m in re.finditer("\n", text)]
        self.findings = []
        self.themes = set(ctx.themes)
        self.display = ctx.display_res
        suffix = Path(rel).suffix.lower()
        self.kind = ("css" if suffix in CSS_EXT else "html" if suffix in HTML_EXT
                     else "js" if suffix in JS_EXT else "content")
        self.jsx = suffix in JSX_EXT
        self.is_theme_file = any(r.match(rel) for r in ctx.theme_file_res)
        self.allowed = [name for regex, name in ctx.allowed if regex is None or regex.match(rel)]
        self.comments = []
        self.rule_spans = []
        self.css_parts = []
        self.js_parts = []
        self.remainder = None
        self.layer_parts = []
        self.whole_copy = None
        self.floating_classes = set()

    def line(self, offset):
        return bisect.bisect_right(self.starts, offset)

    def add(self, offset, rule, message, key, level=None):
        self.findings.append(Finding(self.rel, self.line(offset), rule, message, key, offset, level))

    def line_text(self, offset):
        number = self.line(offset)
        start = self.starts[number - 1]
        end = self.starts[number] - 1 if number < len(self.starts) else len(self.text)
        return self.text[start:end].strip()[:160]

    # -- preparing: split the file once, and add what it defines to the shared context

    def prepare(self):
        text = self.text
        if self.kind in ("css", "js"):
            copy = layer_copy_ok(text)
            if copy is not None:
                self.whole_copy = copy
                if copy[0] and self.kind == "css":
                    self.ctx.add_inline_layer(text, LAYER_HEADER.match(text).group(2))
                return
        words = [text]
        if self.kind == "css":
            self.add_css(0, text)
        elif self.kind == "html":
            self.remainder, css_parts, js_parts, self.layer_parts = split_html(text)
            words = [self.remainder] + [body for _, body in css_parts] + [body for _, body, _ in js_parts]
            for offset, ok, version, kind, body in self.layer_parts:
                if ok and kind == "css":
                    self.ctx.add_inline_layer(body, LAYER_HEADER.match(body).group(2))
            for m in re.finditer(r"<!--.*?(?:-->|\Z)", text, re.S):
                self.comments.append((m.start(), m.end()))
            for offset, body in css_parts:
                self.add_css(offset, body)
            for offset, body, jsx in js_parts:
                self.add_js(offset, body, jsx)
            self.markup_classes()
        elif self.kind == "js":
            self.add_js(0, text, self.jsx)
        else:
            for m in re.finditer(r"<!--.*?(?:-->|\Z)", text, re.S):
                self.comments.append((m.start(), m.end()))
        for chunk in words:  # pasted layer copies are left out: their words are not the app's
            self.ctx.lower_words.update(w.lower() for w in re.findall(r"[A-Za-z][a-z]+", chunk))
        self.contribute()

    def markup_classes(self):
        """Add what this page's markup shows about each class to the shared context: the tags it sits on, whether
        its text (descendants included) has lowercase letters, and whether its element is empty or aria-hidden."""
        info, remainder, stack = self.ctx.class_info, self.remainder, []

        def close(element):
            name, classes, hidden, flags = element
            for c in classes:
                entry = info.setdefault(c, {"tags": set(), "count": 0, "empty": 0, "hidden": 0, "text": False, "lower": False})
                entry["tags"].add(name)
                entry["count"] += 1
                entry["empty"] += 0 if flags["text"] else 1
                entry["hidden"] += 1 if hidden else 0
                entry["text"] = entry["text"] or flags["text"]
                entry["lower"] = entry["lower"] or flags["lower"]

        pos = 0
        for m in HTML_TAG.finditer(remainder):
            segment = entities_blank(remainder[pos:m.start()])
            if segment.strip():
                lower = bool(re.search(r"[a-z]", segment))
                for element in stack:
                    element[3]["text"] = True
                    element[3]["lower"] = element[3]["lower"] or lower
            pos = m.end()
            name = m.group(2).lower()
            if m.group(1):
                for k in range(len(stack) - 1, -1, -1):
                    if stack[k][0] == name:
                        for element in reversed(stack[k:]):
                            close(element)
                        del stack[k:]
                        break
                continue
            values = {a[0]: a[1] for a in html_attrs(m)}
            hidden = values.get("aria-hidden", "").strip().lower() == "true" or any(e[2] for e in stack)
            element = (name, values.get("class", "").split(), hidden, {"text": False, "lower": False})
            if name in VOID_TAGS or m.group(3).rstrip().endswith("/"):
                close(element)
            else:
                stack.append(element)
        for element in reversed(stack):
            close(element)

    def add_css(self, base, body):
        for m in re.finditer(r"/\*.*?(?:\*/|\Z)", body, re.S):
            self.comments.append((base + m.start(), base + m.end()))
        stripped = strip_css_comments(body)
        self.css_parts.append((base, stripped, css_rules(stripped)))

    def add_js(self, base, body, jsx):
        parts = split_js(body, jsx)
        self.comments.extend((base + a, base + b) for a, b in parts.comments)
        self.js_parts.append((base, body, jsx, parts))

    def contribute(self):
        ctx = self.ctx
        for base, stripped, rules in self.css_parts:
            for rule in rules:
                selector = rule.selector
                if selector.startswith("@"):
                    continue
                # A class this file places like a floating layer (fixed or absolute with a z-index, or with a
                # ::backdrop) takes the floating layers' shadow, unless it names a control (Claude's default).
                placed = bool(re.search(r"(?<![\w-])position\s*:\s*(?:fixed|absolute)", rule.decls, re.I)
                              and re.search(r"(?<![\w-])z-index\s*:\s*(?!auto\b)[-\w(]", rule.decls, re.I))
                backdrop = "::backdrop" in selector
                for part in split_selectors(selector) if placed or backdrop else ():
                    if backdrop and "::backdrop" in part:
                        compound = subject(part.split("::backdrop")[0])
                    elif placed:
                        compound = subject(part)
                    else:
                        continue
                    self.floating_classes.update(c for c in classes_of(compound) if not CONTROL_WORDS.search(c))
                if "--" in rule.decls:
                    inc, _ = selector_theme_sets(selector)
                    for prop, value, _ in parse_decls(rule.decls):
                        if not prop.startswith("--"):
                            continue
                        if inc:
                            for theme in inc:
                                ctx.theme_values.setdefault(theme, {}).setdefault(prop[2:], value)
                        elif not re.search(r"dark", selector, re.I):
                            ctx.app_values.setdefault(prop[2:], value)
                if "var(" in rule.decls:
                    for m in re.finditer(r"(?<![\w-])font(?:-family)?\s*:([^;{}]*)", rule.decls, re.I):
                        ctx.font_var_uses.update(VAR_NAME.findall(m.group(1)))
                if DISPLAY_FONT.search(rule.decls):
                    for part in split_selectors(selector):
                        ctx.display_classes.update(c for c in classes_of(subject(part)) if not EYEBROW.search(c))
        for base, body, jsx, parts in self.js_parts:
            for m in re.finditer(r"""fontFamily\s*:\s*['"`][^'"`]*?var\(\s*--([\w-]+)""", parts.nocomment):
                ctx.font_var_uses.add(m.group(1))

    # -- running the rules

    def run(self):
        if self.whole_copy is not None:
            ok, version = self.whole_copy
            if ok:
                self.ctx.inline_ok += 1
            else:
                self.add(0, "layer-intact", "a copy of a Gong brand layer file was edited: its fingerprint no longer "
                         "matches; copy the generated file again", "copy")
            return
        self.retired(self.text)
        if self.kind == "css":
            for base, stripped, rules in self.css_parts:
                self.css(base, stripped, rules)
        elif self.kind == "html":
            self.html()
        elif self.kind == "js":
            for base, body, jsx, parts in self.js_parts:
                self.js(base, body, jsx, parts)
        else:
            self.visible(self.text)
            self.emoji(self.text, 0, level="warn")

    # -- rules over raw text

    def retired(self, text, base=0):
        for m in RETIRED.finditer(text):
            self.add(base + m.start(), "retired-value", f"retired colour {m.group(0)} (gong.io no longer uses it)", m.group(0).lower())
        for m in POPPINS.finditer(text):
            self.add(base + m.start(), "retired-value", "Poppins is not a Gong typeface", "poppins")

    def env_hits(self, text, base):
        for m in ENV_NAME.finditer(text):
            if self.allowed and self.ctx.env_allowed(self.allowed, text, m.start(), m.end()):
                continue
            at = base + m.start()
            self.add(at, "env-name", f"environment name '{m.group(0)}' in text or a link people see; say 'Live' and use the short link", self.line_text(at))

    def hidden_hits(self, text, base):
        if self.ctx.hidden is None:
            return
        for m in self.ctx.hidden.finditer(text):
            name = self.ctx.hidden_spelling.get(m.group(0).lower(), m.group(0))
            self.add(base + m.start(), "hidden-name", f"the code name '{m.group(0)}' (hidden_names: {name}) in text, a link or an "
                     "attribute people see; name the tool the way people know it", name)

    def visible(self, text, base=0):
        for m in MIDDLE_DOT.finditer(text):
            self.add(base + m.start(), "middle-dot", "middle dot as a separator in text people see; use a comma, a word or a line break", self.line_text(base + m.start()))
        self.env_hits(text, base)
        self.hidden_hits(text, base)

    def emoji(self, text, base, level=None, mode="text", context=()):
        """Emoji and symbols that stand in for icons. Arrows, the multiplication sign and keyboard symbols
        count by mode: never in running text ("text"), at the start or end of the text of a button or link
        ("markup", with its element stack as context), at the edge of a short string ("code"), always in
        CSS content ("decoration")."""
        stripped = text.strip()
        for m in ICON_CHAR.finditer(text):
            char = m.group(0)
            if char in TYPOGRAPHIC_OK:
                continue
            if char in FLEXIBLE_CHARS:
                at_edge = stripped.startswith(char) or stripped.endswith(char)
                if mode == "text":
                    continue
                if mode == "markup" and not (in_control(context) and at_edge):
                    continue
                if mode == "code" and not (at_edge and len(stripped.split()) <= 4):
                    continue
            self.add(base + m.start(), "emoji-icon", f"'{char}' (U+{ord(char[0]):04X}) stands in for an icon; use a Lucide line icon "
                     "or one of the system's two-tone icons", char, level)
        for m in re.finditer(r"&#x([0-9a-f]+);|&#(\d+);", text, re.I):
            try:
                char = chr(int(m.group(1), 16) if m.group(1) else int(m.group(2)))
            except (ValueError, OverflowError):
                continue
            if ICON_CHAR.fullmatch(char) and (char not in FLEXIBLE_CHARS or mode == "decoration"):
                self.add(base + m.start(), "emoji-icon", f"'{char}' (U+{ord(char):04X}) stands in for an icon; use a Lucide line icon "
                         "or one of the system's two-tone icons", char, level)

    def theme_os(self, text, base=0):
        for m in PREFERS.finditer(text):
            self.add(base + m.start(), "theme-os", "prefers-color-scheme picks a theme from the computer's setting; Light unless someone picked Dark", self.line_text(base + m.start()))

    def theme_like(self, value):
        """A theme name other than light: one of this app's themes, or a word that picks one."""
        if value == "light":
            return False
        return value in self.themes or value in ("dark", "system", "auto", "os", "girly")

    def theme_name(self, name, offset, where):
        if self.themes and name not in self.themes:
            self.add(offset, "theme-unknown", f"theme '{name}' in {where} is not one of this app's themes ({', '.join(sorted(self.themes))})", name)

    def google_fonts(self, text, base=0):
        for m in GOOGLE_FONTS.finditer(text):
            query = html_lib.unescape(m.group(1))
            for param in re.split(r"[&;]", query):
                if not param.lower().startswith("family="):
                    continue
                for family in unquote_plus(param[7:]).split("|"):
                    name = " ".join(family.split(":")[0].split())
                    if name and name.lower() not in GOOGLE_FONT_FAMILIES:
                        self.add(base + m.start(), "font-family", f"Google Fonts loads '{name}', which is not a brand typeface; "
                                 "the layer serves the brand fonts", name.lower())

    def typed_caps(self, text, base, context=()):
        if any(self.caps_exempt(element) for element in context):
            return
        for start, end, words in caps_runs(entities_blank(text), self.ctx.acronyms):
            phrase = " ".join(text[start:end].split())
            if len(words) >= 2:
                self.add(base + start, "typed-caps", f"capitals typed in '{phrase[:60]}'; write it in sentence case "
                         "(only BN Axel display text is set in capitals)", phrase[:60])
                continue
            letters = "".join(LETTERS.findall(words[0]))
            # A capital word the app never writes in lowercase or sentence case is an acronym the config does not
            # list (PITR, SIGINT). One written both ways is a typed label (Claude's default).
            if letters.lower() not in self.ctx.lower_words:
                continue
            if len(letters) >= 3 and re.search(r"\d", text[start:end]):
                self.add(base + start, "typed-caps", f"capitals typed in '{phrase[:60]}'; write it in sentence case, such as "
                         "'Step 1' (only BN Axel display text is set in capitals)", phrase[:60])
            elif len(letters) >= 4:
                self.add(base + start, "typed-caps", f"capitals typed in '{phrase[:60]}'; write it in sentence case "
                         "unless it is an acronym (add it to the config's acronyms)", phrase[:60], "warn")

    def caps_exempt(self, element):
        tag, classes, role, uid = element
        if tag.lower() in CODE_TAGS:
            return True
        if self.ctx.public:
            return False  # no BN Axel in the public profile, so no element holds display capitals
        names = classes.split()
        if any(c in self.ctx.display_classes or CAPS_DISPLAY_CLASS.fullmatch(c) for c in names):
            return True
        if self.display:
            pseudo = tag + "".join("." + c for c in names)
            return any(r.search(pseudo) for r in self.display)
        return False

    def headings(self, texts, text_of, base=0):
        """title-case-heading over [(start, end, stack)]: the text of each h1 to h6, joined."""
        groups = collections.OrderedDict()
        for start, end, stack in texts:
            heading = next((e for e in reversed(stack) if e[0].lower() in HEADING_TAGS), None)
            if heading is None:
                continue
            groups.setdefault(heading[3], []).append((start, end))
        for spans in groups.values():
            words = " ".join(" ".join(entities_blank(text_of(s, e)).split()) for s, e in spans).strip()
            if words and title_case(words, self.ctx.names, self.ctx.acronyms):
                self.add(base + spans[0][0], "title-case-heading", f"heading typed in Title Case: '{words[:60]}'; headings are sentence case", words[:60])

    # -- CSS

    def is_display(self, selector, decls):
        if self.ctx.public:
            return False  # the public profile has no BN Axel: display text is Inter Tight in its own case
        parts = split_selectors(selector)
        if parts and any(EYEBROW.search(c) for p in parts for c in classes_of(subject(p))):
            return False  # eyebrows are never BN Axel display text
        if DISPLAY_FONT.search(decls) or any(r.search(selector) for r in self.display):
            return True
        if not parts:
            return False
        for part in parts:
            subj = subject(part)
            if not (BN_AXEL_CLASS.search(subj) or self.ctx.display_classes.intersection(classes_of(subj))):
                return False
        return True

    def declarations(self, selector, decls, base, kind="rule", props=None, parents=(), element=None, keyframe=False):
        """Every rule that reads one block of declarations: a CSS rule, a style attribute or CSS text in code."""
        if props is None:
            props = parse_decls(decls, base)
        display = self.is_display(selector, decls)
        for m in re.finditer(r"(?<![\w-])font-family\s*:\s*([^;{}]+)", decls, re.I):
            self.font_list(m.group(1), base + m.start())
        for m in re.finditer(r"(?<![\w-])font\s*:\s*([^;{}]+)", decls, re.I):
            families = shorthand_families(m.group(1))
            if families:
                self.font_list(families, base + m.start())
        colours = FRAGMENT_URL.sub(lambda m: blank(m.group(0), 0, len(m.group(0))), decls)
        for m in HEX_COLOR.finditer(colours):
            self.add(base + m.start(), "raw-color", f"raw colour {m.group(0)} outside the brand layer; use a token", m.group(0).lower())
        for m in FUNC_COLOR.finditer(colours):
            self.add(base + m.start(), "raw-color", f"raw colour {m.group(0)}...) outside the brand layer; use a token", m.group(0).lower())
        if not display:
            for m in re.finditer(r"text-transform\s*:\s*(?:uppercase|var\([^)]*,\s*uppercase\s*\))", decls, re.I):
                self.add(base + m.start(), "uppercase", f"capitals on '{short(selector)}'; only BN Axel display text is set in capitals", short(selector))
            for m in re.finditer(r"letter-spacing\s*:\s*(-?\d*\.?\d+)\s*(em|rem|px)?", decls, re.I):
                if too_wide(m.group(1), m.group(2)):
                    self.add(base + m.start(), "letter-spacing", f"letter-spacing {m.group(1)}{m.group(2) or ''} on '{short(selector)}'; labels take no added letter-spacing", short(selector))
        self.font_variables(props)
        if not keyframe:
            self.card_shadow(selector, props)
        for prop, value, offset in props:
            if prop == "content":
                at = offset + len(prop)
                self.visible(value, at)
                self.emoji(decode_escapes(value, css=True), at, mode="decoration")
        self.theme_os(decls, base)
        if not self.is_theme_file:
            self.token_redefined(props)
        self.gradient_fill(selector, props)
        self.graphic_text(selector, props, display)
        self.small_text(selector, props)
        self.color_mix(selector, props)
        if not keyframe:
            self.accent_bar(selector, props, kind, element)
            self.control_shape(selector, props)
            self.logo_filter(selector, props, element)
            self.text_opacity(selector, props)
            self.pair_contrast(selector, props, parents)
        if kind == "attr":
            for prop, value, offset in props:
                if prop in ("outline", "outline-style", "outline-width") and self.outline_off(prop, value):
                    self.add(offset, "focus-removed", f"outline turned off on '{short(selector)}' in an inline style, so keyboard "
                             "users lose the focus ring; keep the layer's ring", short(selector))

    def font_list(self, value, offset):
        names = parse_families(value)
        real = [n for n in names if not n.startswith("var(") and n not in FONT_KEYWORDS]
        if not real:
            return
        first_is_var = names and names[0].startswith("var(")
        for index, name in enumerate(real):
            primary = index == 0 and not first_is_var
            if self.ctx.public and BN_AXEL.fullmatch(name):
                self.add(offset, "font-family", f"'{name}' is BN Axel, Gong's licensed font, which the public profile leaves "
                         "out; display text there is Inter Tight in its own case", name)
                continue
            if not (is_brand_family(name) or (not primary and name in FALLBACK_FAMILIES)):
                role = "typeface" if primary else "font in the stack"
                self.add(offset, "font-family", f"{role} '{name}' is not a brand typeface (BN Axel Grotesk, Inter Tight, Inter, IBM Plex Mono)", name)

    def font_variables(self, props):
        """A custom property that holds a font stack: by its name (font, family, typeface), because a
        font-family or font shorthand reads it anywhere in the app, or because it names a known non-brand face."""
        for prop, value, offset in props:
            if not prop.startswith("--") or not looks_like_families(value):
                continue
            name = prop[2:]
            fontish = re.search(r"font|family|typeface", name, re.I) and not re.search(
                r"size|weight|line|height|spacing|tracking|leading|style|feature|variation|smoothing", name, re.I)
            if fontish or name in self.ctx.font_var_uses or any(f in KNOWN_NON_BRAND for f in parse_families(value)):
                self.font_list(value, offset)

    def card_shadow(self, selector, props):
        for prop, value, offset in props:
            if prop != "box-shadow" or not self.elevation(value):
                continue
            for part in split_selectors(selector) or [selector]:
                if FOCUS_MARK.search(part):
                    continue
                subj = subject(part)
                if FLOATING.search(subj) or not subj or self.floating_classes.intersection(classes_of(subj)):
                    continue
                self.add(offset, "card-shadow", f"shadow on '{short(selector)}'; only floating layers (dialogs, drawers, menus, "
                         "popovers and toasts) take shadows, so cards, tiles and buttons stay flat", short(selector))
                break

    def elevation(self, value):
        """True when a box-shadow lifts its box: a layer that is not inset, with a blur or an offset."""
        v = value.strip()
        if v.lower() in ("none", "initial", "unset", "inherit", "revert", "0", ""):
            return False
        if "var(" in v:
            resolved = self.ctx.resolve(v)
            if resolved is not None:
                v = resolved
            elif re.fullmatch(r"var\([^()]*\)", v):
                return bool(re.search(r"var\(\s*--[\w-]*(?:shadow|elev|lift|glow|drop)", v, re.I))
        for layer in split_top(v):
            tokens = split_top(layer, None)
            if any(t.lower() == "inset" for t in tokens):
                continue
            lengths = [self.ctx.length(t) for t in tokens if LENGTH.fullmatch(t.lower())]
            lengths = [x for x in lengths if x is not None]
            if len(lengths) >= 2 and (lengths[0] != 0 or lengths[1] != 0 or (len(lengths) > 2 and lengths[2] > 0)):
                return True
        return False

    def token_redefined(self, props):
        names = self.ctx.redefine_names()
        if not names:
            return
        for prop, value, offset in props:
            if prop.startswith("--") and prop[2:] in names:
                self.token_hit(prop, offset)

    def token_hit(self, prop, offset):
        self.add(offset, "token-redefined", f"'{prop}' is a layer token. App styles load after the layer, so this changes every "
                 f"gb- component that reads it; rename it (for example --app-{prop[2:]}) or move it to a theme file listed in theme_files", prop)

    def gradient_fill(self, selector, props):
        for prop, value, offset in props:
            if not (prop.startswith("background") or prop.startswith("border-image") or prop in ("fill", "content", "list-style-image")):
                continue
            if blended_gradient(value):
                self.add(offset, "gradient-fill", f"gradient fill on '{short(selector)}'; fills are solid (the gradient tokens are only "
                         "soft glows and scrims, through var(--gradient-...))", short(selector))

    def bar_colour(self, value, depth=0):
        """'neutral' or 'accent' for a border or shadow colour, or None when the check cannot tell."""
        v = value.strip()
        low = v.lower()
        if not v or depth > 8:
            return None
        if low in ("transparent", "inherit", "initial", "unset", "none"):
            return "neutral"
        if low == "currentcolor":
            return None
        m = re.fullmatch(r"var\(\s*--([\w-]+)\s*(?:,(.*))?\)", v, re.S)
        if m:
            name = m.group(1)
            if name in NEUTRAL_TOKENS or name.startswith(("surface-", "neutral-")):
                return "neutral"
            if self.ctx.is_layer_token(name):
                colour = self.ctx.colour(v)
                return None if colour is None else ("neutral" if chroma(colour) < 0.1 or colour[3] < 0.35 else "accent")
            defined = self.ctx.app_values.get(name)
            if defined is not None:
                found = self.bar_colour(defined, depth + 1)
                if found:
                    return found
            if m.group(2):
                found = self.bar_colour(m.group(2), depth + 1)
                if found:
                    return found
            if NEUTRAL_NAME.search(name):
                return "neutral"
            return "accent" if ACCENT_NAME.search(name) else None
        colour = parse_colour(v)
        if colour is not None:
            return "neutral" if chroma(colour) < 0.1 or colour[3] < 0.35 else "accent"
        if low in COLOUR_WORDS:
            return "accent"
        return None

    def border_parts(self, value):
        width = style = colour = None
        for token in split_top(value, None):
            low = token.lower()
            if low in BORDER_STYLES:
                style = low
            elif low in WIDTH_KEYWORDS or LENGTH.fullmatch(low):
                width = token
            elif low.startswith(("var(", "calc(")):
                resolved = self.ctx.resolve(token) if low.startswith("var(") else token
                if resolved is not None and (self.ctx.length(resolved) is not None) and parse_colour(resolved) is None:
                    width = token
                else:
                    colour = token
            else:
                colour = token
        return width, style, colour

    def draws_line(self, selector, props, element, side, visible_sides):
        """True when a one-side border draws a line, not the edge of a box (Claude's default): a bottom border on a
        link-like subject is its underline, and an empty element that sets a width but no height or padding is a
        connector line."""
        set_props = {p for p, v, o in props}
        parts = split_selectors(selector) or [selector]
        if visible_sides == {"bottom"} and side == "bottom":
            values = {p: v.strip().lower() for p, v, o in props}
            inline_link = values.get("cursor") == "pointer" and values.get("display") in ("inline", "inline-block")
            for part in parts:
                subj = subject(part)
                tags = set()
                for c in classes_of(subj):
                    tags |= self.ctx.class_info.get(c, {}).get("tags", set())
                if not (tag_of(subj) == "a" or "[href" in subj or any(c.lower().endswith("link") for c in classes_of(subj))
                        or inline_link or (element is not None and element[0] == "a") or (tags and tags <= {"a"})):
                    break
            else:
                return True
        if len(visible_sides) != 1 or set_props & {"padding", "padding-top", "padding-bottom", "padding-left", "padding-right",
                                                   "padding-block", "padding-inline", "padding-block-start", "padding-block-end",
                                                   "padding-inline-start", "padding-inline-end"}:
            return False
        across, along = (("height", "min-height", "block-size"), ("width", "inline-size")) if side in ("top", "bottom") \
            else (("width", "min-width", "inline-size"), ("height", "block-size"))
        if set_props & set(across) or not set_props & set(along):
            return False
        if element is not None:
            return len(element) > 2 and bool(element[2])
        for part in parts:
            if "::" in part:
                return False
            info = [self.ctx.class_info.get(c) for c in classes_of(subject(part))]
            if not info or any(i is None or i["count"] == 0 or i["empty"] < i["count"] for i in info):
                return False
        return True

    def accent_bar(self, selector, props, kind, element=None):
        parts = split_selectors(selector) or [selector]
        if any(FOCUS_MARK.search(p) for p in parts) or any(SPINNER.search(subject(p)) for p in parts):
            return
        # A box with no width or height drawn by its borders is a triangle (a caret or a tooltip arrow).
        if any(p in ("width", "height") and self.ctx.length(v) == 0 for p, v, o in props):
            return
        selected = bool(SELECTED_MARK.search(selector))
        quote = bool(QUOTE_SEL.search(selector))
        base = {"width": None, "style": None, "colour": None}
        sides = {}
        for prop, value, offset in props:
            if prop == "border":
                width, style, colour = self.border_parts(value)
                base = {"width": width, "style": style or "none", "colour": colour}
                sides = {}
            elif prop in ("border-width", "border-color", "border-style"):
                field = {"border-width": "width", "border-color": "colour", "border-style": "style"}[prop]
                values = split_top(value, None)
                if len(values) < 2:
                    base[field] = values[0] if values else None
                    continue
                expanded = {2: lambda v: [v[0], v[1], v[0], v[1]], 3: lambda v: [v[0], v[1], v[2], v[1]]}.get(
                    len(values), lambda v: v[:4])(values)
                if len(set(expanded)) > 1:
                    for side, item in zip(("top", "right", "bottom", "left"), expanded):
                        sides.setdefault(side, {"offset": offset})[field] = item
            elif prop == "box-shadow":
                self.inset_bar(selector, value, offset, selected)
            else:
                m = SIDE_LONGHAND.fullmatch(prop)
                if not m:
                    continue
                side, field = SIDES[m.group(1)], m.group(2)
                if field is None:
                    width, style, colour = self.border_parts(value)
                    sides[side] = {"offset": offset, "width": width or "medium", "style": style or "none", "colour": colour, "short": True}
                else:
                    entry = sides.setdefault(side, {"offset": offset})
                    entry["offset"] = offset
                    entry[{"width": "width", "color": "colour", "style": "style"}[field]] = value
        resolved = {}
        for side, entry in sides.items():
            if entry.get("short"):
                resolved[side] = (entry["style"], entry["width"])
            else:
                resolved[side] = (entry.get("style") or base["style"],
                                  entry.get("width") or base["width"] or ("medium" if base["style"] not in (None, "none") else None))
        visible_sides = {s for s, (style, _) in resolved.items() if style not in (None, "none", "hidden")}
        if base["style"] not in (None, "none", "hidden"):
            visible_sides |= {s for s in ("top", "right", "bottom", "left") if s not in resolved}
        for side, entry in sides.items():
            style, width_token = resolved[side]
            if style in ("none", "hidden"):
                continue
            width = self.ctx.length(width_token) if width_token is not None else None
            if width is not None and width < 2 - 0.01:
                continue
            colour = entry.get("colour") or base["colour"]
            if colour is None or self.bar_colour(colour) != "accent":
                continue
            if (base["colour"] or "").strip().lower() == "transparent":
                continue  # one coloured side of a transparent border: an arrow, not a bar
            if width is None and not entry.get("colour"):
                continue
            if selected and (width is None or width <= 2 + 0.01):
                continue
            if quote and side == "left" and width is not None and abs(width - 4) < 0.6:
                found = self.ctx.colour(colour)
                if found is not None and hex6(found) == LAVENDAR:
                    continue
            if self.draws_line(selector, props, element, side, visible_sides):
                continue
            bar = f"a {width:g}px accent bar" if width is not None else "an accent bar"
            self.add(entry["offset"], "accent-bar", f"{bar} on the {side} of '{short(selector)}'; boxes take a 1px edge all round "
                     "(the exceptions are the quote's 4px Lavendar rule, the 2px active-tab underline, the 2px selected edge and "
                     "focus rings)", f"{short(selector)}|{side}")

    def inset_bar(self, selector, value, offset, selected):
        resolved = self.ctx.resolve(value) if "var(" in value else value
        for layer in split_top(resolved if resolved is not None else value):
            tokens = split_top(layer, None)
            if not any(t.lower() == "inset" for t in tokens):
                continue
            lengths, colour = [], None
            for token in tokens:
                if token.lower() == "inset":
                    continue
                length = self.ctx.length(token) if (LENGTH.fullmatch(token.lower()) or token.lower().startswith(("var(", "calc("))) else None
                if length is not None and parse_colour(token) is None:
                    lengths.append(length)
                else:
                    colour = token
            if len(lengths) < 2 or colour is None:
                continue
            x, y = lengths[0], lengths[1]
            blur = lengths[2] if len(lengths) > 2 else 0
            spread = lengths[3] if len(lengths) > 3 else 0
            if blur or spread or not ((abs(x) >= 2 and y == 0) or (abs(y) >= 2 and x == 0)):
                continue
            width = abs(x) or abs(y)
            if selected and width <= 2 + 0.01:
                continue
            if self.bar_colour(colour) == "accent":
                side = ("left" if x > 0 else "right") if x else ("top" if y > 0 else "bottom")
                self.add(offset, "accent-bar", f"an inset shadow drawn as a {width:g}px accent bar on the {side} of '{short(selector)}'; "
                         "boxes take a 1px edge all round, with no accent bars", f"{short(selector)}|inset-{side}")

    def outline_off(self, prop, value):
        low = value.strip().lower()
        if prop == "outline-width":
            return low in ("0", "0px")
        if prop == "outline-style":
            return low in ("none", "hidden")
        tokens = low.split()
        return low in ("none", "0", "0px", "hidden") or "none" in tokens or (bool(tokens) and tokens[0] in ("0", "0px"))

    def control_kind(self, compound):
        low = compound.lower()
        if "::" in low and "::file-selector-button" not in low:
            return None
        tag = tag_of(low)
        classes = classes_of(low)
        if tag == "textarea" or any(re.search(r"(?:^|[-_])textarea(?:--[\w-]+)?$", c) for c in classes):
            return "multiline"
        if tag == "input":
            kind = re.search(r"""\[type\s*=\s*["']?(\w+)""", low)
            if kind and kind.group(1) in ("checkbox", "radio", "range", "color", "file", "hidden", "image"):
                return None
            return "pill"
        if tag in ("button", "select") or "::file-selector-button" in low:
            return "pill"
        for c in classes:
            if "swatch" in c:
                continue  # a colour swatch is a sample, not a control
            if re.search(r"(?:^|[-_])(?:btn|button|chip|tag|pill|badge|input|select|search(?:-?(?:box|field|input))?)(?:--[\w-]+)?$", c):
                return "pill"
        return None

    def radius_px(self, value):
        found = []
        for token in split_top(value.split("/")[0], None):
            low = token.lower()
            if low.endswith("%"):
                try:
                    found.append(9999.0 if float(low[:-1]) >= 50 else None)
                except ValueError:
                    return None
                continue
            if "pill" in low or "full" in low or "round" in low:
                found.append(9999.0)
                continue
            found.append(self.ctx.length(token))
        if not found or any(x is None for x in found):
            return None
        return min(found)

    def pill_role(self, compound):
        """button, chip or field, for a compound control_kind calls a pill."""
        low = compound.lower()
        if tag_of(low) == "button" or "::file-selector-button" in low or any(
                re.search(r"(?:^|[-_])(?:btn|button)(?:--[\w-]+)?$", c) for c in classes_of(low)):
            return "button"
        if any(re.search(r"(?:^|[-_])(?:chip|tag|pill|badge)(?:--[\w-]+)?$", c) for c in classes_of(low)):
            return "chip"
        return "field"

    def not_a_pill(self, part, props):
        """Controls the system does not draw as pills (Claude's default): a button that is a row or a card (full width
        and start-aligned, or a column), a button in a nav, menu, tree, list, tab row or sidebar, and a chip, tag or
        badge drawn as an icon square (equal width and height)."""
        role = self.pill_role(subject(part))
        values = {p: " ".join(v.lower().split()) for p, v, o in props}
        if role == "button":
            full_row = values.get("width") == "100%" and values.get("text-align") in ("left", "start")
            column = values.get("flex-direction", "").startswith("column") or values.get("flex-flow", "").startswith("column")
            return full_row or column or bool(ROW_CONTAINER.search(part))
        if role == "chip":
            if values.get("aspect-ratio") in ("1", "1 / 1", "1/1"):
                return True
            width, height = values.get("width"), values.get("height")
            if width and height:
                w, h = self.ctx.length(width), self.ctx.length(height)
                return w is not None and h is not None and abs(w - h) < 0.01
        return False

    def control_shape(self, selector, props):
        radii = [(v, o) for p, v, o in props if p == "border-radius"]
        if not radii:
            return
        for part in split_selectors(selector):
            kind = self.control_kind(subject(part))
            if not kind:
                continue
            if kind == "pill" and self.not_a_pill(part, props):
                return
            for value, offset in radii:
                radius = self.radius_px(value)
                if radius is None:
                    continue
                if kind == "pill" and radius < 16 - 1e-9:
                    self.add(offset, "control-shape", f"{radius:g}px corners on '{short(selector)}'; buttons, fields, tags, chips and "
                             "badges are pills (radius-pill)", short(selector))
                elif kind == "multiline" and radius < 12 - 1e-9:
                    self.add(offset, "control-shape", f"{radius:g}px corners on '{short(selector)}'; multi-line fields take radius-2xl", short(selector))
            return

    def graphic_name(self, value):
        if not value or value.strip().lower() in ("inherit", "currentcolor", "transparent", "initial", "unset"):
            return None
        named = re.fullmatch(r"\s*var\(\s*--([\w-]+)\s*(?:,[^()]*)?\)\s*", value)
        if named and named.group(1) in GRAPHIC_TOKENS:
            return GRAPHIC_TOKENS[named.group(1)], "light"
        for theme in self.ctx.colour_themes():
            colour = self.ctx.colour(value, theme)
            if colour is not None and colour[3] > 0:
                name = GRAPHIC.get(hex6(colour))
                if name:
                    return name, theme
        return None

    def graphic_text(self, selector, props, display):
        if display:
            return
        parts = split_selectors(selector)
        # color on an icon (an svg, img, path or use, or a class ending in icon or ico) colours a graphic.
        if parts and all(tag_of(subject(p)) in ("svg", "img", "path", "use", "image")
                         or any(re.search(r"(?:icon|ico)$", c, re.I) for c in classes_of(subject(p))) for p in parts):
            return
        svg_text = any(tag_of(subject(p)) in SVG_TEXT_TAGS for p in parts)
        for prop, value, offset in props:
            if prop in ("color", "-webkit-text-fill-color") or (prop == "fill" and svg_text):
                found = self.graphic_name(value)
                if found:
                    self.graphic_hit(found, offset, short(selector))

    def graphic_hit(self, found, offset, where):
        name, theme = found
        when = "" if theme == "light" else f" (in {theme})"
        self.add(offset, "graphic-text", f"{name}{when} as a text colour on '{where}'; Teal, Pink and Blue are for graphics, not words "
                 "(BN Axel stats are the one exception)", f"{where}|{name}")

    def font_px(self, value, depth=0):
        v = value.strip().lower()
        if depth > 8 or not v:
            return None
        func = re.fullmatch(r"(max|min|clamp)\((.*)\)", v, re.S)
        if func:
            values = [self.font_px(a, depth + 1) for a in split_top(func.group(2))]
            known = [x for x in values if x is not None]
            if not known:
                return None
            if func.group(1) == "max":
                return max(known)
            if func.group(1) == "min":
                return min(known)
            return values[0]
        if "var(" in v:
            resolved = self.ctx.resolve(value)
            return None if resolved is None else self.font_px(resolved, depth + 1)
        keywords = {"xx-small": 9.0, "x-small": 10.0, "small": 13.0, "medium": 16.0, "large": 18.0, "x-large": 24.0, "xx-large": 32.0}
        if v in keywords:
            return keywords[v]
        m = re.fullmatch(r"(\d*\.?\d+)(px|rem|pt)", v)
        if m:
            number = float(m.group(1))
            return number * {"px": 1, "rem": 16, "pt": 4 / 3}[m.group(2)]
        if v.startswith("calc("):
            return self.ctx.length(v)
        return None

    def glyph_subject(self, selector):
        """True when every selector's subject names a glyph or decoration (a caret, chevron, arrow, icon, glyph,
        monogram or watermark), so the rule sizes or fades a graphic, not text people read."""
        parts = split_selectors(selector)
        return bool(parts) and all(any(GLYPH_WORDS.search(c) for c in classes_of(subject(p))) for p in parts)

    def small_text(self, selector, props):
        if self.glyph_subject(selector):
            return  # a glyph's size; the glyph itself is emoji-icon's to flag
        for prop, value, offset in props:
            size = value if prop == "font-size" else shorthand_size(value) if prop == "font" else None
            if size is None:
                continue
            px = self.font_px(size)
            if px is not None and 0 < px < 12 - 1e-6:
                self.small_hit(px, offset, short(selector))

    def small_hit(self, px, offset, where):
        self.add(offset, "small-text", f"text at {px:g}px on '{where}'; no text is smaller than text-xs (12px)", f"{px:g}px")

    def color_mix(self, selector, props):
        for prop, value, offset in props:
            if "color-mix(" in value.lower():
                self.add(offset, "color-mix", f"color-mix() on '{short(selector)}' makes a colour outside the system; use a token", short(selector))

    def logo_filter(self, selector, props, element):
        named = bool(LOGO_WORDS.search(selector)) if element is None else bool(
            element[0] in ("img", "svg", "picture", "image", "source") and LOGO_WORDS.search(" ".join(v for _, v, _, _ in element[1])))
        if element is None and not named:
            # An image in a brand, masthead or header is the logo there (Claude's default).
            named = any(tag_of(subject(p)) in ("img", "svg", "picture", "image") and re.search(r"brand|masthead|header", p, re.I)
                        for p in split_selectors(selector))
        for prop, value, offset in props:
            if prop not in ("filter", "-webkit-filter"):
                continue
            # A filter read from a custom property named for a logo recolours the logo wherever it is used.
            if not named and not re.search(r"var\(\s*--[\w-]*logo", value, re.I):
                continue
            if value.strip().lower() not in ("none", "initial", "unset", "inherit", "revert"):
                self.add(offset, "logo-filter", f"a CSS filter on the logo '{short(selector)}'; logos swap by file per theme and are never "
                         "recoloured", short(selector))

    def text_opacity(self, selector, props):
        values = [(v, o) for p, v, o in props if p == "opacity"]
        if not values or DISABLED_MARK.search(selector) or self.glyph_subject(selector):
            return
        # A subject whose classes sit only on aria-hidden elements in the scanned markup is decoration.
        parts = split_selectors(selector)
        infos = [self.ctx.class_info.get(c) for p in parts for c in classes_of(subject(p))]
        if parts and infos and all(i is not None and i["count"] and i["hidden"] == i["count"] for i in infos):
            return
        value, offset = values[-1]
        if "disabled" in value:
            return
        number = self.ctx.resolve(value) if "var(" in value else value
        try:
            number = float(number.strip()[:-1]) / 100 if number.strip().endswith("%") else float(number)
        except (ValueError, AttributeError):
            return
        if not 0 < number < 1:
            return
        if any(p in TEXT_PROPS or p.startswith(("font", "text-")) for p, _, _ in props):
            self.add(offset, "text-opacity", f"opacity {number:g} on '{short(selector)}', which sets text; faded text loses contrast, "
                     "so use text-body instead", short(selector))

    def large_text(self, props):
        size = weight = None
        for prop, value, _ in props:
            if prop == "font-size":
                size = self.font_px(value)
            elif prop == "font":
                token = shorthand_size(value)
                size = self.font_px(token) if token else size
                m = re.search(r"(?:^|\s)(bold|bolder|[1-9]00)(?:\s|$)", value)
                if m:
                    weight = 700.0 if m.group(1).startswith("bold") else float(m.group(1))
            elif prop == "font-weight":
                resolved = self.ctx.resolve(value) if "var(" in value else value
                if resolved:
                    low = resolved.strip().lower()
                    weight = 700.0 if low in ("bold", "bolder") else (float(low) if re.fullmatch(r"\d+(?:\.\d+)?", low) else weight)
        if size is None:
            return False
        return size >= 24 - 1e-6 or (size >= 18.66 - 1e-6 and (weight or 400) >= 600)

    def pair_contrast(self, selector, props, parents, where=None):
        fg = bg = None
        for prop, value, offset in props:
            if prop == "color":
                fg = (value, offset)
            elif prop in ("background-color", "background"):
                bg = (value, offset)
            elif prop == "content" and value.strip() in ('""', "''"):
                return
        if not fg or not bg or any("forced-colors" in p for p in parents):
            return
        if re.search(r"url\(|gradient\(", bg[0], re.I) or len(split_top(bg[0], None)) != 1:
            return
        for part in split_selectors(selector):
            subj = subject(part).lower()
            if tag_of(subj) in NON_TEXT_TAGS or re.search(r"""type\s*=\s*["']?(?:checkbox|radio|range|color)""", subj) \
                    or "::backdrop" in subj or "scrollbar" in subj or "::-webkit-slider" in subj or "::-moz-range" in subj:
                return
        inc, exc = selector_theme_sets(selector)
        themes = [t for t in self.ctx.themes if t in inc] if inc else [t for t in self.ctx.themes if t not in exc]
        need = 3.0 if self.large_text(props) else 4.5
        worst = None
        for theme in themes:
            f, b = self.ctx.colour(fg[0], theme, app=False), self.ctx.colour(bg[0], theme, app=False)
            if f is None or b is None or b[3] < 0.95:
                continue
            page = self.ctx.colour("var(--surface-page)", theme, app=False) or (1.0, 1.0, 1.0, 1.0)
            ratio = contrast_ratio(f, b, page)
            if ratio + 1e-9 < need and (worst is None or ratio < worst[1]):
                worst = (theme, ratio)
        if worst:
            label = where or short(selector)
            self.add(fg[1], "pair-contrast", f"text on '{label}' reads {worst[1]:.1f}:1 against its background in {worst[0]} "
                     f"(it needs {need:g}:1)", f"{label}|{worst[0]}")

    def css(self, base, stripped, rules):
        self.theme_os(stripped, base)
        self.google_fonts(stripped, base)
        focus_styles, removals, display_rules, upper = [], [], [], set()
        for rule in rules:
            selector = rule.selector
            for m in re.finditer(r"""\[\s*data-theme\s*[~|^$*]?=\s*["']?([\w-]+)""", selector):
                self.theme_name(m.group(1), base + rule.start, "a selector")
            self.rule_spans.append((base + rule.sel_start, base + rule.end, base + rule.start))
            if selector.startswith("@") and not selector.lower().startswith(("@font-face", "@page")):
                continue
            keyframe = bool(KEYFRAME_STOP.fullmatch(selector)) or any("keyframes" in p.lower() for p in rule.parents)
            props = parse_decls(rule.decls, base + rule.start)
            self.declarations(selector, rule.decls, base + rule.start, props=props, parents=rule.parents, keyframe=keyframe)
            if selector.lower().startswith("@") or keyframe:
                continue
            removes = [(p, v, o) for p, v, o in props if p in ("outline", "outline-style", "outline-width") and self.outline_off(p, v)]
            replacement = any((p == "box-shadow" and v.strip().lower() not in ("none", "0"))
                              or p.startswith(("border", "background", "text-decoration", "stroke", "fill", "filter")) or p == "color"
                              or (p.startswith("outline") and p != "outline-offset" and not self.outline_off(p, v))
                              for p, v, o in props)
            parts = split_selectors(selector)
            focus_rule = replacement and any(FOCUS_MARK.search(part) for part in parts)
            if focus_rule:
                for part in parts:
                    if FOCUS_MARK.search(part):
                        focus_styles.append(normal_selector(part))
                        within = re.match(r"(.*?):focus-within", part)
                        if within:
                            focus_styles.append(normal_selector(within.group(1)) + " *")
            if removes and not focus_rule:
                for part in parts:
                    if re.search(r":not\(\s*:focus-visible\s*\)", part):
                        continue
                    if NON_INTERACTIVE.search(normal_selector(subject(part))):
                        continue
                    if re.search(r":focus(?![\w-])", part) and any(
                            FOCUS_TARGET_WORDS.intersection(re.split(r"[-_]+", name.lower()))
                            for name in re.findall(r"[.#]([\w-]+)", subject(part))):
                        continue  # a script focus target (a main, status or live region), with the ring kept for :focus-visible
                    removals.append((part, removes[0][2]))
            if DISPLAY_FONT.search(rule.decls) and not rule.selector.lower().startswith("@font-face"):
                display_rules.append((selector, props, rule))
            if re.search(r"text-transform\s*:[^;]*uppercase", rule.decls, re.I):
                upper.update(normal_selector(p) for p in split_selectors(selector))
        within_box = any(style.endswith(" *") for style in focus_styles)
        for part, offset in removals:
            target = normal_selector(part)
            if any(style == target or style.startswith((target + " ", target + "::", target + ":"))
                   or (style.endswith(" *") and target.startswith(style[:-1])) for style in focus_styles):
                continue
            if within_box and re.search(r"(?:^|[\s>+~])(?:input|textarea|select)\b|\[contenteditable", target):
                continue  # a field inside a box that shows the ring with :focus-within
            self.add(offset, "focus-removed", f"outline turned off on '{short(part)}' with no focus style to replace it; keep the 2px "
                     "focus ring or add a :focus-visible rule for it", short(part))
        for selector, props, rule in display_rules if not self.ctx.public else ():
            fonts = [(p, v, o) for p, v, o in props if p in ("font-family", "font")]
            if not fonts or self.first_face(fonts[-1][1], fonts[-1][0] == "font") == "other":
                continue  # the display variable holds another face, which font-family flags where it is set
            offset = fonts[-1][2]
            parts = split_selectors(selector)
            if parts and any(EYEBROW.search(c) for p in parts for c in classes_of(subject(p))):
                self.add(offset, "display-face-case", f"BN Axel on the eyebrow '{short(selector)}'; eyebrows are never BN Axel: "
                         "set them in Inter SemiBold, in sentence case", short(selector))
                continue
            if re.search(r"text-transform\s*:[^;]*uppercase", rule.decls, re.I):
                continue
            if parts and all(normal_selector(p) in upper for p in parts):
                continue
            if any(r.search(selector) for r in self.display) or all(BN_AXEL_CLASS.search(subject(p)) for p in parts):
                continue
            if parts and all(any(self.ctx.class_info.get(c, {}).get("text") and not self.ctx.class_info[c]["lower"]
                                 for c in classes_of(subject(p))) for p in parts):
                continue  # its text in the scanned markup has no lowercase letters, such as the digits 01
            self.add(offset, "display-face-case", f"BN Axel (the display face) on '{short(selector)}' without capitals; it is set only in "
                     "capitals, for big numbers and short hero lines, so add text-transform: uppercase or use Inter Tight", short(selector))

    def first_face(self, value, shorthand=False):
        """'bn' when the first face a font-family (or font shorthand) value names is BN Axel, once its custom
        properties are resolved through the app's own definitions and then the layer's; 'other' for any other face;
        None when the check cannot tell, and then the display variable's name counts (Claude's default)."""
        families = value
        if shorthand:
            families = shorthand_families(value)
            if not families:
                m = re.search(r"var\(\s*(?:" + DISPLAY_VAR + r")|[\"']?bn\s*axel", value, re.I)
                families = value[m.start():] if m else value
        if "var(" in families:
            families = self.ctx.resolve(families, "light", app=True)
            if families is None:
                return None
        names = parse_families(families)
        if not names or names[0].startswith("var("):
            return None
        return "bn" if BN_AXEL.fullmatch(names[0]) else "other"

    # -- JS

    def js(self, base, body, jsx, parts):
        code, nocomment, strings, jsx_text = parts.code, parts.nocomment, parts.strings, parts.jsx_text
        self.theme_os(nocomment, base)
        self.google_fonts(nocomment, base)
        for m in MIDDLE_DOT.finditer(nocomment):
            self.add(base + m.start(), "middle-dot", "middle dot as a separator in text people see; use a comma, a word or a line break", self.line_text(base + m.start()))
        for offset, value, attribute, stack, tag in strings:
            at = base + offset
            if offset > 0 and body[offset - 1] == "`" and "${" in value:
                value = template_holes(value)  # the strings inside ${...} are read on their own
            stripped = value.strip()
            shown = string_shown(code, offset, len(value), attribute)
            if shown and attribute is None and self.server_identifier(code, offset, value):
                shown = False
            markup = attribute is None and looks_like_markup(value)
            if markup:
                self.fragment(value, at, shown)
            elif shown:
                self.env_hits(value, at)
                self.hidden_hits(value, at)
                mode = "code"
                if stripped in FLEXIBLE_CHARS and value[:1].isspace() and value[-1:].isspace() and (
                        re.search(r"\+\s*$", code[max(0, offset - 40):max(0, offset - 1)])
                        or re.match(r"\s*\+", code[offset + len(value) + 1:offset + len(value) + 40])):
                    mode = "text"  # " -> " joined into running text with +: an arrow between words, not an icon
                self.emoji(decode_escapes(value), at, mode=mode)
                if attribute in CAPS_ATTRS and (attribute != "value" or (tag or "").lower() in ("input", "button")):
                    self.typed_caps(value, at, stack)
            css_text = markup
            key = re.search(r"([A-Za-z_$][\w$]*)\s*:\s*$", code[max(0, offset - 61):max(0, offset - 1)])
            if markup:
                pass
            elif HEX_COLOR.fullmatch(stripped) or re.fullmatch(r"(?:rgba?|hsla?)\(.*\)", stripped, re.I):
                if not SELECTOR_USE.search(code[max(0, offset - 121):max(0, offset - 1)]):
                    self.add(at, "raw-color", f"raw colour '{stripped[:40]}' in code; use a token (var(--name))", stripped.lower()[:40])
            elif re.fullmatch(r"var\(\s*--[\w-]+\s*,\s*(#[0-9a-f]{3,8}|(?:rgba?|hsla?)\(.*\))\s*\)", stripped, re.I):
                self.add(at, "raw-color", f"raw colour as a var() fallback '{stripped[:40]}' in code; drop the fallback and use the token", stripped.lower()[:40])
            elif (CSS_COLOR_PROP.search(value) and (HEX_COLOR.search(value) or FUNC_COLOR.search(value))) \
                    or "font-family" in value or "text-transform" in value or CSS_TEXT_PROP.search(value):
                css_text = True
                self.declarations("", value, at, kind="js")
            elif key and STYLE_COLOR_KEY.fullmatch(key.group(1)):
                colours = FRAGMENT_URL.sub(lambda m: blank(m.group(0), 0, len(m.group(0))), value)
                for m in list(HEX_COLOR.finditer(colours)) + list(FUNC_COLOR.finditer(colours)):
                    self.add(at + m.start(), "raw-color", f"raw colour {m.group(0)}{'...)' if m.group(0).endswith('(') else ''} in a "
                             f"style value; use a token (var(--name))", m.group(0).lower())
            if not css_text:
                if blended_gradient(value):
                    key = re.search(r"([\w$-]+)\s*:\s*$", code[max(0, offset - 61):max(0, offset - 1)])
                    if not (key and re.search(r"mask", key.group(1), re.I)):
                        self.add(at, "gradient-fill", "gradient fill in code; fills are solid (the gradient tokens are only soft glows "
                                 "and scrims, through var(--gradient-...))", self.line_text(at))
                if "color-mix(" in value.lower():
                    self.add(at, "color-mix", "color-mix() in code makes a colour outside the system; use a token", self.line_text(at))
            if re.fullmatch(r"--[A-Za-z][\w-]*", stripped) and not self.is_theme_file:
                names = self.ctx.redefine_names()
                if names and stripped[2:] in names:
                    after = code[offset + len(value) + 1:offset + len(value) + 40]
                    before = code[max(0, offset - 41):max(0, offset - 1)]
                    if re.match(r"\s*:", after) or re.search(r"setProperty\(\s*$", before):
                        self.token_hit(stripped, at)
            if attribute in ("fontfamily", "font-family"):
                self.font_list(value, at)
            if tag and tag.lower() in SVG_TEXT_TAGS:
                if attribute == "fill":
                    found = self.graphic_name(value)
                    if found:
                        self.graphic_hit(found, at, f"<{tag}>")
                elif attribute in ("fontsize", "font-size"):
                    px = self.font_px(value if re.search(r"[a-z%]", value) else value + "px")
                    if px is not None and 0 < px < 12 - 1e-6:
                        self.small_hit(px, at, f"<{tag}>")
        for start, end, stack in jsx_text:
            segment = body[start:end]
            self.env_hits(segment, base + start)
            self.hidden_hits(segment, base + start)
            if not any(e[0].lower() in CODE_TAGS for e in stack):
                self.emoji(segment, base + start, mode="markup", context=stack)
            self.typed_caps(segment, base + start, stack)
        self.headings(jsx_text, lambda s, e: body[s:e], base)
        for m in re.finditer(r"""fontFamily\s*:\s*(['"`])(.*?)\1""", nocomment):
            self.font_list(m.group(2), base + m.start())
            if not self.ctx.public and DISPLAY_JS.search(m.group(2)) and self.first_face(m.group(2)) != "other":
                lo, hi = enclosing_braces(code, m.start())
                if not re.search(r"""textTransform\s*:\s*(['"`])uppercase\1""", nocomment[lo:hi]):
                    self.add(base + m.start(), "display-face-case", "BN Axel (the display face) in a style without capitals; it is set "
                             "only in capitals, so add textTransform: 'uppercase' or use Inter Tight", self.line_text(base + m.start()))
        for m in re.finditer(r"""(?<![\w-])font\s*(?::|=(?!=))\s*(['"`])(.*?)\1""", nocomment):
            families = shorthand_families(m.group(2))
            if families:
                self.font_list(families, base + m.start())
            size = shorthand_size(m.group(2))
            px = self.font_px(size) if size else None
            if px is not None and 0 < px < 12 - 1e-6:
                self.small_hit(px, base + m.start(), "a font in code")
        for m in re.finditer(r"""textTransform\s*:\s*(['"`])uppercase\1""", nocomment):
            lo, hi = enclosing_braces(code, m.start())
            if self.ctx.public or not DISPLAY_JS.search(nocomment[lo:hi]):
                self.add(base + m.start(), "uppercase", "textTransform 'uppercase'; only BN Axel display text is set in capitals", self.line_text(base + m.start()))
        for m in re.finditer(r"""className\s*=\s*["'`{][^>]*?\buppercase\b""", nocomment):
            self.add(base + m.start(), "uppercase", "the 'uppercase' class; only BN Axel display text is set in capitals", self.line_text(base + m.start()))
        for m in re.finditer(r"""letterSpacing\s*:\s*['"`]?(-?\d*\.?\d+)\s*(em|rem|px)?""", nocomment):
            unit = m.group(2) or "px"
            if too_wide(m.group(1), unit):
                self.add(base + m.start(), "letter-spacing", f"letterSpacing {m.group(1)}{unit}; labels take no added letter-spacing", self.line_text(base + m.start()))
        for m in re.finditer(r"""boxShadow\s*:\s*(?:(['"`])(.*?)\1)?""", nocomment):
            line = self.line_text(base + m.start())
            if m.group(1) and not self.elevation(m.group(2)):
                if "inset" in m.group(2):
                    self.inset_bar("inline style", m.group(2), base + m.start(), False)
                continue
            if CARD_LIKE.search(line) and not FLOATING.search(line):
                self.add(base + m.start(), "card-shadow", "boxShadow on a card; only floating layers (dialogs, drawers, menus, popovers and "
                         "toasts) take shadows", line)
        self.js_styles(base, code, nocomment)
        for m in re.finditer(r"""(?:\|\||\?\?)\s*(['"`])([\w-]+)\1""", nocomment):
            value = m.group(2)
            if not self.theme_like(value):
                continue
            before = nocomment[max(0, m.start() - 240):m.start()]
            before = before[before.rfind("\n") + 1:]
            if THEMEISH.search(left_operand(before)) or THEMEISH.search(assignment_target(before)):
                self.add(base + m.start(), "theme-default", f"theme falls back to '{value}'; the default is light", value)
        # The name may not start inside a longer word, so a long run of letters (a base64 string) is read once.
        for m in re.finditer(r"""(\b(?:let|var|const)\s+)?(?<![\w$])([A-Za-z_$][\w$]*)\s*([:=])(?!=)\s*(['"`])([\w-]+)\4""", nocomment):
            declared, name, sign, value = m.group(1), m.group(2), m.group(3), m.group(5)
            if self.theme_like(value) and starting_theme_name(name) \
                    and (EXPLICIT_DEFAULT.search(name.replace("_", "").replace("$", "")) or (declared and sign == "=")):
                self.add(base + m.start(), "theme-default", f"theme starts as '{value}'; the default is light", value)
        for m in re.finditer(r"""dataset\.theme\s*=\s*(['"`])([\w-]+)\1""", nocomment):
            self.theme_name(m.group(2), base + m.start(), "code")
        for m in re.finditer(r"""setAttribute\(\s*(['"`])data-theme\1\s*,\s*(['"`])([\w-]+)\2""", nocomment):
            self.theme_name(m.group(3), base + m.start(), "code")
        self.origin_links(base, nocomment)

    def server_identifier(self, code, offset, value):
        """True for a string only servers read (Claude's default): the fallback of an environment variable that names
        an id, a database or a project, and an OAuth return address (a redirect or callback key or object)."""
        before = code[max(0, offset - 121):max(0, offset - 1)]
        if SERVER_ID_BEFORE.search(before):
            return True
        if not ENV_NAME.search(value) or not re.search(r"[{,]\s*[\w$]+\s*:\s*$", before):
            return False
        lo, _ = enclosing_braces(code, offset)
        if code[lo:lo + 1] != "{":
            return False
        m = SERVER_ID_OBJECT.search(code[max(0, lo - 80):lo])
        return bool(m and SERVER_ID_NAME.search(m.group(1)))

    def origin_links(self, base, nocomment):
        """runtime-origin-link: location.origin, host or href concatenated or interpolated into a string, passed
        to the clipboard, or used as the base of a URL on a line about sharing, copying or links."""
        place = r"(?:(?:window|document|globalThis|self)\s*\.\s*)?location\s*\.\s*(origin|host|href)\b"
        for m in re.finditer(place, nocomment):
            before = nocomment[max(0, m.start() - 40):m.start()]
            after = nocomment[m.end():m.end() + 40]
            if re.match(r"\s*(?:[!=]==?|=(?!=))", after) or re.search(r"(?:[!=]==?)\s*$", before):
                continue
            line_start = nocomment.rfind("\n", 0, m.start()) + 1
            line_end = nocomment.find("\n", m.end())
            line = nocomment[line_start:line_end if line_end != -1 else len(nocomment)]
            built = re.match(r"\s*\+", after) or re.search(r"\+\s*$", before) or re.search(r"\$\{\s*$", before) \
                or re.search(r"writeText\(\s*$", before)
            if not built and re.search(r"\bnew\s+URL\([^()]*,\s*$", before):
                built = re.search(r"share|copy|clipboard|link|permalink|invite", line, re.I)
            if not built or re.search(r"\bfetch\s*\(|/api/|axios|XMLHttpRequest", line):
                continue
            at = base + m.start()
            self.add(at, "runtime-origin-link", f"a link built from location.{m.group(1)}; share and copy links use the tool's short link", self.line_text(at))

    def fragment(self, frag, at, shown):
        """HTML markup inside a JS string (a template literal the app writes into the page): its style
        attributes, SVG attributes and raw colour attributes always, and its text when people see it."""
        remainder, css_parts, js_parts, layer_parts = split_html(frag)
        for offset, body in css_parts:
            stripped = strip_css_comments(body)
            self.css(at + offset, stripped, css_rules(stripped))
        self.markup_rules(remainder, at, shown)
        for m in re.finditer(r"""(?<![\w-])(fill|stroke|stop-color|flood-color|lighting-color|color|bgcolor)\s*=\s*(["'])\s*(#[0-9a-f]{3,8}|(?:rgba?|hsla?)\()""", remainder, re.I):
            self.add(at + m.start(), "raw-color", f"raw colour in the {m.group(1)} attribute; use a token or currentColor", m.group(3).lower())
        if shown:
            visible = visible_html(remainder)
            self.env_hits(visible, at)
            self.hidden_hits(visible, at)

    def markup_rules(self, remainder, base, shown=True):
        """The rules that read markup: style attributes, SVG font and fill attributes, and the text and
        attributes people see (emoji, typed capitals and headings)."""
        tags, texts = html_structure(remainder)
        for name, attrs, start, end, stack in tags:
            values = {a: v for a, v, s, e in attrs}
            for attr, value, s, e in attrs:
                if attr == "style":
                    pseudo = name + "".join("." + c for c in values.get("class", "").split()) + "".join(
                        f'[{a}="{values[a]}"]' for a in ("aria-selected", "aria-current", "aria-pressed", "aria-checked") if a in values)
                    empty = name in VOID_TAGS or bool(re.match(r"\s*</" + re.escape(name) + r"\s*>", remainder[end:], re.I))
                    self.declarations(pseudo, value, base + s, kind="attr", element=(name, attrs, empty))
                elif attr == "font-family":
                    self.font_list(value, base + s)
                elif name in SVG_TEXT_TAGS and attr in ("fill", "color"):
                    found = self.graphic_name(value)
                    if found:
                        self.graphic_hit(found, base + s, f"<{name}>")
                elif name in SVG_TEXT_TAGS and attr == "font-size":
                    px = self.font_px(value if re.search(r"[a-z%]", value) else value + "px")
                    if px is not None and 0 < px < 12 - 1e-6:
                        self.small_hit(px, base + s, f"<{name}>")
                if not shown:
                    continue
                if attr in CAPS_ATTRS and (attr != "value" or name in ("input", "button")):
                    self.typed_caps(value, base + s, stack + ((name, values.get("class", ""), values.get("role", ""), 0),))
                if attr in SHOWN_HTML_ATTRS and attr != "content":
                    self.emoji(value, base + s)
        if not shown:
            return
        for start, end, stack in texts:
            segment = remainder[start:end]
            if not segment.strip():
                continue
            if not any(e[0] in CODE_TAGS for e in stack):
                self.emoji(segment, base + start, mode="markup", context=stack)
            self.typed_caps(segment, base + start, stack)
        self.headings(texts, lambda s, e: remainder[s:e], base)

    def js_styles(self, base, code, nocomment):
        """The style rules for JS style objects (camelCase keys) and JSX attributes."""
        def obj(at):
            lo, hi = enclosing_braces(code, at)
            return nocomment[lo:hi]
        for m in re.finditer(r"""\boutline(?:Style|Width)?\s*:\s*(?:(['"`])\s*(?:none|0(?:px)?)\s*\1|0(?![\w.]))""", nocomment):
            if re.search(r"""boxShadow\s*:\s*(['"`])(?!\s*none)""", obj(m.start())):
                continue
            at = base + m.start()
            self.add(at, "focus-removed", "outline turned off in an inline style, so keyboard users lose the focus ring; keep the "
                     "layer's ring", self.line_text(at))
        for m in re.finditer(r"""\bfontSize\s*[:=]\s*(?:(['"`])\s*([^'"`]*?)\s*\1|\{?\s*(\d+(?:\.\d+)?)(?![\w.%]))""", nocomment):
            value = m.group(2) if m.group(1) else (m.group(3) + "px" if m.group(3) else None)
            if value is None:
                continue
            if m.group(1) and not re.search(r"[a-z%]", value):
                value += "px"
            px = self.font_px(value)
            if px is not None and 0 < px < 12 - 1e-6:
                self.small_hit(px, base + m.start(), "an inline style")
        for m in re.finditer(r"""\b(color|WebkitTextFillColor)\s*:\s*(['"`])(.*?)\2""", nocomment):
            found = self.graphic_name(m.group(3))
            if found and (self.ctx.public or not DISPLAY_JS.search(obj(m.start()))):
                self.graphic_hit(found, base + m.start(), "an inline style")
        for m in re.finditer(r"""\bopacity\s*:\s*(?:(['"`])\s*(0?\.\d+)\s*\1|(0?\.\d+)(?![\w.]))""", nocomment):
            number = float(m.group(2) or m.group(3))
            style = obj(m.start())
            if 0 < number < 1 and re.search(r"\b(?:color|fontSize|fontWeight|fontFamily|lineHeight|letterSpacing|textTransform)\s*:", style) \
                    and not re.search(r"disabled", style, re.I):
                at = base + m.start()
                self.add(at, "text-opacity", f"opacity {number:g} on a style that sets text; faded text loses contrast, so use text-body instead", self.line_text(at))
        for m in re.finditer(r"""\bcolor\s*:\s*(['"`])(.*?)\1""", nocomment):
            style = obj(m.start())
            bg = re.search(r"""\bbackground(?:Color)?\s*:\s*(['"`])(.*?)\1""", style)
            if bg:
                props = [("color", m.group(2), base + m.start()), ("background", bg.group(2), base + m.start())]
                size = re.search(r"""\bfontSize\s*:\s*(?:(['"`])(.*?)\1|(\d+(?:\.\d+)?))""", style)
                if size:
                    props.append(("font-size", size.group(2) or (size.group(3) + "px"), 0))
                weight = re.search(r"""\bfontWeight\s*:\s*['"`]?(\w+)""", style)
                if weight:
                    props.append(("font-weight", weight.group(1), 0))
                self.pair_contrast("", props, (), where="an inline style")
        side = r"(Left|Right|Top|Bottom|InlineStart|InlineEnd|BlockStart|BlockEnd)"
        for m in re.finditer(r"""\bborder""" + side + r"""\s*:\s*(['"`])(.*?)\2""", nocomment):
            raw, variants, selected = m.group(3), [m.group(3)], False
            if m.group(2) == "`" and "${" in raw:
                # A template literal such as `3px solid ${active ? '#8039df' : 'transparent'}`: the width is written
                # out and each quoted colour in the ${...} part is one the border can take.
                static = " ".join(template_holes(raw).split())
                holes = " ".join(raw[a:b] for a, b in template_hole_spans(raw))
                variants = [f"{static} {c}" for _, c in re.findall(r"""(['"])(.*?)\1""", holes)]
                selected = bool(re.search(r"active|selected|current|checked|pressed", holes, re.I))
                if not self.border_parts(static)[0]:
                    variants = []  # the width comes from code: the check cannot tell
            for variant in variants:
                width, style, colour = self.border_parts(variant)
                px = self.ctx.length(width or "medium")
                if style not in (None, "none", "hidden") and px is not None and px >= 2 - 0.01 and colour \
                        and self.bar_colour(colour) == "accent" and not (selected and px <= 2 + 0.01):
                    at = base + m.start()
                    where = SIDES[re.sub(r"(?<!^)([A-Z])", r"-\1", m.group(1)).lower()]
                    self.add(at, "accent-bar", f"a {px:g}px accent bar on the {where} of an inline style; boxes take a 1px edge all round, "
                             "with no accent bars", f"inline style|{where}")
                    break
        for m in re.finditer(r"""\bborder""" + side + r"""Color\s*:\s*(['"`])(.*?)\2""", nocomment):
            style = obj(m.start())
            width = re.search(r"""\bborder""" + m.group(1) + r"""Width\s*:\s*(?:(['"`])(.*?)\1|(\d+(?:\.\d+)?))""", style)
            px = None
            if width:
                px = self.ctx.length(width.group(2) or (width.group(3) + "px"))
            if px is not None and px >= 2 - 0.01 and self.bar_colour(m.group(3)) == "accent":
                at = base + m.start()
                where = SIDES[re.sub(r"(?<!^)([A-Z])", r"-\1", m.group(1)).lower()]
                self.add(at, "accent-bar", f"a {px:g}px accent bar on the {where} of an inline style; boxes take a 1px edge all round, "
                         "with no accent bars", f"inline style|{where}")
        for m in re.finditer(r"""\.create(?:Linear|Radial|Conic)Gradient\s*\(""", code):
            at = base + m.start()
            self.add(at, "gradient-fill", "a canvas gradient fill; fills are solid", self.line_text(at))
        for m in re.finditer(r"<img\b(?:[^<>{}]|\{(?:[^{}]|\{[^{}]*\})*\})*>", nocomment):
            tag_text = m.group(0)
            if LOGO_WORDS.search(tag_text) and re.search(r"""\bfilter\s*:\s*(['"`])(?!\s*none)""", tag_text):
                at = base + m.start()
                self.add(at, "logo-filter", "a CSS filter on a logo image; logos swap by file per theme and are never recoloured", self.line_text(at))

    # -- HTML

    def html(self):
        remainder = self.remainder
        for offset, ok, version, kind, body in self.layer_parts:
            if ok:
                self.ctx.inline_ok += 1
            else:
                self.add(offset, "layer-intact", f"this inlined copy of the Gong brand layer ({version}) was edited: its fingerprint no "
                         "longer matches; paste the generated file again", "inline")
        for base, stripped, rules in self.css_parts:
            self.css(base, stripped, rules)
        for base, body, jsx, parts in self.js_parts:
            self.js(base, body, jsx, parts)
        self.markup_rules(remainder, 0)
        self.theme_os(remainder)
        self.google_fonts(remainder)
        shown = visible_html(remainder)
        self.visible(re.sub(r"&#?\w+;", lambda m: m.group(0) if MIDDLE_DOT.fullmatch(m.group(0)) else blank(m.group(0), 0, len(m.group(0))), shown))
        for m in re.finditer(r"""(?<![\w-])(fill|stroke|stop-color|flood-color|lighting-color|color|bgcolor)\s*=\s*(["'])\s*(#[0-9a-f]{3,8}|(?:rgba?|hsla?)\()""", remainder, re.I):
            self.add(m.start(), "raw-color", f"raw colour in the {m.group(1)} attribute; use a token or currentColor", m.group(3).lower())
        html_tag = re.search(r"""<html\b[^>]*?\bdata-theme\s*=\s*(["'])([^"']*)\1""", remainder, re.I)
        if html_tag and html_tag.group(2) != "light":
            self.add(html_tag.start(), "theme-default", f"the page starts in '{html_tag.group(2)}'; the default is light", html_tag.group(2))
        for m in re.finditer(r"""\bdata-theme\s*=\s*(["'])([\w-]+)\1""", remainder, re.I):
            self.theme_name(m.group(2), m.start(), "the markup")
        for m in re.finditer(r"""\bdata-themes\s*=\s*(["'])([^"']*)\1""", remainder, re.I):
            for name in m.group(2).split():
                self.theme_name(name, m.start(), "theme-init's data-themes")
        for m in re.finditer(r"""\bclass\s*=\s*(["'])([^"']*)\1""", remainder, re.I):
            if re.search(r"(?<![\w-])uppercase(?![\w-])", m.group(2)):
                self.add(m.start(), "uppercase", "the 'uppercase' class; only BN Axel display text is set in capitals", self.line_text(m.start()))

    # -- flavour markers and the finished list

    def markers(self):
        found = []
        for start, end in self.comments:
            m = FLAVOUR_MARK.search(self.text, start, end)
            if not m:
                continue
            reason = re.sub(r"\s*(?:\*/|-->|\*+|\})+\s*$", "", m.group(1)[:max(0, end - m.start(1))]).strip()
            reason = " ".join(reason.split())
            found.append((start, end, reason, m.start()))
        return found

    def finish(self):
        markers = self.markers()
        line_marks, by_end, by_start = {}, {}, {}
        for start, end, reason, at in markers:
            if not reason:
                self.add(at, "flavour-marker", "a gb-flavour marker with no reason does not count; write gb-flavour: <why it is kept>", "no reason")
                continue
            first, last = self.line(start), self.line(max(start, end - 1))
            # A marker covers its own lines, and the next line too when it stands on a line of its own.
            line_start = self.starts[first - 1]
            line_end = self.starts[last] - 1 if last < len(self.starts) else len(self.text)
            alone = not (self.text[line_start:start].strip() + self.text[end:line_end].strip()).strip("{}")
            for number in range(first, last + (2 if alone else 1)):
                line_marks.setdefault(number, reason)
            by_end[end] = reason
            by_start[start] = reason
        rule_marks = []
        if by_end:
            for sel_start, end, inner in self.rule_spans:
                k = sel_start
                while k > 0 and self.text[k - 1].isspace():
                    k -= 1
                reason = by_end.get(k)
                if reason is None:
                    j = inner
                    while j < len(self.text) and self.text[j].isspace():
                        j += 1
                    reason = by_start.get(j)
                if reason:
                    rule_marks.append((sel_start, end, reason))
        for f in self.findings:
            if f.rule in NEVER_FLAVOUR:
                continue
            reason = line_marks.get(f.line)
            if reason is None:
                for start, end, why in rule_marks:
                    if start <= f.offset < end:
                        reason = why
                        break
            if reason is None:
                for regex, rules, why in self.ctx.flavour_entries:
                    if regex.match(self.rel) and (rules is None or f.rule in rules):
                        reason = why
                        break
            f.flavour = reason
        unique, seen = [], set()
        for f in self.findings:
            marker = (f.line, f.rule, f.key, f.message)
            if marker not in seen:
                seen.add(marker)
                unique.append(f)
        return unique


def normal_selector(part):
    """A selector with its focus states taken out and its combinators spaced, so a :focus-visible rule
    can be matched with the rule that turned the outline off."""
    s = FOCUS_MARK.sub("", part)
    s = re.sub(r":(?:hover|active)(?![\w-])|\.is-(?:hover|active)(?![\w-])", "", s)
    s = re.sub(r":not\(\s*\)", "", s)
    s = re.sub(r"\s*([>+~])\s*", r" \1 ", s)
    return " ".join(s.split())


# ------------------------------------------------------------------ layer and tools integrity

def check_layer(root, config):
    findings = []
    layer = config.get("layer")
    if not layer:
        return findings, "not configured"
    folder = root / layer
    version_file = folder / "VERSION.json"
    rel_folder = Path(layer).as_posix().rstrip("/")

    def add(rel, message, key):
        findings.append(Finding(f"{rel_folder}/{rel}", 1, "layer-intact", message, key))

    try:
        record = json.loads(version_file.read_text(encoding="utf-8"))
        if not isinstance(record, dict):
            raise ValueError("not an object")
    except (OSError, ValueError):
        add("VERSION.json", "no vendored Gong brand layer here (VERSION.json missing or unreadable)", "missing")
        return findings, "missing"
    fingerprint = record.pop("fingerprint", None)
    if fingerprint != sha256(canonical(record)):
        add("VERSION.json", "VERSION.json was edited in place; vendor the layer again", "VERSION.json")
    files = record.get("files", {}) if isinstance(record.get("files"), dict) else {}
    for rel, info in sorted(files.items()):
        path = folder / rel
        if not path.is_file():
            add(rel, "file is missing from the vendored layer", rel)
            continue
        data = path.read_bytes()
        if not isinstance(info, dict) or sha256(data) != info.get("sha256"):
            add(rel, "edited in place: the file no longer matches VERSION.json; regenerate and vendor the layer", rel)
            continue
        if rel.endswith((".css", ".js")):
            text = data.decode("utf-8", errors="replace")
            first, _, body = text.partition("\n")
            m = re.search(r"fingerprint sha256:([0-9a-f]{64})", first)
            if not m or m.group(1) != sha256(body):
                add(rel, "edited in place: the header fingerprint does not match the file", rel)
    for path in sorted(p for p in folder.rglob("*") if p.is_file() and not JUNK_NAME.fullmatch(p.name)):
        rel = path.relative_to(folder).as_posix()
        if rel not in ("VERSION.json", "VENDOR.json") and rel not in files:
            add(rel, "file is not part of the layer; app files go outside the vendored folder", rel)
    vendor_file = folder / "VENDOR.json"
    if vendor_file.is_file():
        try:
            vendor = json.loads(vendor_file.read_text(encoding="utf-8"))
            if not isinstance(vendor, dict):
                raise ValueError("not an object")
        except (OSError, ValueError):
            add("VENDOR.json", "VENDOR.json is unreadable; vendor the layer again", "VENDOR.json")
        else:
            stamp = vendor.pop("fingerprint", None)
            if stamp != sha256(canonical(vendor)):
                add("VENDOR.json", "VENDOR.json was edited in place; vendor the layer again", "VENDOR.json")
            elif vendor.get("layer_version") not in (None, record.get("layer_version")):
                add("VENDOR.json", f"VENDOR.json names layer {vendor.get('layer_version')} but VERSION.json holds "
                    f"{record.get('layer_version')}; vendor the layer again", "VENDOR.json")
    profile = record.get("profile")
    label = f"{record.get('layer_version', '?')}" + (f" ({profile} profile)" if profile and profile != "full" else "")
    return findings, f"{label} " + ("intact" if not findings else "CHANGED")


def check_tools(root):
    """tools-intact: when generate.py --tools wrote TOOLS.json next to this check, every file it lists
    still matches it. Returns (findings, status or None)."""
    record_path = HERE / "TOOLS.json"
    if not record_path.is_file():
        return [], None
    try:
        where = HERE.relative_to(root).as_posix() + "/"
    except ValueError:
        where = ""
    findings = []

    def add(name, message):
        findings.append(Finding(f"{where}{name}", 1, "tools-intact", message, name))

    try:
        record = json.loads(record_path.read_text(encoding="utf-8"))
        files = record.get("files")
        if not isinstance(files, dict):
            raise ValueError("no files")
    except (OSError, ValueError, AttributeError):
        add("TOOLS.json", "TOOLS.json is unreadable; copy the check again with generate.py --tools")
        return findings, "CHANGED"
    own = Path(__file__).resolve().name
    if own not in files:
        add("TOOLS.json", f"TOOLS.json does not list {own}; copy the check again with generate.py --tools")
    for name, info in sorted(files.items()):
        path = HERE / name
        if not path.is_file():
            add(name, f"{name} is missing from the brand check folder; copy the check again with generate.py --tools")
            continue
        data = path.read_bytes()
        if not isinstance(info, dict) or sha256(data) != info.get("sha256") or (
                info.get("bytes") is not None and info.get("bytes") != len(data)):
            add(name, f"{name} was edited in place and no longer matches TOOLS.json; copy the check again with generate.py --tools")
    version = record.get("layer_version", "?")
    return findings, f"{version} " + ("intact" if not findings else "CHANGED")


# ------------------------------------------------------------------ baseline and run

def counts_from(data):
    counts = collections.Counter()
    for item in data.get("findings", []) if isinstance(data, dict) else []:
        try:
            counts[(item["file"], item["rule"], item["key"])] += int(item.get("count", 1))
        except (KeyError, TypeError, ValueError):
            continue
    return counts


def load_baseline(path):
    if path and path.exists():
        try:
            return counts_from(json.loads(path.read_text(encoding="utf-8")))
        except ValueError as error:
            raise CheckError(f"cannot read the baseline {path}: {error}") from None
    return collections.Counter()


def load_reference(spec, baseline_path):
    """(counts or None, note): the reference baseline for --baseline-ref."""
    if spec.startswith("git:"):
        ref = spec[4:]
        if not ref:
            raise CheckError("--baseline-ref git: needs a ref, such as git:origin/main")
        if baseline_path is None:
            raise CheckError("--baseline-ref needs a baseline file in the config")
        folder, name = baseline_path.parent, baseline_path.name

        def git(*args):
            try:
                return subprocess.run(["git", "-C", str(folder)] + list(args), capture_output=True, text=True)
            except OSError:
                raise CheckError("git is not installed, so --baseline-ref git: cannot read the reference") from None
        found = git("rev-parse", "--verify", "--quiet", ref + "^{commit}")
        if found.returncode != 0:
            raise CheckError(f"git cannot find {ref} from {folder}; fetch it first (for example git fetch origin main)")
        if git("cat-file", "-e", f"{ref}:./{name}").returncode != 0:
            return None, f"{name} does not exist at {ref} yet, so nothing was compared"
        shown = git("show", f"{ref}:./{name}")
        if shown.returncode != 0:
            raise CheckError(f"git cannot read {name} at {ref}: {shown.stderr.strip()}")
        text = shown.stdout
    else:
        path = Path(spec)
        if not path.is_file():
            raise CheckError(f"--baseline-ref: {spec} is not a file")
        text = path.read_text(encoding="utf-8")
    try:
        return counts_from(json.loads(text)), None
    except ValueError as error:
        raise CheckError(f"the reference baseline {spec} is not valid JSON: {error}") from None


def baseline_counts(findings):
    # The layer and the tools must always be intact, and flavour is kept on purpose, so neither is baselined.
    return collections.Counter((f.file, f.rule, f.key) for f in findings if f.rule not in NEVER_BASELINED and not f.flavour)


def write_baseline(path, counts):
    items = [{"file": k[0], "rule": k[1], "key": k[2], "count": v} for k, v in sorted(counts.items()) if v > 0]
    payload = {"about": "Brand findings accepted on the day the check was adopted. CI fails only on new ones. "
                        "brand-check.py --update-baseline only lowers it; --allow-raise is needed to add to it.",
               "version": 1, "findings": items}
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def describe(key):
    return f"{key[0]} {key[1]} '{key[2]}'"


def rewrite_baseline(findings, baseline_path, reference, allow_raise, out):
    current = baseline_counts(findings)
    existing = load_baseline(baseline_path) if baseline_path.exists() else None
    caps = existing
    if reference is not None:
        caps = reference if caps is None else collections.Counter({k: min(v, reference.get(k, 0)) for k, v in caps.items()})
    rises = [] if caps is None else sorted((k, caps.get(k, 0), v) for k, v in current.items() if v > caps.get(k, 0))
    if caps is None or allow_raise:
        new = current
    else:
        new = collections.Counter({k: min(v, caps[k]) for k, v in current.items() if caps.get(k, 0) > 0})
    write_baseline(baseline_path, new)
    note = ""
    if caps is not None:
        lowered = sum(1 for k, v in caps.items() if 0 < new.get(k, 0) < v)
        dropped = sum(1 for k, v in caps.items() if v > 0 and new.get(k, 0) == 0)
        note = f" ({lowered} lowered, {dropped} fixed and dropped)"
    out(f"brand-check: wrote {sum(new.values())} finding(s) to {baseline_path.name}{note}")
    for key, before, after in rises:
        if allow_raise:
            out(f"brand-check: raised {describe(key)} from {before} to {after} (--allow-raise)")
        else:
            out(f"brand-check: would raise {describe(key)} from {before} to {after}; not written (fix it, mark it as "
                "flavour, or pass --allow-raise)")
    broken = [f for f in findings if f.rule in NEVER_BASELINED]
    for f in broken:
        out(f.format())
    return 1 if broken or (rises and not allow_raise) else 0


def run(root, config, config_path=None, update_baseline=False, new_only=False, out=print,
        baseline_ref=None, allow_raise=False):
    root = Path(root).resolve()
    ctx = Context(root, config)
    findings, layer_status = check_layer(root, config)
    tool_findings, tools_status = check_tools(root)
    findings.extend(tool_findings)
    files, too_big = discover(root, config)
    scans = []
    for rel, path in files:
        try:
            raw = path.read_bytes()
        except OSError:
            continue
        if b"\0" in raw[:4096]:
            continue
        scans.append(Scan(rel, raw.decode("utf-8", errors="replace"), ctx))
    for scan in scans:
        scan.prepare()
    ctx.token_notes()
    for scan in scans:
        scan.run()
        findings.extend(scan.finish())
    findings.sort(key=lambda f: (f.file, f.line, f.rule))
    base_dir = config_path.parent if config_path else root
    baseline_path = (base_dir / config["baseline"]) if config.get("baseline") else None
    reference, ref_note = (None, None)
    if baseline_ref:
        reference, ref_note = load_reference(baseline_ref, baseline_path)
    for note in ctx.notes:
        out(f"brand-check: warning: {note}")
    if update_baseline and baseline_path:
        return rewrite_baseline(findings, baseline_path, reference, allow_raise, out)
    local = load_baseline(baseline_path)
    allowance = local if reference is None else collections.Counter({k: min(v, reference.get(k, 0)) for k, v in local.items()})
    if reference is not None:
        try:
            rel_baseline = baseline_path.relative_to(root).as_posix()
        except ValueError:
            rel_baseline = baseline_path.name
        for key, count in sorted(local.items()):
            if count > reference.get(key, 0):
                findings.append(Finding(rel_baseline, 1, "baseline-raised", f"the baseline raises {describe(key)} from "
                                        f"{reference.get(key, 0)} to {count} compared with {baseline_ref}; the baseline only goes down",
                                        "|".join(key)))
    used = collections.Counter()
    for f in findings:
        key = (f.file, f.rule, f.key)
        if f.rule not in NEVER_BASELINED and not f.flavour and used[key] < allowance[key]:
            used[key] += 1
            f.baselined = True
    for f in findings:
        if not (new_only and (f.baselined or f.flavour)):
            out(f.format())
    counted = [f for f in findings if not f.flavour]
    errors = [f for f in counted if f.severity == "error"]
    new_errors = [f for f in errors if not f.baselined]
    warnings = [f for f in counted if f.severity == "warn"]
    kept = [f for f in findings if f.flavour]
    gone = sum((allowance - used).values())
    summary = (f"brand-check: {len(files)} file(s) scanned, {len(errors)} error(s) ({len(new_errors)} new), "
               f"{len(warnings)} warning(s), {sum(1 for f in findings if f.baselined)} in the baseline; "
               f"layer {layer_status}")
    if tools_status:
        summary += f"; tools {tools_status}"
    if ctx.inline_ok:
        summary += f"; {ctx.inline_ok} inlined {'copy' if ctx.inline_ok == 1 else 'copies'} of the layer intact"
    if kept:
        reasons = list(dict.fromkeys(f.flavour for f in kept))
        summary += f"; {len(kept)} kept as flavour ({'; '.join(reasons)})"
    if baseline_ref:
        summary += f"; {ref_note}" if ref_note else f"; compared with {baseline_ref}"
    if gone:
        summary += f"; {gone} baseline finding(s) are fixed, run --update-baseline to lock that in"
    if too_big:
        summary += f"; skipped {len(too_big)} file(s) over {MAX_BYTES // 1_000_000} MB"
    out(summary)
    return 1 if new_errors else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check an app against the Gong brand layer rules.")
    parser.add_argument("--root", required=True, help="the app repo to check")
    parser.add_argument("--config", help="config file (default: <root>/brand-check.json)")
    parser.add_argument("--update-baseline", action="store_true", help="lower the baseline to today's findings (or write the first one)")
    parser.add_argument("--allow-raise", action="store_true", help="with --update-baseline: also raise counts and add keys")
    parser.add_argument("--baseline-ref", metavar="REF", help="a reference baseline file, or git:<ref> for the baseline at that commit")
    parser.add_argument("--new-only", action="store_true", help="print only findings that are not in the baseline")
    args = parser.parse_args(argv)
    if args.allow_raise and not args.update_baseline:
        parser.error("--allow-raise works only with --update-baseline")
    root = Path(args.root).resolve()
    try:
        config, config_path = load_config(root, Path(args.config) if args.config else None)
        return run(root, config, config_path, args.update_baseline, args.new_only,
                   baseline_ref=args.baseline_ref, allow_raise=args.allow_raise)
    except CheckError as error:
        print(f"brand-check: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
