---
name: demo-gif
description: >
  Record a terminal or TUI demo as a GIF with VHS, using sample data only,
  check every frame for private data and host it for a README. Use when the
  user says "make a GIF of this", "record a demo of the CLI", "add a demo GIF
  to the README", "show how the extension works in a GIF" or "/demo-gif". Not
  for animated explainers or motion graphics.
allowed-tools: Bash(vhs:*), Bash(ffmpeg:*), Bash(ffprobe:*)
---

# Demo GIF

Record the real tool in a scripted terminal, with sample data, and check every
frame before anything is published.

[VHS](https://github.com/charmbracelet/vhs) plays a `.tape` script in a
headless terminal and writes a GIF. Install it with `brew install vhs` once the
user agrees. It pulls in `ttyd`. The frame check needs `ffmpeg`.

## 1. Pick the data

Sample data only. Never record the user's real sessions, inbox, queue or
history, even when they call a screenshot of it harmless. A screenshot shows
one view. The GIF shows every tab, preview pane and detail line it passes, and
preview panes show message text.

1. Use the tool's demo mode when it has one, for example `/comms demo`.
2. Otherwise build a throwaway world in a setup script the tape runs while
   hidden. It creates a temp root with `HOME` inside it, points the tool's
   config and state directories there, puts fake CLIs that print fixture JSON
   first on `PATH`, and starts a private tmux server through `TMUX_TMPDIR`. It
   prints `export` lines, and the tape runs `eval "$(node <script>)"`. A
   detached watchdog stops the tmux server and deletes the root after a few
   minutes.

Worked example: `docs/demo/agents-world.mjs` in
[pi-extensions](https://github.com/alexoberneyer/pi-extensions).

## 2. Isolation traps

- **Unset `TMUX` and `TMUX_PANE`.** VHS inherits the caller's environment. A
  recording started inside tmux points the tool at the real server.
- **Resolve the temp root with `realpath`.** macOS maps `/var` to
  `/private/var`, and paths then stop displaying under `~`.
- **Hide the launch.** Startup banners list skills, context files, home paths
  and login warnings. `Hide`, launch, open the view, then `Show`. End the GIF
  before leaving the view.
- **Neutral fixtures.** `example.invalid` addresses, projects like
  `~/projects/shop-api`, no real names.

## 3. Write the tape

```
Output "/tmp/<name>-demo.gif"

Set FontSize 16
Set Width 1200
Set Height 640
Set Padding 24
Set WindowBar Colorful
Set TypingSpeed 80ms

Hide
Type `eval "$(node docs/demo/<name>-world.mjs)"` Enter
Sleep 6s
Type "<launch command>" Enter
Sleep 6s
Show

Sleep 2.5s
```

- Quote `Output` paths. An unquoted path with a dash fails to parse.
- One story per GIF, 20 to 35 seconds. A GIF cannot pause or scrub, so two
  short GIFs beat one long one.
- Give each view 1.5 to 3 seconds. Leave out plumbing such as starting the tool.
- Keep the tape and setup script in the repo, for example `docs/demo/`, so
  anyone re-renders with `vhs docs/demo/<name>.tape`.
- Run `vhs validate <tape>` before rendering. When rendering yourself, copy the
  tape to the scratchpad with only the `Output` line changed.

## 4. Check every frame

`Screenshot` inside a tape can capture a step late. Review the GIF itself:

```bash
ffprobe -v error -show_entries format=duration -of csv=p=0 demo.gif
ffmpeg -loglevel error -y -i demo.gif \
  -vf "fps=1/1.5,scale=600:-1,tile=4x6" -frames:v 1 sheet.png
```

Read the sheet. Look for names, real paths, hostnames, IDs, message text and
anything from outside the fake world, such as a project you did not create.
Views shorter than 1.5 seconds can fall between samples. Raise `fps`, or accept
them only when every source is fake. Fix, re-render, check again. Delete any
render that showed private data.

## 5. Host it

- Ask before every push, tag or upload. Each one is public.
- If the repo keeps binaries out, for example through a release check, upload
  the GIF as a release asset and link
  `https://github.com/<owner>/<repo>/releases/download/<tag>/<file>.gif`.
  GitHub renders it in the README. Replace it later with
  `gh release upload <tag> <file> --clobber`.
- Otherwise commit it next to the tape and link it relatively.
- README: GIFs above Install, at most two, a one-line caption each. Reuse the
  same link in the matching sub-README.
- Write the re-render and upload steps into the repo, not only into agent
  memory.

## Not this skill

Animated explainers, title cards and motion graphics belong to Remotion and its
agent skills. Install those inside the Remotion project
(`npx skills add remotion-dev/skills`), never globally for every agent.
Remotion animates a mock-up. It does not record the real tool.
