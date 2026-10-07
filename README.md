# devin-cli

Release automation for [Devin CLI](https://docs.devin.ai/cli). The README that
npm shows for the `devin` package is [`npm/README.md`](npm/README.md); the demo
gif it embeds is `assets/devin-cli.gif`.

## Install with npm

```sh
npm install -g devin
```

`scripts/publish_npm.py` (run hourly by `.github/workflows/publish-npm.yml`)
repackages each new stable release from `static.devin.ai` into the `devin` npm
package. The launcher lives in `npm/`; the native binary for each platform is
published as `devin@<version>-<os>-<cpu>` and pulled in as an optional
dependency. The workflow authenticates with
[npm trusted publishing](https://docs.npmjs.com/trusted-publishers) (OIDC): the
`devin` package on npmjs.com must list `CognitionAI/devin-cli` and
`publish-npm.yml` as a trusted publisher; no token is stored in the repository.
