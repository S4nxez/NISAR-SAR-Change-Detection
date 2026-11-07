"""Download NISAR products from ASF with the NASA Earthdata credentials of ``.env``.

A file already on disk with the expected size is skipped, so interrupted runs can be resumed.

Run: ``python -m irrigation_footprint.download <product name> [...]`` (names from ``<data>/inventory/gunw.csv``).
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from irrigation_footprint.config import EarthdataCredentials, data_dir, earthdata_credentials


def needs_download(path: Path, expected_bytes: int | None) -> bool:
    """True unless the file exists with the expected size (any size if unknown)."""
    if not path.is_file():
        return True
    return expected_bytes is not None and path.stat().st_size != expected_bytes


def asf_session(creds: EarthdataCredentials):
    """Authenticated ASF session: the token first, then username + password if the token is rejected."""
    import asf_search as asf

    if creds.token:
        try:
            return asf.ASFSession().auth_with_token(creds.token)
        except asf.ASFAuthenticationError:
            if not (creds.username and creds.password):
                raise
            print("Earthdata token rejected (invalid or expired): using username and password")
    return asf.ASFSession().auth_with_creds(creds.username, creds.password)


def download(urls_and_sizes: list[tuple[str, int | None]], out_dir: Path) -> list[Path]:
    """Download each URL into ``out_dir``; returns the local paths."""
    import asf_search as asf

    out_dir.mkdir(parents=True, exist_ok=True)
    session = asf_session(earthdata_credentials())
    paths = []
    for url, size in urls_and_sizes:
        path = out_dir / url.rsplit("/", 1)[-1]
        if needs_download(path, size):
            path.unlink(missing_ok=True)
            asf.download_url(url=url, path=str(out_dir), filename=path.name, session=session)
            if needs_download(path, size):
                raise RuntimeError(f"incomplete download of {path.name}: expected {size} bytes")
        paths.append(path)
    return paths


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("names", nargs="+", help="GUNW product names from the inventory")
    parser.add_argument("--inventory", type=Path, default=None, help="default: <data>/inventory/gunw.csv")
    parser.add_argument("--out", type=Path, default=None, help="default: <data>/gunw")
    args = parser.parse_args(argv)
    with (args.inventory or data_dir() / "inventory" / "gunw.csv").open(encoding="utf-8") as fh:
        rows = {r["name"]: r for r in csv.DictReader(fh)}
    missing = [n for n in args.names if n not in rows]
    if missing:
        raise SystemExit(f"not in the inventory: {missing}")
    wanted = [(rows[n]["url"], int(rows[n]["h5_bytes"]) if rows[n]["h5_bytes"] else None) for n in args.names]
    for path in download(wanted, args.out or data_dir() / "gunw"):
        print(path)


if __name__ == "__main__":
    main()
