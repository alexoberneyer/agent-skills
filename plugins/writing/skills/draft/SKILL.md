---
name: draft
description: >
  Write a message, reply or short write-up that the user sends under their own
  name, in their voice, from whatever the conversation holds: research, a support
  investigation, notes or bullet points. Use when the user says "write a message
  to <name> about this", "draft a reply", "reply to <name>", "turn this into a
  Teams message", "email <name> about this", "write this up in my voice", or
  "/draft". Not for text the user wrote or dictated (polish-text) or for
  proofreading a post (proofread-post).
---

# Draft

Turn what the conversation already holds into a message the user sends as
themselves.

## Input

The source is whatever is in context: an agent's research, a support
investigation, notes, bullet points, a pasted thread. When another skill already
drafted a reply, treat that reply and the evidence behind it as the source.

Work out from the conversation:

- **Recipient:** who, and how they relate to the user (colleague, friend, family,
  customer).
- **Channel:** chat (Teams, Slack, SMS), email, or a doc.
- **Language:** the language of the message being answered, otherwise the
  language of the conversation.

Ask one question covering only what is still missing.

## Steps

1. **Read `voice.md`** next to this file.
2. **Pick the voice.**
   - Sent as the user personally: follow `voice.md`.
   - Sent in a company's name to its customers or partners: follow that company's
     tone guide if one is loaded in this session, and keep only the bans from
     `voice.md`. If none is loaded, say so and use `voice.md`.
3. **List the claims** the message will make, each with where it comes from in
   the conversation. Keep the list to yourself.
4. **Write the message.** For chat, use no markdown emphasis (`**bold**`,
   `_italic_`). Teams and Slack show the markers literally. Carry emphasis through
   short lines instead.
5. **Check it** against the accuracy rules below. Then search it for em-dashes and
   en-dashes.
6. **Output** the message on its own, ready to paste. Under it, add one line per
   claim you dropped or softened, so the user can check. Skip that part when
   nothing was dropped.
7. **Copy to clipboard**: `pbcopy` on macOS, `wl-copy` or `xclip -selection
   clipboard` on Linux, `clip` on Windows. Confirm only after the command
   succeeds. If it fails, say the message needs manual copying.

## Accuracy

Research is long and hedged. A short message in a confident voice strips the
hedges. That is the main way this skill goes wrong.

- **Every claim traces to the conversation.** Add no facts, numbers, dates,
  promises or next steps the source does not hold.
- **Uncertainty survives.** If the source says "likely" or "not verified", the
  message says so, once and plainly: "Probably the customer discount. Not
  verified yet."
- **A guess never becomes a cause.** Open questions stay open.
- **Cut detail, never the strength of the evidence.**
- **Only what the recipient should see.** Conversations hold private context,
  internal IDs and other people's names. Leave out what this recipient has no
  reason to read.
