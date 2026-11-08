# Roadmap agent

Unattended Claude Code runs that implement `docs/roadmap-*.md` items and open PRs against `develop`.
Runs Mon-Fri at 01:00 (an otherwise unused 5h usage window) on the Raspberry Pi.

## How a run works (`run.sh`)

1. Fetches `origin` and lists `docs/roadmap-*.md` on `origin/develop`.
2. Picks the next roadmap after the last one used (round-robin), skipping roadmaps with no `- [ ]` items under `## Roadmap` or with an open PR from `roadmap/<name>/*`.
3. Creates a detached worktree from `origin/develop` and runs `claude -p` (Opus, max effort) with `prompt.md`. Claude follows `AGENT.md`: picks one item, creates `roadmap/<name>/<slug>`, implements, validates, commits and moves the item to `## Completed`.
4. Checks the roadmap was only changed by moving one item verbatim; otherwise the PR is opened as **draft** with warnings.
5. Pushes, opens the PR with `gh` and replaces `PR: pending` with the PR number.

The orchestrator never merges or approves. Claude can't `git push` or use `gh` (denied tools).

## Files

| File | Purpose |
|---|---|
| `AGENT.md` | Shared rules for the agent (developers edit this, roadmaps only hold items) |
| `prompt.md` | Prompt template (`{{ROADMAP}}`, `{{BASE_REF}}`, `{{BRANCH_PREFIX}}`, `{{RUN_DIR}}`) |
| `run.sh` | Orchestrator |
| `systemd/` | User service + timer templates |
| `install.sh` | Installs/updates the timer for this checkout |

## Setup

```bash
gh auth login              # HTTPS, and authenticate git with gh credentials
tools/roadmap-agent/install.sh
```

Requires `claude` logged in, `gh`, `jq`, a `develop` branch on `origin` and user lingering (`loginctl enable-linger`).

## Operating

```bash
systemctl --user list-timers roadmap-agent.timer      # next runs
ROADMAP_AGENT_DRY_RUN=1 tools/roadmap-agent/run.sh     # which roadmap would be picked
systemctl --user start --no-block roadmap-agent        # run now
journalctl --user -u roadmap-agent -f                  # follow logs
ls ~/.local/state/roadmap-agent/runs/                  # per-run logs, Claude output, PR body
systemctl --user disable --now roadmap-agent.timer     # stop scheduling
```

Settings can be overridden in `~/.config/roadmap-agent.env`: `ROADMAP_AGENT_MODEL`, `ROADMAP_AGENT_EFFORT`, `ROADMAP_AGENT_TIMEOUT`, `ROADMAP_AGENT_BASE`, `ROADMAP_AGENT_REMOTE`.
Schedule changes go in `systemd/roadmap-agent.timer` followed by `install.sh`.

Recommended: protect `main` and `develop` on GitHub so PRs need a human review.
