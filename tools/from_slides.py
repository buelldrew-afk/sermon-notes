"""Start a new sermon from Drew's PowerPoint slides.

    python tools/from_slides.py "path/to/031) Hard Words for Hard Hearts.pptx" 2026-11-15

Creates sermons/<date>-<title>/ with:
  notes.txt  - a draft outline (title, series, points, quotes, photos) to finish by hand
  hero.jpg   - the title-slide background, for the top of the page
  photo-N.jpg - every picture-only slide, shrunk for phones

Nothing it writes is final: open notes.txt, paste the Scripture text, add the
"See also" references and any [[blanks]], then run tools/build.py.
It never overwrites an existing notes.txt.
"""
import re
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent.parent
IMAGE_PS1 = ROOT / "tools" / "image.ps1"


def rels(z, part):
    """Map rId -> target path for one part of the pptx."""
    p = PurePosixPath(part)
    rel_path = str(p.parent / "_rels" / (p.name + ".rels"))
    if rel_path not in z.namelist():
        return {}
    xml = z.read(rel_path).decode("utf8")
    out = {}
    for rid, target in re.findall(r'Id="([^"]+)"[^>]*Target="([^"]+)"', xml):
        out[rid] = str(PurePosixPath(*_norm((p.parent / target).parts)))
    return out


def _norm(parts):
    stack = []
    for s in parts:
        if s == "..":
            stack.pop()
        elif s != ".":
            stack.append(s)
    return stack


def paragraphs(xml):
    paras = []
    for p in re.findall(r"<a:p>.*?</a:p>|<a:p .*?</a:p>", xml, re.S):
        t = "".join(re.findall(r"<a:t>([^<]*)</a:t>", p))
        t = (t.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
              .replace("&quot;", '"').replace("&apos;", "'"))
        t = re.sub(r"\s+", " ", t).strip()
        if t:
            paras.append(t)
    return paras


def slides_in_order(z):
    pres = z.read("ppt/presentation.xml").decode("utf8")
    r = rels(z, "ppt/presentation.xml")
    ids = re.findall(r'<p:sldId [^>]*r:id="([^"]+)"', pres)
    out = []
    for rid in ids:
        part = r[rid]
        xml = z.read(part).decode("utf8")
        srels = rels(z, part)
        pics = []
        for emb in re.findall(r'<p:pic>.*?</p:pic>', xml, re.S):
            m = re.search(r'r:embed="([^"]+)"', emb)
            if not m:
                continue
            crop = re.search(r'<a:srcRect([^>]*)/?>', emb)
            c = {k: 0.0 for k in "ltrb"}
            if crop:
                for k, v in re.findall(r'\b([ltrb])="(-?\d+)"', crop.group(1)):
                    c[k] = max(0.0, int(v) / 100000)
            rot = re.search(r'<a:xfrm[^>]*rot="(-?\d+)"', emb)
            c["rot"] = round(int(rot.group(1)) / 60000) if rot else 0
            pics.append((srels.get(m.group(1)), c))
        layout = next((t for t in srels.values() if "slideLayout" in t), None)
        out.append({"part": part, "text": paragraphs(xml), "pics": pics, "layout": layout})
    return out


def first_layout_image(z, layout):
    if not layout:
        return None
    for t in rels(z, layout).values():
        if "/media/" in t and t.lower().endswith((".jpg", ".jpeg", ".png")):
            return t
    return None


POINT = re.compile(r"(?:^|\s)(\d{1,2})\s+(.+?)\s*\((v{1,2}\.\s*[^)]*)\)")


def outline_points(text):
    return POINT.findall(" ".join(text))


