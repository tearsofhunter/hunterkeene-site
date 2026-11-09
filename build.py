#!/usr/bin/env python3
"""Builds the static site from content.json.  Run:  python3 build.py
Outputs one HTML file per page into this folder (GitHub Pages serves /about.html as /about)."""
import html
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else ROOT
C = json.load(open(os.path.join(ROOT, "content.json")))
e = html.escape

FONTS = "https://fonts.googleapis.com/css2?family=Geist:wght@400;500&display=swap"


def year_key(y):
    return 9999 if str(y).lower() == "ongoing" else int(str(y)[:4]) if str(y)[:4].isdigit() else 0


sections = C["sections"]
by_section = {s["id"]: sorted([p for p in C["projects"] if p["section"] == s["id"]],
                              key=lambda p: -year_key(p["year"])) for s in sections}
ordered = [p for s in sections for p in by_section[s["id"]]]
section_title = {s["id"]: s["title"] for s in sections}
news = sorted(C.get("news", []), key=lambda n: (bool(n.get("date")), str(n.get("date") or "")), reverse=True)


MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def fmt_date(d):
    if not d:
        return ""
    parts = str(d).split("-")
    if len(parts) >= 2 and parts[1].isdigit() and 1 <= int(parts[1]) <= 12:
        return f"{MONTHS[int(parts[1]) - 1]} {parts[0]}"
    return str(d)


def cover(p):
    if p.get("cover"):
        return p["cover"]
    return p["images"][0]["src"] if p.get("images") else ""


def nav(current):
    items = [(s["id"] + ".html", s["title"], s["id"]) for s in sections if by_section[s["id"]]]
    items.append(("about.html", "About", "about"))
    cur = ' aria-current="page"'
    return "".join(
        f'<li><a href="{h}"{cur if k == current else ""}>{e(t)}</a></li>' for h, t, k in items
    )


def page(title, current, body, description=None, full_doc=True, kind=""):
    desc = e(description or C["description"])
    head = f"""<title>{e(title)}</title>
<meta name="description" content="{desc}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{desc}">
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="{FONTS}">
<link rel="stylesheet" href="assets/style.css">"""
    content = f"""<div class="page{(" " + kind) if kind else ""}">
<header class="top">
  <a class="name" href="index.html">{e(C["name"])}</a>
  <nav aria-label="Main"><ul class="nav" id="nav">{nav(current)}</ul></nav>
  <button type="button" class="menu-btn" aria-expanded="false" aria-controls="nav" aria-label="Menu"><span></span><span></span><span></span></button>
</header>
<main>
{body}
</main>
<footer class="foot"><span>{e(C["name"])}, New York</span><a href="mailto:{e(C["contact"]["email"])}">{e(C["contact"]["email"])}</a></footer>
</div>
<script src="assets/site.js"></script>"""
    if not full_doc:
        return head + "\n" + content
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
{head}
</head>
<body>
{content}
</body>
</html>
"""


def tile(p):
    src = cover(p)
    img = f'<img src="{e(src)}" alt="" loading="lazy">' if src else ""
    right = e(p["year"])
    return f"""<a class="tile" href="{p["slug"]}.html">
  <div class="img">{img}</div>
  <div class="cap"><span>{e(p["title"])}{(", " + e(p["note"])) if p.get("note") else ""}</span><span>{right}</span></div>
</a>"""


def index_body(projects, cols=3, key="index"):
    rows = "".join(
        f'<tr><td><a href="{p["slug"]}.html">{e(p["title"])}</a></td>'
        f'<td>{e(p.get("note", ""))}</td><td>{e(p["year"])}</td></tr>' for p in projects
    )
    return f"""<div data-view="grid">
<div class="controls">
  <div class="views">
    <button type="button" data-set-view="grid" aria-pressed="true">Grid</button>
    <button type="button" data-set-view="list" aria-pressed="false">List</button>
  </div>
  <label class="scale" for="scale-{key}">Scale <input type="range" id="scale-{key}" min="2" max="6" step="1" value="{cols}"></label>
