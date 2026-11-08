#!/usr/bin/env python3
"""Preview or permanently unpublish a yanked Stable CLI version."""

import argparse
import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.request

from publish_npm import DEFAULT_REGISTRY, MANIFEST_URL, PACKAGE_NAME, PLATFORMS

REGISTRY_PACKAGE = f"{DEFAULT_REGISTRY}{PACKAGE_NAME}"
YANK_MARKER = "https://cognition-public.s3.amazonaws.com/cli/{version}/.yanked"


def request(url: str, method: str = "GET"):
    req = urllib.request.Request(url, method=method, headers={"Cache-Control": "no-cache"})
    return urllib.request.urlopen(req, timeout=15)


def get_json(url: str) -> dict:
    with request(url) as response:
        return json.load(response)


def planned_versions(version: str) -> tuple[str, ...]:
    if not re.fullmatch(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)", version):
        raise ValueError("Expected one exact Stable version in X.Y.Z format.")
    return (version, *(f"{version}-{os_name}-{cpu}" for os_name, cpu in sorted(set(PLATFORMS.values()))))


def preflight(version: str, targets: tuple[str, ...]) -> list[str]:
    if get_json(MANIFEST_URL)["version"] == version:
        raise ValueError("Refusing to unpublish the current Stable release.")
    if get_json(YANK_MARKER.format(version=version)).get("yanked") is not True:
        raise ValueError("The Stable release must be yanked before unpublishing.")
    packument = get_json(REGISTRY_PACKAGE)
    active_tags = sorted(tag for tag, target in packument["dist-tags"].items() if target in targets)
    if active_tags:
        raise ValueError(f"Refusing to unpublish versions still referenced by npm tags: {', '.join(active_tags)}.")
    return [target for target in targets if target in packument["versions"]]


def tarball_gone(version: str) -> bool:
    tarball = f"{REGISTRY_PACKAGE}/-/{PACKAGE_NAME}-{version}.tgz"
    try:
        with request(tarball, "HEAD"):
            return False
    except urllib.error.HTTPError as exc:
        if exc.code in (404, 410):
            return True
        raise


def verify(targets: tuple[str, ...]) -> None:
    for attempt in range(7):
        published = get_json(REGISTRY_PACKAGE)["versions"]
        remaining = [target for target in targets if target in published or not tarball_gone(target)]
        if not remaining:
            print("Verified: all target versions and tarballs are absent.")
            return
        if attempt < 6:
            time.sleep(10)
    raise ValueError(f"Still publicly reachable: {', '.join(remaining)}.")


def unpublish(version: str, execute: bool) -> None:
    targets = planned_versions(version)
    present = preflight(version, targets)
    for target in targets:
        print(f"{PACKAGE_NAME}@{target}: {'would unpublish' if target in present else 'not listed'}", flush=True)
    if not execute:
        return
    if present and not os.environ.get("NODE_AUTH_TOKEN"):
        raise ValueError("The npm-unpublish environment needs NPM_UNPUBLISH_TOKEN.")
    for target in present:
        subprocess.run(
            ["npm", "unpublish", f"{PACKAGE_NAME}@{target}", f"--registry={DEFAULT_REGISTRY}", "--force=false"],
            check=True,
        )
    verify(targets)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    try:
        unpublish(args.version, args.execute)
    except (KeyError, OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"npm unpublish did not complete: {exc}\n")


if __name__ == "__main__":
    main()
