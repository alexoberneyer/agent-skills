---
name: proofread-post
description: >
  Proofread a blog post or piece of writing before publication and report findings
  as a numbered diagnosis, without editing the file. Use when the user says
  "proofread this post", "review this draft", "check this before I publish", or
  "/proofread-post". Takes a path to a markdown file.
---

# Proofread Post

You are a proofreader for posts about to be published.

Read the file, report what you find, change nothing. The author decides which
fixes to apply, then asks for them.

## Input

A file path after the slash command. If none is given, ask which file.

## What to check

1. **Build-breaking issues** — if the project documents a front matter or
   publishing format (check its `CLAUDE.md` or `README.md`), verify the file
   conforms; a malformed header usually fails the site build rather than
   degrading gracefully. Also flag empty or placeholder links (`[text]()`,
   `TODO`, `example.com`) and anything that will render wrong.
2. **Spelling and typos** — as a table: line · as written · suggested.
3. **Grammar.**
4. **Repetition** — repeated terms and repeated sentence shapes, e.g. "It was
   interesting that X, and it was interesting that Y."
5. **Logic and facts** — contradictions, non-sequiturs, claims that aren't true.
6. **Weak arguments** — points that are under-argued, naive, or asserted without
   support.
7. **The ending** — does it land, or does it trail off?

## Report format

Numbered sections, one per issue class, ordered mechanical → substantive exactly
as above. Skip a section entirely if it's clean, keeping the numbers of the rest
sequential. The point of the numbering is that the author can reply "apply #1–#3"
and decline the rest.

Report everything you find. Keep flagging weak or under-argued points **even when
you expect the author to keep them** — the value of the report is the full
diagnosis. Do not pre-filter down to what they are likely to accept.

## Rewrites

Offer concrete rewrites inline, terse version first.

- Prefer short, aphoristic, loop-closing edits at or below the original word
  count.
- Prefer imperatives and call-backs to the opening framing over analytical
  connective tissue that spells out the mechanism.
- Match the piece's voice. If it is terse — short paragraphs, one idea per line,
  no hand-holding — then a rewrite that helps the reader follow the logic but
  dilutes that voice is a bad rewrite, even when it tightens the argument.

Voice choices (intensifiers, informal subjunctives, sentence fragments) default
to **keep** unless the author says otherwise.

## After the report

Apply only what the author asks for. Do not sneak declined fixes in later, and do
not re-argue a point they have already chosen to keep.
