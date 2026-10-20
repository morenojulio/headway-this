#!/usr/bin/env python3
"""Render a folder of chapter summaries into one self-contained HTML book.

Usage:
    python3 build_book.py <summary-folder>

Reads <folder>/_book.json ({"title", "author", "lang"} or, for a bilingual
book, {"title", "author", "langs": ["en", "es"], "titles": {"es": "..."}}),
00-overview.md and NN-*.md chapter files, and writes <folder>/book.html.
Extra languages live beside the primary files as NN-slug.<lang>.md and
00-overview.<lang>.md; the page gets an EN/ES switch. Stdlib only.

Markdown subset: # / ## / ### headings, paragraphs, "- " lists, "> " quotes,
**bold**, *italic*, ==highlight==, [text](url), plus visual blocks:

    ::: idea               one-sentence core idea (banner)
    ::: concept <Term>     term card (consecutive cards form a grid)
    ::: flow               Step A -> Step B -> Step C
    ::: compare            Left | Right   (first row = headers)
    ::: stat <Number>      big number + caption
    ::: quote              short quote from the author
    ::: takeaways          "- " one-liners -> numbered cards
    ::: actions            "- " actions -> persistent checklist
"""
import html
import json
import re
import sys
from pathlib import Path

LABELS = {
    "es": {"idea": "La idea central", "takeaways": "Ideas clave", "actions": "Ponlo en práctica",
           "overview": "Resumen general", "chapters": "Capítulos", "all": "Todas las ideas clave",
           "min": "min de lectura", "prev": "Anterior", "next": "Siguiente", "theme": "Tema",
           "font": "Fuente de lectura", "smaller": "Texto más pequeño", "bigger": "Texto más grande"},
    "en": {"idea": "The core idea", "takeaways": "Key takeaways", "actions": "Put it into practice",
           "overview": "Overview", "chapters": "Chapters", "all": "All key takeaways",
           "min": "min read", "prev": "Previous", "next": "Next", "theme": "Theme",
           "font": "Reading font", "smaller": "Smaller text", "bigger": "Larger text"},
}


def inline(text: str) -> str:
    t = html.escape(text, quote=False)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*", r"<em>\1</em>", t)
    t = re.sub(r"==(.+?)==", r"<mark>\1</mark>", t)

    def link(m):
        label, href = m.group(1), m.group(2)
        ch = re.match(r"(\d{2})-.*\.md$", href)
        href = f"#ch-{ch.group(1)}" if ch else href
        return f'<a href="{html.escape(href)}">{label}</a>'

    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, t)


def items(body):
    return [l[2:].strip() for l in body if l.startswith("- ")]


def render_block(kind, arg, body, L, ch_id, takeaways):
    text = " ".join(l.strip() for l in body if l.strip())
    if kind == "idea":
        return f'<div class="idea"><span class="eyebrow">{L["idea"]}</span><p>{inline(text)}</p></div>'
    if kind == "concept":
        return f'<div class="concept"><div class="term">{inline(arg)}</div><p>{inline(text)}</p></div>'
    if kind == "flow":
        steps = [s.strip() for s in text.split("->") if s.strip()]
        parts = '<span class="arrow" aria-hidden="true">→</span>'.join(
            f'<div class="step"><span class="n">{i}</span>{inline(s)}</div>' for i, s in enumerate(steps, 1))
        return f'<div class="flow">{parts}</div>'
    if kind == "compare":
        rows = [[c.strip() for c in l.split("|")] for l in body if "|" in l]
        if not rows:
            return ""
        head = "".join(f"<th>{inline(c)}</th>" for c in rows[0])
        trs = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rows[1:])
        return f'<table class="compare"><thead><tr>{head}</tr></thead><tbody>{trs}</tbody></table>'
    if kind == "stat":
        return f'<div class="stat"><div class="num">{inline(arg)}</div><p>{inline(text)}</p></div>'
    if kind == "quote":
        return f'<blockquote class="pull">{inline(text)}</blockquote>'
    if kind == "takeaways":
        lst = items(body)
        takeaways.extend(lst)
        cards = "".join(f'<li><span class="n">{i:02d}</span><p>{inline(x)}</p></li>' for i, x in enumerate(lst, 1))
        return f'<h2 class="sec">{L["takeaways"]}</h2><ol class="takeaways">{cards}</ol>'
    if kind == "actions":
        lis = "".join(
            f'<li><label><input type="checkbox" data-key="{ch_id}-{i}"><span>{inline(x)}</span></label></li>'
            for i, x in enumerate(items(body), 1))
        return f'<h2 class="sec">{L["actions"]}</h2><ul class="actions">{lis}</ul>'
    return f"<p>{inline(text)}</p>"


