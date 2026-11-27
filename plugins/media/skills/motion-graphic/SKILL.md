---
name: motion-graphic
description: >
  Build a short motion graphic or animated explainer as an MP4 with
  HyperFrames (HTML and GSAP rendered to video), from a storyboard agreed in
  chat to a checked render. Use when the user says "make a motion graphic",
  "animate how X works", "an explainer video of my workflow", "turn this into
  a short video" or "/motion-graphic". Not for recording a real terminal (use
  demo-gif) or for downloading or summarizing an existing video (use video).
allowed-tools: Bash(ffmpeg:*), Bash(ffprobe:*)
---

# Motion graphic

Write the film as HTML scenes driven by one GSAP timeline.
[HyperFrames](https://github.com/heygen-com/hyperframes) seeks that paused
timeline frame by frame in headless Chrome and encodes an MP4, so every render
is identical. It is Apache 2.0, renders locally and needs Node 22+ and ffmpeg.

The CLI is pinned to `hyperframes@0.9.102`, with telemetry and the update check
off. Shell state does not persist between calls, so start every shell call that
runs it with:

```bash
hf() { HYPERFRAMES_NO_TELEMETRY=1 HYPERFRAMES_NO_UPDATE_CHECK=1 npx --yes hyperframes@0.9.102 "$@"; }
```

To upgrade, change the version here and in the docs URL in step 3 together.

## 1. Agree on the film

Before writing any file, settle the goal in one sentence, the audience, where
it plays, the language, the length (15 to 30 s), the brand and the sound.
Defaults: 1920 x 1080, 30 fps, silent, because Teams and Slack autoplay muted.

Propose 4 to 6 beats in chat, one line each, and build after the user agrees.
Skip that stop only when the user asked for no questions. When the organisation
has a brand skill, load it for colors, fonts and logo.

## 2. Real output, made-up input

When the film shows a tool at work, run the real tool on made-up input and put
its actual output on screen. Read hotkeys from the tool's settings. Run the
real script on the sample text. Never show real messages, names, customers or
paths.

Show every manual step the real flow needs, such as a copy before a paste. A
film that skips one shows a flow the viewer cannot reproduce.

## 3. Set up the project

Projects live in `~/Movies/motion/<slug>/` unless the user names a folder, so
a later session can edit and re-render them.

```bash
hf() { HYPERFRAMES_NO_TELEMETRY=1 HYPERFRAMES_NO_UPDATE_CHECK=1 npx --yes hyperframes@0.9.102 "$@"; }
mkdir -p ~/Movies/motion && cd ~/Movies/motion
hf init <slug> --non-interactive --skip-skills --example blank --resolution landscape
```

**Always pass `--skip-skills`.** Without it, `init` installs six HyperFrames
skills into `~/.claude/skills` and `~/.agents/skills`, creates skill folders
for Cursor, Gemini, OpenCode and Factory, and writes
`~/.agents/.skill-lock.json`.

Fetch the upstream guidance at the pinned tag into the project instead:

```bash
cd ~/Movies/motion/<slug>
base=https://raw.githubusercontent.com/heygen-com/hyperframes/v0.9.102/skills/hyperframes
mkdir -p .hf-docs/types
for f in SKILL.md references/format.md references/motion.md references/spec.md \
  references/review.md references/types/explainer.md; do
  curl -fsSL "$base/$f" -o ".hf-docs/${f#references/}"
done
```

Read all six before writing a scene. `SKILL.md` holds the render contract.
Other film types have their own file under `references/types/`, and sound has
`references/sound.md`. Fetch those the same way when needed. Skip two upstream
instructions: the usage beacon (`events`) and the `plugin-cli.mjs` launcher.
This skill runs the pinned CLI through `hf`. Run `hf` only in projects this
skill created.

## 4. Spec, then scenes

Write `SPEC.md` at the project root as `spec.md` describes: goal, output,
time, look in hex values and pixel sizes, objects, eases, one line per shot
with its time range, banned defaults and the instants to check.

A structure that works:

- `index.html` holds only the root: length, background, one host per scene.
- One stage scene for the whole demo, so the window or product never cuts
  away, then a short outro scene.
- A font HyperFrames does not bundle needs `@font-face` with a file in
  `assets/fonts/`. Decode a base64 webfont to `.woff2` files first.

Traps the checker catches, and patterns that held up:

- **Never transform a `.clip`.** Give each timed element a `.clip` wrapper and
  animate its child.
- **No template literals in selectors.** `` `#${id} .line` `` fails `check`
  with `template_literal_selector`, because the bundler's CSS parser crashes on
  them. Concatenate strings.
- **`fromTo` for the first tween on a property,** `to` after it.
- **Deterministic motion only.** Waveforms and noise come from a seeded PRNG.
  A blinking caret is a finite run of `tl.set` calls.
- **A word replaced by one of another width:** size an inline-block box from
  the final word, hidden, and place both words absolutely inside it. Keep
  trailing punctuation inside the box, or a gap shows.
- **Typing:** reveal one span per letter with `tl.set`. Hidden letters keep
  their width, so leave the caret out while typing.
- **An overlay that covers text on purpose**, such as a launcher over a chat
  bubble: `data-layout-allow-overlap` on the covered text block clears
  `content_overlap`. `data-layout-allow-occlusion` on the overlay does not.
- Text is at least 28 px at 1080p. Placeholder grey needs 3:1 contrast.

## 5. Check, look, fix

```bash
hf check --json > /dev/null 2> .hf-check.log
rep=$(ls -t .hyperframes/artifacts/checks/*.json | head -1)
jq -r '.ok' "$rep"
jq -r '.. | objects | select(has("code") and has("severity"))
  | select(.severity != "info")
  | "\(.severity) \(.code) t=\(.time // "-") \(.selector // "")"' "$rep" | sort -u
```

Progress goes to `.hf-check.log`. Read it when no new report appears. Fix
every error. Weigh each warning. `film_silent` stays for a muted film.
`line_unread` can stay for text that remains readable in its next place, such
as a draft that becomes the sent message.

Then snapshot the instants from the spec and read the contact sheets the
output lists:

```bash
hf snapshot --at 1.5,5,8,12,17,23
```

Describe each frame as a stranger would. Fix what reads wrong, then snapshot
only the changed range, for example `hf snapshot --range 9,11 --frames 6`.

## 6. Render and verify the file

```bash
hf render -o <slug>.mp4
ffprobe -v error -show_entries format=duration:stream=width,height,r_frame_rate \
  -of compact <slug>.mp4
ffmpeg -v error -y -i <slug>.mp4 \
  -vf "select='not(mod(n\,90))',scale=640:-1,tile=4x3" \
  -frames:v 1 -fps_mode vfr sheet.jpg
```

Read the sheet made from the MP4, not only the snapshots. Hand over the
absolute path, and send the file when the host can.

Write a short `REVIEW.md` next to the spec: the creative calls, what was
measured, the warnings kept and why, and the weakest shot.

## Later edits

Open the project folder and read `SPEC.md` and `REVIEW.md` first. Change the
scene, run step 5 on the changed range, then render again.

## Not this skill

- Recording a real terminal or TUI: `demo-gif`.
- Remotion also renders code to video and ships agent skills. Its license
  requires a paid company license for organisations of four or more people.
  HyperFrames has no such limit.
