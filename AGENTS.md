# AGENTS.md

Instructions for AI coding agents (Claude Code, Codex, Copilot, Cursor...) and for
humans contributing to this repository.

## Language: English only

Everything that is written into the repository or its GitHub history must be in
**English**, whatever language the conversation with the agent or the issue uses:

- Source code: identifiers, comments, log messages, error messages and any text
  shown to users (frontend, API responses, TUI of the model lab).
- Documentation: READMEs, `docs/`, roadmap items, code examples.
- Configuration and scripts: comments in YAML, Containerfiles, shell, PowerShell,
  Makefiles, SQL migrations, CI workflows.
- Git and GitHub: branch names, commit messages, pull request titles and
  descriptions, review comments, issues.
- Data written by migrations or seed scripts (names, descriptions).

Before committing, check the diff for Spanish (accents, `ñ`, `¿`, `¡` and common
words are a quick signal). Translate text you touch, even if it was not yours.

Exceptions, kept on purpose:

- Proper nouns (place names such as `Albufera de Valencia`, `Serrania de Cuenca`).
- Applied Flyway migrations (`server/src/main/resources/db/migration/V*__*.sql`)
  are immutable: editing them, even a comment, changes their checksum and breaks
  startup in every environment. Fix their content with a new migration instead.

## Git conventions

- Commit messages and PR titles: `type(scope): description`
  (`feat`, `fix`, `doc`, `refactor`, `test`, `ci`, `chore`...), imperative mood.
- Work on a branch and open pull requests against `develop`; `main` is
  updated by the weekly release merge.
- Never commit secrets or environment files (`.env`).

## Project map

| Path | What |
|---|---|
| `server/` | Spring Boot 3 backend (Java 21, Maven, Flyway, MySQL) |
| `frontend/` | Vanilla JS/HTML/CSS served by nginx; calls `/api/*` on the same origin |
| `fractal_model_lab/` | C/ncurses TUI, follows 42's Norminette (see its README) |
| `data/` | CSV sources and the synthetic SQL generator |
| `tools/ci/`, `.github/workflows/` | Validation, image builds, deploy and PR previews |
| `podman-compose.yml`, `Caddyfile` | Production stack on the Raspberry Pi |
