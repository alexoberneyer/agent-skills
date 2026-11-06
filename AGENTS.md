# Public repository rules

This repository is public. Treat committed content and Git history as publishable.

- Never copy private memory, conversations, customer or personnel data, internal configuration, logs or real business identifiers into this repository.
- Use synthetic examples, fixtures, screenshots and demos. Anonymizing names alone does not make a real record safe.
- Keep private configuration, matching rules and generated personal artifacts outside the checkout. Gitignore is not a disclosure boundary.
- Review the complete diff and outgoing commit messages before committing or publishing. Review media, PR descriptions and release assets separately.
- If disclosure status is unclear, stop and ask. Do not bypass a failing disclosure guard or create an exemption without approval.
- Implementing a change does not authorize pushing, tagging or publishing it.

Run `python3 scripts/public_repo_guard.py worktree` before handing off changes.
Before a push, also inspect the staged snapshot with
`python3 scripts/public_repo_guard.py staged`. Install the local pre-push guard
with `python3 scripts/public_repo_guard.py install` on each new clone.

See [public repository safety](docs/public-repo-safety.md) for private rules,
coverage and limitations. These instructions and checks reduce mistakes. They
are not a sandbox or a guarantee that content is safe to publish.
