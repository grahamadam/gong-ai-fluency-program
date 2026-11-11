"""WCAG contrast checker for the Gong Design System tokens.json, per theme.

usage: contrast.py <tokens.json> [--pairs pairs.json] [--json]
Default pairs cover the text, control and chart pairs the tool-screen rules rely on.
A pair is [foreground, background, minimum], with an optional fourth item naming the one theme it
applies to. Prints every pair per theme; exit 1 if any fails.
"""
import json, re, sys

def load(path):
    t = json.load(open(path))
    themes = [th["id"] for th in t["color"]["themes"]]
    raw = {x["name"]: x["value"] for x in t["color"]["tokens"]}
    return themes, raw

def resolve(raw, themes, name, theme, depth=0):
    if depth > 20:
        raise ValueError(f"alias loop at {name}")
    v = raw[name]
    if isinstance(v, dict):
        val = v.get(theme, v.get(themes[0]))
    else:
        val = v if theme == themes[0] else v
    m = re.fullmatch(r"\{(.+)\}", str(val).strip())
    if m:
        return resolve(raw, themes, m.group(1), theme, depth + 1)
    return str(val).strip()

def rgba(hexv):
    h = hexv.lstrip("#")
    if len(h) in (3, 4):
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    a = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
    return r, g, b, a

def over(fg, bg):
    r, g, b, a = fg
    R, G, B, _ = bg
    return (r * a + R * (1 - a), g * a + G * (1 - a), b * a + B * (1 - a), 1.0)

def lum(c):
    def ch(x):
        return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4
    r, g, b, _ = c
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)

def ratio(fg_hex, bg_hex, page_hex="#ffffff"):
    bg = rgba(bg_hex)
    if bg[3] < 1:
        bg = over(bg, rgba(page_hex))
    fg = rgba(fg_hex)
    if fg[3] < 1:
        fg = over(fg, bg)
    l1, l2 = sorted((lum(fg), lum(bg)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)

DEFAULT = []
for fg, mn in (("text-heading", 4.5), ("text-body", 4.5)):
    for bg in ("surface-page", "surface-card", "surface-muted", "surface-tint", "surface-raised", "surface-hover", "surface-tint-raised"):
        DEFAULT.append([fg, bg, mn])
for bg in ("surface-page", "surface-card", "surface-raised"):
    DEFAULT.append(["text-accent", bg, 4.5])
# selected segmented options and the rail's current item: a text-heading pill with a surface-page label or icon
DEFAULT.append(["surface-page", "text-heading", 4.5])
DEFAULT += [["cta-label", "cta", 4.5], ["cta-label", "cta-hover", 4.5], ["Midnight", "Teal", 4.5]]
for s in ("success", "warning", "error"):
    DEFAULT += [[f"{s}-text", f"{s}-surface", 4.5], [f"{s}-text", "surface-page", 4.5], [f"{s}-text", "surface-card", 4.5]]
for bg in ("surface-page", "surface-card"):
    # control-border is the 3:1 control edge in both themes; field-border keeps gong.io's 1.7:1 in Light
    # (documented as a miss in the README) and must reach 3:1 in Dark.
    DEFAULT += [["focus", bg, 3.0], ["control-border", bg, 3.0], ["field-border", bg, 3.0, "dark"]]
    DEFAULT += [[f"chart-{i}", bg, 3.0] for i in range(1, 6)]
DEFAULT += [["text-on-dark", "surface-announce", 4.5], ["text-on-dark", "Midnight", 4.5], ["text-on-dark", "Violet", 4.5]]

def main():
    args = sys.argv[1:]
    path = args[0]
    pairs = DEFAULT
    if "--pairs" in args:
        pairs = json.load(open(args[args.index("--pairs") + 1]))
    themes, raw = load(path)
    rows, fails = [], 0
    for th in themes:
        page = resolve(raw, themes, "surface-page", th) if "surface-page" in raw else "#ffffff"
        for pair in pairs:
            fg, bg, mn = pair[:3]
            if len(pair) > 3 and pair[3] != th:
                continue
            if fg not in raw or bg not in raw:
                rows.append({"theme": th, "fg": fg, "bg": bg, "min": mn, "ratio": None, "ok": False, "note": "missing token"})
                fails += 1
                continue
            f, b = resolve(raw, themes, fg, th), resolve(raw, themes, bg, th)
            r = ratio(f, b, page)
            ok = r + 1e-9 >= mn
            fails += 0 if ok else 1
            rows.append({"theme": th, "fg": fg, "fg_hex": f, "bg": bg, "bg_hex": b, "min": mn, "ratio": round(r, 2), "ok": ok})
    if "--json" in args:
        print(json.dumps({"fails": fails, "rows": rows}, indent=1))
    else:
        for x in rows:
            mark = "ok  " if x["ok"] else "FAIL"
            print(f"{mark} {x['theme']:5s} {x['fg']:16s} on {x['bg']:16s} {x.get('ratio')} (min {x['min']}) {x.get('note', '')}")
        print(f"{fails} failing pair(s)")
    sys.exit(1 if fails else 0)

if __name__ == "__main__":
    main()
