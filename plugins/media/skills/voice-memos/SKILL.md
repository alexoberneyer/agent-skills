---
name: voice-memos
description: >
  Transcribe Apple Voice Memos recorded on iPhone or Apple Watch, locally on the
  Mac, without opening Voice Memos. Picks up the memos added since the last run.
  Use when the user says "transcribe my voice memos", "my latest voice memo",
  "new voice memos", "what did I record on my watch", or "/voice-memos".
---

# Voice Memos

Memos recorded on iPhone or Apple Watch sync to the Mac through iCloud. The
user's terminal copies them to `~/.local/share/voice-memos`, and
`scripts/memos.py` transcribes them from there, locally.
Resolve it relative to this SKILL.md, following the skill folder symlink to its
source, and call it by absolute path:

```bash
python3 "<resolved-skill-directory>/scripts/memos.py"
```

- Without options it takes the memos added since the last run. The first run
  takes only the newest memo.
- `--last 3` takes the newest three, handled before or not.
- `--since 2026-09-01` takes memos from that day on.
- `--dry-run` lists what it would take, without transcribing.
- `--language ja` is only needed for languages outside Parakeet's 25 European
  ones. It switches to Whisper.

Expect about a minute per hour of audio. The first transcription also downloads
the model (2.4 GB), so give the command a long timeout.

## Requirements

A Mac with Apple silicon, `brew install ffmpeg uv`, Voice Memos turned on under
iCloud on the Mac and the phone, and the mirror set up as the README describes.

The script reads only the mirror. macOS guards the Voice Memos sync folder
itself. Never read it, and do not look for a way around the block.

- The mirror refreshes when the user opens a new terminal tab, or when they run
  the sync by hand (`memosync` on this Mac). When the memo the user expects is
  missing, ask for that first.
- When the script says the mirror does not exist, point the user to the README.

## After transcribing

1. Read each **whole** transcript file.
2. For each memo, give the recording time, then the text. Mention the `title:`
   only when the user set it: "Recording N" and place names are automatic. Summarize a long memo
   when the user did not ask for the full text.
3. Then do what the user asked. When they want a message out of it, hand the
   text to the matching skill, for example `polish-text`.

### Traps

- Transcripts garble names. Keep a name as transcribed and flag it unless the
  user confirms the spelling. Do not pick between similar names from notes or
  memory.
- Memos are private. Do not paste them into other tools or files unless the user
  asks.
- A stale mirror usually means the copy failed, not that the memo is missing.
  The tab hook discards rsync's output, so failure is silent. An error like
  `froot_open: ... Operation not permitted` means the terminal lost Full Disk
  Access. Fix: System Settings, Privacy & Security, Full Disk Access, remove the
  terminal and add it back, then quit and relaunch it. Do not go looking for the
  memo until the sync reports success.
- memosync succeeds but the memo is still missing: iCloud has not delivered it
  to the Mac yet. None of the Voice Memos apps has a sync button. Run
  `zsh -ic memosync` yourself to recheck, since it works from an agent shell.
  If the user can't wait: AirDrop the memo to `~/Downloads`, copy it into a temp
  folder, and run `memos.py --dir <folder>`. Never drop files into the mirror:
  memosync runs `--delete`.
