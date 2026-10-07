<p align="center">
  <strong>Devin CLI</strong><br/>
  The AI software engineer in your terminal, with every frontier model.
</p>

<p align="center">
  <a href="https://docs.devin.ai/cli">Docs</a> ·
  <a href="https://devin.ai/cli">Website</a> ·
  <a href="https://docs.devin.ai/cli/essential-commands">Essential commands</a> ·
  <a href="https://docs.devin.ai/cli/changelog/stable">Changelog</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/CognitionAI/devin-cli/main/assets/devin-cli.gif" alt="Devin CLI answering a question about a repository, then switching models with /model" width="100%" />
</p>

## Install

```sh
npm install -g devin
```

Then open a project and start a session:

```sh
cd my-project
devin
```

Sign in with your Devin account when prompted. Devin CLI is also available
through the [install script, Homebrew, and a Windows
installer](https://docs.devin.ai/cli).

## Why Devin CLI

- **Runs on your machine.** Your repo, your shell, your credentials.
- **Hand off to the cloud.** `/handoff` moves the session to Devin Cloud; close
  your laptop and come back to a PR.
- **Every frontier model.** Anthropic, OpenAI, Google, Cognition, and
  open-weight models, switchable mid-session with `/model`.
- **Fusion.** A frontier lead model makes the decisions while a cheaper sidekick
  does the legwork, so you pay frontier prices only where they matter.
  [How Fusion works →](https://cognition.ai/blog/fusion-in-devin-cli)
- **Built in Rust.** Installs in under a minute, starts instantly.
- **Bring your setup.** `AGENTS.md` rules, MCP servers, skills, hooks, and
  Claude Code plugins work as-is.

## Essential commands

| Command     | What it does                                              |
| ----------- | --------------------------------------------------------- |
| `/model`    | Pick any model, effort level, or Fusion pairing           |
| `/plan`     | Agree on the approach before any edits                    |
| `/ask`      | Read-only mode for exploring a codebase                   |
| `/loop`     | Implement, then auto-review the diff until it's right     |
| `/handoff`  | Continue the task in Devin Cloud                          |
| `/fork`     | Branch the session from any step                          |
| `/revert`   | Roll files and conversation back to a step                |
| `/resume`   | Pick up any previous session                              |
| `/compact`  | Compress context without losing the thread                |
| `devin -p`  | Single-turn mode for scripts and CI                       |

Full list: [Command reference](https://docs.devin.ai/cli/reference/commands) ·
[Keyboard shortcuts](https://docs.devin.ai/cli/reference/keyboard-shortcuts)

## Works with

- **Your editor.** Runs as an ACP agent inside
  [Zed](https://docs.devin.ai/cli/acp/zed),
  [JetBrains](https://docs.devin.ai/cli/acp/jetbrains), and
  [Xcode](https://docs.devin.ai/cli/acp/xcode).
- **Your tools.** [MCP servers](https://docs.devin.ai/cli/extensibility/mcp/overview),
  [skills](https://docs.devin.ai/cli/extensibility/skills/overview),
  [hooks](https://docs.devin.ai/cli/extensibility/hooks/overview), and
  [plugins](https://docs.devin.ai/cli/extensibility/plugins/overview).
- **Your team.** [Enterprise controls](https://docs.devin.ai/cli/enterprise/controls)
  and [team settings](https://docs.devin.ai/cli/enterprise/team-settings),
  plus an optional [sandbox](https://docs.devin.ai/cli/sandbox) for
  autonomous runs.

## Learn more

- [Quickstart](https://docs.devin.ai/cli)
- [Models](https://docs.devin.ai/cli/models) and
  [Fusion](https://docs.devin.ai/cli/fusion)
- [Devin Cloud from the terminal](https://docs.devin.ai/cli/cloud) and
  [SSH into a cloud session](https://docs.devin.ai/cli/ssh)
- [Subagents](https://docs.devin.ai/cli/subagents)
- [Configuration](https://docs.devin.ai/cli/reference/configuration/config-file)
  and [permissions](https://docs.devin.ai/cli/reference/permissions)
- [Troubleshooting](https://docs.devin.ai/cli/troubleshooting)

## About this package

Supported platforms: macOS, Linux, and Windows on x64 and arm64. The package
contains a small Node launcher; the native binary for your platform is pulled
from the npm registry as an optional dependency, so nothing is downloaded from
outside the registry at install time and it works behind npm registry mirrors.

To update:

```sh
npm install -g devin@latest
```
