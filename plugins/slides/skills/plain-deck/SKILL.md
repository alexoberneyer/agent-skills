---
name: plain-deck
description: >
  Build a plain, unbranded HTML slide deck in two stops: write a slide outline
  and align on it with the user, then build 16:9 slides with one visual each,
  check them once and publish. Use when the user asks for a deck, slides, a
  presentation or a talk, or says "make a presentation", "slides for this",
  "turn this into a deck", "a simpler version of the deck", or
  "/slides:plain-deck". If the project or organisation has its own deck or
  brand skill, use that one instead. Not for PowerPoint files (use pptx) or
  long scrolling documents.
---

# Plain deck

A slide deck as one HTML file: 16:9 slides that scale to any screen, arrow keys
or click to advance, one slide per landscape page on print. A dark, editorial
look: light Newsreader headlines with one italic phrase in amber, DM Sans body
text, JetBrains Mono labels, hairlines instead of boxes, no logo. Fonts come
from Google Fonts. Nothing is embedded, so the file stays small and shareable.

Two stops. **Never build before the outline is agreed.** A model-written deck
fails on language long before it fails on layout.

Paths below are relative to this skill's directory.

## Stop 1: outline

Write `<name>-outline.md` next to where the deck will live:

```markdown
# <Deck name> · Slide Outline

**Purpose:** what the audience should understand or decide.
**Audience:** who, and what they already know.
**Source:** what the content comes from. Nothing beyond it.
**Format:** HTML deck, N slides.
**Language:** the language the deck is in.

## 1. <Slide title>
**Text:** the words on the slide.
**Visual:** what the picture shows, and what it proves.

## Left out on purpose
## Open questions
```

At most four open questions, each with a proposal, so the user can answer with
"go". Then stop. Show a table of slide · visual plus the questions, and build
nothing until the user answers. Record the answers in the outline.

## Stop 2: build

1. Write the slide body to a scratch file: the `<section class="slide">`
   elements, optionally one `<style>` block first for deck-specific tokens.
   Start from `assets/example-body.html`.
2. Build:
   `python3 scripts/build.py body.html <deck>.html --title "<Deck name>"`.
   It exits 1 on dashes or unfilled placeholders.
3. Look once:
   `python3 scripts/shot.py <deck>.html <scratch dir>`, then read every PNG.
   Fix what they show in one pass and rebuild. Do not loop.
4. Publish with the Artifact tool if the session has one: a one-word `icon`
   such as `slides` on the first publish, and the artifact `url` on every
   republish. Say the link is private until the user shares it. Commit the deck
   and the outline.

A deck built here keeps its body between `deck:body` markers. To pick up a
later fix to the shell, rebuild it in place: `build.py <deck>.html <deck>.html`.
Decks built before version 0.2 used a light look and tokens that no longer
exist (`--accent-10`, `--warm` and others). Leave them as built.

## Palette

The shell defines every colour as a token on `:root`. To give a deck its own
look, redefine the tokens in the body's `<style>` block, which lands after the
shell's CSS:

```html
<style>:root{ --accent:#8fd1a8; --accent-hi:#c4ead2; --accent-lo:#3f6b51; --accent-soft:#16211b; --glow:rgba(143,209,168,.12); }</style>
```

| Token | Carries |
| --- | --- |
| `--paper`, `--surface` | the near-black ground, and a raised fill for SVG panels and bar tracks |
| `--ink`, `--muted`, `--faint` | headline and body text, secondary text, quiet labels |
| `--line`, `--line-strong` | hairlines: dividers, table rules, outlines |
| `--accent`, `--accent-hi`, `--accent-lo`, `--accent-soft` | amber: the italic phrase, numbers, rules, the lead bar, highlighted rows |
| `--alt`, `--alt-hi`, `--alt-lo`, `--alt-soft` | steel blue: a second dimension in charts and visuals |
| `--flag` | one thing only, kept under about 5% of the surface |
| `--glow`, `--glow-alt` | the soft radial glows behind slides |
| `--display`, `--body`, `--mono` | type: Newsreader, DM Sans and JetBrains Mono respectively |

Amber is scarce on purpose. If everything glows, nothing does.

## Typography

Use the default pairing consistently:

