# devin-cli

Try Devin CLI: https://docs.devin.ai/cli

## Install with npm

```sh
npm install -g devin
```

`scripts/publish_npm.py` (run hourly by `.github/workflows/publish-npm.yml`)
repackages each new stable release from `static.devin.ai` into the `devin` npm
package. The launcher lives in `npm/`; the native binary for each platform is
published as `devin@<version>-<os>-<cpu>` and pulled in as an optional
dependency.
