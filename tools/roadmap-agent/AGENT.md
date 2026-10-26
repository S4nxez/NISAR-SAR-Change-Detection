# Roadmap Agent Rules

Shared rules for the unattended agent that implements roadmap items from `docs/roadmap-*.md`.
Roadmap files only contain the items (plus optional roadmap-specific context); everything common lives here.

## Item format

```
- [ ] - <impact 0-10> **[Short task title]** — Desired outcome and relevant scope.
```

## Choosing the item

- Implement **exactly one roadmap item per run / pull request**, following logical dependency order rather than the order in which items are listed.
- Before starting, inspect the current codebase, infrastructure and the remaining items of the roadmap to identify dependencies, blockers and prerequisites.
- Prioritize foundational work before dependent features (e.g. create a resource before implementing functionality that uses it).
- Among items that are ready to implement, prioritize by impact, reliability, security and operational value.
- If an item depends on unfinished work, skip it and select the next highest-priority item whose dependencies are satisfied.
- If an item is ambiguous, investigate the project and make reasonable decisions consistent with its architecture. Nobody will answer questions during the run: if a significant decision cannot be made safely, do not implement that item.
- If no item is actionable, stop and report `BLOCKED` (see *Run outputs*).

## Implementing

- Do not bundle unrelated items or silently expand the scope.
- Follow existing project conventions and minimize unnecessary changes. Do not rewrite unrelated code or infrastructure.
- Preserve existing functionality unless the item explicitly requires changing it.
- Keep changes focused, maintainable and consistent with the current architecture.
- Never commit secrets, credentials or environment-specific sensitive data (e.g. `.env`).
- Do not introduce new infrastructure, dependencies or services unless required by the item or explicitly justified in the PR.
- Include any necessary tests and documentation in the same change.
- Run the relevant tests, builds and validation checks. Never mark an item as complete unless its implementation and relevant validation have succeeded. If something cannot be validated on this machine, say so explicitly in the PR body.

## Machine safety

This runs on the Raspberry Pi that **also serves production**.

- Never deploy, stop, restart, remove or modify running containers, pods, volumes, networks, systemd services, Caddy or Tailscale on this machine.
- If you need to start something for validation, use unique names and free ports, and clean it up before finishing.
- Never touch files outside the working directory and the run directory given in the prompt.

## Editing the roadmap

Roadmaps are owned by the developers. The **only** change allowed in a roadmap file is moving the implemented item to `## Completed`:

1. Remove the item line from `## Roadmap`.
2. Add it under `## Completed` **verbatim**, only changing `- [ ]` to `- [x]` and appending ` — PR: pending` (the orchestrator replaces `pending` with the PR number).

Never reword, reorder, add, split or delete other items, and never edit other sections or other roadmap files. Do not modify `tools/roadmap-agent/`.
Blockers, notes and follow-up suggestions go in the PR body, not in the roadmap.

## Git

- Create your branch before committing: `git switch -c <branch prefix given in the prompt><short-kebab-slug>`.
- Commit messages follow the repo convention: `type(scope): description` (`feat`, `fix`, `doc`, `refactor`, `test`, `ci`, ...).
- Commit everything (implementation, tests, docs and the roadmap move). Leave the working tree clean.
- Do **not** push, use `gh`, open/merge/approve PRs, or touch other branches: the orchestrator handles that.

## Run outputs

Write these files in the run directory given in the prompt:

- `status`: first line `DONE` or `BLOCKED: <reason>`.
- `pr-title.txt` (only if `DONE`): one line, same convention as commit messages.
- `pr-body.md` (only if `DONE`): what item was implemented and why it was chosen, summary of changes, how it was validated (commands + results), anything not validated, risks and follow-ups.
