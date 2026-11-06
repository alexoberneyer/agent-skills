# Public repository safety

## Enable the local guard

Requires Git and Python 3.10 or newer. No additional packages are needed.

```sh
python3 scripts/public_repo_guard.py install
python3 scripts/public_repo_guard.py worktree
python3 scripts/public_repo_guard.py staged
```

The installer creates this checkout's `.git/hooks/pre-push`. It preserves an
existing unrelated hook or `core.hooksPath` and stops rather than overwriting
it. Integrate `python3 scripts/public_repo_guard.py pre-push "$@"` into an
existing hook manually, passing through its original stdin. The guard consumes
stdin, so another hook that needs the ref updates must receive its own copy.
Nothing is installed globally. Repeat installation for each new clone.

`AGENTS.md` carries the public-content policy. `CLAUDE.md` imports that same
file rather than maintaining a separate policy.

## Private matching rules

Keep organization-specific identifiers, internal domains and other sensitive
patterns outside the public checkout. The default location is
`~/.config/public-repo-guard/patterns.txt`, respecting `XDG_CONFIG_HOME`.
Use one Python regular expression per line. Blank lines and lines starting
with `#` are ignored. Matching is case-sensitive unless a rule uses `(?i)`.

Synthetic examples only:

```text
(?i)\bfictional-private-client\b
(?i)\binternal\.example\.invalid\b
```

Restrict the private directory to `0700` and its file to `0600`. To pin a
specific external file for this clone:

```sh
git config --local publicRepoGuard.patternsFile "$HOME/.config/public-repo-guard/patterns.txt"
```

An explicitly configured missing, unreadable or invalid file blocks checks.
A file inside the checkout is rejected. Without private rules, the guard
prints a warning and runs generic checks only. Do not commit your private
rules or copy their contents into issues, test fixtures or public logs.

## What is checked

1. `worktree` checks tracked and non-ignored untracked files. `staged` checks
   the entire index snapshot, even when the working copy differs.
2. The pre-push hook checks the actual ref updates supplied by Git. It checks
   every outgoing commit's complete file tree and commit metadata, including
   messages. A credential added and removed in successive commits still
   blocks. Destination ref names and annotated tag messages are checked too.
3. Generic checks flag some common credential formats, personal absolute home
   paths, private configuration/data filenames and private-pattern matches.
   Binary files, LFS pointers, symlinks, submodules and files over 2 MiB block
   because this guard cannot review their disclosure safety. Home paths using
   the explicit synthetic users `example`, `fixture` or `remote` are allowed.

An existing ref uses the remote object ID supplied by Git as its baseline.
Missing baseline objects block the push. Fetch that remote and retry. A new
ref has no baseline, so its entire reachable history is inspected, including
already published commits. Deleting a ref uploads no new content and is skipped.
Non-commit refs and shallow repositories are blocked. Inspection errors block
rather than silently pass.

Diagnostics identify paths, commit IDs and rule numbers, never matching text
or the private rule itself. Inspect failures locally. Paths and Git's own
output can still contain sensitive information.

Run the synthetic regression suite with:

```sh
python3 -m unittest discover -s tests -p test_public_repo_guard.py
```

The guard and regression suite are deliberately identical standalone copies
in both public tooling repositories. Keep them in sync when changing either.
Neither repository depends on the other's checkout.

## Limits and disclosure review

This is best-effort pattern matching, not a complete secret scanner or a
semantic confidentiality review. It will miss unrecognized credentials,
encoded data and private facts that do not match a rule. It does not inspect
PR descriptions, issues, release uploads or untracked ignored files.
Manually review examples, screenshots and release assets before publishing.

A local hook is bypassable, and editing the guard can weaken it. It is not an
OS security boundary. CI finds problems only after content reaches a remote.
Use an isolated agent environment without private files or connectors when
stronger separation is needed. A fresh conversation may still inherit private
memory.

If a check finds a credential in an unpushed commit, removing it from the
latest tree is insufficient. Stop and repair the affected outgoing history
with explicit approval. If it has already been published, rotate it. Do not
assume deleting a file removes its previous copies.
