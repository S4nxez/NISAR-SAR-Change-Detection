# AGENTS.md

Instructions for AI coding agents (Claude Code, Codex, Copilot, Cursor...) and for
humans contributing to this repository.

## Language: English only

Everything that is written into the repository or its GitHub history must be in
**English**, whatever language the conversation with the agent or the issue uses:

- Source code: identifiers, comments, log messages, error messages and any text
  shown to users (frontend, API responses, TUI of the model lab), tests and their
  names.
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

## Tests: every code change ships with its unit tests

When you add or change code that can be tested, add or update its unit tests in the
same pull request (and preferably the same commit). A change without them is not
finished:

- New behaviour comes with tests of that behaviour, including its edge and error
  cases (empty input, missing data, invalid user input, failing network calls).
- A bug fix comes with a test that fails without the fix.
- Refactoring keeps the existing tests green; change a test only when the behaviour
  it checks changes on purpose, and say so in the pull request.
- Testable means logic: calculations, parsing, rules, state, formatting, data
  transformations, request handling, CI scripts. Markup, styles and generated data
  need no unit tests. Keep code that only wires a framework or a browser API thin
  and move its logic into modules that can be tested.
- Write code so it can be tested: pure functions for the logic, side effects (DOM,
  network, files, clock, environment) at the edges and passed in where possible.
- Unit tests never use the network or real credentials: mock or inject the HTTP
  client, use temporary directories, keep fixtures next to the tests.
- Run the tests before committing. They run in the `validate` job of Build Images
  (`.github/workflows/build.yml`) on every pull request into `develop` and every
  push to `develop` and `main`, and nothing is deployed while one fails.

| Project | Tests | Run them |
|---|---|---|
| `server/` | JUnit, `server/src/test` | `cd server && mvn verify` |
| `frontend/` | `node:test`, `frontend/tests` (`jsdom` for page tests) | `cd frontend && npm ci && npm test` |
| `processing/` | `unittest`, `processing/tests` | `python -m unittest discover -s processing/tests -t processing` |
| `tools/ci/` | shell test scripts, `tools/ci/test-*.sh` | `tools/ci/test-rollback.sh` |
| `fractal_model_lab/` | no test harness yet: it must compile with `-Werror` | `make -C fractal_model_lab` |

A new project, language or test suite gets its command added to the `validate` job
and to this table in the same pull request.

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
| `frontend/` | Vanilla JS/HTML/CSS served by nginx under a path prefix (use relative URLs); calls `api/*` on the same origin |
| `processing/` | Python NISAR radar processing (river lifeline monitor), writes the static data the frontend reads |
| `fractal_model_lab/` | C/ncurses TUI, follows 42's Norminette (see its README) |
| `data/` | CSV sources and the synthetic SQL generator |
| `tools/ci/`, `.github/workflows/` | Validation, image builds, deploy and PR previews |
| `podman-compose.yml`, `Caddyfile` | Production stack on the Raspberry Pi |
