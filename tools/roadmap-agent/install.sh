#!/usr/bin/env bash
# Installs the roadmap agent as a systemd user timer pointing at this checkout.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"

mkdir -p "$UNIT_DIR"
sed "s|@REPO_DIR@|$REPO_DIR|g" "$SCRIPT_DIR/systemd/roadmap-agent.service" > "$UNIT_DIR/roadmap-agent.service"
cp "$SCRIPT_DIR/systemd/roadmap-agent.timer" "$UNIT_DIR/roadmap-agent.timer"
chmod +x "$SCRIPT_DIR/run.sh"

systemctl --user daemon-reload
systemctl --user enable --now roadmap-agent.timer

[[ "$(loginctl show-user "$USER" -p Linger --value)" == yes ]] \
  || echo "WARNING: lingering is disabled, run: sudo loginctl enable-linger $USER"

systemctl --user list-timers roadmap-agent.timer
