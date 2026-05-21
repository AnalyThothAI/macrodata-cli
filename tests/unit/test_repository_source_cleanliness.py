from __future__ import annotations

import subprocess
from pathlib import Path
from shutil import which

ROOT = Path(__file__).resolve().parents[2]


def _git() -> str:
    git = which("git")
    assert git is not None
    return git


def test_repository_does_not_track_worktree_or_gitlink_entries() -> None:
    result = subprocess.run(  # noqa: S603 - fixed git executable plus static arguments.
        [_git(), "ls-files", "--stage"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    tracked_worktrees = [line for line in result.stdout.splitlines() if "\t.worktrees/" in line]
    tracked_gitlinks = [line for line in result.stdout.splitlines() if line.startswith("160000 ")]

    assert tracked_worktrees == []
    assert tracked_gitlinks == []


def test_local_worktree_directory_is_ignored() -> None:
    result = subprocess.run(  # noqa: S603 - fixed git executable plus static arguments.
        [_git(), "check-ignore", "-q", ".worktrees/example"],
        cwd=ROOT,
        check=False,
    )

    assert result.returncode == 0
