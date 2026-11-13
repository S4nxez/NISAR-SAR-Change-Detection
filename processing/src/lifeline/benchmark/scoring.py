"""Pure scoring functions of the benchmark: water mask agreement, community status agreement, rank correlation."""
import math

import numpy as np
from scipy import ndimage, stats

from lifeline.analysis.water import wide_water
from lifeline.config import STATUS

LINKED = (STATUS["connected"], STATUS["at_risk"])
STATUS_KEYS = ("connected", "at_risk", "isolated")
CODE_KEY = {STATUS[k]: k for k in STATUS_KEYS}
SHORE_M = 100.0   # commission within this distance of reference water is a shoreline error, beyond it a far one


def confusion(pred, ref, mask):
    """Pixel counts {tp, fp, fn, tn} of a predicted against a reference boolean mask, inside `mask`."""
    p, r = pred[mask], ref[mask]
    return {"tp": int((p & r).sum()), "fp": int((p & ~r).sum()), "fn": int((~p & r).sum()), "tn": int((~p & ~r).sum())}


def add_counts(a, b):
    return {k: a.get(k, 0) + b.get(k, 0) for k in set(a) | set(b)}


def ratio(num, den):
    return None if den == 0 else round(num / den, 4)


def rates(c):
    """IoU, F1, precision and recall of the positive class from confusion counts (None when undefined)."""
    tp, fp, fn = c["tp"], c["fp"], c["fn"]
    return {"iou": ratio(tp, tp + fp + fn), "f1": ratio(2 * tp, 2 * tp + fp + fn),
            "precision": ratio(tp, tp + fp), "recall": ratio(tp, tp + fn)}


def width_strata(ref_water, px_m):
    """Reference water split by channel width: narrow (< 60 m), medium (60-200 m) and wide (>= 200 m), with the
    same width rule the monitor uses for its own channels (analysis.water.wide_water)."""
    inside_m = ndimage.distance_transform_edt(ref_water) * px_m
    w60 = wide_water(ref_water, inside_m, 60.0, px_m)
    w200 = wide_water(ref_water, inside_m, 200.0, px_m)
    return {"narrow_lt60m": ref_water & ~w60, "medium_60_200m": w60 & ~w200, "wide_ge200m": w200}


def water_scores(pred, ref, common, px_m):
    """Agreement of a predicted water mask with a reference one on the pixels both cover (`common`):
    overall counts and rates, recall per reference width class, and commission near and far from the shore."""
    c = confusion(pred, ref, common)
    out = {"counts": c, **rates(c), "recall_by_width": {}}
    for name, stratum in width_strata(ref, px_m).items():
        m = common & stratum
        out["recall_by_width"][name] = {"pixels": int(m.sum()), "recall": ratio(int((pred & m).sum()), int(m.sum()))}
    near = ndimage.distance_transform_edt(~ref) * px_m <= SHORE_M
    land = common & ~ref
    out["false_water"] = {
        "shore": {"pixels": int((land & near).sum()), "rate": ratio(int((pred & land & near).sum()), int((land & near).sum()))},
        "far": {"pixels": int((land & ~near).sum()), "rate": ratio(int((pred & land & ~near).sum()), int((land & ~near).sum()))},
    }
    return out


def cohen_kappa(pairs, labels):
    """Cohen's kappa of (predicted, reference) label pairs; None with no pairs or no chance disagreement."""
    n = len(pairs)
    if n == 0:
        return None
    po = sum(a == b for a, b in pairs) / n
    pe = sum((sum(a == k for a, _ in pairs) / n) * (sum(b == k for _, b in pairs) / n) for k in labels)
    return None if pe >= 1 else round((po - pe) / (1 - pe), 4)


def status_scores(pred, ref, ids, access_m):
    """
    Community status of one pass against a reference status (both {id: [code, bottleneck_m, distance_m]}).
    Only communities both judge (no no_data) and that are not inland in both (water within access_m) count.
      false_route   the method shows a water route (connected or at risk) the reference does not have: the
                    dangerous error, a community told it can travel when it cannot
      overconfident connected where the reference only finds a narrow route (at risk)
      false_isolated  no route where the reference has one: the safe-side error
    """
    pairs, matrix = [], {p: {r: 0 for r in STATUS_KEYS} for p in STATUS_KEYS}
    for cid in ids:
        a, b = pred.get(cid), ref.get(cid)
        if not a or not b or a[0] not in CODE_KEY or b[0] not in CODE_KEY:
            continue
        inland = all(r[2] is not None and r[2] > access_m for r in (a, b))
        if inland:
            continue
        pairs.append((a[0], b[0]))
        matrix[CODE_KEY[a[0]]][CODE_KEY[b[0]]] += 1
    n = len(pairs)
    false_route = sum(p in LINKED and r == STATUS["isolated"] for p, r in pairs)
    over = sum(p == STATUS["connected"] and r == STATUS["at_risk"] for p, r in pairs)
    false_iso = sum(p == STATUS["isolated"] and r in LINKED for p, r in pairs)
    ref_iso = sum(r == STATUS["isolated"] for _, r in pairs)
    return {"n": n, "agreement": ratio(sum(p == r for p, r in pairs), n),
            "kappa": cohen_kappa(pairs, [STATUS[k] for k in STATUS_KEYS]),
            "false_route": false_route, "overconfident": over, "false_isolated": false_iso,
            "isolated_recall": ratio(sum(p == r == STATUS["isolated"] for p, r in pairs), ref_iso),
            "matrix_pred_by_ref": matrix}


def spearman(x, y):
    """Spearman rank correlation {rho, n} (rho None with fewer than 3 pairs or a constant series)."""
    pairs = [(a, b) for a, b in zip(x, y, strict=True) if a is not None and b is not None]
    if len(pairs) < 3 or len({a for a, _ in pairs}) < 2 or len({b for _, b in pairs}) < 2:
        return {"rho": None, "n": len(pairs)}
    rho = stats.spearmanr([a for a, _ in pairs], [b for _, b in pairs]).statistic
    return {"rho": None if math.isnan(rho) else round(float(rho), 4), "n": len(pairs)}


def grade(expected, code):
    """
    Grade of one synthetic community status against what the scene allows:
      expected "connected"  correct only when connected; at_risk or isolated is a conservative miss
      expected "narrow"     channel narrower than the safe width: at_risk or isolated are correct (going the safe
                            way is accepted), connected is dangerous
      expected "isolated"   no navigable route (blocked by vegetation or mud): isolated is correct, any route is
                            dangerous
    Returns "correct", "conservative", "dangerous" or "no_data".
    """
    if code not in CODE_KEY:
        return "no_data"
    if expected == "connected":
        return "correct" if code == STATUS["connected"] else "conservative"
    if expected == "narrow":
        return "dangerous" if code == STATUS["connected"] else "correct"
    if expected == "isolated":
        return "correct" if code == STATUS["isolated"] else "dangerous"
    raise ValueError(f"unknown expectation {expected!r}")


def unpack_layers(path):
    """Every boolean layer of a mask file written by output.layers (packed bits plus `shape`), by name."""
    with np.load(path) as z:
        shape = tuple(int(v) for v in z["shape"])
        n = shape[0] * shape[1]
        return {k: np.unpackbits(z[k])[:n].reshape(shape).astype(bool) for k in z.files if k != "shape"}
