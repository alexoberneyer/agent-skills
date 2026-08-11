---
name: polish-text
description: >
  Polish and structure a text message while keeping the original language and intent,
  then copy the result to the clipboard. Use when the user says "polish this text",
  "clean up this message", "structure this", "polish my clipboard", or "/polish-text".
  The user provides raw text (e.g. voice memo transcript, draft message), or provides
  nothing and the text is taken from the clipboard, and gets back a polished version
  automatically copied to the clipboard.
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

## Instructions

1. **Detect the language** of the input and keep the output in the same language.
2. **Polish the text** while preserving the original intent, tone, and meaning:
   - Fix grammar, spelling, and punctuation
   - Improve sentence structure and flow
   - Add paragraph breaks for readability
   - Use **bold** for key points, headings, or names where appropriate
   - Convert lists or options into numbered/bulleted lists
   - Remove filler words, false starts, and verbal tics (common in voice transcripts)
   - Keep the author's voice — don't make it sound robotic or overly formal
   - **Never use em-dashes (—) in the output.** Use a comma, colon, parentheses, or a period + new sentence instead. This applies to both the text shown to the user and the text copied to the clipboard.
3. **Do NOT** add new information, change the meaning, or remove important content.
4. **Output the polished text** to the user so they can review it.
5. **Copy to clipboard**: `pbcopy` on macOS, `wl-copy` or `xclip -selection clipboard`
   on Linux, `clip` on Windows.
6. Confirm that the text has been copied to the clipboard.
