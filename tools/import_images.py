#!/usr/bin/env python3
"""Run by the "Import project images" GitHub job.

For each project in tools/import_sources.json that lists "behance_files"
(file names taken from the project's Behance page), downloads each image at
the largest size Behance's image server offers into images/<slug>/NN.<ext>,
in the listed order, and records the result in images/_import/<slug>.json.
Projects with "behance_cover" also get images/<slug>/cover.<ext>.
"""
import json
import os
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
CDN = "https://mir-s3-cdn-cf.behance.net"
MODULE_SIZES = ["source", "max_3840", "fs", "2800_opt_1", "1400_opt_1", "1400", "max_1200", "disp"]
COVER_SIZES = ["max_808", "808", "max_632", "404"]


def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "image/*,*/*"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):
                return None
            time.sleep(2 * (i + 1))
        except Exception:
            time.sleep(2 * (i + 1))
    return None


def fetch_first(paths):
    for size, url in paths:
        data = get(url)
        if data and len(data) > 2000:
            return size, data
    return None, None


def main():
    src = json.load(open(os.path.join(ROOT, "tools", "import_sources.json")))
    os.makedirs(os.path.join(ROOT, "images", "_import"), exist_ok=True)
    for p in src["projects"]:
        slug = p["slug"]
        outdir = os.path.join(ROOT, "images", slug)

        if p.get("behance_cover") and not any(f.startswith("cover.") for f in (os.listdir(outdir) if os.path.isdir(outdir) else [])):
            name = p["behance_cover"]
            size, data = fetch_first([(s, f"{CDN}/projects/{s}/{name}") for s in COVER_SIZES])
            if data:
                os.makedirs(outdir, exist_ok=True)
                open(os.path.join(outdir, "cover" + (os.path.splitext(name)[1].lower() or ".jpg")), "wb").write(data)

        names = p.get("behance_files") or []
        if not names:
            continue
        os.makedirs(outdir, exist_ok=True)
        saved, sizes = [], []
        for i, name in enumerate(names, 1):
            ext = os.path.splitext(name)[1].lower() or ".jpg"
            fn = f"{i:02d}{ext}"
            if os.path.exists(os.path.join(outdir, fn)):
                saved.append(f"images/{slug}/{fn}")
                continue
            size, data = fetch_first([(s, f"{CDN}/project_modules/{s}/{name}") for s in MODULE_SIZES])
            if data:
                open(os.path.join(outdir, fn), "wb").write(data)
                saved.append(f"images/{slug}/{fn}")
                sizes.append(size)
            else:
                print(f"{slug}: could not download {name}")
        json.dump({"slug": slug, "files": names, "saved": saved, "sizes": sizes},
                  open(os.path.join(ROOT, "images", "_import", f"{slug}.json"), "w"), indent=2)
        print(f"{slug}: {len(saved)}/{len(names)} images (sizes: {sorted(set(sizes))})")


if __name__ == "__main__":
    main()
