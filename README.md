# Sermon Notes

Fill-in-the-blank sermon notes for Cool Community Church, one web page per
sermon, made for phones during the Sunday service. Replaces the Subsplash
fill-in pages. Built as a plain static site for GitHub Pages.

What people get: the series art from the slides, the passage to read along,
each point with tappable blanks (type the word, or tap the eye to see it),
a notes box under each point, quotes and photos (tap to enlarge, swipe
through), larger-text button, "Save" (shares or copies their filled-in notes),
and "Clear". Everything they type stays on their own phone.

## Making next week's page

**Easiest:** ask Claude: "Make the sermon notes page for [sermon] from the
slides." Claude follows these same steps.

**By hand** (from this folder, in a terminal):

1. Start from the slides (pass the Sunday's date):

   ```
   python tools/from_slides.py "C:\Users\buell\OneDrive\Ministry\Sermons\01) Expository Series\43) John\Slides\032) ....pptx" 2026-11-22
   ```

   This makes `sermons/2026-11-22-<title>/` with a draft `notes.txt`, the
   title-slide background as `hero.jpg`, and every picture slide as
   `photo-1.jpg`, `photo-2.jpg` ... (turned upright and shrunk for phones).
   It picks up the series, title, passage, points and verse ranges, and
   quote slides, and puts each quote and photo under the point where it
   appears in the deck.

   No slides? Copy last week's folder, rename it, and edit `notes.txt`.

2. Finish `notes.txt` in any text editor: paste the Scripture text, fill in the
   "See also" references, and mark blanks with `[[double brackets]]`.

3. Build and look at it:

   ```
   python tools/build.py
   python tools/preview.py
   ```

   Then open http://localhost:8642/ (Ctrl+C stops the preview).

4. Publish: commit and push. GitHub Pages republishes in a minute or two.
   The home page always shows the newest sermon first, so one QR code or
   link in the bulletin works every week.

## The notes.txt format

```
title: Hard Words for Hard Hearts…
series: Believe…
subtitle: The Gospel of John
passage: John 6:52–59
date: 2026-11-15
hero: hero.jpg

>> The Jews then disputed among themselves ...
>> — John 6:52–59

> A quote, one or more lines.
> — J. C. Ryle

![](photo-1.jpg)
![Optional description](photo-2.jpg "Optional caption under the photo")

# Believe the [[Hard]] Things Jesus Says (v. 52–55)
See also: John 6:35, 51; 12:32–34
[notes]

## A smaller sub-heading
A plain paragraph, with a [[blank]] in it.
- a bullet with a [[blank]]
```

| You write | You get |
|---|---|
| `>> text` ... `>> — John 6` | the Scripture reading card |
| `> text` ... `> — Name` | a quote with the speaker in gold |
| `# Heading (v. 1–4)` | a numbered point (numbers are automatic) |
| `## Heading` | a sub-heading inside a point |
| `See also: refs` | the gold "See also" line |
| `[notes]` | a notes box |
| `[[word]]` | a blank; `[[Christ\|Jesus]]` accepts either answer, shows the first |
| `![](photo.jpg)` | a photo; photos next to each other become a tap-to-enlarge gallery |
| `**bold**`, `*italic*`, `- bullet`, `---` | bold, italic, bullet list, divider line |

Optional settings at the top: `slug:` (the web address; default is the
date), `description:` (link preview text), `background:` and `accent:` (hex
colors, e.g. for a new series whose slides use a different palette).

## Folder map

- `sermons/` – one folder per sermon: `notes.txt` plus its photos. This is the source.
- `template/` – the page design: `page.html`, `index.html`, `assets/notes.css`, `assets/notes.js`, church logo.
- `tools/` – `from_slides.py`, `build.py`, `preview.py`, `image.ps1` (photo shrinking).
- `docs/` – the built website that GitHub Pages publishes. Don't edit by hand; `build.py` rewrites it.
- `site.json` – church name, place, and (once published) the site address and custom domain.

## Design

Colors and serif headings come from the series slides (deep green, cream,
gold, Georgia); body text, logo and overall church identity follow the CCC
brand guide (Avenir-style sans serif, white logo). Fonts fall back to
Gelasio and Nunito Sans from Google Fonts on phones without Georgia/Avenir.

## Publishing

Live at **https://www.drewbuell.com/sermon-notes/** (GitHub repository
`buelldrew-afk/sermon-notes`; Pages publishes the `docs/` folder of `main`).
The address is on drewbuell.com because that account's GitHub site uses that
domain. Each sermon is at `/sermon-notes/<date>/`; the home page always
features the newest. To publish a new week: build, then commit and push.

A different custom domain (e.g. a church domain) can be added later: put it in
`site.json` (`domain` and `url`), rebuild, push, and add a DNS CNAME record
pointing to `buelldrew-afk.github.io`.
