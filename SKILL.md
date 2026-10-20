---
name: headway-this
description: Turn a whole book file (EPUB, PDF, TXT) into Headway/Blinkist-style chapter-by-chapter summaries, rendered as a minimal-modern visual HTML book and written in the author's own voice, each ending with one-line key takeaways and practical actions, plus a book overview. Use this whenever the user wants to summarize a book, get chapter summaries, "resumir un libro", "resumen por capítulos", make Blinkist/Headway-style notes, extract the key ideas or lessons from a book they have as a file, or study a non-fiction book faster, or says "headway this", even if they only say "resúmeme este libro" or drop an .epub/.pdf and ask for the main ideas.
---

# Headway This

You get a whole book and write one source file per chapter and render the whole book into a single, minimal-modern HTML page built for visual learners. Each one keeps the chapter's core argument, sounds like the author wrote it, and ends with one-line key takeaways and concrete practical actions. A short overview file ties the book together.

The bar is: someone who reads only these files understands what each chapter argued, remembers the stories that made it stick, and knows what to do differently. A fan of the author shouldn't be able to tell, from the tone, that a model wrote it.

## 1. Set up

Before anything else, confirm two things with the user (skip whichever they already said):

- **Language(s)** of the summaries. Ask every time; the user chooses per book, and can pick one language or two (for example English + Spanish, shown with an EN/ES switch). If a language differs from the book's, carry the voice over (rhythm, attitude, terms of art) instead of translating sentence by sentence. For Spanish, read `references/spanish-plain.md`: plain, simple Spanish (neutral Latin American by default), with Spanglish where translating would kill the meaning or the joke. Ask once whether they want a regional flavor (for example, Dominican) or pure Spanish without Spanglish.
- **Output folder.** Default: `./book-summaries/<book-slug>/` in the current directory.

You need the book file. If the user only gives a title, ask for the file. Working from memory makes chapters and stories up, which defeats the purpose.

## 2. Split the book into chapters

```bash
python3 <skill-dir>/scripts/extract_chapters.py "<book-file>" "<output-folder>/_source"
```

It prints each detected chapter with its word count and writes `_source/NN.txt` plus `_source/index.json`. Check the list against the book's table of contents:
- A front-matter chunk, a part divider, or a split chapter? Merge or rename by editing the files.
- Only one chapter detected? Read the text and split it yourself on the real headings.
- Skip front/back matter (copyright, acknowledgments, notes, index). Keep a substantive introduction or epilogue: authors often put the thesis there.

## 3. Build a voice profile first

Read the introduction plus two or three passages from different chapters, then write `<output-folder>/_voice.md` (around 200 words) covering:

- Point of view (I / we / you / impersonal) and how they address the reader
- Sentence and paragraph rhythm (give an actual short example sentence)
- Tone and attitude (wry, urgent, warm, academic, contrarian…)
- Signature moves: recurring metaphors, how they open chapters, use of stories vs. data, humor
- Terms of art the book coins, kept verbatim
- The book's one-sentence thesis

Every chapter summary is written against this profile, so getting it right here is what keeps the voice consistent across 15 chapters. Then read `references/anti-ai-voice.md`; it lists the patterns that make summaries feel generated and what to do instead.

## 4. Summarize each chapter

For each chapter, read the **whole** chapter text before writing. Skimming loses the turn in the argument that makes a chapter worth reading. Then work out:

1. The chapter's core idea in one sentence (for you, not for the output)
2. The steps of the argument, in the author's order
3. The two or three stories, studies, or examples that carry it; keep names and numbers
4. Any coined term or framework introduced here

Write it to `<output-folder>/NN-<chapter-slug>.md`. These Markdown files are the source; step 6 renders them into a single HTML book. Built for visual learners: besides prose the format has visual blocks (`::: name` … `:::`) that the build script turns into cards, diagrams, and checklists. Template:

```markdown
# <Chapter number>. <Chapter title>

::: idea
<The chapter's core idea in one sentence, in the author's voice.>
:::

<Summary: 800–1200 words of prose in the author's voice, following the
author's order of argument. No narrator ("the author says…").
Weave in 2–4 visual blocks where they genuinely clarify (see below).
Use ==highlight== on the one or two sentences a reader would underline.>

::: takeaways
- <One line. A core concept, stated so it stands alone.>
- <…5–8 total, each under ~20 words, most important first>
:::

::: actions
- <Concrete action with a verb, specific enough to do this week.>
- <…3–5 total. Use the author's own exercises when the book has them.>
:::
```

