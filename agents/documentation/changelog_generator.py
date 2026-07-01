"""
Changelog Generator Agent

Automatically generates and maintains CHANGELOG.md based on git commits,
pull requests, and semantic versioning.
"""

import os
import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ChangelogGenerator:
    """
    Autonomous agent that generates and maintains changelog documentation.

    Features:
    - Parses git commit history
    - Groups changes by type (feat, fix, docs, etc.)
    - Generates semantic version numbers
    - Updates CHANGELOG.md automatically
    """

    def __init__(self, repo_path: str = "."):
        """
        Initialize changelog generator.

        Args:
            repo_path: Path to git repository
        """
        self.repo_path = repo_path
        logger.info(f"ChangelogGenerator initialized for {repo_path}")

    def generate_changelog(
        self, version: Optional[str] = None, since_tag: Optional[str] = None
    ) -> str:
        """
        Generate changelog content.

        Args:
            version: Version number for this release
            since_tag: Generate changes since this git tag

        Returns:
            Formatted changelog content
        """
        logger.info(f"Generating changelog for version {version}")

        changes = self._parse_commits(since_tag)
        version_str = version or "Unreleased"
        return self._format_changelog(version_str, changes)

    def _parse_commits(self, since_tag: Optional[str] = None) -> List[Dict]:
        """Parse git commits into structured data using ``git log``.

        Returns a list of dicts with keys: ``hash``, ``type``, ``scope``,
        ``message``, ``breaking``, ``author``, ``date``.
        """
        import subprocess, re
        cmd = ["git", "log", "--pretty=format:%H|%an|%ad|%s", "--date=short"]
        if since_tag:
            cmd.append(f"{since_tag}..HEAD")
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                cwd=self.repo_path, timeout=30,
            )
            if result.returncode != 0:
                logger.warning("git log failed: %s", result.stderr.strip())
                return []
        except Exception as exc:
            logger.warning("git log subprocess error: %s", exc)
            return []

        # Conventional commit pattern: type(scope)!: message
        conv_re = re.compile(
            r"^(?P<type>feat|fix|docs|style|refactor|test|chore|perf|ci|build|revert)"
            r"(?:\((?P<scope>[^)]+)\))?"
            r"(?P<breaking>!)?"
            r":\s*(?P<message>.+)$"
        )
        commits = []
        for line in result.stdout.splitlines():
            parts = line.split("|", 3)
            if len(parts) < 4:
                continue
            sha, author, date, subject = parts
            m = conv_re.match(subject.strip())
            if m:
                commits.append({
                    "hash":     sha[:8],
                    "type":     m.group("type"),
                    "scope":    m.group("scope") or "",
                    "message":  m.group("message").strip(),
                    "breaking": bool(m.group("breaking")),
                    "author":   author,
                    "date":     date,
                })
            else:
                commits.append({
                    "hash":     sha[:8],
                    "type":     "other",
                    "scope":    "",
                    "message":  subject.strip(),
                    "breaking": False,
                    "author":   author,
                    "date":     date,
                })
        return commits

    def _format_changelog(self, version: str, changes: List[Dict]) -> str:
        """Format changes as markdown"""
        date = datetime.now().strftime("%Y-%m-%d")

        output = f"## [{version}] - {date}\n\n"

        # Group by type
        features = [c for c in changes if c.get("type") == "feat"]
        fixes = [c for c in changes if c.get("type") == "fix"]

        if features:
            output += "### Added\n"
            for feat in features:
                output += f"- {feat.get('message', '')}\n"
            output += "\n"

        if fixes:
            output += "### Fixed\n"
            for fix in fixes:
                output += f"- {fix.get('message', '')}\n"
            output += "\n"

        return output

    def update_changelog_file(self, content: str, filepath: str = "CHANGELOG.md"):
        """
        Update CHANGELOG.md file with new content.

        Args:
            content: New changelog content
            filepath: Path to changelog file
        """
        try:
            # Read existing content
            existing = ""
            if os.path.exists(filepath):
                with open(filepath, "r", encoding="utf-8") as f:
                    existing = f.read()

            # Prepend new content
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
                if existing:
                    f.write("\n")
                    f.write(existing)

            logger.info(f"Updated {filepath}")
        except Exception as e:
            logger.error(f"Failed to update changelog: {e}")


# Made with Bob