def render(md: str, L, ch_id):
    """Return (title, html, idea_text, takeaways)."""
    out, para, lst, takeaways = [], [], [], []
    title, idea = "", ""
    lines = md.splitlines()

    def flush():
        if para:
            out.append(f"<p>{inline(' '.join(para))}</p>")
            para.clear()
        if lst:
            out.append("<ul>" + "".join(f"<li>{inline(x)}</li>" for x in lst) + "</ul>")
            lst.clear()

    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if line.startswith(":::") and line.strip() != ":::":
            flush()
            head = line[3:].strip().split(" ", 1)
            kind, arg = head[0].lower(), (head[1] if len(head) > 1 else "")
            body = []
            i += 1
            while i < len(lines) and lines[i].strip() != ":::":
                body.append(lines[i])
                i += 1
            if kind == "idea" and not idea:
                idea = " ".join(l.strip() for l in body if l.strip())
            block = render_block(kind, arg, body, L, ch_id, takeaways)
            # Group consecutive concept cards into one grid.
            if kind == "concept" and out and out[-1].startswith('<div class="concepts">'):
                out[-1] = out[-1][:-6] + block + "</div>"
            elif kind == "concept":
                out.append(f'<div class="concepts">{block}</div>')
            else:
                out.append(block)
        elif line.startswith("# "):
            flush()
            title = line[2:].strip()
        elif line.startswith("## ") or line.startswith("### "):
            flush()
            lvl = 2 if line.startswith("## ") else 3
            out.append(f"<h{lvl}>{inline(line[lvl + 1:].strip())}</h{lvl}>")
        elif line.startswith("- "):
            if para:
                flush()
            lst.append(line[2:].strip())
        elif line.startswith("> "):
            flush()
            out.append(f"<blockquote>{inline(line[2:].strip())}</blockquote>")
        elif not line.strip():
            flush()
        else:
            para.append(line.strip())
        i += 1
    flush()
    return title, "\n".join(out), idea, takeaways