def save_image(z, member, dest, crop=None):
    tmp = dest.with_suffix(".src" + PurePosixPath(member).suffix)
    tmp.write_bytes(z.read(member))
    c = crop or {}
    subprocess.run([
        "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(IMAGE_PS1),
        "-In", str(tmp), "-Out", str(dest), "-MaxSide", "1600",
        "-CropL", str(c.get("l", 0)), "-CropT", str(c.get("t", 0)),
        "-CropR", str(c.get("r", 0)), "-CropB", str(c.get("b", 0)),
        "-Rotate", str(int(c.get("rot", 0)) // 90 * 90),
    ], check=True)
    tmp.unlink()


def slugify(s):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:50].rstrip("-")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    pptx, date = Path(sys.argv[1]), sys.argv[2]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        sys.exit("Date must look like 2026-11-15")
    z = zipfile.ZipFile(pptx)
    slides = slides_in_order(z)

    # Title slide: the first slide whose text has "Title · Passage".
    title, passage, series, subtitle, hero_src = "", "", "", "", None
    for s in slides:
        joined = [t for t in s["text"] if "·" in t]
        if joined:
            title, _, passage = (x.strip() for x in joined[0].partition("·"))
            others = [t for t in s["text"] if t != joined[0]]
            series = others[0] if others else ""
            subtitle = others[1] if len(others) > 1 else ""
            hero_src = first_layout_image(z, s["layout"]) or (s["pics"][0][0] if s["pics"] else None)
            break
    if not title:
        title = re.sub(r"^\d+\)\s*", "", pptx.stem)

    folder = ROOT / "sermons" / f"{date}-{slugify(title)}"
    folder.mkdir(parents=True, exist_ok=True)
    notes = folder / "notes.txt"
    if notes.exists():
        sys.exit(f"{notes} already exists; not overwriting it.")

    # Walk the slides, tracking which point we are in.
    counts = [len(outline_points(s["text"])) for s in slides]
    all_points = max((outline_points(s["text"]) for s in slides), key=len, default=[])
    blocks = {i: [] for i in range(len(all_points) + 1)}
    current, seen_titles, photo_n, used_media, pending = 0, set(), 0, {}, []
    outline_idx = [i for i, c in enumerate(counts) if c]
    for i, s in enumerate(slides):
        text = s["text"]
        if any("·" in t for t in text):
            continue  # title slide (and its repeats)
        if counts[i]:
            k = outline_idx.index(i)
            nxt = counts[outline_idx[k + 1]] if k + 1 < len(outline_idx) else None
            is_overview = k == 0 and nxt is not None and nxt < counts[i]
            if not is_overview:
                current = counts[i]
            continue
        # Quote slides start with a decorative “ mark in its own text box; a quote
        # that runs over several slides has the citation only on the last one.
        quote_paras = [t for t in text if t not in ("“", "”", '"') and "·" not in t]
        is_quote_slide = bool(text) and text[0] in ("“", '"') and quote_paras
        if is_quote_slide or (text and re.match(r"^[-–—]\s*\S", text[-1]) and len(text) >= 2):
            who = None
            if re.match(r"^[-–—]\s*\S", quote_paras[-1]):
                who = re.sub(r"^[-–—]\s*", "", quote_paras[-1])
                quote_paras = quote_paras[:-1]
            pending.extend(quote_paras)
            if who is None:
                continue  # quote continues on the next slide
            lines_q = []
            for n, para in enumerate(pending):
                lines_q += ([">"] if n else []) + [f"> {para}"]
            lines_q.append(f"> — {who}")
            blocks[current].append(chr(10).join(lines_q))
            pending = []
            continue
        if s["pics"] and not text:
            for media, crop in s["pics"]:
                if media is None:
                    continue
                key = (media, tuple(sorted(crop.items())))
                if key in used_media:
                    continue  # same photo shown again later in the deck
                photo_n += 1
                name = f"photo-{photo_n}.jpg"
                save_image(z, media, folder / name, crop)
                used_media[key] = name
                blocks[current].append(f"![]({name})")
            continue
        if text:
            blocks[current].append("# NOTE: slide text, place or delete: " + " / ".join(text))

    if hero_src:
        save_image(z, hero_src, folder / "hero.jpg")

    lines = [
        f"title: {title}",
        f"series: {series}",
        f"subtitle: {subtitle}",
        f"passage: {passage}",
        f"date: {date}",
        "hero: hero.jpg" if hero_src else "hero:",
        "",
        f">> PASTE THE TEXT OF {passage or 'THE PASSAGE'} HERE",
        f">> — {passage}",
        "",
    ]
    for b in blocks[0]:
        lines += [b, ""]
    for n, (num, heading, verses) in enumerate(all_points, start=1):
        lines += [f"# {heading.strip()} ({verses.strip()})", "See also: ", "[notes]", ""]
        for b in blocks.get(n, []):
            lines += [b, ""]
    notes.write_text("\n".join(lines).rstrip() + "\n", encoding="utf8")
    print(f"Draft written: {notes}")
    print("Next: paste the Scripture, add See also refs and [[blanks]], then run tools/build.py")


if __name__ == "__main__":
    main()
