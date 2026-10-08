# Development

This repository holds the release automation for Devin CLI, not the CLI
source. The root `README.md` doubles as the npm package page for `devin`.

## npm publishing

`scripts/publish_npm.py` (run hourly by `.github/workflows/publish-npm.yml`)
reads the stable release manifest at
`https://static.devin.ai/cli/current/manifest.json` and, if that version is
not on npm yet, publishes:

- `devin@<version>-<os>-<cpu>` for each of the six platforms, containing the
  native binary extracted from the release archive after its SHA-256 is
  checked against the manifest. Published first, under per-platform dist-tags.
- `devin@<version>`: the launcher in `npm/` (`bin/devin.js`) plus the root
  `README.md`, with the platform packages as `optionalDependencies` via npm
  aliases. Published last, under `latest`.

Only the version currently in the manifest is published; there is no
historical backfill. Runs are idempotent, so a failed run can be retried.

Build everything locally without publishing:

```sh
python3 scripts/publish_npm.py --no-publish --out dist
```

### Authentication

The workflow uses [npm trusted publishing](https://docs.npmjs.com/trusted-publishers)
(OIDC): `id-token: write` plus npm >= 11.5.1, no token stored anywhere. The
`devin` package on npmjs.com must list GitHub owner `CognitionAI`, repository
`devin-cli`, workflow `publish-npm.yml` (no environment) as its trusted
publisher.

## Tests

With Python and npm on `PATH`, run the packaging tests without publishing:

```sh
python -m unittest discover -s tests -v
```

## GitHub releases

`scripts/release_from_manifest.py` (run hourly by
`.github/workflows/release-from-manifest.yml`) creates a GitHub release for
each new manifest version.

## Demo gif

`assets/devin-cli.gif` is a [vhs](https://github.com/charmbracelet/vhs)
recording of the stable binary; re-record it when the UI changes noticeably.
