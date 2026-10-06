#!/usr/bin/env python3
"""Publish the Devin CLI to npm from the published manifest.

Reads the stable manifest and, if its version is not on npm yet, repackages the
release archives from static.devin.ai as npm packages:

  * devin@<version>-<os>-<cpu>   one per platform, containing the native bundle
  * devin@<version>              launcher (npm/bin/devin.js) whose
                                 optionalDependencies alias the platform
                                 versions above, so npm installs only the one
                                 matching the user's os/cpu

Every archive is verified against the manifest's sha256 before packaging. The
script is idempotent: versions already on the registry are skipped, so a failed
run can simply be retried.

Usage:
    # Build the package directories and tarballs only (no registry writes)
    python scripts/publish_npm.py --no-publish --out dist

    # Publish whatever is missing for the current manifest version
    python scripts/publish_npm.py

Environment variables:
    NODE_AUTH_TOKEN: npm token, read by the .npmrc that actions/setup-node writes.
"""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

MANIFEST_URL = "https://static.devin.ai/cli/current/manifest.json"
DEFAULT_REGISTRY = "https://registry.npmjs.org/"
PACKAGE_NAME = "devin"
USER_AGENT = "devin-cli-release-bot/1.0"
REPO_ROOT = Path(__file__).resolve().parent.parent
LAUNCHER_DIR = REPO_ROOT / "npm"

# Manifest platform key -> (npm os, npm cpu). The manifest also lists legacy
# aliases (e.g. x86_64-unknown-linux-musl) that point at these same archives.
PLATFORMS = {
    "aarch64-apple-darwin": ("darwin", "arm64"),
    "x86_64-apple-darwin": ("darwin", "x64"),
    "aarch64-unknown-linux": ("linux", "arm64"),
    "x86_64-unknown-linux": ("linux", "x64"),
    "aarch64-pc-windows": ("win32", "arm64"),
    "x86_64-pc-windows": ("win32", "x64"),
}

# Written next to bin/ so the CLI knows npm manages this install and does not
# try to update itself.
DISTRIBUTION_MARKER = "npm"

COMMON_PACKAGE_FIELDS = {
    "description": "Devin for Terminal",
    "homepage": "https://docs.devin.ai/cli",
    "license": "SEE LICENSE IN https://cognition.ai/terms-of-service",
    "repository": {"type": "git", "url": "git+https://github.com/CognitionAI/devin-cli.git"},
}


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=300) as response:
        return response.read()


# Semantic version with an optional prerelease (e.g. 2026.5.26-7) and no build
# metadata, which npm strips. Platform packages append "-<os>-<cpu>" to it.
SEMVER_RE = re.compile(
    r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(-(0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)(\.(0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*))*)?"
)


def get_version(manifest: dict) -> str:
    """Extract the version and check that npm will accept it."""
    version = manifest.get("version")
    if not isinstance(version, str) or not SEMVER_RE.fullmatch(version):
        raise ValueError(f"Manifest version is not a valid npm version: {version!r}")
    return version


def published_versions(registry: str) -> set[str]:
    """Return every version of the package already on the registry."""
    url = urllib.parse.urljoin(registry, PACKAGE_NAME)
    try:
        packument = json.loads(fetch(url))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return set()
        raise
    return set(packument.get("versions", {}))


def safe_extract(archive: Path, dest: Path) -> None:
    """Extract a release archive, refusing entries that would escape dest."""
    dest_root = dest.resolve()

    def check(name: str) -> None:
        if not (dest_root / name).resolve().is_relative_to(dest_root):
            raise ValueError(f"Archive entry escapes the package directory: {name}")

    if archive.name.endswith(".zip"):
        with zipfile.ZipFile(archive) as zf:
            for name in zf.namelist():
                check(name)
            zf.extractall(dest)
    else:
        with tarfile.open(archive) as tf:
            for member in tf.getmembers():
                check(member.name)
                if not (member.isfile() or member.isdir()):
                    raise ValueError(f"Unexpected archive entry type: {member.name}")
            tf.extractall(dest, filter="data")


