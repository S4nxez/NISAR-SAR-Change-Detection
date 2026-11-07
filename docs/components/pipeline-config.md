# Component: pipeline configuration

`pipeline/src/irrigation_footprint/config.py`

## What it does

Resolves where the pipeline keeps its data and reads the NASA Earthdata Login credentials needed to download NISAR
products from ASF.

## Inputs

| Variable | Meaning |
| --- | --- |
| `EARTHDATA_TOKEN` | Earthdata bearer token. Wins over username/password if both are set |
| `EARTHDATA_USERNAME`, `EARTHDATA_PASSWORD` | Earthdata Login, used when there is no token |
| `IRRIGATION_DATA_DIR` | Optional data root; default `<repo>/data`. Use a large disk: the selected GUNW stack is about 115 GB |

Values come from the process environment first, then from the git-ignored `.env` at the repository root
(template: `.env.example`). The same `.env` is read by `podman-compose.yml`, so it also holds the MySQL variables.

## Outputs

- `data_dir()`: data root path (reads `.env` itself, so every command honours `IRRIGATION_DATA_DIR`).
- `earthdata_credentials()`: `EarthdataCredentials(username, password, token)`; raises `MissingCredentialsError` if
  neither a token nor a username + password is set.

## How to run

```python
from irrigation_footprint.config import data_dir, earthdata_credentials
creds = earthdata_credentials()
```

Tests: `cd pipeline && pytest tests/test_config.py`.

## Limitations

- The `.env` parser handles `KEY=VALUE`, `export KEY=VALUE`, `#` comment lines and quoted values; it does not expand
  `${VAR}` references or strip inline comments after a value.
- Secrets are kept out of `repr()` and error messages, but they live in `os.environ` once loaded.
