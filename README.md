# agent-skills

Personal [Claude Code](https://claude.com/claude-code) skills and commands,
packaged as a plugin marketplace. The skills also run in Codex, pi and omp.

## Install

```
/plugin marketplace add alexoberneyer/agent-skills
/plugin install writing@alexoberneyer
/plugin install boards@alexoberneyer
/plugin install context@alexoberneyer
/plugin install media@alexoberneyer
/plugin install slides@alexoberneyer
```

## Local Codex, pi and omp

Run `./install.sh` from this checkout. It links the skill folders into
`~/.agents/skills`, preserves conflicting entries, and can be rerun after pulls.
All three agents read that folder.

Invoke a skill as `$<name>` in Codex or `/skill:<name>` in pi and omp:
`polish-text`, `proofread-post`, `draft`, `notion-ticket`, `copy-answer`, `keep`, `video`, `voice-memos` and `plain-deck`.
Describing the task naturally works too. `copy-answer` adapts the existing `copy`
command without duplicating its workflow or shadowing the Claude command name.

## Plugins

### `writing`

| Command | What it does |
| --- | --- |
| `/writing:polish-text <text>` | Polishes raw text (voice memo transcript, rough draft) into a clean structured message in the same language, then copies it to the clipboard. |
| `/writing:proofread-post <file>` | Proofreads a post before publishing and reports findings as a numbered diagnosis. Changes nothing until you ask. |
| `/writing:draft [recipient]` | Writes a message you send under your own name from whatever the conversation holds: research, an investigation, notes. Keeps the uncertainty the source had, then copies it to the clipboard. |
| `/writing:copy [what]` | Copies the deliverable out of the agent's previous message to the clipboard. The draft or the snippet, not the commentary wrapped around it. |

`proofread-post` reports mechanical issues first and substantive ones last, so
you can reply "apply #1 to #3" and decline the rest. It reads the project's
`AGENTS.md`, `CLAUDE.md` or `README.md` for any front matter or publishing format
it should check against, so it stays useful across different site generators.

`draft` follows `skills/draft/voice.md`, which describes my writing voice. If you
use it, replace that file with yours. `polish-text` and `proofread-post` do not
load it, because they work on text you already wrote.

`copy` and `polish-text` use the available local clipboard tool. Without one,
they return the text for manual copying and never claim clipboard success.

### `boards`

| Command | What it does |
| --- | --- |
| `/boards:notion-ticket <url or id>` | Fetches a Notion page with its properties, full body and comments, and presents it for analysis. |

**Setup.** `notion-ticket` needs `NOTION_API_KEY`, either exported in your shell
or in a `.env` file in the working directory:

1. Create an internal integration at <https://www.notion.so/my-integrations> and
   copy its token.
2. In Notion, open the page or its parent database → **⋯ → Connections** → add
   the integration. Without this the API returns 404 even for pages you can
   see in the browser.

The script is a self-contained [uv](https://docs.astral.sh/uv/) script, so its
dependencies install on first run. No virtualenv to manage.

### `context`

| Command | What it does |
| --- | --- |
| `/context:keep` | Reviews the conversation and proposes what to keep: a memory entry, a repo context file, a skill, or nothing. Flags memories the conversation made stale. Writes only after you approve. |

It also triggers on questions like "does any memory need to be updated?" or
"should this be a skill?". Direct orders like "put X in memory" skip the review.

It proposes a skill only for a procedure that recurs, starts on a phrase you say
and took correction to get right. Anything less stays a memory line or a file.

Memory is per agent. Claude Code and Codex each keep their own store, and pi and
omp have none by default. `keep` sends facts every agent needs to repo files
instead.

### `media`

| Command | What it does |
| --- | --- |
| `/media:video <url>` | Downloads a video as mp4, or reads it and reports a verdict, key points, weak evidence and what watching adds over the summary. Works for YouTube, X, Instagram and every other site yt-dlp supports. |
| `/media:voice-memos` | Transcribes Apple Voice Memos recorded on iPhone or Apple Watch, locally on the Mac, without opening Voice Memos. Picks up the memos added since the last run. |

Downloads go to `~/Downloads` under the name you give. Trimming to a section and
a size limit are optional. Reviews use the video's captions when it has them and
otherwise transcribe it locally.

Local transcription runs [mlx-audio](https://github.com/Blaizzy/mlx-audio)
through `uvx`, pinned to one version. Parakeet v3 handles its 25 European
languages and audio in an unknown language. Whisper turbo handles the rest. Each
model downloads once to the Hugging Face cache: 2.4 GB for Parakeet, 1.5 GB for
Whisper the first time a video needs it.

`voice-memos` transcribes a copy of the folder macOS syncs memos into,
`~/Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings`, and
remembers what it handled in `~/.local/state/voice-memos/`. macOS guards that
folder, so the agent never reads it. Your terminal copies it instead. Give the
terminal Full Disk Access under System Settings → Privacy & Security, restart
it, and add this to `~/.zshrc`:

```zsh
# Ghostty has Full Disk Access. Change the check for another terminal.
# -a keeps mtimes, which the skill sorts memos by.
# Every new tab runs it silently. Run memosync to see what it copies, or why it
# fails. Pass -n for a dry run.
memosync() {
  rsync -av --delete --include='*.m4a' --include='*.qta' --exclude='*' "$@" \
    ~/Library/Group\ Containers/group.com.apple.VoiceMemos.shared/Recordings/ \
    ~/.local/share/voice-memos/
}
if [[ $TERM_PROGRAM == ghostty ]]; then
  memosync >/dev/null 2>&1 &!
fi
```

Every new tab refreshes the copy in `~/.local/share/voice-memos`. A memo
recorded since the last new tab shows up once you open another. The agent needs
no Full Disk Access, wherever it runs.

If a memo never appears, run `memosync` yourself. The tab hook hides rsync's
output, so a terminal that lost Full Disk Access fails silently and looks like a
memo that never synced.

**Setup.** A Mac with Apple silicon, and `brew install yt-dlp ffmpeg uv`. The
scripts use only the Python standard library.

### `slides`

| Command | What it does |
| --- | --- |
| `/slides:plain-deck` | Builds a plain HTML slide deck: agrees a slide outline with you first, then builds 16:9 slides with one visual each, screenshots them once and hands back one file. |

The deck is one HTML file. Slides scale to any screen, arrow keys or click
advance them, and print gives one slide per landscape page. Type comes from
Google Fonts, so nothing is embedded and the file stays small.

It stops after the outline and waits. That stop is the point: a deck written
straight through fails on language long before it fails on layout.

The palette is a set of CSS tokens on `:root`. Redefine them in the deck body's
`<style>` block to theme a deck without touching the skill. If your company has
its own deck or brand skill, use that one instead of this.

**Setup.** Python 3, and Chrome or Chromium for the screenshot pass. Set
`CHROME` if it lives somewhere the script does not look.

## Local development

Add your working copy as a marketplace instead of the GitHub source, so edits
take effect without pushing:

```
/plugin marketplace add /path/to/your/clone/agent-skills
```

Run the tests with `python3 -m unittest discover tests`.

## Credits

`proofread-post` grew out of the **Proofreader** prompt in Simon Willison's
[Agentic Engineering Patterns](https://simonwillison.net/guides/agentic-engineering-patterns/prompts/#proofreader)
guide. His six checks are the core of it. The numbered report format, the rewrite
rules, and the build-breaking check are additions.

## Layout

```
.claude-plugin/marketplace.json   # marketplace manifest
install.sh                        # links skills into ~/.agents/skills
tests/                            # installer and script tests
plugins/<name>/
  .claude-plugin/plugin.json      # plugin manifest
  commands/                       # slash commands
  skills/<name>/SKILL.md          # skills
  skills/<name>/scripts/          # bundled scripts, resolved relative to SKILL.md
```

Skills are invocable as `/<plugin>:<skill-name>` on their own, so they need no
command wrapper. **Never give a command the same name as a skill in the same
plugin.** Running the command injects a `<command-name>` block, the follow-up
`Skill` call is deduplicated against it ("already loaded, instructions
unchanged"), and `SKILL.md` never reaches the model. Only the wrapper's few
lines do, so every rule that lives in the skill is silently skipped.
