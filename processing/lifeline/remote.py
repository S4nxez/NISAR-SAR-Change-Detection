"""Earthdata credentials and ranged reads of remote products (never the whole ~2 GB file)."""
import io
import os
import time

import requests

from .config import USER_AGENT

BLOCK = 4 * 1024 * 1024
ATTEMPTS = 5


def earthdata_token(environ=os.environ):
    """NASA Earthdata user token from EARTHDATA_TOKEN (on Windows the user-level variable is also
    read from the registry, so no restart is needed). Exits with instructions when missing."""
    tok = environ.get("EARTHDATA_TOKEN", "").strip()
    if not tok and os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                tok = str(winreg.QueryValueEx(k, "EARTHDATA_TOKEN")[0]).strip()
        except OSError:
            tok = ""
    if not tok:
        raise SystemExit("EARTHDATA_TOKEN is not set: create a token at https://urs.earthdata.nasa.gov "
                         "(Generate Token) and store it in that environment variable.")
    return tok


class RemoteFile(io.RawIOBase):
    """Seekable read-only view of a remote file through HTTP range requests (block cache).

    The product URL redirects to a signed CDN location that expires: on 401/403 the file is
    signed again. `bytes` counts what was actually downloaded.
    """

    def __init__(self, url, token, session=None, retry_wait=2.0):
        super().__init__()
        self.src, self.token, self.retry_wait = url, token, retry_wait
        self.session = session or requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self.pos, self.cache, self.bytes = 0, {}, 0
        self._sign()

    def _sign(self):
        r = self.session.get(self.src, headers={"Range": "bytes=0-0", "Authorization": "Bearer " + self.token},
                             timeout=90)
        if r.status_code in (401, 403):
            raise PermissionError(f"Earthdata refused the token (HTTP {r.status_code}); "
                                  "check that it has not expired.")
        r.raise_for_status()
        self.url = r.url  # signed CDN location of the product
        self.size = int(r.headers["Content-Range"].split("/")[1])

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, off, whence=io.SEEK_SET):
        if whence == io.SEEK_SET:
            self.pos = off
        elif whence == io.SEEK_CUR:
            self.pos += off
        else:
            self.pos = self.size + off
        return self.pos

    def _block(self, i):
        if i in self.cache:
            return self.cache[i]
        a, b = i * BLOCK, min(self.size, (i + 1) * BLOCK) - 1
        last_error = None
        for attempt in range(ATTEMPTS):
            try:
                r = self.session.get(self.url, headers={"Range": f"bytes={a}-{b}"}, timeout=180)
                if r.status_code in (401, 403):  # signed URL expired
                    last_error = PermissionError(f"HTTP {r.status_code} reading {self.src}")
                    self._sign()
                    continue
                r.raise_for_status()
                if len(r.content) != b - a + 1:
                    raise IOError(f"short read: {len(r.content)} of {b - a + 1} bytes")
                self.cache[i] = r.content
                self.bytes += len(r.content)
                return r.content
            except (requests.RequestException, IOError) as e:
                last_error = e
                if attempt < ATTEMPTS - 1:
                    time.sleep(self.retry_wait * (1 + 1.5 * attempt))
        raise IOError(f"could not read bytes {a}-{b} of {self.src} after {ATTEMPTS} attempts") from last_error

    def readinto(self, buf):
        n = max(0, min(len(buf), self.size - self.pos))
        out, done = memoryview(buf).cast("B"), 0
        while done < n:
            i, off = divmod(self.pos + done, BLOCK)
            blk = self._block(i)
            k = min(n - done, len(blk) - off)
            out[done:done + k] = blk[off:off + k]
            done += k
        self.pos += n
        return n

    def close(self):
        if not self.closed:
            self.session.close()
            self.cache.clear()
        super().close()
