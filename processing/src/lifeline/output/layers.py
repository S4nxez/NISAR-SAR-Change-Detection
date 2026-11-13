"""Images of a pass for the web page and the stored water mask.

  radar.webp   HH backscatter preview at half resolution, -25..0 dB in grey, no data transparent
  water.png    water mask; channels narrower than the safe width in amber, water under vegetation in green
  change.png   water lost / gained since the previous pass of the same track
  water.npz    packed water mask, validity and, when known, water under vegetation (input of the change layer
               and of `reevaluate`)
  backscatter.npz  filtered HH (and HV) in float16, only with MONITOR_KEEP_BACKSCATTER=1 (the benchmark)
"""
import os

import numpy as np
from PIL import Image

from lifeline.analysis.radar import block_mean

RADAR_DB_RANGE = (-25.0, 0.0)
# none, wide water (blue), narrow channel (amber), water under vegetation (green: not a route, ADR-004)
WATER_PALETTE = [0, 0, 0, 61, 139, 255, 255, 176, 32, 76, 195, 138]
CHANGE_PALETTE = [0, 0, 0, 228, 119, 89, 104, 214, 230]     # none, water lost, water gained
WATER_WIDE, WATER_NARROW, WATER_VEGETATED = 1, 2, 3
CHANGE_LOST, CHANGE_GAINED = 1, 2


def _indexed_png(idx, palette, path):
    img = Image.fromarray(idx, "P")
    img.putpalette(palette + [0] * (256 * 3 - len(palette)))
    img.save(path, transparency=0, optimize=True)


def save_radar(db, path):
    small = block_mean(db, 2)
    ok = np.isfinite(small)
    lo, hi = RADAR_DB_RANGE
    g = (np.clip((np.nan_to_num(small, nan=lo) - lo) / (hi - lo), 0, 1) * 255).astype(np.uint8)
    Image.fromarray(np.dstack([g, ok.astype(np.uint8) * 255]), "LA").convert("RGBA").save(path, "WEBP", quality=78)


def save_water(water, wide, path, vegetated=None):
    idx = np.zeros(water.shape, np.uint8)
    if vegetated is not None:
        idx[vegetated & ~water] = WATER_VEGETATED
    idx[water] = WATER_NARROW
    idx[wide] = WATER_WIDE
    _indexed_png(idx, WATER_PALETTE, path)


def change_index(prev, cur):
    """Indexed change image between two (water, valid) masks, judged only where both have data."""
    pw, pv = prev
    cw, cv = cur
    both = pv & cv
    idx = np.zeros(cw.shape, np.uint8)
    idx[both & pw & ~cw] = CHANGE_LOST
    idx[both & ~pw & cw] = CHANGE_GAINED
    return idx


def save_change(prev, cur, path):
    """Write change.png; returns (pixels of water lost, pixels of water gained)."""
    idx = change_index(prev, cur)
    _indexed_png(idx, CHANGE_PALETTE, path)
    return int((idx == CHANGE_LOST).sum()), int((idx == CHANGE_GAINED).sum())


def save_mask(water, valid, path, vegetated=None):
    extra = {} if vegetated is None else {"vegetated": np.packbits(vegetated)}
    np.savez_compressed(path, shape=np.array(water.shape), water=np.packbits(water), valid=np.packbits(valid),
                        **extra)


def save_backscatter(hh, hv, path):
    """Filtered backscatter (dB) of a pass in float16 (about 0.01 dB steps at -20 dB), HV only when given."""
    extra = {} if hv is None else {"hv": hv.astype(np.float16)}
    np.savez_compressed(path, hh=hh.astype(np.float16), **extra)


def load_backscatter(path):
    """(hh, hv or None) float32 arrays stored by save_backscatter, or (None, None) when the file is missing."""
    if not os.path.exists(path):
        return None, None
    with np.load(path) as z:
        return z["hh"].astype(np.float32), (z["hv"].astype(np.float32) if "hv" in z.files else None)


def load_mask(path):
    """(water, valid) boolean arrays stored by save_mask."""
    with np.load(path) as z:
        shape = tuple(z["shape"])
        n = shape[0] * shape[1]
        return (np.unpackbits(z["water"])[:n].reshape(shape).astype(bool),
                np.unpackbits(z["valid"])[:n].reshape(shape).astype(bool))


def save_sentinel1(view, path):
    """The Sentinel-1 classes a pass used (sources.sentinel1.pass_view): water, land and seen, packed, with the
    scene dates, so reevaluate applies the same rules without reading Sentinel-1 again."""
    shape = view["water"].shape
    np.savez_compressed(path, shape=np.array(shape), dates=np.array(view["dates"]),
                        **{k: np.packbits(view[k]) for k in ("water", "land", "seen")})


def load_sentinel1(path):
    """{"dates", "water", "land", "seen"} stored by save_sentinel1, or None when the pass has none."""
    if not os.path.exists(path):
        return None
    with np.load(path) as z:
        shape = tuple(z["shape"])
        n = shape[0] * shape[1]
        out = {k: np.unpackbits(z[k])[:n].reshape(shape).astype(bool) for k in ("water", "land", "seen")}
        out["dates"] = [str(d) for d in z["dates"]]
    return out


def load_vegetated(path):
    """The water-under-vegetation mask stored by save_mask, or None (single-polarisation pass, older record)."""
    with np.load(path) as z:
        if "vegetated" not in z.files:
            return None
        shape = tuple(z["shape"])
        return np.unpackbits(z["vegetated"])[:shape[0] * shape[1]].reshape(shape).astype(bool)