CSS = """
:root{--bg:#fbfaf7;--surface:#fff;--ink:#1d1d1f;--muted:#6b6b70;--line:#e7e4dd;
--accent:#3b5bdb;--accent-soft:#eef1fd;--mark:#fff1b8;--ok:#2b8a3e}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#141416;--surface:#1c1c1f;
--ink:#ececee;--muted:#9a9aa2;--line:#2c2c31;--accent:#8ea2ff;--accent-soft:#222842;--mark:#5a4b12;--ok:#69db7c}}
:root[data-theme="dark"]{--bg:#141416;--surface:#1c1c1f;--ink:#ececee;--muted:#9a9aa2;--line:#2c2c31;
--accent:#8ea2ff;--accent-soft:#222842;--mark:#5a4b12;--ok:#69db7c}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--read,"Newsreader"),Georgia,serif;
font-size:calc(17px * var(--scale,1));line-height:var(--lh,1.7);
-webkit-font-smoothing:antialiased}
.ui,nav,.eyebrow,.meta,.sec,th,.step,.term,.num,.takeaways .n,button{font-family:"Inter",system-ui,sans-serif}
#bar{position:fixed;top:0;left:0;height:3px;background:var(--accent);width:0;z-index:20}
nav{position:fixed;inset:0 auto 0 0;width:280px;padding:28px 20px;border-right:1px solid var(--line);
overflow-y:auto;background:var(--bg);font-size:14px}
nav .book{font-weight:700;font-size:15px;line-height:1.3}nav .author{color:var(--muted);margin-bottom:24px}
nav a{display:flex;gap:10px;padding:7px 10px;border-radius:8px;color:var(--muted);text-decoration:none;line-height:1.35}
nav a:hover{background:var(--accent-soft);color:var(--ink)}
nav a.on{background:var(--accent-soft);color:var(--accent);font-weight:600}
nav a .k{min-width:20px;font-variant-numeric:tabular-nums;opacity:.7}
main{margin-left:280px;padding:64px 24px 120px}
article{max-width:680px;margin:0 auto}
.meta{color:var(--muted);font-size:13px;letter-spacing:.04em;text-transform:uppercase}
h1{font:700 2.4rem/1.15 "Inter",system-ui,sans-serif;letter-spacing:-.02em;margin:.3em 0 .8em}
h2,h3{font-family:"Inter",system-ui,sans-serif;letter-spacing:-.01em;line-height:1.3}
h2{font-size:1.35rem;margin:2.2em 0 .6em}h3{font-size:1.1rem;margin:1.8em 0 .4em}
a{color:var(--accent)}mark{background:var(--mark);color:inherit;padding:0 .15em;border-radius:3px}
strong{font-weight:650}
blockquote{margin:1.6em 0;padding-left:18px;border-left:3px solid var(--line);color:var(--muted);font-style:italic}
[data-font="opendyslexic"]{--lh:1.85}[data-font="opendyslexic"] .pull{font-size:1.2rem}
.langs{display:flex;gap:4px;margin-bottom:20px;background:var(--surface);border:1px solid var(--line);
border-radius:10px;padding:3px;width:max-content}
.langs button{font:600 12px "Inter",system-ui,sans-serif;border:0;background:none;color:var(--muted);
padding:5px 12px;border-radius:7px;cursor:pointer}
.langs button.on{background:var(--accent-soft);color:var(--accent)}
.navlang[hidden]{display:none}
.reader{margin-top:24px;display:grid;gap:8px}
.reader select,.reader button{font:13px "Inter",system-ui,sans-serif;border:1px solid var(--line);
background:var(--surface);color:var(--ink);border-radius:8px;padding:6px 10px;cursor:pointer}
.reader .row{display:flex;gap:6px}.reader .row button{flex:1;white-space:nowrap}
.pull{border:0;padding:0;margin:2.2em 0;font-size:1.45rem;line-height:1.45;color:var(--ink);text-align:center}
.pull::before{content:"“";display:block;font-size:3rem;line-height:1;color:var(--accent)}
.idea{background:var(--accent-soft);border-radius:14px;padding:22px 26px;margin:0 0 2.2em}
.idea p{margin:.3em 0 0;font-size:1.25rem;line-height:1.5;font-weight:500}
.eyebrow{font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--accent)}
.concepts{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:1.8em 0}
.concept{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:16px 18px}
.concept .term{font-weight:700;font-size:15px;color:var(--accent);margin-bottom:4px}
.concept p{margin:0;font-size:15px;line-height:1.55}
.flow{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin:2em 0}
.step{flex:1 1 120px;background:var(--surface);border:1px solid var(--line);border-radius:12px;
padding:12px 14px;font-size:14px;line-height:1.4;font-weight:500}
.step .n{display:block;font-size:11px;color:var(--accent);font-weight:700;margin-bottom:2px}
.arrow{color:var(--accent);font-size:20px}
.compare{width:100%;border-collapse:separate;border-spacing:0;margin:2em 0;font-size:15px;
border:1px solid var(--line);border-radius:12px;overflow:hidden;background:var(--surface)}
.compare th{text-align:left;padding:12px 16px;font-size:13px;background:var(--accent-soft);color:var(--accent)}
.compare td{padding:10px 16px;border-top:1px solid var(--line);vertical-align:top;line-height:1.5}
.compare td+td,.compare th+th{border-left:1px solid var(--line)}
.stat{display:flex;gap:18px;align-items:center;margin:2em 0;padding:18px 0;border-block:1px solid var(--line)}
.stat .num{font-size:2.6rem;font-weight:800;color:var(--accent);letter-spacing:-.03em;line-height:1}
.stat p{margin:0;color:var(--muted);font-size:15px;line-height:1.5}
.sec{font-size:13px!important;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);
margin-top:3.2em!important;padding-top:1.6em;border-top:1px solid var(--line)}
.takeaways{list-style:none;padding:0;display:grid;gap:10px}
.takeaways li{display:flex;gap:14px;align-items:flex-start;background:var(--surface);
border:1px solid var(--line);border-radius:12px;padding:14px 18px}
.takeaways .n{font-weight:800;color:var(--accent);font-size:14px;padding-top:3px}
.takeaways p{margin:0;font-weight:500;line-height:1.5}
.actions{list-style:none;padding:0}.actions li{border-bottom:1px solid var(--line)}
.actions label{display:flex;gap:12px;padding:12px 2px;cursor:pointer;line-height:1.5}
.actions input{accent-color:var(--ok);width:18px;height:18px;margin-top:4px;flex:none}
.actions input:checked+span{color:var(--muted);text-decoration:line-through}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:12px;margin:1.4em 0}
.card{display:block;text-decoration:none;color:inherit;background:var(--surface);border:1px solid var(--line);
border-radius:12px;padding:16px 18px;transition:border-color .15s,transform .15s}
.card:hover{border-color:var(--accent);transform:translateY(-2px)}
.card .k{font:700 12px "Inter",sans-serif;color:var(--accent)}
.card b{display:block;font:600 15px/1.35 "Inter",sans-serif;margin:4px 0 6px}
.card span{font-size:14px;color:var(--muted);line-height:1.45;display:block}
.all h3{font-size:14px;color:var(--muted)}.all ul{padding-left:20px}.all li{margin:.3em 0}
.pager{display:flex;justify-content:space-between;gap:12px;margin-top:4em}
.pager a{font:600 14px "Inter",sans-serif;text-decoration:none;padding:10px 14px;border:1px solid var(--line);
border-radius:10px;max-width:48%}
section[hidden]{display:none}
@media (max-width:900px){nav{position:static;width:auto;border-right:0;border-bottom:1px solid var(--line);
max-height:none;padding:20px 16px}main{margin-left:0;padding:36px 16px 80px}h1{font-size:1.9rem}
.arrow{transform:rotate(90deg);width:100%;text-align:center}.flow{flex-direction:column;align-items:stretch}}
"""

