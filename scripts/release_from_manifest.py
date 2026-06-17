#!/usr/bin/env python3
"""Create a GitHub release for a new Devin CLI manifest version.

Reads the published manifest, and if its version has not yet been released,
creates a GitHub release for that version whose notes link to the corresponding
entry in the CLI changelog. No binaries are attached — the binaries are served
from static.devin.ai and the release simply records the version.

Usage:
    # Check only (no release); exits 0 if up to date, 10 if a new version exists
    python scripts/release_from_manifest.py --check

    # Create the release if the manifest version is new
    python scripts/release_from_manifest.py

Environment variables:
    GH_TOKEN / GITHUB_TOKEN: token used by the `gh` CLI to create the release.
"""

import argparse
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request

MANIFEST_URL = "https://static.devin.ai/cli/current/manifest.json"
CHANGELOG_BASE = "https://docs.devin.ai/cli/changelog/stable"
USER_AGENT = "devin-cli-release-bot/1.0"

NEW_VERSION_EXIT_CODE = 10


def fetch_manifest(url: str) -> dict:
    """Download and parse the manifest JSON."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def get_version(manifest: dict) -> str:
    """Extract and validate the version from the manifest."""
    version = manifest.get("version")
    if not isinstance(version, str) or not re.fullmatch(r"[0-9A-Za-z][0-9A-Za-z.+-]*", version):
        raise ValueError(f"Manifest has an invalid version: {version!r}")
    return version


def changelog_url(version: str) -> str:
    """Build the changelog anchor URL for a version (e.g. 2026.5.26-7 -> #2026-5-26-7)."""
    anchor = version.replace(".", "-")
    return f"{CHANGELOG_BASE}#{anchor}"


def build_release_notes(version: str) -> str:
    """Build markdown release notes linking to the changelog entry."""
    return f"See the [changelog]({changelog_url(version)}) for what's included in `{version}`."


def release_exists(tag: str) -> bool:
    """Return True if a GitHub release with the given tag already exists."""
    result = subprocess.run(
        ["gh", "release", "view", tag],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def create_release(tag: str, version: str, notes: str) -> None:
    """Create a GitHub release (no assets) via the gh CLI."""
    subprocess.run(
        ["gh", "release", "create", tag, "--title", version, "--notes", notes],
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only report whether a new version exists; do not create a release.",
    )
    parser.add_argument(
        "--manifest-url",
        default=MANIFEST_URL,
        help="Override the manifest URL (for testing).",
    )
    args = parser.parse_args()

    try:
        manifest = fetch_manifest(args.manifest_url)
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: could not fetch manifest: {exc}", file=sys.stderr)
        return 1

    try:
        version = get_version(manifest)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    tag = version
    print(f"Manifest version: {version}")

    if release_exists(tag):
        print(f"Release {tag} already exists; nothing to do.")
        return 0

    print(f"Release {tag} does not exist yet.")
    if args.check:
        return NEW_VERSION_EXIT_CODE

    notes = build_release_notes(version)
    print(f"Creating release {tag}...")
    create_release(tag, version, notes)
    print(f"Created release {tag}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
