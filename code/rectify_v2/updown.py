"""0/180 decision on a rectified page (staff lines horizontal). Three cues, summed:
   ink at staff ends (clef/brace side is denser), and two clef-template matches (different staff finders).
   Templates: clef_tpl_f.npy, cut from renderings of the OLD print set (pieces not in the test set)."""
import os
import numpy as np
from ud2 import prep, end_score
from clef import find_staves_rect, find_staves_profile, refine_ends, crop_end, ncc_shift
from staff import ink_map

T = np.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'clef_tpl_f.npy'))

def _clef(st, ink, refine):
    sc = []
    for x0, x1, yt, il in st:
        a, b = refine_ends(ink, x0, x1, yt, il) if refine else (x0, x1)
        sc.append(ncc_shift(crop_end(ink, a, yt, il, 'L'), T) - ncc_shift(crop_end(ink, b, yt, il, 'R'), T))
    return float(np.mean(sc)) if sc else 0.0

def _one(g):
    s_ink, _ = end_score(prep(g))
    st1, _ = find_staves_rect(g)
    c1 = _clef(st1, ink_map(g), True)
    st2, _, ink2 = find_staves_profile(g)
    c2 = _clef(st2, ink2, False)
    return s_ink + 0.5 * c1 + 0.5 * c2, dict(ink=s_ink, c1=c1, c2=c2)


def updown(g):
    """g: gray rectified page (~1600 px wide). Returns score: >0 upright, <0 upside down.
    Antisymmetric by construction: score(g) = -score(rot180(g))."""
    a, ca = _one(g)
    b, cb = _one(np.ascontiguousarray(g[::-1, ::-1]))
    return (a - b) / 2, {k: (ca[k] - cb[k]) / 2 for k in ca}
