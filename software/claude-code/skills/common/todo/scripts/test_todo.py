#!/usr/bin/python3
"""Tests for todo.py against throwaway git repos and a throwaway vault.

Run:  /usr/bin/python3 -m unittest software/claude-code/skills/common/todo/scripts/test_todo.py
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import todo  # noqa: E402


def sh(cwd: Path, *args: str) -> str:
    return subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, check=True).stdout.strip()


def make_repo(root: Path, name: str = "proj") -> Path:
    repo = root / name
    repo.mkdir()
    sh(repo, "git", "init", "-q", "-b", "main")
    sh(repo, "git", "config", "user.email", "t@example.invalid")
    sh(repo, "git", "config", "user.name", "t")
    sh(repo, "git", "config", "commit.gpgsign", "false")
    (repo / "README").write_text("x\n")
    sh(repo, "git", "add", ".")
    sh(repo, "git", "commit", "-q", "-m", "init")
    return repo


class Run:
    """Runs todo.main with captured stdout/stderr and optional stdin JSON."""

    def __init__(self, cwd: Path, session: str = "s1"):
        self.cwd = cwd
        self.session = session

    def __call__(self, *args: str, stdin: object = None, env: dict = None) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        argv = ["--cwd", str(self.cwd), "--session", self.session, *args]
        saved = dict(os.environ)
        os.environ.update(env or {})
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                sys.stdin = io.StringIO(json.dumps(stdin) if stdin is not None else "")
                code = todo.main(argv)
        finally:
            sys.stdin = sys.__stdin__
            os.environ.clear()
            os.environ.update(saved)
        return code, out.getvalue(), err.getvalue()


class TodoFileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.repo = make_repo(self.root)
        self.todos = self.repo / ".claude" / "scratchpad.local" / "todos.md"
        os.environ.pop("CLAUDE_TODO_HOOKS", None)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def add(self, run: Run, text: str, by: str = "user", **extra: str) -> tuple[int, str, str]:
        args = ["add", "--by", by, "--text", text, "--while", "testing"]
        for key, value in extra.items():
            args += [f"--{key}", value]
        return run(*args)

    def test_add_on_feature_branch_creates_file_and_gitignore(self) -> None:
        sh(self.repo, "git", "checkout", "-q", "-b", "feat/nvm-fish")
        code, out, _ = self.add(Run(self.repo), "Fix the flaky test", title="nvm for fish")
        self.assertEqual(code, 0, out)
        content = self.todos.read_text()
        self.assertIn("## feat-nvm-fish\n", content)
        self.assertRegex(
            content,
            r'- \[ \] Fix the flaky test  \(by user; added \d{4}-\d\d-\d\d \d\d:\d\d; session s1 "nvm for fish"; branch feat/nvm-fish; while testing\)',
        )
        self.assertEqual((self.todos.parent / ".gitignore").read_text(), "*\n")

    def test_default_branch_needs_section(self) -> None:
        code, _, err = self.add(Run(self.repo), "Thing")
        self.assertEqual(code, 1)
        self.assertIn("--section", err)
        code, _, _ = self.add(Run(self.repo), "Thing", section="2026-10-15_thing")
        self.assertEqual(code, 0)
        self.assertIn("## 2026-10-15_thing\n", self.todos.read_text())

    def test_story_from_branch_and_worktree_field(self) -> None:
        sh(self.repo, "git", "checkout", "-q", "-b", "ABC-12-add-thing")
        sh(self.repo, "git", "checkout", "-q", "main")
        wt = self.root / "proj-wt"
        sh(self.repo, "git", "worktree", "add", "-q", str(wt), "ABC-12-add-thing")
        code, _, _ = self.add(Run(wt), "From the worktree")
        self.assertEqual(code, 0)
        content = self.todos.read_text()
        self.assertIn("## ABC-12-add-thing\n", content)
        self.assertIn("; worktree ../proj-wt; story ABC-12; while testing)", content)

    def test_list_current_first_and_remove_by_number(self) -> None:
        sh(self.repo, "git", "checkout", "-q", "-b", "a")
        self.add(Run(self.repo), "A one")
        self.add(Run(self.repo), "A two", by="claude")
        sh(self.repo, "git", "checkout", "-q", "-b", "b")
        self.add(Run(self.repo), "B one")
        run = Run(self.repo)
        code, out, _ = run("list")
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines()[0], "b  (current)")
        self.assertIn("1. B one  [by user,", out)
        self.assertIn("Other open sections: a (2)", out)
        self.assertNotIn("A one", out)
        code, out, _ = run("list", "--all")
        self.assertIn("2. A one", out)
        self.assertIn("3. A two  [by claude,", out)
        code, out, _ = run("remove", "3")
        self.assertEqual(code, 0, out)
        self.assertNotIn("A two", self.todos.read_text())
        code, out, _ = run("remove", "1")
        self.assertEqual(code, 0, out)
        content = self.todos.read_text()
        self.assertNotIn("## b", content)
        self.assertEqual(content, content.lstrip("\n"))
        code, out, _ = run("remove", "2")
        self.assertEqual(code, 0, out)
        self.assertFalse(self.todos.exists())

    def test_stale_number_is_rejected_with_fresh_listing(self) -> None:
        sh(self.repo, "git", "checkout", "-q", "-b", "a")
        self.add(Run(self.repo), "One")
        self.add(Run(self.repo), "Two")
        run = Run(self.repo)
        run("list")
        other = Run(self.repo, session="s2")
        other("list")
        other("remove", "1")
        code, _, err = run("remove", "1")
        self.assertEqual(code, 1)
        self.assertIn("stale", err)
        self.assertIn("1. Two", err)
        code, _, _ = run("remove", "1")
        self.assertEqual(code, 0)

    def test_hand_edits_survive(self) -> None:
        sh(self.repo, "git", "checkout", "-q", "-b", "a")
        self.add(Run(self.repo), "One")
        content = self.todos.read_text()
        content = "<!-- my note -->\n" + content.replace("## a\n", "## a\nSome prose I typed.\n")
        self.todos.write_text(content)
        self.add(Run(self.repo), "Two")
        content = self.todos.read_text()
        self.assertTrue(content.startswith("<!-- my note -->\n"))
        self.assertIn("Some prose I typed.\n", content)
        self.assertLess(content.index("One"), content.index("Two"))

    def test_idea_routes(self) -> None:
        vault = self.root / "vault"
        (vault / ".obsidian").mkdir(parents=True)
        note = vault / "Ideas.md"
        cfg = self.root / "cfg"
        cfg.mkdir()
        todo.CONFIG_DIR, todo.IDEAS_NOTE_FILE = cfg, cfg / "ideas-note"
        run = Run(self.repo)
        code, _, err = run("idea", "--text", "Something")
        self.assertEqual(code, 1)
        self.assertIn("ideas-note", err)
        (cfg / "ideas-note").write_text(str(self.root / "outside.md") + "\n")
        code, _, err = run("idea", "--text", "Something")
        self.assertEqual(code, 1)
        self.assertIn("Obsidian vault", err)
        (cfg / "ideas-note").write_text(str(note) + "\n")
        note.write_text("# Ideas\n\n## alpha\n\n- 2026-01-01: Old one.\n\n## zeta\n\n- 2026-01-02: Z.\n")
        self.assertEqual(run("idea", "--text", "Add a fish config. Two shells.")[0], 0)
        self.assertEqual(Run(self.root)("idea", "--text", "Unrelated.")[0], 0)
        self.assertEqual(run("idea", "--text", "Second for proj.")[0], 0)
        content = note.read_text()
        self.assertEqual(
            content,
            "# Ideas\n\n## alpha\n\n- 2026-01-01: Old one.\n\n## General\n\n- %s: Unrelated.\n\n"
            "## proj\n\n- %s: Add a fish config. Two shells.\n- %s: Second for proj.\n\n## zeta\n\n- 2026-01-02: Z.\n"
            % ((todo.dt.date.today().isoformat(),) * 3),
        )


class HookTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.repo = make_repo(self.root)
        sh(self.repo, "git", "checkout", "-q", "-b", "feat")
        self.run = Run(self.repo)
        self.state = self.repo / ".claude" / "scratchpad.local" / "todos.state"
        self.notifications: list = []
        todo.notify = lambda message: self.notifications.append(message)
        os.environ.pop("CLAUDE_TODO_HOOKS", None)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def hook(self, name: str, **data: object) -> tuple[int, str]:
        payload = {"session_id": "s1", "cwd": str(self.repo), "hook_event_name": name, **data}
        code, out, _ = self.run(name.lower().replace("session", "session-"), stdin=payload)
        return code, out

    def context(self, out: str) -> str:
        return json.loads(out)["hookSpecificOutput"]["additionalContext"]

    def add(self, text: str) -> None:
        self.assertEqual(self.run("add", "--by", "user", "--text", text, "--while", "t")[0], 0)

    def test_session_start_silent_without_tasks(self) -> None:
        self.assertEqual(self.hook("SessionStart"), (0, ""))

    def test_session_start_lists_and_arms_stop(self) -> None:
        self.add("One")
        code, out = self.hook("SessionStart")
        self.assertEqual(code, 0)
        ctx = self.context(out)
        self.assertIn("This session's id is s1", ctx)
        self.assertIn("1. One", ctx)
        self.assertIn("ask which to pick up", ctx)
        self.assertTrue((self.state / "offered.s1").exists())
        self.assertEqual(self.hook("Stop"), (0, ""))

    def test_stop_speaks_once_per_change(self) -> None:
        self.assertEqual(self.hook("Stop"), (0, ""))
        self.add("One")
        code, out = self.hook("Stop")
        self.assertIn("1. One", self.context(out))
        self.assertEqual(self.hook("Stop"), (0, ""))
        self.add("Two")
        self.assertIn("2. Two", self.context(self.hook("Stop")[1]))
        self.assertEqual(self.hook("Stop", stop_hook_active=True), (0, ""))
        self.run("list")
        self.run("remove", "1")
        self.run("remove", "2")
        self.assertIn("No open side tasks remain", self.context(self.hook("Stop")[1]))
        self.assertEqual(self.hook("Stop"), (0, ""))

    def test_hooks_off_and_outside_repo(self) -> None:
        self.add("One")
        code, out, _ = self.run("stop", stdin={"session_id": "s1", "cwd": str(self.repo)}, env={"CLAUDE_TODO_HOOKS": "0"})
        self.assertEqual((code, out), (0, ""))
        outside = Run(self.root)
        code, out, _ = outside("session-start", stdin={"session_id": "s1", "cwd": str(self.root)})
        self.assertEqual((code, out), (0, ""))

    def test_session_end_marker_and_next_start(self) -> None:
        self.assertEqual(self.hook("SessionEnd", reason="other"), (0, ""))
        self.assertFalse((self.state / "last-session.json").exists())
        self.add("One")
        self.hook("SessionEnd", reason="clear")
        self.assertEqual(self.notifications, [])
        self.hook("SessionEnd", reason="other", session_title="my work")
        self.assertEqual(self.notifications, ["1 open side task(s) left in proj: feat (1)"])
        marker = json.loads((self.state / "last-session.json").read_text())
        self.assertEqual((marker["open"], marker["sections"], marker["title"]), (1, {"feat": 1}, "my work"))
        ctx = self.context(self.hook("SessionStart")[1])
        self.assertIn("The last session on this project (my work,", ctx)
        self.assertIn("ended with 1 open side task(s)", ctx)
        self.assertFalse((self.state / "last-session.json").exists())
        self.assertNotIn("last session", self.context(self.hook("SessionStart")[1]))


if __name__ == "__main__":
    unittest.main()
