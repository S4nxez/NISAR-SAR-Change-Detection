"""Repository paths and credentials.

Credentials come from the environment or from the git-ignored ``.env`` at the repository root (template:
``.env.example``). Variables already set in the environment win over ``.env``. Secrets are never logged or included
in error messages.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def data_dir() -> Path:
    """Root of downloaded and derived data: ``$IRRIGATION_DATA_DIR`` or ``<repo>/data`` (git-ignored)."""
    return Path(os.environ.get("IRRIGATION_DATA_DIR", REPO_ROOT / "data"))


def parse_env_file(path: Path) -> dict[str, str]:
    """Parse ``KEY=VALUE`` lines; blank lines and ``#`` comments are skipped, surrounding quotes are removed."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key.startswith("export "):
            key = key[len("export ") :].strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key] = value
    return values


def load_env(path: Path | None = None) -> None:
    """Copy the variables of ``.env`` into ``os.environ`` without overriding the ones already set."""
    for key, value in parse_env_file(path or REPO_ROOT / ".env").items():
        os.environ.setdefault(key, value)


class MissingCredentialsError(RuntimeError):
    pass


@dataclass(frozen=True)
class EarthdataCredentials:
    """NASA Earthdata Login: a bearer token, or a username and password (as read by ``earthaccess``)."""

    username: str | None = None
    password: str | None = field(default=None, repr=False)
    token: str | None = field(default=None, repr=False)


def earthdata_credentials(env_file: Path | None = None) -> EarthdataCredentials:
    """Read ``EARTHDATA_TOKEN`` or ``EARTHDATA_USERNAME`` + ``EARTHDATA_PASSWORD``; the token wins if both are set."""
    load_env(env_file)
    token = os.environ.get("EARTHDATA_TOKEN") or None
    username = os.environ.get("EARTHDATA_USERNAME") or None
    password = os.environ.get("EARTHDATA_PASSWORD") or None
    if token:
        return EarthdataCredentials(username=username, token=token)
    if username and password:
        return EarthdataCredentials(username=username, password=password)
    raise MissingCredentialsError(
        "NASA Earthdata credentials not found: set EARTHDATA_TOKEN, or EARTHDATA_USERNAME and EARTHDATA_PASSWORD, "
        "in the environment or in the repository .env (see .env.example)"
    )
