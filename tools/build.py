"""Build the sermon-notes website from sermons/*/notes.txt into docs/.

    python tools/build.py

docs/ is what GitHub Pages publishes. Run this after editing any notes.txt.
The notes.txt format is described in README.md.
"""
import html
import json
import re
import shutil
import subprocess
import time
from datetime import date as Date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERMONS = ROOT / "sermons"
TEMPLATE = ROOT / "template"
DOCS = ROOT / "docs"
SITE = json.loads((ROOT / "site.json").read_text(encoding="utf8"))
VERSION = str(int(time.time()))
BIG_IMAGE = 700_000  # bytes; larger photos are shrunk for phones

KEYS = {"title", "series", "subtitle", "passage", "date", "hero", "slug", "description",
        "background", "accent"}


# ---------------------------------------------------------------- parsing
def parse(path):
    meta, body = {}, []
    lines = path.read_text(encoding="utf8").splitlines()
    i = 0
    while i < len(lines):
        m = re.match(r"^([a-z_]+):\s*(.*)$", lines[i])
        if m and m.group(1) in KEYS:
            meta[m.group(1)] = m.group(2).strip()
            i += 1
        elif not lines[i].strip() and not body:
            i += 1
        else:
            break
    body = lines[i:]
    return meta, body


def esc(s):
    return html.escape(s, quote=True)


BLANK_RE = re.compile(r"\[\[(.+?)\]\]")


def inline(text, counter):
    """Escape text, then turn [[answer]], **bold**, *italic* into HTML."""
    parts, last = [], 0
    for m in BLANK_RE.finditer(text):
        parts.append(_fmt(esc(text[last:m.start()])))
        answer = m.group(1).strip()
        first = answer.split("|")[0]
        counter[0] += 1
        parts.append(
            f'<span class="blank" data-answer="{esc(answer)}">'
            f'<input type="text" aria-label="Blank {counter[0]}" autocomplete="off" autocorrect="off" '
            f'autocapitalize="none" spellcheck="false" enterkeyhint="next" style="--len:{max(len(first), 3)}">'
            f'<button class="peek" type="button" aria-label="Show the answer">'
            f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round">'
            f'<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg>'
            f'</button></span>')
        last = m.end()
    parts.append(_fmt(esc(text[last:])))
    return "".join(parts)


def _fmt(s):
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?![*\w])", r"<em>\1</em>", s)
    s = s.replace("--", "–")
    return s


IMG_RE = re.compile(r'^!\[(.*?)\]\(\s*([^\s)]+)(?:\s+"(.*?)")?\s*\)\s*$')
POINT_RE = re.compile(r"^#\s+(.*?)(?:\s*\(((?:vv?\.|verses?)\s*[^)]*)\))?\s*$")


