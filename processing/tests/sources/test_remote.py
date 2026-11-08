import unittest
from unittest import mock

import requests

from lifeline.sources import remote
from lifeline.sources.remote import RemoteFile, earthdata_token

from ..helpers import FakeResponse

DATA = bytes(range(256)) * 64   # 16 KiB product


class FakeSession:
    """Serves DATA with range requests; `script` overrides the answer of the next block reads."""

    def __init__(self, script=None, sign_status=200):
        self.headers, self.calls, self.script, self.sign_status, self.closed = {}, [], list(script or []), sign_status, False

    def get(self, url, headers=None, timeout=None):
        rng = headers["Range"].removeprefix("bytes=")
        a, b = (int(v) for v in rng.split("-"))
        self.calls.append((url, a, b))
        if "Authorization" in headers:   # signing request on the product URL
            if self.sign_status != 200:
                return FakeResponse(self.sign_status)
            return FakeResponse(206, DATA[:1], headers={"Content-Range": f"bytes 0-0/{len(DATA)}"},
                                url="https://cdn.example/signed")
        if self.script:
            step = self.script.pop(0)
            if isinstance(step, Exception):
                raise step
            if step == "short":
                return FakeResponse(206, DATA[a:b])
            return FakeResponse(step)
        return FakeResponse(206, DATA[a:b + 1])

    def close(self):
        self.closed = True


def open_file(session, block=4096):
    patcher = mock.patch.object(remote, "BLOCK", block)
    patcher.start()
    rf = RemoteFile("https://data.example/product.h5", "tok", session=session, retry_wait=0)
    return rf, patcher


class TestRemoteFile(unittest.TestCase):
    def setUp(self):
        self.session = FakeSession()
        self.rf, patcher = open_file(self.session)
        self.addCleanup(patcher.stop)

    def test_signs_with_the_token_and_reads_the_size(self):
        self.assertEqual(self.rf.size, len(DATA))
        self.assertEqual(self.rf.url, "https://cdn.example/signed")
        self.assertEqual(self.session.calls[0], ("https://data.example/product.h5", 0, 0))

    def test_reads_across_blocks_and_counts_downloaded_bytes(self):
        self.rf.seek(4000)
        self.assertEqual(self.rf.read(200), DATA[4000:4200])
        self.assertEqual(self.rf.tell(), 4200)
        self.assertEqual(self.rf.bytes, 2 * 4096)

    def test_blocks_are_cached(self):
        self.rf.read(10)
        self.rf.seek(0)
        self.rf.read(10)
        self.assertEqual(len(self.session.calls), 2)   # signing + one block

    def test_seek_whence_and_read_past_the_end(self):
        self.assertEqual(self.rf.seek(-6, 2), len(DATA) - 6)
        self.assertEqual(self.rf.read(100), DATA[-6:])
        self.assertEqual(self.rf.read(10), b"")
        self.rf.seek(10)
        self.assertEqual(self.rf.seek(5, 1), 15)

    def test_close_releases_the_session(self):
        with self.rf:
            self.rf.read(1)
        self.assertTrue(self.session.closed)
        self.assertTrue(self.rf.closed)


class TestRemoteFileFailures(unittest.TestCase):
    def open(self, **kw):
        session = FakeSession(**kw)
        rf, patcher = open_file(session)
        self.addCleanup(patcher.stop)
        return rf, session

    def test_rejected_token_says_so(self):
        with self.assertRaisesRegex(PermissionError, "refused the token"):
            self.open(sign_status=401)

    def test_expired_signed_url_is_signed_again(self):
        rf, session = self.open(script=[403])
        self.assertEqual(rf.read(4), DATA[:4])
        signs = [c for c in session.calls if c[0].startswith("https://data.example")]
        self.assertEqual(len(signs), 2)

    def test_short_reads_and_network_errors_are_retried(self):
        rf, _ = self.open(script=["short", requests.ConnectionError("reset")])
        self.assertEqual(rf.read(4), DATA[:4])

    def test_gives_up_with_an_error_after_the_last_attempt(self):
        rf, _ = self.open(script=[500] * remote.ATTEMPTS)
        with self.assertRaisesRegex(IOError, "after 5 attempts"):
            rf.read(4)

    def test_signed_url_expiring_on_every_attempt_raises_instead_of_returning_nothing(self):
        rf, _ = self.open(script=[403] * remote.ATTEMPTS)
        with self.assertRaises(IOError):
            rf.read(4)


class TestEarthdataToken(unittest.TestCase):
    def test_token_from_the_environment_is_stripped(self):
        self.assertEqual(earthdata_token({"EARTHDATA_TOKEN": "  abc \n"}), "abc")

    @unittest.skipIf(remote.os.name == "nt", "the registry is read on Windows")
    def test_missing_token_exits_with_instructions(self):
        with self.assertRaisesRegex(SystemExit, "urs.earthdata.nasa.gov"):
            earthdata_token({})


if __name__ == "__main__":
    unittest.main()
