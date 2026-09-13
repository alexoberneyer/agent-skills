---
name: copy-answer
description: Copy a deliverable from the previous answer to the clipboard. Use for "copy that", "copy your answer", or /writing:copy.
---

Read the [canonical workflow](../../commands/copy.md) and follow it for the user's request.
Resolve this skill folder to its canonical source before resolving that relative
path, since the installed folder may be a symlink. Treat the command frontmatter
as metadata and substitute the user's arguments for `$ARGUMENTS` in the body.
Use the host's available tools for the operations described. If a required tool
is unavailable, report the specific missing capability rather than claiming success.
