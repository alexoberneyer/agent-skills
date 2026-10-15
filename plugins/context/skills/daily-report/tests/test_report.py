"""Isolated tests. No real agent logs, SSH, or external dependencies."""
from datetime import date, datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import shutil
import shlex
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

SKILL = Path(__file__).resolve().parents[1]
SCRIPT = SKILL / "scripts" / "report.py"
TEMPLATE = SKILL / "assets" / "template.html"
SPEC = importlib.util.spec_from_file_location("daily_report_runtime", SCRIPT)
r = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r)
ZONE = ZoneInfo("Europe/Berlin")
DAY = date(2026, 10, 14)
START, END = r.window(DAY, ZONE)


class Dates(unittest.TestCase):
    def test_relative_dates_follow_local_midnight(self):
        now = datetime(2026, 10, 14, 22, 30, tzinfo=timezone.utc)
        self.assertEqual(r.parse_day("today", ZONE, now), date(2026, 10, 15))
        self.assertEqual(r.parse_day("yesterday", ZONE, now), DAY)
        self.assertEqual(r.parse_day("tomorrow", ZONE, now), date(2026, 10, 16))
        self.assertEqual(r.parse_day("2 days ago", ZONE, now), date(2026, 10, 13))
        self.assertEqual(r.parse_day("2026-10-14", ZONE, now), DAY)

    def test_invalid_dates(self):
        for value in ("last Tuesday", "2026-02-30", "14/10/2026", "20261014", "-1 days ago"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                r.parse_day(value, ZONE)

    def test_dst_day_lengths(self):
        for day, hours in ((date(2026, 3, 29), 23), (date(2026, 10, 25), 25), (DAY, 24)):
            start, end = r.window(day, ZONE)
            self.assertEqual((end.timestamp() - start.timestamp()) / 3600, hours)


class Workspace(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve()
        isolated = {k: v for k, v in r.GIT_ENV.items() if not k.startswith("GIT_")}
        isolated.update(HOME=str(self.home), GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_CONFIG_SYSTEM=os.devnull, GIT_CONFIG_NOSYSTEM="1",
                        GIT_NO_LAZY_FETCH="1", GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")
        self.git_environment = isolated
        self.git_patch = patch.dict(r.GIT_ENV, isolated, clear=True)
        self.git_patch.start()
        self.addCleanup(self.git_patch.stop)

    def write_jsonl(self, path, records):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(json.dumps(record) for record in records) + "\n")
        return path

    def repo(self, name="repo", bare=False):
        path = self.home / name
        path.mkdir(parents=True)
        self.command(path, "init", "--initial-branch=main", *(["--bare"] if bare else []))
        self.command(path, "config", "user.name", "Report User")
        self.command(path, "config", "user.email", "user@example.test")
        return path

    def command(self, path, *args, env=None):
        return subprocess.run(["git", "-c", f"core.hooksPath={os.devnull}", "-c", "commit.gpgSign=false",
                               "-C", str(path), *args], check=True, capture_output=True,
                              text=True, env=dict(self.git_environment, **(env or {}))).stdout.strip()

    def commit(self, path, title, when="2026-10-14T12:00:00+02:00", author=None):
        args = ["commit", "--allow-empty", "-m", title]
        if author:
            args += ["--author", author]
        self.command(path, *args, env={"GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when})
        return self.command(path, "rev-parse", "HEAD")


class Histories(Workspace):
    def test_date_filter_uses_message_time_not_creation_or_mtime(self):
        path = self.write_jsonl(self.home / "old.jsonl", [
            {"type": "session", "cwd": "/outside/repo", "timestamp": "2026-01-01T00:00:00Z"},
            {"type": "message", "timestamp": "2026-10-13T21:59:59Z", "message": {"role": "user", "content": "before"}},
            {"type": "message", "timestamp": "2026-10-13T22:00:00Z", "message": {"role": "user", "content": "start"}},
            {"type": "message", "timestamp": "2026-10-14T21:59:59Z", "message": {"role": "assistant", "content": [{"type": "text", "text": "end"}]}},
            {"type": "message", "timestamp": "2026-10-14T22:00:00Z", "message": {"role": "assistant", "content": "after"}},
        ])
        session, cwds, issues = r.read_session(path, "Pi", "local", START, END)
        self.assertEqual([m["text"] for m in session["messages"]], ["start", "end"])
        self.assertEqual(cwds, {"/outside/repo"})
        self.assertIsNone(issues)

    def test_claude_excludes_tool_results_thinking_and_api_blobs(self):
        path = self.write_jsonl(self.home / "claude.jsonl", [
            {"type": "user", "cwd": "/repo", "timestamp": "2026-10-14T08:00:00Z", "message": {"role": "user", "content": "question"}},
            {"type": "user", "timestamp": "2026-10-14T08:00:01Z", "message": {"role": "user", "content": [{"type": "tool_result", "content": "secret output"}]}},
            {"type": "assistant", "timestamp": "2026-10-14T08:00:02Z", "message": {"role": "assistant", "content": [{"type": "thinking", "thinking": "private"}, {"type": "text", "text": "answer"}, {"type": "tool_use", "input": {"secret": "x"}}]}},
            {"type": "api-request-blob", "message": {"role": "user", "content": "api secret"}},
            {"type": "user", "isCompactSummary": True, "timestamp": "2026-10-14T08:00:03Z", "message": {"role": "user", "content": "old work summary"}},
        ])
        session, _, _ = r.read_session(path, "Claude", "local", START, END)
        self.assertEqual([m["text"] for m in session["messages"]], ["question", "answer"])

    def test_codex_response_items_not_duplicated_by_events(self):
        path = self.write_jsonl(self.home / "codex.jsonl", [
            {"type": "session_meta", "payload": {"cwd": "/repo"}},
            {"type": "response_item", "timestamp": "2026-10-14T09:00:00Z", "payload": {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "done"}]}},
            {"type": "event_msg", "timestamp": "2026-10-14T09:00:00Z", "payload": {"type": "agent_message", "message": "done"}},
            {"type": "response_item", "timestamp": "2026-10-14T09:00:00Z", "payload": {"type": "reasoning", "content": [{"type": "text", "text": "hidden"}]}},
        ])
        session, _, _ = r.read_session(path, "Codex", "local", START, END)
        self.assertEqual(len(session["messages"]), 1)
        self.assertEqual(session["messages"][0]["text"], "done")

    def test_omp_millisecond_message_timestamp_and_clipping(self):
        path = self.write_jsonl(self.home / "omp.jsonl", [
            {"type": "session", "cwd": "/repo"},
            {"type": "message", "message": {"role": "user", "timestamp": 1791968400000, "content": "x" * (r.MAX_TEXT + 4)}},
        ])
        session, _, _ = r.read_session(path, "OMP", "local", START, END)
        self.assertEqual(session["messages"][0]["omitted_characters"], 4)
        self.assertEqual(len(session["messages"][0]["text"]), r.MAX_TEXT)

    def test_malformed_and_undated_records_are_visible(self):
        path = self.write_jsonl(self.home / "bad.jsonl", [
            {"type": "message", "message": {"role": "user", "content": "no date"}},
        ])
        with path.open("a") as stream:
            stream.write('{"unfinished":\n')
        _, _, issue = r.read_session(path, "Pi", "local", START, END)
        self.assertEqual(issue["malformed_lines"], 1)
        self.assertEqual(issue["undated_messages"], 1)

    def test_structurally_malformed_records_do_not_abort_later_valid_messages(self):
        path = self.write_jsonl(self.home / "shapes.jsonl", [
            {"type": []},
            {"type": "message", "message": {"role": [], "content": "invalid"}},
            {"type": "message", "id": ["bad"], "timestamp": "2026-10-14T08:00:00Z",
             "message": {"role": "user", "content": "invalid ID"}},
            *({"type": "message", "id": invalid, "timestamp": "2026-10-14T08:00:00Z",
               "message": {"role": "user", "content": "invalid falsey ID"}} for invalid in ([], {})),
            {"type": "message", "timestamp": "2026-10-14T08:00:00Z", "message": {
                "role": "user", "content": [{"type": ["text"], "text": "bad content type"}]}},
            {"type": "message", "timestamp": "2026-10-14T08:00:00Z", "message": {
                "role": "user", "content": {"text": "bad content container"}}},
            {"type": "message", "id": "good", "timestamp": "2026-10-14T08:01:00Z",
             "message": {"role": "user", "content": "valid dated message"}},
        ])
        session, _, issue = r.read_session(path, "Pi", "local", START, END)
        self.assertEqual(issue["malformed_lines"], 7)
        self.assertEqual([m["text"] for m in session["messages"]], ["valid dated message"])
        self.assertEqual(r.text_content([{"type": ["text"], "text": "bad block type"}]), "")

    def test_known_metadata_only_claude_stub_is_not_unknown_format(self):
        path = self.write_jsonl(self.home / "stub.jsonl", [
            {"type": "ai-title", "aiTitle": "Unused", "sessionId": "stub"},
            {"type": "agent-name", "agentName": "Agent", "sessionId": "stub"},
        ])
        session, _, issue = r.read_session(path, "Claude", "local", START, END)
        self.assertIsNone(session)
        self.assertIsNone(issue)

    def test_missing_sources_archives_and_nested_subagents(self):
        for relative, agent, payload in (
            (".claude/projects/project/session/subagents/agent.jsonl", "Claude", {"type": "user", "message": {"role": "user", "content": "delegated"}}),
            (".codex/archived_sessions/old.jsonl", "Codex", {"type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "archive"}]}}),
        ):
            payload["timestamp"] = "2026-10-14T08:00:00Z"
            self.write_jsonl(self.home / relative, [payload])
        with patch.dict(os.environ, {}, clear=True):
            sessions, _, coverage = r.collect_sessions(self.home, "local", START, END)
        self.assertEqual({s["agent"] for s in sessions}, {"Claude", "Codex"})
        self.assertEqual(next(c for c in coverage if c["source"] == "OMP")["status"], "missing")


class GitEvidence(Workspace):
    def test_nested_repos_worktrees_external_session_paths_and_bare(self):
        root = self.home / "Code"
        first = self.repo("Code/first")
        self.commit(first, "Initial")
        nested = self.repo("Code/first/nested")
        second = self.repo("outside/second")
        bare = self.repo("Code/archive.git", bare=True)
        worktree = self.home / "outside/worktree"
        self.command(first, "worktree", "add", "-b", "other", str(worktree))
        paths, issues = r.find_repositories([root], {str(second / "src") if (second / "src").exists() else str(second)})
        self.assertEqual(set(paths), {first, nested, second, bare, worktree})
        self.assertEqual(issues, [])

    def test_deleted_session_scratch_directory_still_finds_parent_repo(self):
        repo = self.repo("outside/repo")
        paths, issues = r.find_repositories([], {str(repo / "deleted" / "scratch")})
        self.assertEqual(paths, [repo])
        self.assertEqual(issues, [])

    def test_worktree_merge_preserves_canonical_project_and_any_identity_match(self):
        repositories = [
            {"path": "/Code/project", "common_dir": "/Code/project/.git", "commits": [
                {"id": "same", "repo": "/Code/project", "matches_identity": True}]},
            {"path": "/elsewhere/tree", "common_dir": "/Code/project/.git", "commits": [
                {"id": "same", "repo": "/elsewhere/tree", "matches_identity": False}]},
        ]
        commit = r.merge_worktree_commits(repositories)["same"]
        self.assertEqual(commit["repo"], "/Code/project")
        self.assertTrue(commit["matches_identity"])
        self.assertEqual(commit["identity_matched_checkouts"], ["/Code/project"])
        self.assertEqual(commit["checkouts"], ["/Code/project", "/elsewhere/tree"])

    def test_git_subprocesses_disable_implicit_fetch_and_optional_locks(self):
        with patch.object(subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "", "")) as run:
            r.git(self.home, "status")
        self.assertEqual(run.call_args.kwargs["env"]["GIT_NO_LAZY_FETCH"], "1")
        self.assertEqual(run.call_args.kwargs["env"]["GIT_OPTIONAL_LOCKS"], "0")

    def test_all_refs_reflog_and_multiple_commit_record_parsing(self):
        repo = self.repo()
        initial = self.commit(repo, "Initial outside day", "2026-10-12T10:00:00+02:00")
        self.command(repo, "checkout", "-b", "topic")
        topic = self.commit(repo, "Topic only")
        lost = self.commit(repo, "Reflog only")
        self.command(repo, "reset", "--hard", topic)
        self.command(repo, "checkout", "main")
        head = self.commit(repo, "Current branch")
        info = r.inspect_repo(repo, "local", START, END, [], False)
        self.assertEqual(info["status"], "scanned", info["issues"])
        self.assertEqual({c["sha"] for c in info["commits"]}, {topic, lost, head})
        self.assertNotIn(initial, {c["sha"] for c in info["commits"]})
        self.assertTrue(all(c["matches_identity"] for c in info["commits"]))
        self.assertIsNone(info["working_tree_now"])

    def test_identity_matching_excludes_unrelated_authors_and_committers(self):
        repo = self.repo()
        self.command(repo, "config", "user.name", "Other Person")
        self.command(repo, "config", "user.email", "other@example.test")
        self.commit(repo, "Other commit")
        self.command(repo, "config", "user.name", "Report User")
        self.command(repo, "config", "user.email", "user@example.test")
        info = r.inspect_repo(repo, "local", START, END, [], False)
        self.assertFalse(info["commits"][0]["matches_identity"])

    def test_shared_worktree_commit_ids_are_identical(self):
        repo = self.repo()
        self.commit(repo, "Shared")
        worktree = self.home / "tree"
        self.command(repo, "worktree", "add", "-b", "other", str(worktree))
        a = r.inspect_repo(repo, "local", START, END, [], False)
        b = r.inspect_repo(worktree, "local", START, END, [], False)
        self.assertEqual(a["commits"][0]["id"], b["commits"][0]["id"])

    def test_empty_and_bare_repositories_are_not_false_errors(self):
        for bare in (False, True):
            repo = self.repo(f"empty-{bare}", bare=bare)
            info = r.inspect_repo(repo, "local", START, END, [], True)
            self.assertEqual(info["status"], "scanned", info["issues"])
            self.assertEqual(info["commits"], [])

    def test_today_does_not_execute_repository_clean_filters(self):
        repo = self.repo()
        (repo / "tracked.txt").write_text("before")
        self.command(repo, "add", "tracked.txt")
        self.commit(repo, "Initial")
        sentinel = self.home / "filter-executed"
        self.command(repo, "config", "filter.sentinel.clean", f"touch {shlex.quote(str(sentinel))}; cat")
        (repo / ".gitattributes").write_text("*.txt filter=sentinel\n")
        (repo / "tracked.txt").write_text("after!")
        info = r.inspect_repo(repo, "local", START, END, [], True)
        self.assertIsNone(info["working_tree_now"])
        self.assertIn("filters", info["working_tree_note"])
        self.assertFalse(sentinel.exists())

    def test_git_version_requirement_is_explicit(self):
        with patch.object(subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "git version 2.34.1\n", "")):
            with self.assertRaisesRegex(ValueError, "Git 2.37"):
                r.require_git()
        with patch.object(subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "git version 2.50.1 (Apple Git)\n", "")):
            r.require_git()


class Packaging(Workspace):
    def test_fixture_ignores_inherited_git_config_injection(self):
        fixture_spec = importlib.util.spec_from_file_location("fixture_runtime", SKILL / "tests/make_fixture.py")
        fixture = importlib.util.module_from_spec(fixture_spec)
        fixture_spec.loader.exec_module(fixture)
        poisoned = self.home / "bad-config"
        poisoned.write_text("[commit]\n\tgpgSign = true\n[user]\n\tname = Wrong User\n")
        home = self.home / "synthetic"
        with patch.dict(os.environ, {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "include.path",
                                    "GIT_CONFIG_VALUE_0": str(poisoned)}):
            fixture.make_fixture(home, DAY)
        self.assertEqual(self.command(home / "Code/app", "log", "-1", "--format=%an"), "Report User")
        self.assertFalse((home / ".local/bin/daily-report").exists())

    def test_copied_plugin_cache_runs_through_skill_symlink_without_dotfiles(self):
        cache = self.home / "plugin cache with spaces" / "context" / "9.0.0" / "skills" / "daily-report"
        shutil.copytree(SKILL, cache, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        link = self.home / ".agents" / "skills" / "daily-report"
        link.parent.mkdir(parents=True)
        link.symlink_to(cache, target_is_directory=True)
        self.repo("Code/demo")
        env = dict(self.git_environment, HOME=str(self.home), TZ="UTC")
        for key in ("CLAUDE_CONFIG_DIR", "PI_CODING_AGENT_DIR", "PI_CODING_AGENT_SESSION_DIR", "CODEX_HOME"):
            env.pop(key, None)
        output = self.home / "output"
        result = subprocess.run([sys.executable, str(link / "scripts/report.py"), "2026-01-15",
                                 "--output", str(output)], env=env, cwd=self.home,
                                text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        document = (output / "report.html").read_text()
        for command in ("/skill:daily-report", "$daily-report", "/context:daily-report"):
            self.assertIn(command, document)
        self.assertIn('id="report-agent"', document)
        self.assertFalse((self.home / ".local/bin/daily-report").exists())
        self.assertFalse((self.home / "Code/dotfiles").exists())

    def test_runtime_and_docs_contain_no_personal_paths_or_host_aliases(self):
        for relative in ("SKILL.md", "README.md", "scripts/report.py", "assets/template.html"):
            content = (SKILL / relative).read_text()
            for private in ("/Users/", "/home/", "~/.local/bin/daily-report", "~/Code/dotfiles"):
                with self.subTest(file=relative, private=private):
                    self.assertNotIn(private, content)


class Output(Workspace):
    def data(self):
        return {"version": 1, "date": "2026-10-14", "timezone": "Europe/Berlin",
                "generated_at": "2026-10-15T10:00:00Z", "hosts": [
                    {"host": "local", "status": "scanned", "roots": ["/Code"], "sources": [],
                     "repositories": [], "commits": [], "unmatched_session_directories": [],
                     "discovery_issues": [], "sessions": [{"id": "s-test", "kind": "session", "host": "local",
                        "agent": "Pi", "path": "/private/session.jsonl", "cwds": ["/Code"], "title": "<script>bad</script>",
                        "first_activity": "2026-10-14T08:00:00Z", "last_activity": "2026-10-14T08:00:00Z",
                        "messages": [{"role": "assistant", "time": "2026-10-14T08:00:00Z", "line": 2,
                                      "text": "</script><img src=x onerror=bad()>", "omitted_characters": 0}]}]}]}

    def test_html_is_escaped_and_self_contained(self):
        data = self.data()
        output = r.render(data, r.default_summary(data), TEMPLATE)
        self.assertNotIn("<script>bad</script>", output)
        self.assertIn("&lt;script&gt;bad&lt;/script&gt;", output)
        self.assertNotIn("<img src=x", output)
        self.assertNotIn("{{", output)
        self.assertIn("default-src 'none'", output)
        self.assertNotIn('src="https://', output)
        self.assertNotIn('href="https://fonts', output)

    def test_stale_hash_invalid_citation_and_false_recorded_status_rejected(self):
        data = self.data()
        for mutation in ("hash", "citation", "status"):
            summary = r.default_summary(data)
            if mutation == "hash":
                summary["evidence_sha256"] = "stale"
            elif mutation == "citation":
                summary["projects"][0]["evidence"] = ["does-not-exist"]
            else:
                summary["projects"][0]["status"] = "recorded"
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                r.validate_summary(summary, data)

    def test_private_atomic_writes(self):
        path = self.home / "private" / "evidence.json"
        r.private_write(path, "first")
        r.private_write(path, "second")
        self.assertEqual(path.read_text(), "second")
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(path.parent.stat().st_mode), 0o700)
        self.assertEqual(list(path.parent.glob(".daily-report-*")), [])

    def test_unavailable_remote_is_explicit(self):
        with patch.object(subprocess, "run", side_effect=subprocess.TimeoutExpired("ssh", 180)):
            result = r.collect_remote("dev-example", DAY, ZONE.key)
        self.assertEqual(result["status"], "unavailable")
        self.assertIn("180", result["error"])

    def test_ssh_host_cannot_inject_options(self):
        with self.assertRaises(ValueError):
            r.collect_remote("-oProxyCommand=bad", DAY, ZONE.key)

    def test_cli_dates_end_to_end_with_an_isolated_home(self):
        repo = self.repo("Code/demo")
        self.commit(repo, "Fixture commit")
        env = dict(self.git_environment, HOME=str(self.home), TZ="Europe/Berlin")
        for key in ("CLAUDE_CONFIG_DIR", "PI_CODING_AGENT_DIR", "PI_CODING_AGENT_SESSION_DIR", "CODEX_HOME"):
            env.pop(key, None)
        today = datetime.now(ZONE).date()
        cases = [("today", today), ("yesterday", today.fromordinal(today.toordinal() - 1)),
                 ("tomorrow", today.fromordinal(today.toordinal() + 1)),
                 ("2 days ago", today.fromordinal(today.toordinal() - 2)), ("2026-10-14", DAY)]
        for value, expected in cases:
            output = self.home / "outputs" / value.replace(" ", "-")
            result = subprocess.run([sys.executable, str(SCRIPT), value,
                                     "--timezone", "Europe/Berlin", "--output", str(output)],
                                    env=env, text=True, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads((output / "evidence.json").read_text())
            self.assertEqual(data["date"], expected.isoformat())
            self.assertEqual(len(data["hosts"][0]["repositories"]), 1)
            self.assertTrue((output / "report.html").is_file())
            if expected != today:
                self.assertIsNone(data["hosts"][0]["repositories"][0]["working_tree_now"])

    def test_configuration_validation(self):
        path = self.home / ".config/daily-report/config.json"
        path.parent.mkdir(parents=True)
        path.write_text('{"roots": "~/Code"}')
        with self.assertRaises(ValueError):
            r.read_config(self.home)


if __name__ == "__main__":
    unittest.main()