JS = """
const KEY=document.body.dataset.book;
const secs=[...document.querySelectorAll('section')];
const links=[...document.querySelectorAll('nav a[href^="#"]')];
const LANGS=document.body.dataset.langs.split(' ');
let lang=LANGS[0];try{const l=localStorage.getItem(KEY+'-lang');if(LANGS.includes(l))lang=l}catch(e){}
function show(keepScroll){const id=(location.hash||'#ch-00').slice(1);
 secs.forEach(s=>s.hidden=!(s.dataset.ch===id&&s.dataset.lang===lang));
 document.querySelectorAll('.navlang').forEach(n=>n.hidden=n.dataset.lang!==lang);
 document.querySelectorAll('[data-set-lang]').forEach(b=>b.classList.toggle('on',b.dataset.setLang===lang));
 document.documentElement.lang=lang;
 links.forEach(a=>a.classList.toggle('on',a.hash==='#'+id));
 if(!keepScroll)window.scrollTo(0,0);bar()}
document.querySelectorAll('[data-set-lang]').forEach(b=>b.onclick=()=>{lang=b.dataset.setLang;
 try{localStorage.setItem(KEY+'-lang',lang)}catch(e){}show(true)});
function bar(){const h=document.documentElement;const p=h.scrollTop/((h.scrollHeight-h.clientHeight)||1);
 document.getElementById('bar').style.width=(p*100)+'%'}
addEventListener('hashchange',()=>show());addEventListener('scroll',bar,{passive:true});
let st={};try{st=JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){}
document.querySelectorAll('.actions input').forEach(c=>{c.checked=!!st[c.dataset.key];
 c.onchange=()=>{st[c.dataset.key]=c.checked;try{localStorage.setItem(KEY,JSON.stringify(st))}catch(e){}}});
const FONTS={newsreader:'"Newsreader"',literata:'"Literata"',sourceserif:'"Source Serif 4"',
 merriweather:'"Merriweather"',atkinson:'"Atkinson Hyperlegible"',lexend:'"Lexend"',opendyslexic:'"OpenDyslexic"',inter:'"Inter"'};
let rp={font:'newsreader',scale:1};try{rp=Object.assign(rp,JSON.parse(localStorage.getItem('reader-prefs')||'{}'))}catch(e){}
const sel=document.getElementById('font');
function applyReader(){const r=document.documentElement;r.style.setProperty('--read',FONTS[rp.font]||FONTS.newsreader);
 r.style.setProperty('--scale',rp.scale);r.dataset.font=rp.font;sel.value=rp.font;
 try{localStorage.setItem('reader-prefs',JSON.stringify(rp))}catch(e){}}
sel.onchange=()=>{rp.font=sel.value;applyReader()};
document.getElementById('smaller').onclick=()=>{rp.scale=Math.max(.85,+(rp.scale-.05).toFixed(2));applyReader()};
document.getElementById('bigger').onclick=()=>{rp.scale=Math.min(1.4,+(rp.scale+.05).toFixed(2));applyReader()};
applyReader();
document.querySelector('.theme').onclick=()=>{const r=document.documentElement;
 const dark=r.dataset.theme?r.dataset.theme==='dark':matchMedia('(prefers-color-scheme: dark)').matches;
 r.dataset.theme=dark?'light':'dark'};
show();
"""


