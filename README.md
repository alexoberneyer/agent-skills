# claude-skills

Personal [Claude Code](https://claude.com/claude-code) skills and commands,
packaged as a plugin marketplace.

## Install

```
/plugin marketplace add alexoberneyer/claude-skills
/plugin install writing@alexoberneyer
/plugin install boards@alexoberneyer
```

## Plugins

### `writing`

| Command | What it does |
| --- | --- |
| `/writing:polish-text <text>` | Polishes raw text (voice memo transcript, rough draft) into a clean structured message in the same language, then copies it to the clipboard. |
| `/writing:proofread-post <file>` | Proofreads a post before publishing and reports findings as a numbered diagnosis. Changes nothing until you ask. |
| `/writing:copy [what]` | Copies the deliverable out of Claude's previous message to the clipboard — the draft or the snippet, not the commentary wrapped around it. |

`proofread-post` reports in a fixed order — mechanical issues first, substantive
last — so you can reply "apply #1–#3" and decline the rest. It reads the
project's `CLAUDE.md` for any front matter or publishing format it should check
against, so it stays useful across different site generators.

`copy` and `polish-text` shell out to `pbcopy`, so the clipboard step is macOS
only. Everything else works anywhere.

### `boards`

| Command | What it does |
| --- | --- |
| `/boards:notion-ticket <url or id>` | Fetches a Notion page — properties, full body, and comments — and presents it for analysis. |

**Setup.** `notion-ticket` needs `NOTION_API_KEY`, either exported in your shell
or in a `.env` file in the directory you run Claude from:

1. Create an internal integration at <https://www.notion.so/my-integrations> and
   copy its token.
2. In Notion, open the page or its parent database → **⋯ → Connections** → add
   the integration. Without this the API returns 404 even for pages you can
   see in the browser.

The script is a self-contained [uv](https://docs.astral.sh/uv/) script, so its
dependencies install on first run. No virtualenv to manage.

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
plugins/<name>/
  .claude-plugin/plugin.json      # plugin manifest
  commands/                       # slash commands
  skills/<name>/SKILL.md          # skills
  skills/<name>/scripts/          # bundled scripts, referenced via ${CLAUDE_PLUGIN_ROOT}
```

Skills are invocable as `/<plugin>:<skill-name>` on their own, so they need no
command wrapper. **Never give a command the same name as a skill in the same
plugin.** Running the command injects a `<command-name>` block, the follow-up
`Skill` call is deduplicated against it ("already loaded, instructions
unchanged"), and `SKILL.md` never reaches the model — only the wrapper's few
lines do, so every rule that lives in the skill is silently skipped.
