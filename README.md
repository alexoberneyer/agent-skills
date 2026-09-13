# claude-skills

Personal [Claude Code](https://claude.com/claude-code) skills and commands,
packaged as a plugin marketplace. The skills also run in Codex, pi and omp.

## Install

```
/plugin marketplace add alexoberneyer/claude-skills
/plugin install writing@alexoberneyer
/plugin install boards@alexoberneyer
/plugin install context@alexoberneyer
```

## Local Codex, pi and omp

Run `./install.sh` from this checkout. It links the skill folders into
`~/.agents/skills`, preserves conflicting entries, and can be rerun after pulls.
All three agents read that folder.

Invoke a skill as `$<name>` in Codex or `/skill:<name>` in pi and omp:
`polish-text`, `proofread-post`, `notion-ticket`, `copy-answer` and `keep`.
Describing the task naturally works too. `copy-answer` adapts the existing `copy`
command without duplicating its workflow or shadowing the Claude command name.

## Plugins

### `writing`

| Command | What it does |
| --- | --- |
| `/writing:polish-text <text>` | Polishes raw text (voice memo transcript, rough draft) into a clean structured message in the same language, then copies it to the clipboard. |
| `/writing:proofread-post <file>` | Proofreads a post before publishing and reports findings as a numbered diagnosis. Changes nothing until you ask. |
| `/writing:copy [what]` | Copies the deliverable out of the agent's previous message to the clipboard. The draft or the snippet, not the commentary wrapped around it. |

`proofread-post` reports mechanical issues first and substantive ones last, so
you can reply "apply #1 to #3" and decline the rest. It reads the project's
`AGENTS.md`, `CLAUDE.md` or `README.md` for any front matter or publishing format
it should check against, so it stays useful across different site generators.

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
| `/context:keep` | Reviews the conversation and proposes what to keep: a memory entry, a repo context file, or nothing. Flags memories the conversation made stale. Writes only after you approve. |

It also triggers on questions like "does any memory need to be updated?". Direct
orders like "put X in memory" skip the review.

Memory is per agent. Claude Code and Codex each keep their own store, and pi and
omp have none by default. `keep` sends facts every agent needs to repo files
instead.

## Local development

Add your working copy as a marketplace instead of the GitHub source, so edits
take effect without pushing:

```
/plugin marketplace add /path/to/your/clone/claude-skills
```

## Credits

`proofread-post` grew out of the **Proofreader** prompt in Simon Willison's
[Agentic Engineering Patterns](https://simonwillison.net/guides/agentic-engineering-patterns/prompts/#proofreader)
guide. His six checks are the core of it. The numbered report format, the rewrite
rules, and the build-breaking check are additions.

## Layout

```
.claude-plugin/marketplace.json   # marketplace manifest
install.sh                        # links skills into ~/.agents/skills
tests/                            # installer tests
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
