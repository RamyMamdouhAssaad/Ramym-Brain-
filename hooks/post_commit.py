#!/usr/bin/env python3
"""Git post-commit hook that auto-logs commits to ramym-brain.

Install: copy to .git/hooks/post-commit (or use install script)
"""

import json
import subprocess
import sys


def get_commit_info():
    """Extract latest commit info."""
    result = subprocess.run(
        ["git", "log", "-1", "--pretty=format:%H|%s|%b|%an|%ai"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None

    parts = result.stdout.split("|", 4)
    if len(parts) < 5:
        return None

    return {
        "hash": parts[0][:8],
        "subject": parts[1],
        "body": parts[2].strip(),
        "author": parts[3],
        "date": parts[4],
    }


def get_changed_files():
    """Get list of changed files in the commit."""
    result = subprocess.run(
        ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip().split("\n") if result.returncode == 0 else []


def get_repo_name():
    """Get repository name from remote or folder."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return result.stdout.strip().split("/")[-1].split("\\")[-1]
    return "unknown"


def call_brain(decision: str, context: str, tags: list[str]):
    """Call the brain's log_decision via MCP client (lightweight HTTP or direct DB)."""
    # For now, write to a local queue file that the brain ingests
    import os

    queue_dir = os.path.expanduser("~/.ramym-brain/queue")
    os.makedirs(queue_dir, exist_ok=True)

    entry = {
        "type": "decision",
        "decision": decision,
        "context": context,
        "tags": tags,
    }

    # Use commit hash as filename to avoid duplicates
    commit_info = get_commit_info()
    filename = f"commit_{commit_info['hash']}.json" if commit_info else "commit_unknown.json"
    filepath = os.path.join(queue_dir, filename)

    with open(filepath, "w") as f:
        json.dump(entry, f, indent=2)


def main():
    commit = get_commit_info()
    if not commit:
        sys.exit(0)

    # Skip merge commits and trivial commits
    if commit["subject"].startswith("Merge"):
        sys.exit(0)

    files = get_changed_files()
    repo = get_repo_name()

    # Build decision entry
    decision = f"[{repo}] {commit['subject']}"
    context_parts = [
        f"Commit: {commit['hash']}",
        f"Files changed: {', '.join(files[:10])}",
    ]
    if commit["body"]:
        context_parts.append(f"Details: {commit['body']}")

    context = "\n".join(context_parts)
    tags = ["git", "commit", repo]

    # Detect type from conventional commit prefix
    prefixes = {
        "feat": "feature",
        "fix": "bugfix",
        "refactor": "refactor",
        "perf": "performance",
        "test": "testing",
    }
    for prefix, tag in prefixes.items():
        if commit["subject"].startswith(f"{prefix}(") or commit["subject"].startswith(f"{prefix}:"):
            tags.append(tag)
            break

    call_brain(decision, context, tags)


if __name__ == "__main__":
    main()
