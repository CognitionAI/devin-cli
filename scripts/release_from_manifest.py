#!/usr/bin/env python3
"""Create a GitHub release for a new Devin CLI manifest version.

Fetches the published manifest, and if its version has not yet been released,
downloads every platform binary, verifies its sha256, and creates a GitHub
release with the binaries (and the manifest) attached.

Usage:
    # Check only (no release); exits 0 if up to date, 10 if a new version exists
    python scripts/release_from_manifest.py --check

    # Create the release if the manifest version is new
    python scripts/release_from_manifest.py

Environment variables:
    GH_TOKEN / GITHUB_TOKEN: token used by the `gh` CLI to create the release.
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

MANIFEST_URL = "https://static.devin.ai/cli/current/manifest.json"
USER_AGENT = "devin-cli-release-bot/1.0"
DOWNLOAD_CHUNK = 1024 * 1024
MANIFEST_ASSET_NAME = "manifest.json"

NEW_VERSION_EXIT_CODE = 10


def fetch_manifest(url: str) -> dict:
    """Download and parse the manifest JSON."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def validate_manifest(manifest: dict) -> tuple[str, dict]:
    """Validate manifest shape and return (version, platforms)."""
    version = manifest.get("version")
    if not isinstance(version, str) or not re.fullmatch(r"[0-9A-Za-z.+-]+", version):
        raise ValueError(f"Manifest has an invalid version: {version!r}")

    platforms = manifest.get("platforms")
    if not isinstance(platforms, dict) or not platforms:
        raise ValueError("Manifest has no platforms")

    for name, target in platforms.items():
        if not isinstance(target, dict):
            raise ValueError(f"Platform {name!r} is not an object")
        url = target.get("url")
        sha256 = target.get("sha256")
        if not isinstance(url, str) or not url.startswith("https://"):
            raise ValueError(f"Platform {name!r} has an invalid url: {url!r}")
        if not isinstance(sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", sha256):
            raise ValueError(f"Platform {name!r} has an invalid sha256: {sha256!r}")

    return version, platforms


def get_release_asset_names(tag: str) -> set[str] | None:
    """Return the asset names of an existing release, or None if it doesn't exist."""
    result = subprocess.run(
        ["gh", "release", "view", tag, "--json", "assets", "--jq", ".assets[].name"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def plan_filenames(platforms: dict) -> dict[str, str]:
    """Map each unique binary URL to a validated, collision-free filename.

    Multiple platform keys can point at the same file; each unique URL appears
    once. Raises on unsafe filenames or distinct URLs that share a filename.
    """
    expected_by_url: dict[str, str] = {}
    for name, target in platforms.items():
        url = target["url"]
        sha256 = target["sha256"]
        existing = expected_by_url.get(url)
        if existing is not None and existing != sha256:
            raise ValueError(
                f"Conflicting sha256 for {url}: {existing} vs {sha256} (platform {name})"
            )
        expected_by_url[url] = sha256

    filename_by_url: dict[str, str] = {}
    seen: dict[str, str] = {}
    for url in sorted(expected_by_url):
        filename = url.rsplit("/", 1)[-1]
        if not filename or "/" in filename or filename in {".", ".."}:
            raise ValueError(f"Refusing to use unsafe asset filename from {url}")
        if filename == MANIFEST_ASSET_NAME:
            raise ValueError(f"Asset filename collides with manifest asset: {url}")
        # Distinct URLs sharing a filename would overwrite each other on disk and
        # ship a duplicate binary, so reject them outright.
        if filename in seen:
            raise ValueError(
                f"Asset filename collision for {filename!r}: {seen[filename]} and {url}"
            )
        seen[filename] = url
        filename_by_url[url] = filename
    return filename_by_url


def expected_asset_names(platforms: dict) -> set[str]:
    """Names of every asset a complete release should contain."""
    return set(plan_filenames(platforms).values()) | {MANIFEST_ASSET_NAME}


def download(url: str, dest: Path) -> str:
    """Download url to dest, returning the hex sha256 of the content."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    digest = hashlib.sha256()
    with urllib.request.urlopen(req, timeout=120) as response, open(dest, "wb") as out:
        while True:
            chunk = response.read(DOWNLOAD_CHUNK)
            if not chunk:
                break
            digest.update(chunk)
            out.write(chunk)
    return digest.hexdigest()


def download_assets(platforms: dict, work_dir: Path) -> list[Path]:
    """Download every unique binary, verifying sha256. Returns asset paths."""
    filename_by_url = plan_filenames(platforms)
    sha_by_url = {target["url"]: target["sha256"] for target in platforms.values()}

    assets: list[Path] = []
    for url, filename in sorted(filename_by_url.items()):
        dest = work_dir / filename
        expected_sha = sha_by_url[url]
        print(f"Downloading {url}", flush=True)
        actual_sha = download(url, dest)
        if actual_sha != expected_sha:
            raise ValueError(
                f"sha256 mismatch for {url}: expected {expected_sha}, got {actual_sha}"
            )
        print(f"  verified sha256 {actual_sha}", flush=True)
        assets.append(dest)

    return assets


def build_release_notes(version: str, platforms: dict) -> str:
    """Build markdown release notes listing each platform and its checksum."""
    lines = [
        f"Devin CLI `{version}`.",
        "",
        "Published from "
        "[`static.devin.ai/cli/current/manifest.json`](https://static.devin.ai/cli/current/manifest.json).",
        "",
        "| Platform | sha256 |",
        "| --- | --- |",
    ]
    for name in sorted(platforms):
        lines.append(f"| `{name}` | `{platforms[name]['sha256']}` |")
    lines.append("")
    return "\n".join(lines)


def create_release(tag: str, version: str, notes: str) -> None:
    """Create an (empty) GitHub release via the gh CLI."""
    subprocess.run(
        ["gh", "release", "create", tag, "--title", version, "--notes", notes],
        check=True,
    )


def upload_assets(tag: str, assets: list[Path]) -> None:
    """Upload (clobbering) assets to an existing release via the gh CLI."""
    cmd = ["gh", "release", "upload", tag, "--clobber"]
    cmd.extend(str(asset) for asset in assets)
    subprocess.run(cmd, check=True)


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
    parser.add_argument(
        "--work-dir",
        default="dist",
        help="Directory to download binaries into.",
    )
    args = parser.parse_args()

    try:
        manifest = fetch_manifest(args.manifest_url)
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: could not fetch manifest: {exc}", file=sys.stderr)
        return 1

    try:
        version, platforms = validate_manifest(manifest)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    tag = version
    print(f"Manifest version: {version}")

    try:
        expected_names = expected_asset_names(platforms)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    existing_names = get_release_asset_names(tag)
    if existing_names is not None and expected_names <= existing_names:
        print(f"Release {tag} already exists with all expected assets; nothing to do.")
        return 0

    if existing_names is None:
        print(f"Release {tag} does not exist yet.")
    else:
        missing = sorted(expected_names - existing_names)
        print(f"Release {tag} exists but is missing assets: {', '.join(missing)}")

    if args.check:
        return NEW_VERSION_EXIT_CODE

    work_dir = Path(args.work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    try:
        assets = download_assets(platforms, work_dir)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        print(f"ERROR: failed to download assets: {exc}", file=sys.stderr)
        return 1

    manifest_asset = work_dir / MANIFEST_ASSET_NAME
    manifest_asset.write_text(json.dumps(manifest, indent=2) + "\n")
    assets.append(manifest_asset)

    # Create the release first if needed, then upload assets with --clobber. This
    # is idempotent: a run that died mid-upload (leaving a partial release) is
    # completed by the next run instead of being skipped.
    if existing_names is None:
        notes = build_release_notes(version, platforms)
        print(f"Creating release {tag}...")
        create_release(tag, version, notes)

    print(f"Uploading {len(assets)} assets to release {tag}...")
    upload_assets(tag, assets)
    print(f"Release {tag} is complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
