import pytest

from irrigation_footprint.download import needs_download, parse_track_frame, select_rows

ROWS = [
    {"name": "a1", "direction": "ASCENDING", "track": "34", "frame": "20"},
    {"name": "a2", "direction": "ASCENDING", "track": "34", "frame": "19"},
    {"name": "d1", "direction": "DESCENDING", "track": "114", "frame": "70"},
    {"name": "d2", "direction": "DESCENDING", "track": "114", "frame": "71"},
]


def test_parse_track_frame():
    assert parse_track_frame("A034F20") == ("ASCENDING", 34, 20)
    assert parse_track_frame("d114f70") == ("DESCENDING", 114, 70)
    with pytest.raises(ValueError):
        parse_track_frame("X034F20")


def test_select_by_track_frame_and_name():
    assert [r["name"] for r in select_rows(ROWS, [], ["A034F20", "D114F70"])] == ["a1", "d1"]
    assert [r["name"] for r in select_rows(ROWS, ["d2"], ["A034F20"])] == ["a1", "d2"]


def test_select_rejects_unknown_names():
    with pytest.raises(ValueError):
        select_rows(ROWS, ["nope"], [])


def test_missing_file_needs_download(tmp_path):
    assert needs_download(tmp_path / "x.h5", 10)


def test_complete_file_is_skipped(tmp_path):
    path = tmp_path / "x.h5"
    path.write_bytes(b"0123456789")
    assert not needs_download(path, 10)
    assert not needs_download(path, None)


def test_partial_file_is_downloaded_again(tmp_path):
    path = tmp_path / "x.h5"
    path.write_bytes(b"01234")
    assert needs_download(path, 10)
