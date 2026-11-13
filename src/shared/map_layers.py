"""
What the web map's tiles (src/04_build_map/build_map_tiles.py) and its page (docs/map/) share:
the category codes, the fixed classes every category uses, and the colours, which
src/04_build_map/write_web_palette.py writes to docs/map/palette.js.

Colours are the Atlas data palette, Riso (atlas.py): cobalt for better access, pale for worse.
"""

import atlas
from common import CATEGORIES

# Short property names in the tiles, in the order of CATEGORIES
CODES = dict(zip(CATEGORIES, ("food", "mkt", "phar", "care", "hosp", "elem", "high", "open", "trans"), strict=True))

# Fixed classes, the same for every category, so colours compare across categories.
# The 15-minute score (M4 as 0-100): under 50, 50-70, 70-80, 80-90, 90-99, 100 (all nine basics)
SCORE_BREAKS = [50, 70, 80, 90, 99.95]
SCORE = atlas.SEQUENTIAL
# Minutes to the nearest (M1): darkest is within 5 minutes, palest 30 or more.
MINUTE_BREAKS = [5, 10, 15, 20, 30]
MINUTES = list(reversed(atlas.SEQUENTIAL))
# Services within the chosen time (M2): none, 1, 2-3, 4-7, 8-15, 16 or more
COUNT_BREAKS = [1, 2, 4, 8, 16]
COUNTS = [atlas.NO_DATA, *atlas.SEQUENTIAL[1:]]
# Categories within the chosen time (M4), people-weighted mean per hexagon: under 5, 5, 6, 7, 8, 9
COVER_BREAKS = [5, 6, 7, 8, 8.95]
COVER = atlas.SEQUENTIAL
# Share of residents with convenient transit (M5): under 25%, 25-50, 50-75, 75-95, 95 or more
SHARE_BREAKS = [25, 50, 75, 95]
SHARE = atlas.SEQUENTIAL[1:]
# The three comparison slots keep the chart colours (cobalt, pink, amber)
SLOTS = atlas.CATEGORICAL[:3]
# Service points: plum, the strongest Riso colour left once the slots take cobalt, pink and amber
# (teal would sit beside the pink slot, which the palette's colour-blind rule forbids); drawn
# with a white halo so they stand out on the pale basemap
SERVICE = atlas.CATEGORICAL[4]
# Transit lines: rail in ink, bus in sky, jeepney in plum (not the barangay colours)
TRANSIT = {"rail": atlas.INK, "bus": atlas.CATEGORICAL[5], "jeepney": atlas.CATEGORICAL[4]}
# Jollibee stores, tracked beside the nine services: ink dots with a white halo, apart from the
# plum service dots and the white rail stations ringed in ink
JOLLIBEE = atlas.INK
NO_PEOPLE = atlas.NO_PEOPLE
