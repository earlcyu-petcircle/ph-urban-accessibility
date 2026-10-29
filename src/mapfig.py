#!/usr/bin/env python3
"""
Step 7: the static preview for the README, figures/preview_map.png.
A large composite map with the three places lived outlined, and one small map per service.
"""
import logging

import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from common import (ACCENT, BG, DERIVED, FAINT, FIGURES, INK, MUTED, SCORE_BREAKS, SCORE_COLOURS, SERVICE_LABELS,
                    SERVICES)

b = gpd.read_file(DERIVED / "barangay_scores.geojson").to_crs("EPSG:32651")
lived = gpd.read_file(DERIVED / "places_lived.geojson").to_crs("EPSG:32651")
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)  # Newsreader falls back to Georgia
cmap = ListedColormap(SCORE_COLOURS)
norm = BoundaryNorm([0] + SCORE_BREAKS + [100.01], cmap.N)

plt.rcParams.update({"font.family": "serif", "font.serif": ["Newsreader", "Georgia", "DejaVu Serif"],
                     "text.color": INK, "axes.edgecolor": BG})
fig = plt.figure(figsize=(14, 9.6), facecolor=BG)
gs = fig.add_gridspec(2, 5, width_ratios=[1.3, 1.3, 1, 1, 1], wspace=0.04, hspace=0.1,
                      left=0.01, right=0.99, top=0.86, bottom=0.03)


def draw(ax, col, title):
    ax.set_facecolor(BG)
    b.plot(column=col, ax=ax, cmap=cmap, norm=norm, linewidth=0.05, edgecolor="#FFFDF7",
           missing_kwds={"color": "#D9CFBA"})
    ax.set_title(title, fontsize=12, color=INK, loc="left")
    ax.set_axis_off()


ax = fig.add_subplot(gs[:, :2])
draw(ax, "composite", "All five services (equal weights)")
lived.boundary.plot(ax=ax, color=ACCENT, linewidth=1.6, linestyle=(0, (4, 2)))
x0, x1 = ax.get_xlim()
ax.set_xlim(x0 - 6000, x1)  # room for the Tondo label over the bay
offsets = {"tondo": (-3000, -5000), "loyola": (3500, 2500), "oranbo": (4500, -1500)}
for _, r in lived.iterrows():
    p = r.geometry.representative_point()
    dx, dy = offsets[r.place_lived]
    ax.annotate(r.label, (p.x, p.y), (p.x + dx, p.y + dy), fontsize=10.5, color=INK,
                ha="right" if dx < 0 else "left",
                bbox=dict(boxstyle="square,pad=0.25", fc="#F8F3E8", ec=ACCENT, lw=0.8),
                arrowprops=dict(arrowstyle="-", color=ACCENT, lw=0.9))

for i, s in enumerate(SERVICES):
    draw(fig.add_subplot(gs[i // 3, 2 + i % 3]), f"score_{s}", SERVICE_LABELS[s])

lax = fig.add_subplot(gs[1, 4])
lax.set_axis_off()
edges = [0] + SCORE_BREAKS + [100]
handles = [Patch(fc=c, ec="none", label=f"{lo}-{hi}") for c, lo, hi in zip(SCORE_COLOURS, edges, edges[1:])][::-1]
handles.append(Line2D([], [], color=ACCENT, lw=1.6, ls=(0, (4, 2)), label="places I have lived"))
lax.legend(handles=handles, loc="center left", frameon=False, title="Walking access score",
           title_fontsize=11, fontsize=10, labelcolor=INK)

fig.text(0.01, 0.958, "Who can walk to the basics in Metro Manila?", fontsize=20, color=INK)
fig.text(0.01, 0.927, "1,710 barangays scored 0-100: a resident counts fully within a 5 minute walk, "
         "two-thirds within 10, a third within 15.  PSA 2020 census, Overture Maps, OpenStreetMap.",
         fontsize=10.5, color=MUTED, family="sans-serif")
fig.text(0.99, 0.012, "Interactive map: docs/index.html", fontsize=9, color=FAINT, ha="right",
         family="sans-serif")
fig.savefig(FIGURES / "preview_map.png", dpi=130, facecolor=BG, metadata={"Software": None})
print("wrote figures/preview_map.png")