**Visual blocks.** Use them where the content already has that shape; don't force them:

| Block | Use when the chapter has… | Body |
|---|---|---|
| `::: concept <Term>` | a coined term or framework (consecutive cards form a grid) | one-sentence definition |
| `::: flow` | a process, sequence, or cause-and-effect chain | `Step -> Step -> Step` (3–5 steps) |
| `::: compare` | a contrast (old vs. new, wrong vs. right) | `Left | Right` rows; first row = headers |
| `::: stat <Number>` | a striking figure from a study or example | one-line caption saying what it measures |
| `::: quote` | one line whose exact wording is the point | the short quote |

You can also use `##`/`###` subheadings when a chapter covers clearly separate parts. Scanners navigate by them, but don't add one every two paragraphs. Visual blocks support the prose; the chapter should still read as a narrative.

Guidance for each part:

- **Summary.** Write it the way the author would compress their own chapter. Use their structure, metaphors, and attitude, including opinions you'd soften. You can quote short lines (one sentence, at most two or three per chapter) when the exact wording is the point. Otherwise paraphrase in their voice: long verbatim passages are both a copyright problem and lazy summarizing. Short chapters (under ~1500 words) can get shorter summaries; don't pad.
- **Key takeaways.** These are the ideas worth remembering a month later. Write them as claims ("Motivation follows action, not the other way around"), not topics ("Motivation"). Each should make sense out of context, because they're also collected in the overview.
- **Practical actions.** Concrete and doable: "Tonight, write tomorrow's three tasks on paper before bed", not "Plan better". If the chapter is purely conceptual (history, theory), turn the idea into a way of noticing or deciding ("Next time you…"). In the HTML they become a checklist the reader can tick off.

### Long books: parallelize

With more than ~6 chapters and a subagent tool available, send chapters out in parallel batches. Give each subagent: the chapter file path, the full `_voice.md` contents, the path to `references/anti-ai-voice.md`, the template and visual-block table above, the target language, and the output path. Afterwards, read a few results yourself for voice drift and fix outliers.

## 5. Write the overview and book metadata

`<output-folder>/_book.json`:

```json
{"title": "<Book title>", "author": "<Author>", "lang": "<es|en|…>"}
```

For two languages, use `"langs": ["<primary>", "<second>"]` and optionally `"titles": {"<second>": "<translated title>"}`.

`<output-folder>/00-overview.md`:

```markdown
::: idea
<What the whole book argues, in one or two sentences, in the author's voice.>
:::

<One short paragraph on why it matters.> **Who it's for:** <one line>

## The big ideas

::: concept <Big idea 1>
<Two sentences, plus where it lives: [Ch. 3](03-slug.md)>
:::

<…5–7 concept blocks: the ideas that run across chapters.>
```

Don't write the chapter list or the full takeaway list; the build script generates both, as cards and an index, from the chapter files.

## 5b. Second language (only if the user asked for two)

Write the primary language first. Then, for every file, write a sibling with the language code before `.md`: `03-non-neediness.es.md` and `00-overview.es.md`. Use the same structure and the same visual blocks in the same order, so the checklists line up between languages (ticked actions are shared). Work from the primary summary plus the source chapter, so nuance isn't lost twice. Keep the `# ` title's chapter number. Parallelize in batches as in step 4.

## 6. Build the HTML book

```bash
python3 <skill-dir>/scripts/build_book.py "<output-folder>"
```

It writes `<output-folder>/book.html`, a single self-contained file: chapter sidebar, reading progress bar, light/dark mode, reading-font and text-size picker, EN/ES switch for bilingual books, overview with chapter cards, and checklists that remember what was ticked. Open it (`open` on macOS) and look at one chapter to check the visual blocks rendered. A stray `:::` or a block showing as plain text means a block wasn't closed.

## 7. Quality pass

Before telling the user it's done, check each file:
- Read the opening and closing paragraph of every summary against `_voice.md`. Rewrite any sentence that could appear in a summary of any book.
- Search for narrator phrases ("the author", "el autor", "in this chapter", "en este capítulo") and remove them.
- Check every summary is roughly 800–1200 words (short chapters excepted) with 5–8 takeaways, 3–5 actions, and 2–4 visual blocks: `wc -w <output-folder>/[0-9]*.md`.
- Check that no fact, story, or number appears that isn't in the source chapter.

Then report the path to `book.html`, the chapter count, and anything you had to guess (for example, chapters the splitter merged).
