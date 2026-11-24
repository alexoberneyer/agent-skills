---
name: polish-text
description: >
  Polish and structure a text message while keeping the original language and intent,
  then copy the result to the clipboard. Use when the user says "polish this text",
  "clean up this message", "structure this", "polish my clipboard", or "/polish-text".
  The user provides raw text (e.g. voice memo transcript, draft message), or provides
  nothing and the text is taken from the clipboard, and gets back a polished version
  copied to the clipboard when local clipboard access is available.
---

# Polish Text

Take the user's raw text input and polish it into a well-structured, clear message.

## Input

The user provides raw text after the slash command, e.g.:

```
/polish:polish-text Hey Lukas, ich wollte mal fragen ob...
```

If no text is provided, read the input from the clipboard: `pbpaste` on macOS,
`wl-paste` or `xclip -selection clipboard -o` on Linux, `powershell Get-Clipboard`
on Windows. Echo the first line back before polishing so the user can confirm you
picked up the right thing. If the clipboard is empty, or its contents are clearly
not prose (a URL, a file path, a credential, a code snippet), ask the user for the
text instead of polishing it.

If clipboard access is unavailable, ask for text only when none was supplied.
Otherwise polish the supplied text and return it for manual copying. Do not claim
to have read or changed the clipboard without a successful tool result.

## Instructions

1. **Polish the text** by the [polish rules](rules.md) in this skill folder.
   `/polish` in Pi, and `/polish` and `/polish-copy` in Claude Code, read the
   same file, so change the rules there, not here.
2. **Output the polished text** to the user so they can review it.
3. **Copy to clipboard**: `pbcopy` on macOS, `wl-copy` or `xclip -selection clipboard`
   on Linux, `clip` on Windows. Keep independent messages separate. For a
   clipboard-history batch with confirmed history support, copy each message
   individually in source order, not as one joined block. If history support is
   unavailable or unknown, leave each message separately copyable instead of
   serially overwriting the clipboard.
4. Confirm each copy only after its clipboard command succeeds. A successful
   write does not prove that clipboard history captured it. If a copy fails,
   leave that polished text available and state that it needs manual copying.
