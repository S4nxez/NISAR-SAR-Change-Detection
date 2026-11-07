"""Inventory of NISAR L2 GUNW products over the area of interest (plan phase 1).

Searches ASF, parses the product names into structured fields and writes a CSV plus a per-track summary: date range,
number of pairs, pairs longer than the nominal 12 days, coverage gaps and duplicated pairs (same track, frame and dates
in several product versions). It does not choose between duplicates: that choice is recorded in an ADR.

Run: ``python -m irrigation_footprint.inventory`` (needs network; writes to ``<data>/inventory/``).
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from dataclasses import asdict, dataclass, fields
from datetime import date, datetime
from pathlib import Path

from irrigation_footprint.aoi import SEARCH_BBOX, bbox_to_wkt
from irrigation_footprint.config import data_dir

NOMINAL_REPEAT_DAYS = 12  # NISAR exact-repeat orbit cycle (ASF, NISAR level 2 docs)

# NISAR_L2_PR_GUNW_<refCycle>_<track>_<A|D>_<frame>_<secCycle>_<mode>_<pol>_<refStart>_<refStop>_<secStart>_<secStop>_
# <CRID>_<field13>_<field14>_<field15>_<counter>. field13..15 are kept raw: their meaning (orbit accuracy, coverage,
# processing site) is inferred, not documented by ASF, and is checked against the HDF5 identification group.
_NAME_RE = re.compile(
    r"^NISAR_L2_(?P<processing>[A-Z]{2})_GUNW_"
    r"(?P<ref_cycle>\d{3})_(?P<track>\d{3})_(?P<direction>[AD])_(?P<frame>\d{3})_(?P<sec_cycle>\d{3})_"
    r"(?P<mode>\d{4})_(?P<polarization>[A-Z]{2})_"
    r"(?P<ref_start>\d{8}T\d{6})_(?P<ref_stop>\d{8}T\d{6})_(?P<sec_start>\d{8}T\d{6})_(?P<sec_stop>\d{8}T\d{6})_"
    r"(?P<crid>[A-Z]\d{5})_(?P<field13>[A-Z])_(?P<field14>[A-Z])_(?P<field15>[A-Z])_(?P<counter>\d{3})$"
)
_TIME_FMT = "%Y%m%dT%H%M%S"


@dataclass(frozen=True)
class GunwName:
    name: str
    processing: str
    ref_cycle: int
    track: int
    direction: str  # ASCENDING | DESCENDING
    frame: int
    sec_cycle: int
    mode: str
    polarization: str
    ref_start: datetime
    ref_stop: datetime
    sec_start: datetime
    sec_stop: datetime
    crid: str
    field13: str
    field14: str
    field15: str
    counter: int

    @property
    def ref_date(self) -> date:
        return self.ref_start.date()

    @property
    def sec_date(self) -> date:
        return self.sec_start.date()

    @property
    def baseline_days(self) -> int:
        """Temporal baseline: secondary minus reference acquisition date, in days."""
        return (self.sec_date - self.ref_date).days

    @property
    def pair_key(self) -> tuple[str, int, int, date, date]:
        """Identifies the interferometric pair regardless of product version."""
        return (self.direction, self.track, self.frame, self.ref_date, self.sec_date)


def parse_gunw_name(name: str) -> GunwName:
    """Parse a GUNW product (scene) name; raises ValueError if it does not follow the convention."""
    stem = name.removesuffix(".h5")
    match = _NAME_RE.match(stem)
    if not match:
        raise ValueError(f"not a NISAR L2 GUNW product name: {name}")
    g = match.groupdict()
    return GunwName(
        name=stem,
        processing=g["processing"],
        ref_cycle=int(g["ref_cycle"]),
        track=int(g["track"]),
        direction="ASCENDING" if g["direction"] == "A" else "DESCENDING",
        frame=int(g["frame"]),
        sec_cycle=int(g["sec_cycle"]),
        mode=g["mode"],
        polarization=g["polarization"],
        ref_start=datetime.strptime(g["ref_start"], _TIME_FMT),
        ref_stop=datetime.strptime(g["ref_stop"], _TIME_FMT),
        sec_start=datetime.strptime(g["sec_start"], _TIME_FMT),
        sec_stop=datetime.strptime(g["sec_stop"], _TIME_FMT),
        crid=g["crid"],
        field13=g["field13"],
        field14=g["field14"],
        field15=g["field15"],
        counter=int(g["counter"]),
    )


@dataclass(frozen=True)
class TrackSummary:
    direction: str
    track: int
    frame: int
    n_products: int
    n_pairs: int
    first_date: date
    last_date: date
    long_pairs: list[tuple[date, date]]  # baseline > NOMINAL_REPEAT_DAYS
    gaps: list[tuple[date, date]]  # intervals not covered by any pair
    duplicated_pairs: list[tuple[date, date]]


def summarize(products: list[GunwName]) -> list[TrackSummary]:
    """Per (direction, track, frame): coverage, long pairs, gaps and duplicated pairs."""
    groups: dict[tuple[str, int, int], list[GunwName]] = defaultdict(list)
    for p in products:
        groups[(p.direction, p.track, p.frame)].append(p)

    summaries = []
    for (direction, track, frame), items in sorted(groups.items()):
        by_pair: dict[tuple[date, date], int] = defaultdict(int)
        for p in items:
            by_pair[(p.ref_date, p.sec_date)] += 1
        pairs = sorted(by_pair)
        gaps = []
        covered_until = pairs[0][1]
        for ref, sec in pairs[1:]:
            if ref > covered_until:
                gaps.append((covered_until, ref))
            covered_until = max(covered_until, sec)
        summaries.append(
            TrackSummary(
                direction=direction,
                track=track,
                frame=frame,
                n_products=len(items),
                n_pairs=len(pairs),
                first_date=pairs[0][0],
                last_date=max(sec for _, sec in pairs),
                long_pairs=[(r, s) for r, s in pairs if (s - r).days > NOMINAL_REPEAT_DAYS],
                gaps=gaps,
                duplicated_pairs=[pair for pair, n in sorted(by_pair.items()) if n > 1],
            )
        )
    return summaries


def search_gunw(bbox: tuple[float, float, float, float] = SEARCH_BBOX) -> list[dict]:
    """Search ASF for every NISAR GUNW intersecting the bbox; one dict per product (name, url, size, ASF metadata)."""
    import asf_search as asf  # network dependency, imported only when searching

    results = asf.search(
        dataset=asf.DATASET.NISAR, processingLevel="GUNW", intersectsWith=bbox_to_wkt(bbox), maxResults=10000
    )
    rows = []
    for r in results:
        props = r.properties
        h5 = next((v["bytes"] for k, v in props.get("bytes", {}).items() if k.endswith(".h5")), None)
        rows.append(
            {
                "name": props["sceneName"],
                "url": props["url"],
                "h5_bytes": h5,
                "asf_path": props.get("pathNumber"),
                "asf_frame": props.get("frameNumber"),
                "asf_direction": props.get("flightDirection"),
                "footprint_wkt": r.geometry and _geometry_wkt(r.geometry),
            }
        )
    return rows


def _geometry_wkt(geometry: dict) -> str | None:
    if geometry.get("type") != "Polygon":
        return None
    ring = geometry["coordinates"][0]
    return "POLYGON((" + ",".join(f"{x} {y}" for x, y in ring) + "))"


def write_inventory(rows: list[dict], out_dir: Path) -> tuple[Path, Path]:
    """Write ``gunw.csv`` (one row per product) and ``gunw_summary.txt``; returns both paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    parsed = [parse_gunw_name(row["name"]) for row in rows]
    name_fields = [f.name for f in fields(GunwName) if f.name != "name"]
    csv_path = out_dir / "gunw.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=["name", *name_fields, "baseline_days", "h5_bytes", "url", "asf_path", "asf_frame",
                            "asf_direction", "footprint_wkt"]
        )
        writer.writeheader()
        for row, p in sorted(zip(rows, parsed), key=lambda rp: (rp[1].pair_key, rp[1].crid, rp[1].field13)):
            record = asdict(p)
            writer.writerow({**record, "baseline_days": p.baseline_days, **row})

    summary_path = out_dir / "gunw_summary.txt"
    summary_path.write_text(format_summary(summarize(parsed), parsed), encoding="utf-8")
    return csv_path, summary_path


