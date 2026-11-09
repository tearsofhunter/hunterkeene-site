#!/usr/bin/env python3
"""One-off importer, run by the "Import project images" GitHub job.

For each project in tools/import_sources.json it finds the project's page on
hunterkeene.com (Adobe Portfolio) and/or Behance, collects the project images in
page order at the largest size offered, downloads them to images/<slug>/NN.<ext>,
and writes images/_import/<slug>.json listing what was saved.
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def get(url, binary=False, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
                return data if binary else data.decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(2 * (i + 1))
        except Exception:
            time.sleep(2 * (i + 1))
    return None


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


# ---------- Adobe Portfolio ----------
ADOBE_RE = re.compile(r"https://cdn\.myportfolio\.com/[^\s\"'<>()]+")


def adobe_index(site):
    """title -> page url, from the project covers on the site's grid pages."""
    out = {}
    for path in ("/work", "/events", "/work-1", "/"):
        html = get(site + path) or ""
        for m in re.finditer(r"<a\b([^>]*)>(.*?)</a>", html, re.S):
            attrs, inner = m.group(1), m.group(2)
            if "project-cover" not in attrs:
                continue
            href = re.search(r'href="([^"]+)"', attrs)
            title = re.search(r'class="[^"]*\btitle\b[^"]*"[^>]*>\s*([^<]+?)\s*<', inner)
            if href and title:
                url = href.group(1)
                if url.startswith("/"):
                    url = site + url
                out.setdefault(norm(title.group(1)), url)
    return out


def slugify(t):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", t.lower())).strip("-")


def adobe_images(html):
    """Ordered unique images (largest rendition) from an Adobe project page."""
    best, order = {}, []
    for url in ADOBE_RE.findall(html.replace("&amp;", "&")):
        base = url.split("?")[0]
        m = re.search(r"(_rw(?:c)?_(\d+)(?:x[\dx]*)?)\.(\w+)$", base)
        width = int(m.group(2)) if m else 0
        key = re.sub(r"_rwc?_[\dx]+(?=\.\w+$)", "", base)
        if key not in best:
            order.append(key)
            best[key] = (width, url)
        elif width > best[key][0]:
            best[key] = (width, url)
    return [best[k][1] for k in order]


# ---------- Behance ----------
BEH_RE = re.compile(r"https://mir-s3-cdn-cf\.behance\.net/project_modules/([a-z0-9_]+)/([^\s\"'<>?]+)")
BEH_SIZES = ["source", "max_3840", "fs", "1400_opt_1", "1400", "max_1200", "disp", "max_632"]


def behance_images(html):
    order, seen = [], set()
    for size, name in BEH_RE.findall(html):
        if name not in seen:
            seen.add(name)
            order.append(name)
    return order


def download_behance(name, dest_base):
    for size in BEH_SIZES:
        data = get(f"https://mir-s3-cdn-cf.behance.net/project_modules/{size}/{name}", binary=True)
        if data and len(data) > 2000:
            ext = os.path.splitext(name)[1].lower() or ".jpg"
            return data, ext
    return None, None


def main():
    src = json.load(open(os.path.join(ROOT, "tools", "import_sources.json")))
    site = src["adobe_site"].rstrip("/")
    index = adobe_index(site)
    print(f"Adobe index: {len(index)} projects found")
    os.makedirs(os.path.join(ROOT, "images", "_import"), exist_ok=True)

    found = {}
    for p in src["projects"]:
        slug = p["slug"]
        adobe_url = p.get("adobe_url")
        if not adobe_url:
            for key in p.get("adobe_titles", []):
                k = norm(key)
                adobe_url = index.get(k) or next((u for t, u in index.items() if t.startswith(k)), None)
                if adobe_url:
                    break
        if not adobe_url:
            for key in p.get("adobe_titles", []):
                guess = f"{site}/{slugify(key)}"
                if get(guess):
                    adobe_url = guess
                    break
        lists = {}
        if adobe_url:
            html = get(adobe_url) or ""
            lists["adobe"] = adobe_images(html)
        if p.get("behance_url"):
            html = get(p["behance_url"]) or ""
            lists["behance"] = behance_images(html)
        found[slug] = {"adobe_url": adobe_url, "behance_url": p.get("behance_url"), "lists": lists}

    # drop site chrome (logos etc.) that shows up on many project pages
    counts = {}
    for f in found.values():
        for u in set(f["lists"].get("adobe", [])):
            k = u.split("?")[0]
            counts[k] = counts.get(k, 0) + 1
    chrome = {k for k, n in counts.items() if n >= 3}

    summary = []
    for slug, f in found.items():
        adobe = [u for u in f["lists"].get("adobe", []) if u.split("?")[0] not in chrome]
        behance = f["lists"].get("behance", [])
        outdir = os.path.join(ROOT, "images", slug)
        os.makedirs(outdir, exist_ok=True)
        saved = []
        source = "behance" if len(behance) >= len(adobe) and behance else "adobe"
        if source == "behance":
            for i, name in enumerate(behance, 1):
                data, ext = download_behance(name, outdir)
                if data:
                    fn = f"{i:02d}{ext}"
                    open(os.path.join(outdir, fn), "wb").write(data)
                    saved.append(f"images/{slug}/{fn}")
        else:
            for i, url in enumerate(adobe, 1):
                data = get(url, binary=True)
                if data and len(data) > 2000:
                    ext = os.path.splitext(url.split("?")[0])[1].lower() or ".jpg"
                    fn = f"{i:02d}{ext}"
                    open(os.path.join(outdir, fn), "wb").write(data)
                    saved.append(f"images/{slug}/{fn}")
        if not saved:
            try:
                os.rmdir(outdir)
            except OSError:
                pass
        rec = {"slug": slug, "source": source if saved else None, "adobe_url": f["adobe_url"],
               "behance_url": f["behance_url"], "adobe_found": len(adobe), "behance_found": len(behance),
               "saved": saved}
        json.dump(rec, open(os.path.join(ROOT, "images", "_import", f"{slug}.json"), "w"), indent=2)
        summary.append(f"{slug}: {len(saved)} images ({rec['source']})")
    print("\n".join(summary))


if __name__ == "__main__":
    sys.exit(main())
