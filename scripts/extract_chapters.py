#!/usr/bin/env python3
"""Split a book file (EPUB, PDF, TXT, MD) into one text file per chapter.

Usage:
    python3 extract_chapters.py <book-file> <out-dir>

Writes <out-dir>/NN.txt per chapter and <out-dir>/index.json with
titles and word counts. Needs `pandoc` for EPUB and `pdftotext` for PDF.
Stdlib only.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

# Heading lines that usually open a chapter, in EN and ES.
CHAPTER_RE = re.compile(
    r"^\s*(#{1,2}\s+.+"
    r"|(chapter|cap[ií]tulo|part|parte|lesson|lecci[oó]n)\s+([0-9]+|[ivxlcdm]+|[a-z]+)\b.*"
    r"|[0-9]{1,2}\.?\s+[A-ZÁÉÍÓÚÑ][^.!?]{2,80}"
    r")\s*$",
    re.IGNORECASE,
)
# Front/back matter we don't want as chapters.
SKIP_RE = re.compile(
    r"(contents|índice|indice|copyright|acknowledg|agradecimiento|index|"
    r"bibliograf|notes$|notas$|about the author|sobre el autor|dedicat|glossary|glosario|further reading|lecturas)",
    re.IGNORECASE,
)
MIN_WORDS = 300  # shorter sections get merged into the previous one


def to_text(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".epub":
        cmd = ["pandoc", str(path), "--wrap=none", "-t",
               "markdown-header_attributes-bracketed_spans-native_spans-native_divs-fenced_divs-link_attributes"]
    elif ext == ".pdf":
        cmd = ["pdftotext", "-enc", "UTF-8", str(path), "-"]
    elif ext in (".txt", ".md", ".markdown"):
        return path.read_text(encoding="utf-8", errors="replace")
    else:
        sys.exit(f"Unsupported format: {ext}")
    return clean(subprocess.run(cmd, capture_output=True, text=True, check=True).stdout)


def clean(text: str) -> str:
    """Strip leftover pandoc/calibre attributes like []{#id} or {.class}."""
    text = re.sub(r"\[\]\{[^}]*\}", "", text)
    text = re.sub(r"\[([^\]]*)\]\{[^}]*\}", r"\1", text)
    text = re.sub(r"\s*\{[#.][^}]*\}", "", text)
    text = re.sub(r"</?(span|div|a)\b[^>]*>", "", text)
    return "\n".join(l for l in text.splitlines() if not l.startswith(":::"))


def split(text: str):
    chapters, title, buf = [], "Front matter", []
    for line in text.splitlines():
        if CHAPTER_RE.match(line) and len(line) < 120:
            chapters.append((title, "\n".join(buf)))
            title, buf = line.strip("# ").strip(), []
        else:
            buf.append(line)
    chapters.append((title, "\n".join(buf)))

    # "Chapter 1" followed straight by "Non-Neediness": fold labels forward.
    folded, carry = [], ""
    for title, body in chapters:
        title = f"{carry}: {title}" if carry else title
        carry = ""
        if len(body.split()) < 30 and re.match(r"^(chapter|cap[ií]tulo|part|parte|conclusion|epilogue|ep[ií]logo)\b", title, re.I):
            carry = title.rstrip(":")
            continue
        folded.append((title, body))

    merged = []
    for title, body in folded:
        words = len(body.split())
        if merged and words < MIN_WORDS:
            prev_title, prev_body = merged[-1]
            merged[-1] = (prev_title, f"{prev_body}\n\n{title}\n{body}")
        else:
            merged.append((title, body))
    return [(t, b) for t, b in merged if not SKIP_RE.search(t) and b.strip()]


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    chapters = split(to_text(src))
    index = []
    for i, (title, body) in enumerate(chapters, 1):
        name = f"{i:02d}.txt"
        (out / name).write_text(f"{title}\n\n{body.strip()}\n", encoding="utf-8")
        index.append({"n": i, "file": name, "title": title, "words": len(body.split())})
    (out / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    for c in index:
        print(f"{c['n']:>3}  {c['words']:>6} words  {c['title'][:70]}")
    if len(index) <= 1:
        print("WARNING: no chapter breaks detected; split manually by reading the text.")


if __name__ == "__main__":
    main()
