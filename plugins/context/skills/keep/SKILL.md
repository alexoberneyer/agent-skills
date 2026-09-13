---
name: keep
description: >
  Review the current conversation and decide what should outlive it: a memory
  entry, a repo context file (README, CLAUDE.md, AGENTS.md, a notes file), or
  nothing. Also finds existing memories the conversation made stale. Proposes
  first and writes only after approval. Use when the user asks "should this go in
  memory?", "does any memory need to be updated?", "update memory, if necessary",
  "file or memory?", or "/keep". Not for direct orders like "put X in memory":
  do those without this review.
---

# Keep

Decide what from this conversation should outlive it, and where it goes.

## 1. Collect candidates

List what will matter in a later session. Skip what only this task needs.

- a correction or preference about how to work
- a fact about the user, their people or projects that no file records
- a decision and its reason
- a location: where something lives, which tool, URL or command to use

## 2. Check what exists

Search before proposing. For each candidate:

- **Memory:** read the index and grep the memory directory for its topic.
- **Repo:** `CLAUDE.md`, `AGENTS.md`, READMEs and notes files on the topic.
- **Public sources** the user named, such as a blog post or docs.

Mark each one: new, already covered, or covered but stale.

## 3. Find stale memories

Grep memory for every topic the conversation touched, not only the candidates.
Flag each entry the conversation contradicts or dates. A stale memory is worse
than a missing one, because it loads as truth. Fix these first.

## 4. Pick a home

| Home | Belongs here | Keep out |
| --- | --- | --- |
| Memory | Facts that change how the agent works later: preferences, corrections, name traps, where things live | Details, histories, anything the repo records |
| Repo file | Details the user rereads or keeps updating: logs, tables, plans, reference data | Instructions for the agent |
| `CLAUDE.md` / `AGENTS.md` | Rules every session in that repo must follow | One-off facts, long explanations |
| Nowhere | Only this task needs it, or it is already covered | |

- **Memory loads into every session.** Each line costs context in unrelated work.
  When a topic has detail, put the detail in a file and give memory one line that
  points to it.
- **Sensitive data** (health, finances, other people's private details) goes in a
  file, never in memory unless it changes how the agent works. Say what is
  sensitive and where the file is hosted.
- **A new file needs an index.** Name the README or list that should mention it.
- **Update before adding.** Edit the existing entry instead of writing a near-duplicate.
- **Memory is per agent.** Claude, Codex, pi and omp do not share it. A fact
  every agent needs goes in `AGENTS.md`, `CLAUDE.md` or a repo file.

## 5. Propose

Show one table, then stop.

| # | What | Action | Home | Why |
| --- | --- | --- | --- | --- |
| 1 | ... | add / update / delete | `path` | one line |

Below it, quote the stale line and its replacement for every memory update. For a
new file, show a short skeleton. If nothing needs keeping, say so in one line and
name what you checked.

Write nothing until the user approves. They may approve a subset: "do 1 and 3".

## 6. Apply

- Write memory the way the host defines it, including any index line. If the host
  forbids editing memory files, use its mechanism instead (Codex: an ad-hoc note).
  If the host has no memory (pi, or omp without a backend), say so and propose a
  file instead.
- Create or edit repo files and update the index named in the proposal.
- Do not commit. Report the changed paths and `git status` for each repo touched.
