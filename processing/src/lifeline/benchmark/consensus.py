"""Reference water from several sources, each one used only where it can be trusted.

Every source casts per-pixel votes: "water", "land" or none (no data, or a place where that source is blind).
A pixel is reference water when at least one source votes water and none votes land, reference land in the opposite
case, and **disputed** when the sources disagree: nobody can say what it is, so it is neither scored nor used
as evidence against the method. The families (optical, radar) are counted too, so a result can tell water that two
independent kinds of sensor agree on from water only one kind sees.

Blind spots, where a vote is dropped:
  optical "land" under herbaceous wetland or mangroves (plants hide the water) and partial-water pixels of
  DSWx-HLS (mixed pixels); radar votes outside the radar's own valid mask.
"""
import numpy as np
from scipy import ndimage

from lifeline.analysis.water import EIGHT_NEIGHBOURS


def votes(name, family, water, land, blind_land=None):
    """One source's votes; `blind_land` marks pixels where its "land" is not trusted."""
    land = land & ~water
    if blind_land is not None:
        land = land & ~blind_land
    return {"name": name, "family": family, "water": water & ~land, "land": land}


def combine(sources, in_area):
    """Consensus of the sources' votes inside the area. Returns masks (water, land, disputed, known) and per pixel
    the number of families agreeing with the consensus (`families`, 0 where not known or disputed)."""
    shape = in_area.shape
    any_water = np.zeros(shape, bool)
    any_land = np.zeros(shape, bool)
    fam_water, fam_land = {}, {}
    for s in sources:
        any_water |= s["water"]
        any_land |= s["land"]
        fam_water[s["family"]] = fam_water.get(s["family"], np.zeros(shape, bool)) | s["water"]
        fam_land[s["family"]] = fam_land.get(s["family"], np.zeros(shape, bool)) | s["land"]
    water = any_water & ~any_land & in_area
    land = any_land & ~any_water & in_area
    disputed = any_water & any_land & in_area
    families = np.zeros(shape, np.uint8)
    for f in fam_water:
        families += (water & fam_water[f]) | (land & fam_land[f])
    return {"water": water, "land": land, "disputed": disputed, "known": water | land | disputed,
            "families": families}


def agreement_by_source(sources, cons):
    """For each source, the share of its votes on decided pixels that match the consensus, and how many pixels it
    voted on: a source that often disagrees with the others is less trustworthy in this area."""
    decided = cons["water"] | cons["land"]
    out = {}
    for s in sources:
        voted = (s["water"] | s["land"]) & (decided | cons["disputed"])
        n = int(voted.sum())
        ok = int(((s["water"] & cons["water"]) | (s["land"] & cons["land"])).sum())
        out[s["name"]] = {"family": s["family"], "voted_px": n,
                          "agrees_share": None if n == 0 else round(ok / n, 4)}
    return out


def status_bounds(status_of, cons):
    """Community status on the consensus: once with the disputed pixels as land (pessimistic) and once as water
    (optimistic). Where both give the same status the reference is decided; elsewhere it is "undecided" (None)."""
    low = status_of(cons["water"], cons["known"])
    high = status_of(cons["water"] | cons["disputed"], cons["known"])
    decided = {cid: (r if high.get(cid) is not None and r[0] == high[cid][0] else None) for cid, r in low.items()}
    return decided, low, high


def shore_band(water, known, px=1):
    """Known pixels within `px` pixels of the water's edge, on either side: mixed pixels at the 20 m grid."""
    if not water.any():
        return np.zeros_like(water)
    edge = ndimage.binary_dilation(water, EIGHT_NEIGHBOURS, iterations=px) & \
        ndimage.binary_dilation(~water & known, EIGHT_NEIGHBOURS, iterations=px)
    return edge & known