</div>
<div class="grid">{"".join(tile(p) for p in projects)}</div>
<table class="list"><tbody>{rows}</tbody></table>
</div>"""


def updates_table(items):
    titles = {p["slug"]: p["title"] for p in C["projects"]}
    rows = ""
    for n in items:
        title = e(n["title"])
        if n.get("link"):
            title = f'<a href="{e(n["link"])}" target="_blank" rel="noopener">{title}</a>'
        if n.get("text"):
            title += f'<p>{e(n["text"])}</p>'
        proj = n.get("project")
        proj = f'<a href="{e(proj)}.html">{e(titles.get(proj, proj))}</a>' if proj else ""
        rows += (f'<tr><td>{e(n.get("outlet", ""))}</td><td>{title}</td>'
                 f'<td>{proj}</td><td>{e(fmt_date(n["date"]))}</td></tr>')
    return f'<table class="list feed"><tbody>{rows}</tbody></table>'


def write(name, text):
    with open(os.path.join(OUT, name), "w") as f:
        f.write(text)


def build(full_doc=True):
    pages = {}
    # home: large name + intro, then current updates (no projects)
    intro = "".join(f"<p>{e(t)}</p>" for t in (C.get("intro") or [C["description"], C["tagline"]]))
    # where the intro sits: "top" (above the photo), "over" (on the photo), "below" (under it)
    layout = C.get("intro_layout", "top")
    intro_html = f'<section class="intro" aria-label="Introduction">{intro}</section>'
    home = intro_html if layout == "top" else ""
    hero = C.get("hero") or []
    if isinstance(hero, dict):
        hero = [hero]
    slides = [h for h in hero if h.get("src")]
    if slides:
        items = ""
        for i, h in enumerate(slides):
            credit = f'<span class="credit">Photo: {e(h["credit"])}</span>' if h.get("credit") else ""
            if h.get("label"):
                credit = f'<span class="label">{e(h["label"])}</span>' + credit
            pc = h.get("phone_crop") or {}
            style = ""
            if pc:
                style = (f' style="--m-pos:{e(pc.get("position", "50% 40%"))};'
                         f'--m-zoom:{float(pc.get("zoom", 1))};--m-origin:{e(pc.get("origin", "50% 50%"))}"')
            mode = f' data-mode="{e(h["mode"])}"' if h.get("mode") else ""
            items += (f'<div class="slide{" on" if i == 0 else ""}"{style}{mode}{"" if i == 0 else " aria-hidden=\"true\""}>'
                      f'<img src="{e(h["src"])}" alt="{e(h.get("alt", ""))}"{"" if i == 0 else " loading=\"lazy\""}>{credit}</div>')
        dots = ""
        if len(slides) > 1:
            dots = '<div class="dots">' + "".join(
                f'<button type="button" aria-label="Show photo {i + 1} of {len(slides)}"{" aria-current=\"true\"" if i == 0 else ""}></button>'
                for i in range(len(slides))) + "</div>"
        over = intro_html.replace('class="intro"', 'class="intro over"') if layout == "over" else ""
        home += f'<figure class="bleed" data-slides="{len(slides)}">{items}{over}{dots}</figure>'
    else:
        home += '<figure class="bleed empty"></figure>'
    if layout == "below" or (layout == "over" and not slides):
        home += intro_html
    cps = C.get("current_projects") or []
    if cps:
        rows = ""
        for cp in cps:
            name = e(cp["name"])
            if cp.get("project"):
                name = f'<a href="{e(cp["project"])}.html">{name}</a>'
            elif cp.get("link"):
                name = f'<a href="{e(cp["link"])}" target="_blank" rel="noopener">{name}</a>'
            rows += f'<tr><td>{e(cp.get("role", ""))}</td><td>{name}</td><td>{e(cp.get("note", ""))}</td></tr>'
        home += f"""<section class="updates current" id="current" aria-labelledby="h-current">
  <h2 id="h-current">Current projects</h2>
  <table class="list current-list"><tbody>{rows}</tbody></table>
</section>"""
    if news:
        home += f"""<section class="updates" id="updates" aria-labelledby="h-updates">
  <h2 id="h-updates">Updates</h2>
  {updates_table(news)}
</section>"""
    pages["index.html"] = page(C["name"], "home", home, full_doc=full_doc, kind=f"home intro-{layout}")

    for s in sections:
        if by_section[s["id"]]:
            pages[s["id"] + ".html"] = page(f'{s["title"]} | {C["name"]}', s["id"], index_body(by_section[s["id"]], key=s["id"]))

    for i, p in enumerate(ordered):
        prev, nxt = ordered[i - 1], ordered[(i + 1) % len(ordered)]
        imgs = p.get("images", [])
        if not imgs and p.get("cover"):
            imgs = [{"src": p["cover"]}]
        def fig(k, im):
            if im.get("model"):  # interactive 3D model (glTF), loads when scrolled into view
                cap = f"<figcaption>{e(im['caption'])}</figcaption>" if im.get("caption") else ""
                return (f'<figure class="model">'
                        f'<script type="module" src="https://cdn.jsdelivr.net/npm/@google/model-viewer@3.5.0/dist/model-viewer.min.js"></script>'
                        f'<model-viewer src="{e(im["model"])}" poster="{e(im.get("poster", ""))}" alt="{e(im.get("alt", p["title"] + " 3D model"))}" '
                        f'camera-controls touch-action="pan-y" loading="lazy" reveal="auto" camera-orbit="35deg 62deg 95%" '
                        f'exposure="0.8" shadow-intensity="0.8" shadow-softness="0.8" tone-mapping="neutral" interaction-prompt="auto"></model-viewer>'
                        f'{cap}</figure>')
            if im.get("heading"):  # a chapter heading within the gallery
                return f'<h2 class="gallery-heading">{e(im["heading"])}</h2>'
            if im.get("text"):  # a text block placed between images
                paras = "".join(f"<p>{e(t)}</p>" for t in im["text"])
                return f'<div class="gallery-text">{paras}</div>'
            return f"""<figure class="{'half' if im.get('size') == 'half' else ''}">
  <button type="button" data-full="{e(im['src'])}" data-cap="{e(im.get('caption', ''))}" aria-label="View image {k + 1}">
    <img src="{e(im['src'])}" alt="{e(im.get('caption') or p['title'])}" loading="{'eager' if k == 0 else 'lazy'}">
  </button>{f"<figcaption>{e(im['caption'])}</figcaption>" if im.get('caption') else ""}