def format_summary(summaries: list[TrackSummary], products: list[GunwName]) -> str:
    lines = [f"NISAR GUNW over {SEARCH_BBOX}: {len(products)} products"]
    lines.append(f"Polarizations: {sorted({p.polarization for p in products})}; modes: {sorted({p.mode for p in products})}")
    lines.append(f"CRIDs: {sorted({p.crid for p in products})}; field13 values: {sorted({p.field13 for p in products})}")
    for s in summaries:
        lines.append("")
        lines.append(
            f"{s.direction} track {s.track} frame {s.frame}: {s.n_products} products, {s.n_pairs} pairs, "
            f"{s.first_date} -> {s.last_date}"
        )
        for label, items in (("long pairs", s.long_pairs), ("gaps", s.gaps), ("duplicated pairs", s.duplicated_pairs)):
            text = ", ".join(f"{a}->{b} ({(b - a).days} d)" for a, b in items) or "none"
            lines.append(f"  {label}: {text}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=None, help="output directory (default: <data>/inventory)")
    args = parser.parse_args(argv)
    csv_path, summary_path = write_inventory(search_gunw(), args.out or data_dir() / "inventory")
    print(summary_path.read_text(encoding="utf-8"))
    print(f"Wrote {csv_path} and {summary_path}")


if __name__ == "__main__":
    main()
