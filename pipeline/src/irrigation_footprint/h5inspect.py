"""Dump the structure of an HDF5 product: every group and dataset with shape, dtype and attributes.

Like ``h5ls -r`` plus the attributes (units, description, EPSG...) needed to document a product. Scalar and small
string datasets are printed with their value, so identification metadata (orbit, polarization, version) is visible.

Run: ``python -m irrigation_footprint.h5inspect <file.h5> [--out dump.txt]``.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import h5py
import numpy as np

MAX_VALUE_CHARS = 200
MAX_INLINE_ELEMENTS = 8


def _fmt(value) -> str:
    if isinstance(value, bytes):
        value = value.decode("utf-8", "replace")
    elif isinstance(value, np.ndarray):
        if value.dtype.kind in "SO":
            value = [v.decode("utf-8", "replace") if isinstance(v, bytes) else v for v in value.ravel()]
        elif value.size > MAX_INLINE_ELEMENTS:
            return f"array{value.shape} {value.dtype}"
        else:
            value = value.tolist()
    text = str(value).replace("\n", " ")
    return text if len(text) <= MAX_VALUE_CHARS else text[:MAX_VALUE_CHARS] + "..."


def dump(path: Path) -> str:
    lines: list[str] = []

    def visit(name: str, obj) -> None:
        indent = "  " * name.count("/")
        if isinstance(obj, h5py.Dataset):
            line = f"{indent}{name}  {obj.shape} {obj.dtype}"
            if obj.size <= MAX_INLINE_ELEMENTS and obj.dtype.kind != "V":
                line += f" = {_fmt(obj[()])}"
        else:
            line = f"{indent}{name}/"
        lines.append(line)
        for key, value in obj.attrs.items():
            lines.append(f"{indent}    @{key} = {_fmt(value)}")

    with h5py.File(path, "r") as f:
        for key, value in f.attrs.items():
            lines.append(f"@{key} = {_fmt(value)}")
        f.visititems(visit)
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("file", type=Path)
    parser.add_argument("--out", type=Path, default=None, help="write the dump to this file instead of stdout")
    args = parser.parse_args(argv)
    text = dump(args.file)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        print(f"Wrote {args.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
