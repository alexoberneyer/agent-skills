---
description: Copy the previous answer to the clipboard
argument-hint: "[what to copy, if the last message had more than one thing]"
allowed-tools: Bash(pbcopy:*)
---

# /copy

Copy content from your previous message to the macOS clipboard.

**What to copy:** $ARGUMENTS

## Behavior

- If arguments are empty → copy the **deliverable** from your previous message: the draft, the message, the query, the snippet. Not your commentary, preamble, or "here's what I did" framing around it.
- If arguments are given → copy that specific thing.
- If the previous message had several candidates and the argument doesn't disambiguate, ask which one. Do not guess and copy the wrong thing.

## Formatting rules

- Strip the outer markdown code fence. Keep fences that are part of the content itself.
- Strip heading syntax (`#`, `##`) unless the destination is a markdown file.
- **Never leave em-dashes (—) in the copied text.** Replace with a comma, colon, parentheses, or a period + new sentence.
- Otherwise copy verbatim. Do not re-edit, re-polish, or "improve" on the way to the clipboard — that is what `/writing:polish-text` is for.

## Mechanics

Pipe with a quoted heredoc so quotes, backticks, and `$` survive intact:

```bash
pbcopy <<'CLIPEOF'
<content>
CLIPEOF
```

Then confirm in one line: what was copied and the character count. No restating the content.
