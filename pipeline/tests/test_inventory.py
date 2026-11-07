from datetime import date, datetime

import pytest

from irrigation_footprint.aoi import bbox_to_wkt
from irrigation_footprint.inventory import parse_gunw_name, summarize, write_inventory

REAL_NAME = (
    "NISAR_L2_PR_GUNW_032_135_A_020_033_4000_SH_20261009T131716_20261009T131751_"
    "20261021T131716_20261021T131751_P05023_N_F_J_001"
)


def make_name(ref: str, sec: str, track=42, direction="D", frame=70, crid="P05023", f13="N") -> str:
    return (
        f"NISAR_L2_PR_GUNW_010_{track:03d}_{direction}_{frame:03d}_011_4000_SH_"
        f"{ref}T025720_{ref}T025755_{sec}T025720_{sec}T025755_{crid}_{f13}_F_J_001"
    )


def test_parse_real_product_name():
    g = parse_gunw_name(REAL_NAME + ".h5")
    assert g.name == REAL_NAME
    assert (g.ref_cycle, g.track, g.direction, g.frame, g.sec_cycle) == (32, 135, "ASCENDING", 20, 33)
    assert (g.mode, g.polarization, g.crid, g.counter) == ("4000", "SH", "P05023", 1)
    assert g.ref_start == datetime(2026, 10, 9, 13, 17, 16)
    assert g.sec_stop == datetime(2026, 10, 21, 13, 17, 51)
    assert g.baseline_days == 12


def test_baseline_sign_is_secondary_minus_reference():
    g = parse_gunw_name(make_name("20260716", "20260821"))
    assert g.baseline_days == 36


@pytest.mark.parametrize("bad", ["NISAR_L2_PR_GSLC_032_135_A_020_4000_SH", "random.h5", REAL_NAME[:-4]])
def test_rejects_other_names(bad):
    with pytest.raises(ValueError):
        parse_gunw_name(bad)


def test_summary_detects_long_pairs_gaps_and_duplicates():
    names = [
        make_name("20260605", "20260617"),
        make_name("20260617", "20260629"),
        make_name("20260617", "20260629", f13="F"),  # same pair, other version
        make_name("20260711", "20260723"),  # 20260629 -> 20260711 not covered
        make_name("20260723", "20260816"),  # 24-day pair bridging a missing acquisition
        make_name("20260101", "20260113", direction="A", track=135, frame=20),
    ]
    summaries = summarize([parse_gunw_name(n) for n in names])
    asc, desc = summaries
    assert (asc.direction, asc.n_pairs, asc.gaps, asc.long_pairs) == ("ASCENDING", 1, [], [])
    assert desc.n_products == 5 and desc.n_pairs == 4
    assert desc.first_date == date(2026, 6, 5) and desc.last_date == date(2026, 8, 16)
    assert desc.gaps == [(date(2026, 6, 29), date(2026, 7, 11))]
    assert desc.long_pairs == [(date(2026, 7, 23), date(2026, 8, 16))]
    assert desc.duplicated_pairs == [(date(2026, 6, 17), date(2026, 6, 29))]


def test_write_inventory_outputs(tmp_path):
    rows = [{"name": make_name("20260605", "20260617"), "url": "u", "h5_bytes": 10, "asf_path": 42,
             "asf_frame": 70, "asf_direction": "DESCENDING", "footprint_wkt": None}]
    csv_path, summary_path = write_inventory(rows, tmp_path / "inv")
    header = csv_path.read_text(encoding="utf-8").splitlines()[0]
    assert "baseline_days" in header and "url" in header
    assert "DESCENDING track 42 frame 70: 1 products, 1 pairs" in summary_path.read_text(encoding="utf-8")


def test_bbox_to_wkt_is_closed_and_validated():
    wkt = bbox_to_wkt((-120.0, 35.0, -119.0, 36.0))
    assert wkt.startswith("POLYGON((-120.0 35.0,") and wkt.endswith("-120.0 35.0))")
    with pytest.raises(ValueError):
        bbox_to_wkt((-119.0, 35.0, -120.0, 36.0))