def build_platform_package(version: str, npm_os: str, cpu: str, entry: dict, out: Path) -> Path:
    """Download, verify and unpack one platform's archive into an npm package directory."""
    url, expected = entry["url"], entry["sha256"]
    pkg_dir = out / f"{npm_os}-{cpu}"
    if pkg_dir.exists():
        shutil.rmtree(pkg_dir)
    pkg_dir.mkdir(parents=True)

    print(f"  downloading {url}")
    data = fetch(url)
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected:
        raise ValueError(f"sha256 mismatch for {url}: expected {expected}, got {actual}")

    archive = out / url.rsplit("/", 1)[-1]
    archive.write_bytes(data)
    safe_extract(archive, pkg_dir)
    archive.unlink()

    binary = pkg_dir / "bin" / ("devin.exe" if npm_os == "win32" else "devin")
    if not binary.is_file():
        raise ValueError(f"Archive for {npm_os}-{cpu} has no {binary.relative_to(pkg_dir)}")
    binary.chmod(0o755)

    (pkg_dir / "distribution").write_text(DISTRIBUTION_MARKER)
    package_json = {
        "name": PACKAGE_NAME,
        "version": f"{version}-{npm_os}-{cpu}",
        **COMMON_PACKAGE_FIELDS,
        "os": [npm_os],
        "cpu": [cpu],
    }
    (pkg_dir / "package.json").write_text(json.dumps(package_json, indent=2) + "\n")
    return pkg_dir


def build_launcher_package(version: str, out: Path) -> Path:
    """Assemble the launcher package that depends on every platform version."""
    pkg_dir = out / "launcher"
    if pkg_dir.exists():
        shutil.rmtree(pkg_dir)
    shutil.copytree(LAUNCHER_DIR, pkg_dir)
    package_json = {
        "name": PACKAGE_NAME,
        "version": version,
        **COMMON_PACKAGE_FIELDS,
        "bin": {"devin": "bin/devin.js"},
        "files": ["bin"],
        "engines": {"node": ">=16"},
        "optionalDependencies": {
            f"{PACKAGE_NAME}-{npm_os}-{cpu}": f"npm:{PACKAGE_NAME}@{version}-{npm_os}-{cpu}"
            for npm_os, cpu in PLATFORMS.values()
        },
    }
    (pkg_dir / "package.json").write_text(json.dumps(package_json, indent=2) + "\n")
    return pkg_dir


def npm(args: list[str], cwd: Path) -> None:
    subprocess.run(["npm", *args], cwd=cwd, check=True)


def release(pkg_dir: Path, tag: str, registry: str, publish: bool, provenance: bool) -> None:
    """Publish a package directory under a dist-tag, or just pack it."""
    if not publish:
        npm(["pack", "--pack-destination", str(pkg_dir.parent)], cwd=pkg_dir)
        return
    args = ["publish", "--access", "public", "--tag", tag, "--registry", registry]
    if provenance:
        args.append("--provenance")
    npm(args, cwd=pkg_dir)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest-url", default=MANIFEST_URL, help="Override the manifest URL (for testing).")
    parser.add_argument("--registry", default=DEFAULT_REGISTRY, help="npm registry to check and publish to.")
    parser.add_argument("--out", default="dist", type=Path, help="Directory to build packages in.")
    parser.add_argument("--no-publish", action="store_true", help="Build and `npm pack` every package; never publish.")
    parser.add_argument("--provenance", action="store_true", help="Publish with npm provenance (GitHub Actions only).")
    args = parser.parse_args()
    registry = args.registry.rstrip("/") + "/"
    publish = not args.no_publish

    try:
        manifest = json.loads(fetch(args.manifest_url))
        version = get_version(manifest)
        existing = published_versions(registry) if publish else set()
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Manifest version: {version}")
    if version in existing:
        print(f"{PACKAGE_NAME}@{version} is already published; nothing to do.")
        return 0

    missing = [key for key in PLATFORMS if key not in manifest.get("platforms", {})]
    if missing:
        print(f"ERROR: manifest is missing platforms: {', '.join(missing)}", file=sys.stderr)
        return 1

    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)

    # Platform versions go first: the launcher must never be installable before
    # the binaries it depends on exist.
    for key, (npm_os, cpu) in PLATFORMS.items():
        platform_version = f"{version}-{npm_os}-{cpu}"
        if platform_version in existing:
            print(f"{PACKAGE_NAME}@{platform_version} is already published; skipping.")
            continue
        print(f"Building {PACKAGE_NAME}@{platform_version}")
        pkg_dir = build_platform_package(version, npm_os, cpu, manifest["platforms"][key], out)
        # A per-platform dist-tag keeps these versions off `latest`.
        release(pkg_dir, f"{npm_os}-{cpu}", registry, publish, args.provenance)
        if publish:
            shutil.rmtree(pkg_dir)

    print(f"Building {PACKAGE_NAME}@{version}")
    release(build_launcher_package(version, out), "latest", registry, publish, args.provenance)
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
