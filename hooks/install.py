#!/usr/bin/env python3
"""Install ramym-brain git hooks into a repository.

Usage:
    python -m hooks.install [repo_path]
    python -m hooks.install  # installs in current git repo
"""

import os
import shutil
import stat
import sys


HOOK_TEMPLATE = '''#!/bin/sh
# ramym-brain auto-capture hook
python "{hook_script}" "$@"
'''


def install(repo_path: str | None = None):
    """Install post-commit hook into the given repo."""
    if repo_path is None:
        repo_path = os.getcwd()

    hooks_dir = os.path.join(repo_path, ".git", "hooks")
    if not os.path.isdir(hooks_dir):
        print(f"Error: {hooks_dir} does not exist. Is this a git repo?")
        sys.exit(1)

    hook_script = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "post_commit.py")
    )

    hook_file = os.path.join(hooks_dir, "post-commit")

    # Don't overwrite existing hooks — chain them
    if os.path.exists(hook_file):
        # Append to existing hook
        with open(hook_file, "a") as f:
            f.write(f'\npython "{hook_script}"\n')
        print(f"Appended brain hook to existing {hook_file}")
    else:
        content = HOOK_TEMPLATE.format(hook_script=hook_script)
        with open(hook_file, "w") as f:
            f.write(content)
        # Make executable
        os.chmod(hook_file, os.stat(hook_file).st_mode | stat.S_IEXEC)
        print(f"Installed brain hook at {hook_file}")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else None
    install(path)
