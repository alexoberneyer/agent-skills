---
name: voice-memos
description: >
  Transcribe Apple Voice Memos recorded on iPhone or Apple Watch, locally on the
  Mac, without opening Voice Memos. Picks up the memos added since the last run.
  Use when the user says "transcribe my voice memos", "my latest voice memo",
  "new voice memos", "what did I record on my watch", or "/voice-memos".
---

# Voice Memos

Memos recorded on iPhone or Apple Watch sync to the Mac through iCloud.
`scripts/memos.py` reads them from the sync folder and transcribes them locally.
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

A Mac with Apple silicon, `brew install ffmpeg uv`, and Voice Memos turned on
under iCloud on the Mac and the phone.

macOS guards the sync folder. When the script says it is blocked, tell the user
to add the terminal app that runs the agent (Ghostty, Terminal, iTerm) under
System Settings > Privacy & Security > Full Disk Access, restart it, and run the
skill again. Do not look for a way around the block.

## After transcribing

1. Read each **whole** transcript file.
2. For each memo, give the recording time, then the text. Summarize a long memo
   when the user did not ask for the full text.
3. Then do what the user asked. When they want a message out of it, hand the
   text to the matching skill, for example `polish-text`.

### Traps

- Transcripts garble names. Keep a name as transcribed and flag it unless the
  user confirms the spelling. Do not pick between similar names from notes or
  memory.
- Memos are private. Do not paste them into other tools or files unless the user
  asks.
