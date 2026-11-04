"""
The static figures, in the Atlas Grid style with the Riso data palette (src/shared/atlas.py),
drawn and saved to results/figures/. Each function takes a results table and returns the saved
file, which the notebook shows inline.

  m1_chart(m)          minutes to the nearest service: median and P10 to P90 per barangay,
                       against the Metro Manila median (m1_nearest_walk.png)
  m2_chart(m)          services within 10 minutes, median resident (m2_choice.png)
  m3_chart(m)          E2SFCA access against the Metro Manila mean (m3_crowding.png)
  m4_chart(m)          how many of the nine categories are within 15 minutes (m4_coverage.png)
  m5_chart(m)          shares with convenient transit, UN SDG 11.2.1 (m5_transit.png)
  context_chart(c)     each barangay's median resident among Metro Manila's (context_percentiles.png)
  robustness_chart(r)  which differences survive the ten checks (robustness.png)

The three barangays keep the first three categorical colours everywhere (cobalt, pink, amber);
Metro Manila is ink.
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))  # shared helpers in src/shared/

import atlas
from common import CATEGORIES, FIGURES
from measures import LABEL, M3_CATEGORIES, STUDY

COLOUR = dict(zip(STUDY, atlas.CATEGORICAL[:3], strict=True)) | {"Metro Manila": atlas.INK}
SOURCE = "Sources: PSA 2024 census, WorldPop, Overture Maps, OpenStreetMap, DepEd. Walking at 4.2 km/h."


def _figure(figsize):
    """A figure on its own Agg canvas, outside pyplot, so a notebook does not also draw it."""
    fig = Figure(figsize=figsize, dpi=200)
    FigureCanvasAgg(fig)
    return fig


def _save(fig, name):
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / name)
    return FIGURES / name


def _value(m, area, measure, stat, category=""):
    v = m[(m.area == area) & (m.measure == measure) & (m.stat == stat) & (m.category.fillna("") == category)].value
    return float(v.iloc[0])


def _legend(fig, names, y=0.012):
    handles = [plt.Line2D([], [], marker="o", linestyle="", markersize=6, color=COLOUR[n], label=n) for n in names]
    fig.legend(handles=handles, loc="lower left", ncol=len(names), fontsize=8, bbox_to_anchor=(0.005, y))


def _source(fig):
    fig.text(0.995, 0.012, SOURCE, ha="right", va="bottom", color=atlas.MUTED, fontsize=6.5)


def _category_axis(ax, cats):
    ax.set_yticks(range(len(cats)), [LABEL[c] for c in cats])
    ax.set_ylim(len(cats) - 0.5, -0.5)
    atlas.bare(ax)


def m1_chart(m):
    cats = list(CATEGORIES)
    top = max(_value(m, a, "M1", "p90_min", c) for a in STUDY for c in cats)
    with plt.rc_context(atlas.style()):
        fig = _figure((8.6, 5.6))
        ax = fig.subplots()
        for i, c in enumerate(cats):
            metro = _value(m, "Metro Manila", "M1", "median_min", c)
            ax.plot([metro, metro], [i - 0.38, i + 0.38], color=atlas.INK, linewidth=1.6, solid_capstyle="butt")
            for k, a in enumerate(STUDY):
                y = i + (k - 1) * 0.22
                lo, mid, hi = (_value(m, a, "M1", s, c) for s in ("p10_min", "median_min", "p90_min"))
                ax.plot([lo, hi], [y, y], color=COLOUR[a], linewidth=1.8, alpha=0.45, solid_capstyle="butt")
                ax.plot(mid, y, "o", color=COLOUR[a], markersize=5.5)
        for x in (5, 10, 15, 20):
            ax.axvline(x, color=atlas.RULE, linewidth=0.8, zorder=0)
        _category_axis(ax, cats)
        ax.set_xlim(0, min(top * 1.05, 40))
        ax.set_xticks(
            [0, 5, 10, 15, 20, 25, 30],
            [f"{x}" for x in (0, 5, 10, 15, 20, 25, 30)],
            fontfamily=atlas.family(atlas.MONO),
            fontsize=7.5,
        )
        ax.set_xlabel("Minutes on foot to the nearest one", fontsize=8.5)
        top_room = atlas.heading(
            fig,
            "M1: how long the walk to the nearest service takes",
            "Dot: median resident. Bar: P10 to P90 of residents. Black tick: Metro Manila median.",
        )
        fig.tight_layout(rect=(0, 0.06, 1, top_room))
        _legend(fig, STUDY + ["Metro Manila"])
        _source(fig)
        return _save(fig, "m1_nearest_walk.png")


def _grouped_bars(ax, cats, values, areas, fmt):
    h = 0.8 / len(areas)
    top = max(max(values[a]) for a in areas) or 1
    for k, a in enumerate(areas):
        ys = np.arange(len(cats)) + (k - (len(areas) - 1) / 2) * h
        ax.barh(ys, values[a], height=h * 0.9, color=COLOUR[a], zorder=2)
        for y, v in zip(ys, values[a], strict=True):
            ax.text(v + top * 0.01, y, fmt(v), va="center", color=atlas.INK, **atlas.mono(6.5))
    _category_axis(ax, cats)
    ax.axvline(0, color=atlas.INK, linewidth=1.5, zorder=3)
    ax.set_xticks([])
    ax.set_xlim(0, top * 1.15)


def m2_chart(m):
    cats = list(CATEGORIES)
    areas = STUDY + ["Metro Manila"]
    values = {a: [_value(m, a, "M2", "median_within_10min", c) for c in cats] for a in areas}
    with plt.rc_context(atlas.style()):
        fig = _figure((8.6, 6.2))
        ax = fig.subplots()
        _grouped_bars(ax, cats, values, areas, lambda v: f"{v:.0f}")
        top_room = atlas.heading(
            fig,
            "M2: how many are within a 10-minute walk",
            "Services of each category within 700 m on foot of the median resident.",
        )
        fig.tight_layout(rect=(0, 0.06, 1, top_room))
        _legend(fig, areas)
        _source(fig)
        return _save(fig, "m2_choice.png")


def m3_chart(m):
    cats = list(M3_CATEGORIES)
    areas = STUDY
    values = {
        a: [_value(m, a, "M3", "mean_per_10k", c) / _value(m, "Metro Manila", "M3", "mean_per_10k", c) for c in cats]
        for a in areas
    }
    with plt.rc_context(atlas.style()):
        fig = _figure((8.6, 5.8))
        ax = fig.subplots()
        _grouped_bars(ax, cats, values, areas, lambda v: f"{v:.1f}x")
        ax.axvline(1, color=atlas.INK, linewidth=1.1, linestyle=(0, (3, 3)), zorder=3)
        top_room = atlas.heading(
            fig,
            "M3: supply per resident once neighbours are counted",
            "E2SFCA access (15-minute catchment, Gaussian decay), mean resident, as a multiple of the Metro Manila"
            "\nmean. Dashed line: Metro Manila. Schools weigh DepEd enrolment; other services count 1 each.",
        )
        fig.tight_layout(rect=(0, 0.06, 1, top_room))
        _legend(fig, areas)
        _source(fig)
        return _save(fig, "m3_crowding.png")


def m4_chart(m):
    areas = STUDY + ["Metro Manila"]
    groups = [("5 or fewer", range(0, 6)), ("6", [6]), ("7", [7]), ("8", [8]), ("All 9", [9])]
    colours = atlas.SEQUENTIAL[1:]
    with plt.rc_context(atlas.style()):
        fig = _figure((8.6, 3.6))
        ax = fig.subplots()
        for i, a in enumerate(areas):
            left = 0.0
            for (_label, ks), col in zip(groups, colours, strict=True):
                share = sum(_value(m, a, "M4", f"share_with_{k}") for k in ks)
                ax.barh(i, share, left=left, color=col, height=0.62, zorder=2)
                if share >= 0.06:
                    ink = atlas.BG if col in colours[2:] else atlas.INK
                    ax.text(
                        left + share / 2,
                        i,
                        f"{share:.0%}",
                        ha="center",
                        va="center",
                        color=ink,
                        **atlas.mono(7, bold=True),
                    )
                left += share
            mean = _value(m, a, "M4", "mean_categories_within_15min")
            ax.text(1.01, i, f"mean {mean:.1f}", va="center", color=atlas.INK, **atlas.mono(7.5))
        ax.set_yticks(range(len(areas)), areas)
        ax.set_ylim(len(areas) - 0.5, -0.5)
        ax.set_xlim(0, 1)
        ax.set_xticks([])
        atlas.bare(ax)
        handles = [plt.Rectangle((0, 0), 1, 1, color=c, label=lab) for (lab, _), c in zip(groups, colours, strict=True)]
        fig.legend(handles=handles, loc="lower left", ncol=5, fontsize=8, bbox_to_anchor=(0.005, 0.012), title=None)
        top_room = atlas.heading(
            fig,
            "M4: how many of the nine basics are within 15 minutes",
            "Share of residents by the number of service categories within 1,050 m on foot.",
        )
        fig.tight_layout(rect=(0, 0.1, 0.9, top_room))
        _source(fig)
        return _save(fig, "m4_coverage.png")


def m5_chart(m):
    areas = STUDY + ["Metro Manila"]
    stats = [
        ("share_within_500m_bus_jeepney", "Bus or jeepney\nwithin 500 m"),
        ("share_within_1km_rail", "LRT or MRT\nwithin 1 km"),
        ("share_convenient", "Either\n(SDG 11.2.1)"),
    ]
    with plt.rc_context(atlas.style()):
        fig = _figure((8.6, 3.9))
        ax = fig.subplots()
        w = 0.8 / len(areas)
        for k, a in enumerate(areas):
            xs = np.arange(len(stats)) + (k - (len(areas) - 1) / 2) * w
            vals = [_value(m, a, "M5", s) for s, _ in stats]
            ax.bar(xs, vals, width=w * 0.9, color=COLOUR[a], zorder=2)
            for x, v in zip(xs, vals, strict=True):
                ax.text(x, v + 0.02, f"{v:.0%}", ha="center", va="bottom", color=atlas.INK, **atlas.mono(6.5))
        atlas.bare(ax)
        atlas.baseline(ax)
        ax.set_ylim(0, 1.15)
        ax.set_yticks([])
        ax.set_xticks(range(len(stats)), [lab for _, lab in stats], fontsize=8.5)
        top_room = atlas.heading(
            fig,
            "M5: share of residents with convenient public transport",
            "By street distance. Jeepneys count anywhere on a mapped route (UN SDG 11.2.1).",
        )
        fig.tight_layout(rect=(0, 0.08, 1, top_room))
        _legend(fig, areas)
        _source(fig)
        return _save(fig, "m5_transit.png")


def context_chart(c):
    metrics = [f"M1 {k}" for k in CATEGORIES] + ["M4"]
    labels = [LABEL[k] for k in CATEGORIES] + ["Coverage (M4)"]
    with plt.rc_context(atlas.style()):
        fig = _figure((8.6, 5.6))
        ax = fig.subplots()
        for i in range(len(metrics)):
            ax.plot([0, 1], [i, i], color=atlas.GRID, linewidth=6, solid_capstyle="butt", zorder=0)
        for k, a in enumerate(STUDY):
            d = c[c.barangay == a].set_index("metric").reindex(metrics)
            ys = np.arange(len(metrics)) + (k - 1) * 0.18
            ax.plot(d.share_metro_worse, ys, "o", color=COLOUR[a], markersize=5.5, zorder=3)
        ax.axvline(0.5, color=atlas.INK, linewidth=1.1, linestyle=(0, (3, 3)))
        ax.set_yticks(range(len(metrics)), labels)
        ax.set_ylim(len(metrics) - 0.5, -0.5)
        ax.set_xlim(-0.02, 1.02)
        ax.set_xticks(
            [0, 0.25, 0.5, 0.75, 1],
            ["0%", "25%", "50%", "75%", "100%"],
            fontfamily=atlas.family(atlas.MONO),
            fontsize=7.5,
        )
        atlas.bare(ax)
        ax.set_xlabel("Share of Metro Manila residents with worse access than the median resident here", fontsize=8.5)
        top_room = atlas.heading(
            fig,
            "Where each barangay's median resident sits in Metro Manila",
            "Right is better. Dashed line: the Metro Manila median.",
        )
        fig.tight_layout(rect=(0, 0.06, 1, top_room))
        _legend(fig, STUDY)
        _source(fig)
        return _save(fig, "context_percentiles.png")


def robustness_chart(r):
    metrics = [f"M1 {k}" for k in CATEGORIES] + ["M4", "M5"]
    labels = [LABEL[k] for k in CATEGORIES] + ["Coverage (M4)", "Transit (M5)"]
    pairs = sorted(set(zip(r.a, r.b, strict=True)), key=lambda p: (STUDY.index(p[0]), STUDY.index(p[1])))
    state = {
        "survives": (atlas.ACCENT, "Holds in every check"),
        "tie": (atlas.SEQUENTIAL[1], "Ties in at least one check, never reverses"),
        "reversed": (atlas.CATEGORICAL[1], "Reverses in at least one check"),
        "base_tie": (atlas.NO_DATA, "No difference in the base case"),
    }
    with plt.rc_context(atlas.style()):
        fig = _figure((8.6, 5.4))
        ax = fig.subplots()
        for i, metric in enumerate(metrics):
            for j, (a, b) in enumerate(pairs):
                row = r[(r.metric == metric) & (r.a == a) & (r.b == b)].iloc[0]
                key = (
                    "base_tie"
                    if row.better_in_base == "tie"
                    else "survives"
                    if row.survives
                    else "tie"
                    if row.never_reversed
                    else "reversed"
                )
                ax.add_patch(plt.Rectangle((j + 0.04, i - 0.42), 0.92, 0.84, color=state[key][0]))
                if row.better_in_base != "tie":
                    ink = atlas.BG if key in ("survives", "reversed") else atlas.INK
                    ax.text(j + 0.5, i, row.better_in_base, ha="center", va="center", color=ink, fontsize=7)
        ax.set_xlim(0, len(pairs))
        ax.set_ylim(len(metrics) - 0.5, -0.5)
        ax.set_yticks(range(len(metrics)), labels)
        ax.set_xticks([j + 0.5 for j in range(len(pairs))], [f"{a}\nvs {b}" for a, b in pairs], fontsize=8)
        ax.xaxis.tick_top()
        atlas.bare(ax)
        handles = [plt.Rectangle((0, 0), 1, 1, color=col, label=lab) for col, lab in state.values()]
        fig.legend(handles=handles, loc="lower left", ncol=2, fontsize=7.5, bbox_to_anchor=(0.005, 0.005))
        top_room = atlas.heading(
            fig,
            "Which differences survive the ten checks",
            "Each cell names the barangay with better access in the base case.",
        )
        fig.tight_layout(rect=(0, 0.1, 1, top_room))
        return _save(fig, "robustness.png")