</figure>"""
        figs = "".join(fig(k, im) for k, im in enumerate(imgs)) or '<div class="blank"></div>'
        meta = ", ".join(x for x in [p.get("note"), section_title[p["section"]], p["year"]] if x)
        context = "".join(f"<span>{e(t)}</span>" for t in (p.get("context") or []))
        text = "".join(f"<p>{e(t)}</p>" for t in (p.get("text") or []))
        links = "".join(f'<a href="{e(l["url"])}" target="_blank" rel="noopener">{e(l["label"])}</a>' for l in (p.get("links") or []))
        refs = [r for r in C.get("references", []) if r.get("project") == p["slug"]]
        refs.sort(key=lambda n: (bool(n.get("date")), str(n.get("date") or "")), reverse=True)
        press = ""
        if refs:
            rows = ""
            for r in refs:
                t = e(r["title"])
                if r.get("link"):
                    t = f'<a href="{e(r["link"])}" target="_blank" rel="noopener">{t}</a>'
                rows += f'<tr><td>{e(r.get("outlet", ""))}</td><td>{t}</td><td>{e(fmt_date(r.get("date")))}</td></tr>'
            press = f"""<section class="project-press" aria-labelledby="press-{p['slug']}">
  <h2 id="press-{p['slug']}">Press</h2>
  <table class="list refs"><tbody>{rows}</tbody></table>
</section>"""
        tz = p.get("teaser") or {}
        teaser = ""
        if tz.get("src"):
            cr = f'<span class="credit">Photo: {e(tz["credit"])}</span>' if tz.get("credit") else ""
            teaser = (f'<figure class="bleed teaser"><div class="slide on">'
                      f'<img src="{e(tz["src"])}" alt="{e(tz.get("alt", p["title"]))}">{cr}</div></figure>')
        body = teaser + f"""<div class="project-head">
  <h1>{e(p["title"])}</h1>
  <span class="meta">{e(meta)}</span>
  {f'<div class="context">{context}</div>' if context else ""}
  {f'<div class="text">{text}</div>' if text else ""}
  {f'<div class="links">{links}</div>' if links else ""}
</div>
{press}
<div class="images">{figs}</div>
<nav class="pager" aria-label="More projects">
  <a href="{prev["slug"]}.html"><span>Previous</span>&nbsp; {e(prev["title"])}</a>
  <a href="{nxt["slug"]}.html">{e(nxt["title"])} &nbsp;<span>Next</span></a>
</nav>"""
        pages[p["slug"] + ".html"] = page(f'{p["title"]} | {C["name"]}', p["section"], body)

    c = C["contact"]
    about_text = "".join(f"<p>{e(t)}</p>" for t in (C.get("about") or [C["description"], C["tagline"]]))
    pt = C.get("portrait") or {}
    portrait = ""
    if pt.get("src"):
        cr = f'<figcaption>Photo: {e(pt["credit"])}</figcaption>' if pt.get("credit") else ""
        portrait = f'<figure class="portrait"><img src="{e(pt["src"])}" alt="{e(pt.get("alt", ""))}">{cr}</figure>'
    about = f"""<div class="about{" has-portrait" if portrait else ""}">
  {portrait}
  <div class="about-text">{about_text}</div>
  <dl>
    <dt>Email</dt><dd><a href="mailto:{e(c["email"])}">{e(c["email"])}</a></dd>
    <dt>Instagram</dt><dd><a href="{e(c["instagram"])}" target="_blank" rel="noopener">@{e(c["instagram"].rstrip("/").split("/")[-1])}</a></dd>
    <dt>LinkedIn</dt><dd><a href="{e(c["linkedin"])}" target="_blank" rel="noopener">Hunter Keene</a></dd>
  </dl>