def render_body(lines, counter, images):
    out = []
    sections = [{"head": None, "html": []}]
    buf = sections[0]["html"]

    def flush_para(p):
        if p:
            text = " ".join(x.strip() for x in p)
            cls = ' class="fill"' if "[[" in text else ""
            buf.append(f"<p{cls}>{inline(text, counter)}</p>")

    i, para = 0, []
    while i < len(lines):
        line = lines[i].rstrip()
        s = line.strip()

        if not s:
            flush_para(para); para = []
            i += 1; continue

        if s.startswith("# NOTE:"):
            i += 1; continue

        m = POINT_RE.match(s) if s.startswith("# ") else None
        if m:
            flush_para(para); para = []
            sections.append({"head": (m.group(1), (m.group(2) or "").strip()), "html": []})
            buf = sections[-1]["html"]
            i += 1; continue

        if s.startswith("## "):
            flush_para(para); para = []
            buf.append(f"<h3>{inline(s[3:].strip(), counter)}</h3>")
            i += 1; continue

        if s.lower().startswith("see also:"):
            flush_para(para); para = []
            refs = s.split(":", 1)[1].strip()
            if refs:
                buf.append(f'<p class="see-also"><b>See also</b>{inline(refs, counter)}</p>')
            i += 1; continue

        if s.lower() in ("[notes]", "[note]"):
            flush_para(para); para = []
            buf.append('<div class="notes"><textarea rows="2" placeholder="Your notes…" '
                       'aria-label="Your notes"></textarea></div>')
            i += 1; continue

        if s == "---":
            flush_para(para); para = []
            buf.append('<hr class="rule">')
            i += 1; continue

        if s.startswith(">>"):
            flush_para(para); para = []
            block = []
            while i < len(lines) and lines[i].strip().startswith(">>"):
                block.append(lines[i].strip()[2:].strip()); i += 1
            buf.append(scripture(block, counter))
            continue

        if s.startswith(">"):
            flush_para(para); para = []
            block = []
            while i < len(lines) and lines[i].strip().startswith(">") and not lines[i].strip().startswith(">>"):
                block.append(lines[i].strip()[1:].strip()); i += 1
            buf.append(quote(block, counter))
            continue

        if IMG_RE.match(s):
            flush_para(para); para = []
            figs = []
            while i < len(lines):
                t = lines[i].strip()
                mm = IMG_RE.match(t)
                if mm:
                    figs.append(mm.groups()); i += 1
                elif not t and i + 1 < len(lines) and IMG_RE.match(lines[i + 1].strip()):
                    i += 1
                else:
                    break
            buf.append(gallery(figs, images))
            continue

        if re.match(r"^([-*]|\d+[.)])\s+", s):
            flush_para(para); para = []
            ordered = bool(re.match(r"^\d", s))
            items = []
            while i < len(lines) and re.match(r"^\s*([-*]|\d+[.)])\s+", lines[i]):
                t = re.sub(r"^\s*([-*]|\d+[.)])\s+", "", lines[i]).strip()
                cls = ' class="fill"' if "[[" in t else ""
                items.append(f"<li{cls}>{inline(t, counter)}</li>"); i += 1
            tag = "ol" if ordered else "ul"
            buf.append(f"<{tag}>" + "".join(items) + f"</{tag}>")
            continue

        para.append(s)
        i += 1
    flush_para(para)

    html_out = []
    n = 0
    for sec in sections:
        if sec["head"] is None:
            if sec["html"]:
                html_out.append('<section class="intro">' + "\n".join(sec["html"]) + "</section>")
            continue
        n += 1
        heading, verses = sec["head"]
        v = f'<div class="verses">{esc(verses)}</div>' if verses else ""
        html_out.append(
            f'<section class="point" id="point-{n}"><div class="point-head">'
            f'<span class="num" aria-hidden="true">{n}</span>'
            f'<h2>{inline(heading, counter)}</h2>{v}</div>\n' + "\n".join(sec["html"]) + "</section>")
    return "\n".join(html_out)


def split_cite(block):
    cite = None
    if block and re.match(r"^[—–-]\s*\S", block[-1]):
        cite = re.sub(r"^[—–-]+\s*", "", block[-1]); block = block[:-1]
    paras, cur = [], []
    for b in block:
        if b:
            cur.append(b)
        elif cur:
            paras.append(" ".join(cur)); cur = []
    if cur:
        paras.append(" ".join(cur))
    return paras, cite


def scripture(block, counter):
    paras, cite = split_cite(block)
    body = "".join(f"<p>{inline(p, counter)}</p>" for p in paras)
    c = f"<cite>{esc(cite)}</cite>" if cite else ""
    return (f'<section class="reading"><p class="label">Read along</p>'
            f'<div class="body">{body}{c}</div>'
            f'<button class="more" type="button">Read the whole passage</button></section>')


def quote(block, counter):
    paras, cite = split_cite(block)
    body = "".join(f"<p>{inline(p, counter)}</p>" for p in paras)
    c = f"<cite>{esc(cite)}</cite>" if cite else ""
    return f'<blockquote class="quote">{body}{c}</blockquote>'


def gallery(figs, images):
    n = len(figs)
    cls = "one" if n == 1 else ""
    items = []
    for alt, src, cap in figs:
        images.append(src)
        a = esc(alt or cap or "Sermon photo")
        fc = f"<figcaption>{esc(cap)}</figcaption>" if cap else ""
        items.append(f'<figure><button type="button" aria-label="Enlarge photo">'
                     f'<img src="{esc(src)}" alt="{a}" loading="lazy" decoding="async"></button>{fc}</figure>')
    return f'<div class="gallery {cls}">' + "".join(items) + "</div>"


