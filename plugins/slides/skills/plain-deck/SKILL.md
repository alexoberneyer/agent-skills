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
or click to advance, one slide per landscape page on print. One type family
(Inter) from Google Fonts, a quiet palette, no logo. Nothing is embedded, so the
file stays small and shareable.

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
4. Publish with the Artifact tool if the session has one: an emoji favicon on
   the first publish, and the artifact `url` on every republish. Say the link is
   private until the user shares it. Commit the deck and the outline.

A deck built here keeps its body between `deck:body` markers. To pick up a
later fix to the shell, rebuild it in place: `build.py <deck>.html <deck>.html`.

## Palette

The shell defines every colour as a token on `:root`. To give a deck its own
look, redefine the tokens in the body's `<style>` block, which lands after the
shell's CSS:

```html
<style>:root{ --accent:#3b3f6d; --accent-70:#272a4c; --alt:#7a9e7f; --flag:#b4462f; }</style>
```

| Token | Carries |
| --- | --- |
| `--accent`, `--accent-60/70/80`, `--accent-10`, `--accent-soft` | the primary family: dark slides, table headers, names |
| `--alt`, `--alt-70`, `--alt-20`, `--alt-05`, `--alt-soft` | the second family: eyebrows, bars, accents on dark |
| `--flag` | one thing only, kept under about 5% of the surface |
| `--warm`, `--warm-soft` | the proposal badge and highlighted table rows |
| `--ink`, `--muted`, `--line`, `--paper`, `--surface` | text and structure |
| `--display`, `--body`, `--mono` | type; set `--display` to a second face if the deck wants one |

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
  (60%). Title and closing slides can go dark.
- Colour carries meaning and keeps it across slides. One family per dimension,
  for example the accent family for audience and the alt family for level.
  `--flag` marks one thing only.
- Reuse one visual to tell a story: an empty grid early, the same grid filled
  at the end.
- SVG: an explicit fill on every shape. Text inherits the body face. Add
  `class="display"` for the display face. Inter bold runs about 0.58 × font size
  per character, so check each label against its neighbours before building.
  Label collisions are the most common defect the one look finds.
- Leave room in the `viewBox` for the outermost labels.

## Components in `assets/deck-shell.html`

| Class | Use |
| --- | --- |
| `.slide`, `.slide.dark` | a slide; dark is the accent gradient |
| `.title-slide`, `.hero-facts`, `.accent-bar` | title slide; the bar is an optional colour strip at the bottom |
| `.title-slide.with-motif` + `svg.title-motif` | a quiet SVG behind the title |
| `.eyebrow`, `h1`, `h2`, `.rule`, `.lede`, `.kicker` | type; `.kicker` closes a full-width slide |
| `.split`, `.copy`, `.viz` | text left, visual right |
| `.items` with `.sw`, `.num` or `.big`, then `.t b` and `.t span` | labelled rows: colour swatch, flagged number, or big numeral |
| `.note` | closing line of a `.copy` column |
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
