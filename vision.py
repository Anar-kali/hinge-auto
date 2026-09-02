"""Image-based detection for UI elements whose position varies per profile.

The compose box (Send Like button + comment input) anchors to whichever
element's heart was tapped, so its absolute y coordinate shifts based on
photo height and scroll state. Static COORDS in config don't survive
across profiles — we have to find these elements at tap-time.
"""

import io

import numpy as np
from PIL import Image
from scipy.ndimage import label, find_objects


def _png_to_array(png: bytes) -> np.ndarray:
    return np.array(Image.open(io.BytesIO(png)).convert("RGB"))


def find_send_like(png: bytes) -> tuple[int, int] | None:
    """Locate the peach 'Send Like' button. Returns (x, y) center or None.

    The button is a wide peach pill (~595x109) sitting on the right side
    of the compose card. Some peach-toned prompt bubbles look similar in
    color and size, so we filter on:
      - width 500-700, height 80-130, area > 30000 (size of the pill)
      - x_center > 500 (Send Like is right-aligned; prompt pills are
        often left-aligned)
    When multiple candidates pass, pick the topmost — the compose card
    sits above any prompt elements visible below it.
    """
    arr = _png_to_array(png)
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    peach = (
        (r > 220) & (g > 190) & (g < 235) & (b > 170) & (b < 220)
        & (r > g) & (g > b)
    )
    labeled, _ = label(peach)
    candidates = []
    for i, sl in enumerate(find_objects(labeled), 1):
        if sl is None:
            continue
        y0, y1 = sl[0].start, sl[0].stop
        x0, x1 = sl[1].start, sl[1].stop
        h, w = y1 - y0, x1 - x0
        area = (labeled[sl] == i).sum()
        if not (500 < w < 700 and 80 < h < 130 and area > 30000):
            continue
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        if cx <= 500:
            continue
        candidates.append((cy, cx))
    if not candidates:
        return None
    candidates.sort()
    cy, cx = candidates[0]
    return (cx, cy)


def _ring_fraction(mask, cx: int, cy: int, r: int, n: int = 48) -> float:
    """Fraction of n points sampled on a circle of radius r that are set."""
    ang = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    xs = np.clip((cx + r * np.cos(ang)).astype(int), 0, mask.shape[1] - 1)
    ys = np.clip((cy + r * np.sin(ang)).astype(int), 0, mask.shape[0] - 1)
    return float(mask[ys, xs].mean())


def _hearts_by_glyph(glyph, disc) -> list[tuple[int, int]]:
    """Locate heart badges via the small glyph, confirming the disc colour
    fills the ring around it. Returns (cy, cx) pairs.

    Anchoring on the glyph rather than the disc is deliberate. The disc
    merges into dark photo content - a doorway, a carved wooden frame -
    which destroys any size or shape filter applied to the disc blob
    itself (observed: a heart fused into a 174x974 blob). The glyph never
    touches the photo, because the disc encloses it.
    """
    labeled, _ = label(glyph)
    out = []
    for i, sl in enumerate(find_objects(labeled), 1):
        if sl is None:
            continue
        y0, y1 = sl[0].start, sl[0].stop
        x0, x1 = sl[1].start, sl[1].stop
        h, w = y1 - y0, x1 - x0
        # Measured glyph across builds: 60x55, area ~1168.
        if not (40 < w < 80 and 35 < h < 75):
            continue
        area = (labeled[sl] == i).sum()
        if not (800 < area < 1900):
            continue
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        if cx <= 800:
            continue
        # Both radii sit inside the ~126px disc but outside the ~60px
        # glyph, so both rings must be disc-coloured.
        if _ring_fraction(disc, cx, cy, 50) < 0.80:
            continue
        if _ring_fraction(disc, cx, cy, 58) < 0.80:
            continue
        out.append((cy, cx))
    return out


def find_first_heart(png: bytes) -> tuple[int, int] | None:
    """Locate the heart icon on photo 1 (topmost heart in current view).

    Hinge's heart-on-photo widget is a ~126px circle at the photo's
    bottom-right, containing a ~60x55 heart glyph. Two builds exist: a
    DARK disc with a white glyph (current), and an older WHITE disc with
    a dark glyph. Both are checked.

    Returns the topmost hit (lowest y) - photo 1 when scrolled to top.
    """
    hearts = find_hearts(png)
    return hearts[0] if hearts else None


def find_hearts(png: bytes) -> list[tuple[int, int]]:
    """Every heart icon in the current view, ordered top to bottom.

    Each photo and prompt card carries its own heart, and liking via a
    given card attaches the like to THAT content. Returns (x, y) centres
    so callers can aim at the card the opener actually talks about.
    """
    arr = _png_to_array(png)
    white = (arr[..., 0] > 235) & (arr[..., 1] > 235) & (arr[..., 2] > 235)
    dark = arr.max(axis=-1) < 90

    hearts = _hearts_by_glyph(white, dark)
    hearts += _hearts_by_glyph(dark, white)
    hearts.sort()                      # by y, then x
    return [(cx, cy) for cy, cx in hearts]


def comment_field_text_pixels(png: bytes, send_like_xy: tuple[int, int]) -> int:
    """Count dark (text) pixels in the comment input area above Send Like.

    Empty field shows only faint grey placeholder ('Add a comment') — very
    few dark pixels. A filled field has many dark pixels from typed text.
    Used to verify that `adb shell input text` actually landed before
    Send Like fires (events can drop under host CPU contention).
    """
    arr = _png_to_array(png)
    sx, sy = send_like_xy
    y0 = max(0, sy - 230)
    y1 = max(0, sy - 60)
    x0 = max(0, sx - 350)
    x1 = min(arr.shape[1], sx + 350)
    region = arr[y0:y1, x0:x1]
    if region.size == 0:
        return 0
    dark = (region.max(axis=-1) < 130).sum()
    return int(dark)


def find_comment_input(send_like_xy: tuple[int, int]) -> tuple[int, int]:
    """Comment input sits at a fixed offset above the Send Like button.

    Measured offset across two profiles: ~171px above, x ~540 (centered
    in the compose card, not aligned with Send Like). Stable because the
    compose card's internal layout is fixed; only the whole card shifts.
    """
    _, send_y = send_like_xy
    return (540, send_y - 171)
