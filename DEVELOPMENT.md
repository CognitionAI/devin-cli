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

### Unpublish a yanked release

Unpublishing is permanent and separate from yanking the CDN and container
artifacts. In Actions, run **Unpublish a yanked npm release** on `main` with the
exact Stable version (for example, `3000.12.1`). Leave **execute** off for a
read-only preview. With it on, review the preview before approving the
`npm-unpublish` environment deployment.

Before enabling execution, a repository admin must configure the
[`npm-unpublish` environment](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments)
to allow only `main`, require release-owner reviewers, prevent self-review,
and disallow bypassing protection rules. Set `NPM_UNPUBLISH_TOKEN` as an
**environment secret**, not a repository or organization secret. npm trusted
publishing cannot unpublish. For an approved removal, an npm maintainer can
provide a short-lived [granular token](https://docs.npmjs.com/about-access-tokens/)
with write access limited to `devin`, if the package's npm settings permit it.
Remove the secret and revoke the token after use. Do not relax npm's package
security settings to run this workflow.

The job refuses the current Stable version or any version with an active npm
dist-tag. It removes the launcher first, then the platform variants, and checks
that the original tarball URLs no longer respond. A partial run can be retried
with the same version. If npm blocks removal under its
[unpublish policy](https://docs.npmjs.com/policies/unpublish/), contact npm
Support; deprecation does not remove the tarballs.

## GitHub releases

`scripts/release_from_manifest.py` (run hourly by
`.github/workflows/release-from-manifest.yml`) creates a GitHub release for
each new manifest version.

## Demo gif

`assets/devin-cli.gif` is a [vhs](https://github.com/charmbracelet/vhs)
recording of the stable binary; re-record it when the UI changes noticeably.