def label(title):
    m = re.match(r"^(\d+)\.", title)
    return m.group(1) if m else "·"


def short(title):
    return re.sub(r"^\d+\.\s*", "", title)


def minutes(md):
    return max(1, round(len(md.split()) / 230))


def build_lang(folder, meta, lang, primary):
    """Render nav links and sections for one language. Returns (nav_html, sections_html, count)."""
    L = LABELS.get(lang[:2], LABELS["en"])
    title_txt = meta.get("titles", {}).get(lang, meta["title"])
    chapters = []
    for f in sorted(folder.glob("[0-9][0-9]-*.md")):
        if "." in f.stem or f.name[:2] == "00":
            continue  # translations are found via their primary file
        src = f if lang == primary else f.with_name(f"{f.stem}.{lang}.md")
        if not src.exists():
            continue
        n = f.name[:2]
        md = src.read_text(encoding="utf-8")
        title, body, idea, tks = render(md, L, f"ch-{n}")
        chapters.append({"n": n, "title": title or f.stem, "body": body, "idea": idea,
                         "takeaways": tks, "min": minutes(md)})

    ov_file = folder / ("00-overview.md" if lang == primary else f"00-overview.{lang}.md")
    ov_md = ov_file.read_text(encoding="utf-8") if ov_file.exists() else ""
    _, ov_body, _, _ = render(ov_md, L, "ch-00")
    grid = "".join(
        f'<a class="card" href="#ch-{c["n"]}"><div class="k">{label(c["title"])} · {c["min"]} {L["min"]}</div>'
        f'<b>{inline(short(c["title"]))}</b><span>{inline(c["idea"])}</span></a>'
        for c in chapters)
    all_tk = "".join(
        f'<h3>{inline(c["title"])}</h3><ul>' + "".join(f"<li>{inline(t)}</li>" for t in c["takeaways"]) + "</ul>"
        for c in chapters if c["takeaways"])
    attrs = f'data-lang="{lang}" lang="{lang}"'
    sections = [f'<section data-ch="ch-00" {attrs}><article><div class="meta">{L["overview"]}</div>'
                f'<h1>{html.escape(title_txt)}</h1>{ov_body}'
                f'<h2 class="sec">{L["chapters"]}</h2><div class="grid">{grid}</div>'
                f'<h2 class="sec">{L["all"]}</h2><div class="all">{all_tk}</div></article></section>']
    order = ["00"] + [c["n"] for c in chapters]
    titles = {"00": L["overview"], **{c["n"]: c["title"] for c in chapters}}
    for idx, c in enumerate(chapters, 1):
        prev_n, next_n = order[idx - 1], (order[idx + 1] if idx + 1 < len(order) else None)
        pager = f'<a href="#ch-{prev_n}">← {inline(titles[prev_n])}</a>'
        pager += f'<a href="#ch-{next_n}">{inline(titles[next_n])} →</a>' if next_n else "<span></span>"
        sections.append(
            f'<section data-ch="ch-{c["n"]}" {attrs} hidden><article><div class="meta">{c["min"]} {L["min"]}</div>'
            f'<h1>{inline(c["title"])}</h1>{c["body"]}<div class="pager">{pager}</div></article></section>')

    nav = (f'<div class="navlang" {attrs}><div class="book">{html.escape(title_txt)}</div>'
           f'<div class="author">{html.escape(meta.get("author", ""))}</div>'
           f'<a href="#ch-00"><span class="k">◎</span>{L["overview"]}</a>' + "".join(
               f'<a href="#ch-{c["n"]}"><span class="k">{label(c["title"])}</span>'
               f'{inline(short(c["title"]))}</a>' for c in chapters) + "</div>")
    return nav, "".join(sections), len(chapters)


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    folder = Path(sys.argv[1])
    meta = json.loads((folder / "_book.json").read_text(encoding="utf-8"))
    langs = meta.get("langs") or [meta.get("lang", "es")]
    primary = langs[0]
    L = LABELS.get(primary[:2], LABELS["en"])
    slug = re.sub(r"[^a-z0-9]+", "-", meta["title"].lower()).strip("-")

    navs, mains, counts = [], [], []
    for lang in langs:
        nav, secs, n = build_lang(folder, meta, lang, primary)
        navs.append(nav)
        mains.append(secs)
        counts.append(f"{lang}: {n}")
    switch = ""
    if len(langs) > 1:
        switch = '<div class="langs" role="group">' + "".join(
            f'<button type="button" data-set-lang="{l}">{l.upper()}</button>' for l in langs) + "</div>"

    page = f"""<!doctype html>
<html lang="{html.escape(primary)}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(meta['title'])}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;1,6..72,400&family=Literata:ital,opsz,wght@0,7..72,400;0,7..72,600;1,7..72,400&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&family=Merriweather:ital,wght@0,400;0,700;1,400&family=Atkinson+Hyperlegible:ital,wght@0,400;0,700;1,400&family=Lexend:wght@400;600&display=swap" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/@fontsource/opendyslexic@5.2.5/400.css" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/@fontsource/opendyslexic@5.2.5/700.css" rel="stylesheet">
<style>{CSS}</style></head>
<body data-book="book-{slug}" data-langs="{' '.join(langs)}"><div id="bar"></div>
<nav>{switch}{''.join(navs)}<div class="reader"><select id="font" aria-label="{L['font']}">
<option value="newsreader">Newsreader</option><option value="literata">Literata</option>
<option value="sourceserif">Source Serif</option><option value="merriweather">Merriweather</option>
<option value="atkinson">Atkinson Hyperlegible</option><option value="lexend">Lexend</option>
<option value="opendyslexic">OpenDyslexic</option><option value="inter">Inter (sans)</option></select>
<div class="row"><button id="smaller" type="button" aria-label="{L['smaller']}">A−</button>
<button id="bigger" type="button" aria-label="{L['bigger']}">A+</button>
<button class="theme" type="button">◐ {L['theme']}</button></div></div></nav>
<main>{''.join(mains)}</main><script>{JS}</script></body></html>"""
    out = folder / "book.html"
    out.write_text(page, encoding="utf-8")
    print(f"Wrote {out} ({', '.join(counts)} chapters)")


if __name__ == "__main__":
    main()