| Role | Family | Weight |
| --- | --- | --- |
| Title slide headline | Newsreader | 300 |
| Slide titles, column heads, big numbers | Newsreader | 300 or 400 |
| The emphasised phrase in a title | Newsreader italic, in `<em>` | inherits |
| Body text, lists and descriptions | DM Sans | 300 or 400 |
| Body emphasis and item labels | DM Sans | 500 |
| Eyebrows, labels, table heads, code | JetBrains Mono | 400 or 500, uppercase and tracked for labels |

At most one `<em>` per slide title, on the words that carry the point. Keep the
shell's responsive `cqw` sizes and tight heading tracking. Load every used
weight in the Google Fonts stylesheet. Keep the system fallbacks; the Google
Fonts faces need a connection on first load and are not embedded in the HTML.

A different typeface also needs its Google Fonts link swapped in
`assets/deck-shell.html`, or added in the body's `<style>` block with `@import`.

## Language

From feedback on a model-written deck an audience found hard to follow:

- One idea per slide. About 30 words of text. The visual carries the rest.
- Use the audience's words. If they say "semi-active", the slide says
  "semi-active", not "L1".
- No model register: nothing like "load-bearing", "how much rope",
  "consequential by function". If a sentence needs reading twice, rewrite it.
- Name systems the way the audience does. When unsure, make it an open
  question. Names are the most common one.
- A number you invented carries a `Proposal` badge, or stays off the slide.
- No em-dashes or en-dashes. Split the sentence instead.

## Visuals

- Default layout: `.split`, text in `.copy` (40%), one inline SVG in `.viz`
  (60%). Title and closing slides take `.dark`, the stage variant.
- Colour carries meaning and keeps it across slides. One family per dimension,
  for example the accent family for audience and the alt family for level.
  `--flag` marks one thing only.
- Reuse one visual to tell a story: an empty grid early, the same grid filled
  at the end.
- SVG on the dark ground: structure in `var(--line)` and `var(--surface)`, the
  point in `var(--accent)`, square corners, 1px strokes. An explicit fill on
  every shape. Text inherits DM Sans. Add `class="display"` for Newsreader and
  `class="mono"` for uppercase mono labels. Check label widths and neighbours
  with the actual font and weight loaded; do not reuse measurements from
  another typeface. Label collisions are the most common defect the one look
  finds.
- Leave room in the `viewBox` for the outermost labels.

## Components in `assets/deck-shell.html`

| Class | Use |
| --- | --- |
| `.slide`, `.slide.dark` | a slide; dark is the stage variant with the warm glow and corner marks |
| `.title-slide`, `.meta`, `.hero-facts` | title slide; the eyebrow pins top left, `.meta` (date, version) top right |
| `.title-slide.with-motif` + `svg.title-motif` | a quiet SVG behind the title |
| `.eyebrow` with `<b>01</b>`, `h1`, `h2` with `<em>`, `.rule`, `.lede`, `.kicker` | type; the `<b>` is the amber section number, `.kicker` closes a full-width slide |
| `.split`, `.copy`, `.viz` | text left, visual right |
| `.items` with `.sw`, `.num` or `.big`, then `.t b` and `.t span` | labelled rows: square swatch, mono number like `01`, or big serif numeral |
| `.note` | closing line of a `.copy` column |
| `.cols.c4` of `.stat` (`<b>` number, `<span>` label) | big numbers; `<i>` inside the `<b>` makes one amber |
| `.stack`, `.rows`, `.cols` (`.c2`, `.c4`), `.groups`, `table`, `.chart` | full-width content slides |
| `.badge` | the Proposal marker |

Sizes are in `cqw`, so slides scale with the screen. Keep new CSS in that unit.

## Traps

- `shot.py` needs Chrome or Chromium. It checks the two macOS paths, then
  `PATH`. Set `CHROME` to the binary anywhere else.
- Python below 3.12 rejects a backslash inside an f-string expression.
- Isolated worktree sessions reject chained git commands that carry a heredoc.
  Run `git add`, `git commit` and `git push` as separate commands.
- Republishing after the source path changed (a removed worktree, a moved file)
  needs the artifact `url`, or a second artifact appears.
- Print is built in, one slide per landscape page. Do not add page breaks.
