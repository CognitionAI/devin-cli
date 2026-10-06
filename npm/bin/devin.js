#!/usr/bin/env node
// Launcher for the Devin CLI npm package. The native binary ships in a
// platform-specific optional dependency; this script finds it and runs it.

"use strict";

const { spawn } = require("child_process");
const path = require("path");

const PLATFORMS = new Set([
  "darwin-arm64",
  "darwin-x64",
  "linux-arm64",
  "linux-x64",
  "win32-arm64",
  "win32-x64",
]);

function fail(message) {
  console.error(`devin: ${message}`);
  console.error("See https://docs.devin.ai/cli for other ways to install the Devin CLI.");
  process.exit(1);
}

const platform = `${process.platform}-${process.arch}`;
if (!PLATFORMS.has(platform)) {
  fail(`unsupported platform ${platform}.`);
}

const packageName = `devin-${platform}`;
let packageDir;
try {
  packageDir = path.dirname(require.resolve(`${packageName}/package.json`));
} catch {
  fail(
    `the ${packageName} package is not installed. It is an optional dependency of devin; ` +
      "reinstall without --omit=optional / --no-optional.",
  );
}

const binary = path.join(packageDir, "bin", process.platform === "win32" ? "devin.exe" : "devin");

const child = spawn(binary, process.argv.slice(2), { stdio: "inherit" });

child.on("error", (error) => {
  fail(`failed to start ${binary}: ${error.message}`);
});

// Signals sent to the launcher alone (e.g. `kill <pid>`) must reach the CLI.
for (const signal of ["SIGINT", "SIGTERM", "SIGHUP"]) {
  process.on(signal, () => {
    if (!child.killed) {
      try {
        child.kill(signal);
      } catch {
        // The child already exited.
      }
    }
  });
}

child.on("exit", (code, signal) => {
  if (signal) {
    // Die from the same signal so the parent shell sees the real cause.
    process.removeAllListeners(signal);
    process.kill(process.pid, signal);
  } else {
    process.exit(code ?? 1);
  }
});
