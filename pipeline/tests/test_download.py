from irrigation_footprint.download import needs_download


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
