"""Images of a pass for the web page and the stored water mask.

  radar.webp   HH backscatter preview at half resolution, -25..0 dB in grey, no data transparent
  water.png    water mask; channels narrower than the safe width in amber
  change.png   water lost / gained since the previous pass of the same track
  water.npz    packed water mask and validity (input of the change layer and of `reevaluate`)
"""
import numpy as np
from PIL import Image

from lifeline.analysis.radar import block_mean

RADAR_DB_RANGE = (-25.0, 0.0)
WATER_PALETTE = [0, 0, 0, 61, 139, 255, 255, 176, 32]       # none, wide water (blue), narrow channel (amber)
CHANGE_PALETTE = [0, 0, 0, 228, 119, 89, 104, 214, 230]     # none, water lost, water gained
WATER_WIDE, WATER_NARROW = 1, 2
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


def save_water(water, wide, path):
    idx = np.zeros(water.shape, np.uint8)
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


def save_mask(water, valid, path):
    np.savez_compressed(path, shape=np.array(water.shape), water=np.packbits(water), valid=np.packbits(valid))


def load_mask(path):
    """(water, valid) boolean arrays stored by save_mask."""
    with np.load(path) as z:
        shape = tuple(z["shape"])
        n = shape[0] * shape[1]
        return (np.unpackbits(z["water"])[:n].reshape(shape).astype(bool),
                np.unpackbits(z["valid"])[:n].reshape(shape).astype(bool))
