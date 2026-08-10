# claude-skills

Personal [Claude Code](https://claude.com/claude-code) skills and commands,
packaged as a plugin marketplace.

## Install

```
/plugin marketplace add alexoberneyer/claude-skills
/plugin install writing@alexoberneyer
```

## Plugins

### `writing`

| Command | What it does |
| --- | --- |
| `/writing:polish-text <text>` | Polishes raw text (voice memo transcript, rough draft) into a clean structured message in the same language, then copies it to the clipboard. |
| `/writing:proofread-post <file>` | Proofreads a post before publishing and reports findings as a numbered diagnosis. Changes nothing until you ask. |

`proofread-post` reports in a fixed order — mechanical issues first, substantive
last — so you can reply "apply #1–#3" and decline the rest. It reads the
project's `CLAUDE.md` for any front matter or publishing format it should check
against, so it stays useful across different site generators.

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
```
