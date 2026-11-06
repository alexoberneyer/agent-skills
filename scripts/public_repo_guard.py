#!/usr/bin/env python3
"""Dependency-free, best-effort disclosure guard for a public Git repository.

Keep this file and its tests identical in both public tooling repositories.
Private matching rules belong outside the checkout, never in this source.
"""

import argparse
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

MAX_BYTES = 2 * 1024 * 1024
OID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
CREDENTIAL = re.compile(
    r"-----BEGIN (?:ENCRYPTED |RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----|"
    r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
    r"sk-(?:proj-|ant-)?[A-Za-z0-9_-]{24,}|AKIA[A-Z0-9]{16}|"
    r"xox[baprs]-[A-Za-z0-9-]{15,})"
)
HOME_PATH = re.compile(r"/(?:Users|home)/([A-Za-z0-9_.-]+)(?:/|\b)")
PRIVATE_NAME = re.compile(
    r"^(?:(?:auth|mcp(?:-auth)?|credentials|config)\.json|.*\.local\.json|"
    r"\.env(?:\..*)?|.*\.(?:pem|key|p12|pfx|sqlite|sqlite3|db))$", re.I
)
HOOK = """#!/bin/sh
# public-repo-guard: repository-local pre-push check
set -eu
root=$(git rev-parse --show-toplevel)
exec python3 "$root/scripts/public_repo_guard.py" pre-push "$@"
"""


class GuardError(Exception):
    """An incomplete check must block the push."""


def git(root, *args):
    result = subprocess.run(
        ["git", "-c", "core.fsmonitor=false", "-C", str(root), *args],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60,
    )
    if result.returncode:
        # Git errors may contain private content. Do not echo them into logs.
        raise GuardError("Git inspection failed. Check repository state and fetch missing objects.")
    return result.stdout


def setting(root, name):
    result = subprocess.run(
        ["git", "-C", str(root), "config", "--get", name],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10,
    )
    if result.returncode == 1:
        return None
    if result.returncode:
        raise GuardError("Cannot read Git configuration.")
    return os.fsdecode(result.stdout).strip()