# ---------------------------------------------------------------- output
def long_date(iso):
    try:
        d = Date.fromisoformat(iso)
    except ValueError:
        return iso
    return d.strftime("%A, %B ") + str(d.day) + d.strftime(", %Y")


def shrink_or_copy(src, dest):
    if src.suffix.lower() in (".jpg", ".jpeg", ".png") and src.stat().st_size > BIG_IMAGE:
        dest = dest.with_suffix(".jpg") if src.suffix.lower() == ".png" else dest
        subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                        str(ROOT / "tools" / "image.ps1"), "-In", str(src), "-Out", str(dest),
                        "-MaxSide", "1600"], check=True)
        return dest.name
    shutil.copy2(src, dest)
    return dest.name


def image_size(path):
    """(width, height) of a JPEG or PNG, or None."""
    try:
        b = path.read_bytes()
    except OSError:
        return None
    if b[:4] == bytes([0x89, 0x50, 0x4E, 0x47]):
        return int.from_bytes(b[16:20], "big"), int.from_bytes(b[20:24], "big")
    i = 2
    while i < len(b) - 9 and b[:2] == bytes([0xFF, 0xD8]):
        if b[i] != 0xFF:
            i += 1; continue
        marker, length = b[i + 1], int.from_bytes(b[i + 2:i + 4], "big")
        if marker in (0xC0, 0xC1, 0xC2):
            return int.from_bytes(b[i + 7:i + 9], "big"), int.from_bytes(b[i + 5:i + 7], "big")
        i += 2 + length
    return None


def fill(template, values):
    return re.sub(r"\{\{(\w+)\}\}", lambda m: str(values.get(m.group(1), "")), template)


def build_page(folder):
    meta, body = parse(folder / "notes.txt")
    m = re.match(r"^(\d{4}-\d{2}-\d{2})", folder.name)
    iso = meta.get("date") or (m.group(1) if m else "")
    slug = meta.get("slug") or iso or folder.name
    out = DOCS / slug
    out.mkdir(parents=True, exist_ok=True)
    for old in out.iterdir():  # clear the last build of this page (OneDrive can lock folders)
        if old.is_file():
            old.unlink()

    counter, images = [0], []
    body_html = render_body(body, counter, images)

    # Copy (and shrink if needed) the images this page uses.
    renamed = {}
    for name in set(images + ([meta["hero"]] if meta.get("hero") else [])):
        src = folder / name
        if not src.exists():
            print(f"  ! missing image {src}")
            continue
        new = shrink_or_copy(src, out / Path(name).name)
        if new != name:
            renamed[name] = new
    for old, new in renamed.items():
        body_html = body_html.replace(f'src="{esc(old)}"', f'src="{esc(new)}"')
    def add_size(m):
        size = image_size(out / html.unescape(m.group(1)))
        return m.group(0) + (f' width="{size[0]}" height="{size[1]}"' if size else "")
    body_html = re.sub(r'<img src="([^"]+)"', add_size, body_html)

    title = meta.get("title", folder.name)
    passage = meta.get("passage", "")
    hero = renamed.get(meta.get("hero", ""), meta.get("hero", ""))
    bg = meta.get("background", "#12231d")
    theme = f"--bg:{bg};" + (f"--accent:{meta['accent']};" if meta.get("accent") else "")
    series_block = ""
    if meta.get("series"):
        series_block = f'<p class="series">{esc(meta["series"])}</p>'
        if meta.get("subtitle"):
            series_block += f'<p class="subtitle">{esc(meta["subtitle"])}</p>'
    elif meta.get("subtitle"):
        series_block = f'<p class="eyebrow">{esc(meta["subtitle"])}</p>'
    desc = meta.get("description") or f"Sermon notes for {title} ({passage}), {SITE['church']}."
    n_blanks = counter[0]
    reveal_button = ""
    how = ""
    if n_blanks:
        reveal_button = ('<button type="button" class="primary" data-action="reveal" aria-label="Show all answers">'
                         '<svg viewBox="0 0 24 24"><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z"/>'
                         '<circle cx="12" cy="12" r="3"/></svg><span>Answers <span class="count" data-count></span></span></button>')
        how = ('<div class="how"><div><b>Fill in the blanks</b> as you listen. Type the word, or tap '
               'the eye to see it. Your notes stay on this phone.</div>'
               '<button class="x" type="button" aria-label="Hide this tip">×</button></div>')
    abs_hero = f"{SITE['url'].rstrip('/')}/{slug}/{hero}" if hero and SITE.get("url") else ""
    page = fill((TEMPLATE / "page.html").read_text(encoding="utf8"), {
        "title": esc(title), "title_attr": esc(title), "passage": esc(passage), "passage_attr": esc(passage),
        "date_long": esc(long_date(iso)), "date_sep": '<span class="dot">·</span>' if iso and passage else "",
        "church": esc(SITE["church"]), "place": esc(SITE["place"]),
        "description": esc(desc), "bg": esc(bg), "theme": theme, "slug": esc(slug),
        "hero_img": f'<img class="hero-img" src="{esc(hero)}" alt="" fetchpriority="high">' if hero else "",
        "hero_class": "" if hero else " no-img",
        "og_image": f'<meta property="og:image" content="{esc(abs_hero)}">' if abs_hero else "",
        "series_block": series_block, "how": how, "body": body_html,
        "reveal_button": reveal_button, "version": VERSION,
    })
    (out / "index.html").write_text(page, encoding="utf8")
    print(f"  built docs/{slug}/  ({n_blanks} blanks, {len(images)} photos)")
    return {"slug": slug, "date": iso, "title": title, "passage": passage, "hero": hero,
            "series": meta.get("series", ""), "subtitle": meta.get("subtitle", "")}


