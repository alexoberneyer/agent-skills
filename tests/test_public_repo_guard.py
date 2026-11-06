"""Disclosure guard regression tests. Only synthetic data and local Git repos."""

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "public_repo_guard.py"
ZERO = "0" * 40


class PublicRepoGuardTest(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix="public-guard-")
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name) / "repo"
        self.root.mkdir()
        self.home = Path(self.scratch.name) / "home"
        self.home.mkdir()
        self.env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": str(self.home),
            "XDG_CONFIG_HOME": str(self.home / ".config"),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_ALLOW_PROTOCOL": "file",
        }
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "Example Developer")
        self.git("config", "user.email", "developer@example.invalid")
        self.patterns = self.home / "patterns.txt"
        self.patterns.write_text("(?i)fictional-private-client\n", encoding="utf-8")
        self.git("config", "publicRepoGuard.patternsFile", str(self.patterns))
        (self.root / "notes.md").write_text("Synthetic public example.\n")
        self.base = self.commit("Initial synthetic example")

    def git(self, *args, cwd=None):
        return subprocess.run(
            ["git", *args], cwd=cwd or self.root, env=self.env,
            capture_output=True, text=True, check=True, timeout=20,
        ).stdout.strip()

    def commit(self, message):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)
        return self.git("rev-parse", "HEAD")

    def run_guard(self, mode, updates=""):
        return subprocess.run(
            [sys.executable, str(SCRIPT), mode], cwd=self.root, env=self.env,
            input=updates, capture_output=True, text=True, timeout=30,
        )

    def push(self, old=None, new=None):
        return self.run_guard("pre-push", self.update(old, new))

    def update(self, old=None, new=None):
        return f"refs/heads/main {new or self.git('rev-parse', 'HEAD')} refs/heads/main {old or self.base}\n"

    def assert_blocked(self, result, reason):
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(reason, result.stderr)

    def test_clean_snapshots_and_existing_ref_pass(self):
        (self.root / "notes.md").write_text("Another synthetic example.\n")
        self.assertEqual(self.run_guard("worktree").returncode, 0)
        self.git("add", "notes.md")
        self.assertEqual(self.run_guard("staged").returncode, 0)
        self.commit("Update public example")
        result = self.push()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("1 outgoing commits", result.stdout)

    def test_secret_removed_in_later_commit_still_blocks(self):
        secret = "ghp_" + "A" * 36
        (self.root / "oops.txt").write_text(secret)
        self.commit("Add fixture")
        (self.root / "oops.txt").unlink()
        self.commit("Remove fixture")
        result = self.push()
        self.assert_blocked(result, "possible credential")
        self.assertNotIn(secret, result.stdout + result.stderr)
        self.assertEqual(self.run_guard("worktree").returncode, 0)

    def test_commit_message_and_identity_are_checked_without_echoing(self):
        marker = "fictional-private-client"
        (self.root / "notes.md").write_text("Safe.\n")
        self.commit("Discuss " + marker)
        result = self.push()
        self.assert_blocked(result, "private rule 1")
        self.assertNotIn(marker, result.stdout + result.stderr)
        self.git("reset", "--soft", self.base)
        self.git("config", "user.email", marker + "@example.invalid")
        self.commit("Public message")
        self.assert_blocked(self.push(), "private rule 1")

    def test_private_filename_and_configuration_block(self):
        for name in (".env", "config.json", "notes.local.json", "private.db"):
            path = self.root / name
            path.write_text("synthetic")
            self.assert_blocked(self.run_guard("worktree"), "private configuration/data filename")
            path.unlink()
        (self.root / "fictional-private-client.txt").write_text("synthetic")
        self.assert_blocked(self.run_guard("worktree"), "private rule 1")

    def test_example_configuration_is_allowed_but_its_content_is_checked(self):
        path = self.root / ".env.example"
        path.write_text("TOKEN=replace-me\n")
        self.assertEqual(self.run_guard("worktree").returncode, 0)
        path.write_text("sk-" + "a" * 32)
        self.assert_blocked(self.run_guard("worktree"), "possible credential")

    def test_home_paths_are_checked_but_explicit_synthetic_users_are_allowed(self):
        for user in ("example", "fixture", "remote"):
            (self.root / "notes.md").write_text("/" + "home/" + user + "/project")
            self.assertEqual(self.run_guard("worktree").returncode, 0)
        for user in ("actual-user", "fixture-person"):
            (self.root / "notes.md").write_text("/" + "Users/" + user + "/private.txt")
            self.assert_blocked(self.run_guard("worktree"), "personal absolute home path")

    def test_binary_large_lfs_and_symlink_content_block(self):
        path = self.root / "fixture.txt"
        for data, reason in (
            (b"image\0data", "binary content"),
            (b"a" * (2 * 1024 * 1024 + 1), "size limit"),
            (b"version https://git-lfs.github.com/spec/v1\n", "LFS content"),
        ):
            path.write_bytes(data)
            self.assert_blocked(self.run_guard("worktree"), reason)
        path.unlink()
        path.symlink_to(self.patterns)
        self.assert_blocked(self.run_guard("worktree"), "symlink")
        self.commit("Add synthetic link")
        self.assert_blocked(self.push(), "symlink")

    def test_staged_content_not_worktree_content_is_checked(self):
        path = self.root / "notes.md"
        path.write_text("ghp_" + "A" * 36)
        self.git("add", "notes.md")
        path.write_text("Safe replacement.\n")
        self.assertEqual(self.run_guard("worktree").returncode, 0)
        self.assert_blocked(self.run_guard("staged"), "possible credential")

    def test_new_ref_checks_all_history_and_deletions_upload_nothing(self):
        (self.root / "notes.md").write_text("fictional-private-client")
        private = self.commit("Synthetic private fixture")
        (self.root / "notes.md").write_text("Public replacement.\n")
        self.commit("Replace fixture")
        self.assertEqual(self.push(old=private).returncode, 0)
        self.assert_blocked(self.push(old=ZERO), "private rule 1")
        self.assertEqual(self.push(new=ZERO).returncode, 0)

    def test_annotated_tag_messages_are_checked_even_without_new_commits(self):
        self.git("tag", "-a", "demo", "-m", "fictional-private-client")
        self.assert_blocked(self.push(new=self.git("rev-parse", "demo")), "private rule 1")

    def test_non_commit_tag_blocks(self):
        blob = self.git("rev-parse", "HEAD:notes.md")
        self.assert_blocked(self.push(new=blob), "Only commit refs")

    def test_destination_ref_names_are_checked_without_echoing(self):
        fields = self.update().split()
        fields[2] = "refs/heads/fictional-private-client"
        result = self.run_guard("pre-push", " ".join(fields) + "\n")
        self.assert_blocked(result, "destination ref: private rule 1")
        self.assertNotIn("fictional-private-client", result.stderr)

    def test_multi_ref_updates_deduplicate_commits(self):
        (self.root / "notes.md").write_text("Public replacement.\n")
        self.commit("Update")
        result = self.run_guard("pre-push", self.update() + self.update())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("1 outgoing commits", result.stdout)

    def test_missing_remote_objects_and_malformed_input_fail_closed(self):
        self.assert_blocked(self.push(old="a" * 40), "Git inspection failed")
        self.assert_blocked(self.run_guard("pre-push", "invalid input\n"), "Malformed pre-push input")

    def test_shallow_history_fails_closed(self):
        (self.root / ".git/shallow").write_text(self.base + "\n")
        self.assert_blocked(self.push(), "Shallow history cannot be fully inspected")

    def test_missing_invalid_or_repo_local_private_rules_fail_closed(self):
        self.patterns.unlink()
        self.assert_blocked(self.run_guard("worktree"), "rules are missing")
        self.patterns.write_text("[invalid-pattern")
        result = self.run_guard("worktree")
        self.assert_blocked(result, "Invalid private rule on line 1")
        self.assertNotIn("[invalid-pattern", result.stderr)
        self.git("config", "publicRepoGuard.patternsFile", str(self.root / "private-rules.txt"))
        self.assert_blocked(self.run_guard("worktree"), "outside the checkout")

    def test_default_rules_and_generic_only_mode(self):
        self.git("config", "--unset", "publicRepoGuard.patternsFile")
        result = self.run_guard("worktree")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("generic checks only", result.stderr)
        default = self.home / ".config/public-repo-guard/patterns.txt"
        default.parent.mkdir(parents=True)
        default.write_text("synthetic-hidden-marker\n")
        (self.root / "notes.md").write_text("synthetic-hidden-marker")
        self.assert_blocked(self.run_guard("worktree"), "private rule 1")

    def test_install_is_idempotent_and_preserves_existing_hooks(self):
        self.assertEqual(self.run_guard("install").returncode, 0)
        self.assertEqual(self.run_guard("install").returncode, 0)
        hook = self.root / ".git/hooks/pre-push"
        self.assertTrue(os.access(hook, os.X_OK))
        hook.write_text("#!/bin/sh\nexit 0\n")
        self.assert_blocked(self.run_guard("install"), "Existing pre-push hook preserved")
        self.assertEqual(hook.read_text(), "#!/bin/sh\nexit 0\n")
        self.git("config", "core.hooksPath", "custom-hooks")
        self.assert_blocked(self.run_guard("install"), "Existing core.hooksPath preserved")

    def test_real_local_push_is_blocked_before_remote_changes(self):
        script = self.root / "scripts/public_repo_guard.py"
        script.parent.mkdir()
        shutil.copyfile(SCRIPT, script)
        self.commit("Install public guard source")
        remote = Path(self.scratch.name) / "remote.git"
        self.git("init", "--bare", "-q", str(remote))
        self.git("remote", "add", "fixture", str(remote))
        self.git("push", "-q", "fixture", "main")
        remote_before = self.git("rev-parse", "refs/heads/main", cwd=remote)
        self.assertEqual(self.run_guard("install").returncode, 0)
        self.assertEqual(self.run_guard("install").returncode, 0)
        (self.root / "oops.txt").write_text("ghp_" + "A" * 36)
        self.commit("Add synthetic fixture")
        (self.root / "oops.txt").unlink()
        self.commit("Remove synthetic fixture")
        result = subprocess.run(
            ["git", "push", "fixture", "main"], cwd=self.root, env=self.env,
            capture_output=True, text=True, timeout=30,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("possible credential", result.stderr)
        self.assertEqual(self.git("rev-parse", "refs/heads/main", cwd=remote), remote_before)


if __name__ == "__main__":
    unittest.main()