class Guard:
    def __init__(self, root):
        self.root = root.resolve()
        self.problems = set()
        self.seen = set()
        self.blobs = set()
        self.commits = set()
        self.rules = []
        configured = setting(root, "publicRepoGuard.patternsFile")
        path = (Path(configured).expanduser() if configured else
                Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
                / "public-repo-guard" / "patterns.txt")
        if not path.is_absolute():
            raise GuardError("Private patternsFile must be an absolute path outside the checkout.")
        path = path.resolve()
        if path.is_relative_to(self.root):
            raise GuardError("Private matching rules must stay outside the checkout.")
        if not path.exists():
            if configured:
                raise GuardError("Configured private matching rules are missing. Restore them before pushing.")
            print("No private rules configured. Running generic checks only.", file=sys.stderr)
            return
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            try:
                self.rules.append((number, re.compile(line)))
            except re.error:
                raise GuardError(f"Invalid private rule on line {number}.") from None

    def problem(self, source, reason):
        self.problems.add(f"{source}: {reason}")

    def text(self, source, text):
        if CREDENTIAL.search(text):
            self.problem(source, "possible credential")
        if any(match.group(1) not in ("example", "fixture", "remote")
               for match in HOME_PATH.finditer(text)):
            self.problem(source, "personal absolute home path")
        for number, pattern in self.rules:
            if pattern.search(text):
                self.problem(source, f"private rule {number} matched")

    def content(self, source, data):
        if len(data) > MAX_BYTES:
            self.problem(source, "file exceeds the review size limit")
            return
        try:
            if b"\0" in data:
                raise UnicodeError
            text = data.decode("utf-8")
        except UnicodeError:
            self.problem(source, "binary content requires separate disclosure review")
            return
        if text.startswith("version https://git-lfs.github.com/spec/v1"):
            self.problem(source, "LFS content cannot be inspected by this guard")
        self.text(source, text)

    def filename(self, source, name):
        base = name.rsplit("/", 1)[-1]
        if PRIVATE_NAME.fullmatch(base) and base not in (".env.example", ".env.sample"):
            self.problem(source, "private configuration/data filename")
        self.text(source, name)

    def blob(self, source, mode, oid, name):
        entry = (mode, oid, name)
        if entry in self.seen:
            return
        self.seen.add(entry)
        self.filename(source, name)
        if mode not in ("100644", "100755"):
            self.problem(source, "symlink, submodule or unresolved index entry requires review")
            return
        if oid in self.blobs:
            return
        self.blobs.add(oid)
        if int(git(self.root, "cat-file", "-s", oid)) > MAX_BYTES:
            self.problem(source, "file exceeds the review size limit")
            return
        self.content(source, git(self.root, "cat-file", "blob", oid))

    def worktree(self):
        names = git(self.root, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
        for raw in sorted(set(names.split(b"\0")) - {b""}):
            name = os.fsdecode(raw)
            source = ascii(name)
            path = self.root / name
            # Reject symlinked parents as well as symlinked leaf entries.
            if any(parent.is_symlink() for parent in [path, *path.parents]
                   if parent != self.root and parent.is_relative_to(self.root)):
                self.problem(source, "symlink requires separate disclosure review")
                continue
            if not path.exists():  # A tracked deletion is not published by this snapshot.
                continue
            self.filename(source, name)
            if not path.is_file():
                self.problem(source, "non-regular file requires separate disclosure review")
                continue
            with path.open("rb") as stream:
                self.content(source, stream.read(MAX_BYTES + 1))

    def staged(self):
        for entry in git(self.root, "ls-files", "--stage", "-z").split(b"\0"):
            if not entry:
                continue
            metadata, raw = entry.split(b"\t", 1)
            mode, oid, stage = metadata.decode("ascii").split()
            name = os.fsdecode(raw)
            self.blob(ascii(name), mode if stage == "0" else "unmerged", oid, name)

    def push(self, updates):
        if git(self.root, "rev-parse", "--is-shallow-repository").strip() == b"true":
            raise GuardError("Shallow history cannot be fully inspected. Fetch the complete history first.")
        for line in updates:
            fields = line.split()
            if len(fields) != 4 or not OID.fullmatch(fields[1]) or not OID.fullmatch(fields[3]):
                raise GuardError("Malformed pre-push input. Push inspection was not completed.")
            _, local, destination, remote = fields
            if set(local) == {"0"}:  # Ref deletion uploads no new content.
                continue
            self.text("destination ref", destination)
            current = local
            for _ in range(16):
                kind = git(self.root, "cat-file", "-t", current).strip()
                if kind != b"tag":
                    break
                data = git(self.root, "cat-file", "tag", current)
                self.content(f"tag {current[:12]}", data)
                current = data.split(b"\n", 1)[0].split()[1].decode("ascii")
            else:
                raise GuardError("Tag nesting limit exceeded.")
            if kind != b"commit":
                raise GuardError("Only commit refs and tags pointing to commits can be inspected.")
            args = ["rev-list", "--reverse", current]
            if set(remote) != {"0"}:
                # Use Git's actual remote tip, not a possibly stale tracking branch.
                args.append("^" + remote)
            # A new ref has no trusted remote baseline: inspect its entire history.
            for commit in git(self.root, *args).decode("ascii").splitlines():
                if commit in self.commits:
                    continue
                self.commits.add(commit)
                self.content(f"commit {commit[:12]}", git(self.root, "cat-file", "commit", commit))
                for entry in git(self.root, "ls-tree", "-r", "-z", commit).split(b"\0"):
                    if not entry:
                        continue
                    metadata, raw = entry.split(b"\t", 1)
                    mode, _, oid = metadata.decode("ascii").split()
                    name = os.fsdecode(raw)
                    self.blob(f"{commit[:12]}:{ascii(name)}", mode, oid, name)

    def finish(self):
        if self.problems:
            for problem in sorted(self.problems):
                print(problem, file=sys.stderr)
            print("Disclosure check blocked. Inspect locally. Do not paste matching content into public logs.",
                  file=sys.stderr)
            return 1
        print(f"Disclosure check passed ({len(self.commits)} outgoing commits). Not a confidentiality guarantee.")
        return 0


def install(root):
    if setting(root, "core.hooksPath") is not None:
        raise GuardError("Existing core.hooksPath preserved. Integrate this guard into that hook manually.")
    hook = Path(os.fsdecode(git(root, "rev-parse", "--git-path", "hooks/pre-push")).strip())
    if not hook.is_absolute():
        hook = root / hook
    if hook.is_symlink() or hook.exists():
        if hook.is_symlink() or hook.read_text(encoding="utf-8") != HOOK:
            raise GuardError("Existing pre-push hook preserved. Integrate the guard manually.")
    else:
        hook.parent.mkdir(parents=True, exist_ok=True)
        with hook.open("x", encoding="utf-8") as stream:
            stream.write(HOOK)
    hook.chmod(hook.stat().st_mode | stat.S_IXUSR)
    print("Installed repository-local pre-push guard. Other hooks were not changed.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("install", "worktree", "staged", "pre-push"))
    parser.add_argument("remote", nargs="?")
    parser.add_argument("url", nargs="?")
    args = parser.parse_args()
    try:
        root = Path(os.fsdecode(git(Path.cwd(), "rev-parse", "--show-toplevel")).strip())
        if args.mode == "install":
            install(root)
            return 0
        guard = Guard(root)
        if args.mode == "pre-push":
            guard.push(sys.stdin)
        else:
            getattr(guard, args.mode)()
        return guard.finish()
    except (GuardError, OSError, UnicodeError, ValueError, subprocess.TimeoutExpired):
        # No traceback, regex, Git stderr or matching content should escape.
        error = sys.exc_info()[1]
        message = str(error) if isinstance(error, GuardError) else "Inspection failed. Check files and configuration locally."
        print(f"Disclosure check blocked: {message}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
