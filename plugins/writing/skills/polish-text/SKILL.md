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
/writing:polish-text Hey Lukas, ich wollte mal fragen ob...
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

1. **Detect the language** of the input and keep the output in the same language.
2. **Polish the text** while preserving the original intent, tone, and meaning:
   - Fix grammar, spelling, and punctuation
   - Fix sentences the transcription broke
   - Add paragraph breaks for readability
   - Do not use markdown emphasis (`**bold**`, `_italic_`). The output is usually
     pasted into Teams or Slack, which render the markers literally instead of
     formatting them. Carry emphasis through structure instead: short paragraphs,
     one idea per line, key term at the front of the line. If the user asks to
     "keep the markdown" (for Notion, GitHub, a doc), use it as normal.
   - Convert lists or options into numbered/bulleted lists
   - Remove filler words, false starts, and verbal tics (common in voice transcripts).
     Keep phrasing the author uses on purpose, like "whatever" or "That's it."
   - Keep the author's voice. The text is already theirs, so change only what is
     broken.
   - No em-dashes in the output. Do not introduce en-dashes, semicolons, or
     phrasing like "not just X, but Y".
3. **Do NOT** add new information, change the meaning, or remove important content.
4. **Output the polished text** to the user so they can review it.
5. **Copy to clipboard**: `pbcopy` on macOS, `wl-copy` or `xclip -selection clipboard`
   on Linux, `clip` on Windows.
6. Confirm copying only after the clipboard command succeeds. If it fails,
   leave the polished text available and state that it needs manual copying.