def build_index(pages):
    pages = sorted(pages, key=lambda p: p["date"], reverse=True)
    feature, rest = "", pages
    if pages:
        p, rest = pages[0], pages[1:]
        img = f'<img src="{esc(p["slug"])}/{esc(p["hero"])}" alt="">' if p["hero"] else ""
        label = "This Sunday" if p["date"] >= Date.today().isoformat() else "Latest sermon"
        feature = (f'<a class="feature" href="{esc(p["slug"])}/">{img}<div class="inner">'
                   f'<p class="eyebrow">{label}</p><h2 class="title">{esc(p["title"])}</h2>'
                   f'<p class="meta"><span class="ref">{esc(p["passage"])}</span>'
                   f'<span class="dot">·</span>{esc(long_date(p["date"]))}</p>'
                   f'<span class="go">Open the notes</span></div></a>')
    lst = ""
    if rest:
        lst = '<p class="label">Earlier sermons</p><ul class="list">' + "".join(
            f'<li><a href="{esc(p["slug"])}/"><div class="t">{esc(p["title"])}</div>'
            f'<div class="m">{esc(p["passage"])} · {esc(long_date(p["date"]))}</div></a></li>' for p in rest) + "</ul>"
    page = fill((TEMPLATE / "index.html").read_text(encoding="utf8"), {
        "church": esc(SITE["church"]), "place": esc(SITE["place"]),
        "feature": feature, "list": lst, "version": VERSION})
    (DOCS / "index.html").write_text(page, encoding="utf8")


def main():
    DOCS.mkdir(exist_ok=True)
    shutil.copytree(TEMPLATE / "assets", DOCS / "assets", dirs_exist_ok=True)
    (DOCS / ".nojekyll").write_text("", encoding="utf8")
    if SITE.get("domain"):
        (DOCS / "CNAME").write_text(SITE["domain"] + "\n", encoding="utf8")
    pages = []
    for folder in sorted(SERMONS.iterdir()):
        if (folder / "notes.txt").exists() and not folder.name.startswith("_"):
            pages.append(build_page(folder))
    build_index(pages)
    print(f"Done: {len(pages)} sermon page(s) in docs/. Preview: python tools/preview.py")


if __name__ == "__main__":
    main()