</div>"""
    pages["about.html"] = page(f'About | {C["name"]}', "about", about)
    return pages


def build_preview(out):
    """Single-file preview for the Claude artifact viewer, which can't follow links between
    separate pages: every page becomes a view inside start.html, switched by #hash.
    Also writes the normal multi-page site and assets alongside it."""
    import re
    import shutil
    os.makedirs(os.path.join(out, "assets"), exist_ok=True)
    pages = build()
    for name, text in pages.items():
        with open(os.path.join(out, name), "w") as f:
            f.write(text)
    for a in ("style.css", "site.js"):
        shutil.copy(os.path.join(ROOT, "assets", a), os.path.join(out, "assets", a))
    if os.path.isdir(os.path.join(ROOT, "models")):
        shutil.copytree(os.path.join(ROOT, "models"), os.path.join(out, "models"), dirs_exist_ok=True)
    if os.path.isdir(os.path.join(ROOT, "images")):
        shutil.copytree(os.path.join(ROOT, "images"), os.path.join(out, "images"), dirs_exist_ok=True)

    # artifacts can't serve .glb: embed each model as a JSON glTF for the preview
    import base64, struct, glob as _g
    for glb in _g.glob(os.path.join(out, "models", "*.glb")):
        raw = open(glb, "rb").read()
        jlen = struct.unpack_from("<I", raw, 12)[0]
        gj = json.loads(raw[20:20 + jlen])
        off = 20 + jlen
        blen = struct.unpack_from("<I", raw, off)[0]
        binc = raw[off + 8: off + 8 + blen]
        gj["buffers"][0]["uri"] = "data:application/octet-stream;base64," + base64.b64encode(binc).decode()
        with open(glb[:-4] + ".gltf.json", "w") as f:
            json.dump(gj, f)
        os.remove(glb)

    def to_hash(m):
        target = m.group(1)
        return f'href="#{"index" if target == "index" else target}"'

    views, titles = [], {}
    for name, text in pages.items():
        key = name[:-5]
        main = text.split("<main>", 1)[1].split("</main>", 1)[0]
        main = re.sub(r'href="([a-z0-9-]+)\.html"', to_hash, main)
        main = re.sub(r'(models/[a-z0-9-]+)\.glb', r'\1.gltf.json', main)
        titles[key] = text.split("<title>", 1)[1].split("</title>", 1)[0]
        views.append(f'<div data-page="{key}"{"" if key == "index" else " hidden"}>{main}</div>')

    home = build(full_doc=False)["index.html"]
    head, rest = home.split('<div class="page', 1)
    rest = '<div class="page' + rest
    header = rest.split("<main>", 1)[0]
    footer = rest.split("</main>", 1)[1]
    header = re.sub(r'href="([a-z0-9-]+)\.html"', to_hash, header)
    footer = re.sub(r'href="([a-z0-9-]+)\.html"', to_hash, footer)
    router = """<script>
(function () {
  var titles = %s;
  var page = document.querySelector(".page");
  function show() {
    var key = (location.hash || "").slice(1) || "index";
    var view = document.querySelector('[data-page="' + key + '"]');
    if (!view) { key = "index"; view = document.querySelector('[data-page="index"]'); }
    document.querySelectorAll("[data-page]").forEach(function (v) { v.hidden = v !== view; });
    page.classList.toggle("home", key === "index");
    var section = view.getAttribute("data-section") || key;
    document.querySelectorAll(".nav a").forEach(function (a) {
      if (a.getAttribute("href") === "#" + section) a.setAttribute("aria-current", "page");
      else a.removeAttribute("aria-current");
    });
    document.title = titles[key] || titles.index;
    window.scrollTo(0, 0);
    if (window.hkUpdateHome) window.hkUpdateHome();
  }
  window.addEventListener("hashchange", show);
  show();
})();
</script>""" % json.dumps(titles)
    sections = {p["slug"]: p["section"] for p in C["projects"]}
    views = [v.replace(f'<div data-page="{k}"', f'<div data-page="{k}" data-section="{sections[k]}"', 1) if k in sections else v
             for v, k in zip(views, [n[:-5] for n in pages])]
    start = head + header + "<main>" + "".join(views) + "</main>" + footer.replace(
        '<script src="assets/site.js"></script>', router + '\n<script src="assets/site.js"></script>')
    with open(os.path.join(out, "start.html"), "w") as f:
        f.write(start)
    print(f"Built preview into {out}")


if __name__ == "__main__" and len(sys.argv) > 2 and sys.argv[1] == "--preview":
    build_preview(sys.argv[2])
    sys.exit(0)

if __name__ == "__main__":
    pages = build()
    for name, text in pages.items():
        write(name, text)
    if OUT == ROOT:  # remove pages for projects that no longer exist
        import glob
        for old in glob.glob(os.path.join(ROOT, "*.html")):
            if os.path.basename(old) not in pages:
                os.remove(old)
    print(f"Built {len(pages)} pages into {OUT}")
