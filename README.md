# Walking to everyday life in Metro Manila

How much of everyday life is a short walk from home, for every resident of every Metro Manila barangay?

**Compare any three barangays on foot: [https://earlcyu-petcircle.github.io/ph-urban-accessibility/](https://earlcyu-petcircle.github.io/ph-urban-accessibility/)**

The site is one full-screen map.
Pick up to three barangays and it compares the walk to nine everyday services (food shops, the palengke, pharmacies, clinics, hospitals, public elementary and high schools, open space and transit) for all 14 million people of the 2024 census, placed in their buildings and walked along the street network.
The method, limitations and citation are below.
Earl Yu, November 2026.
Open data only.

## Where things are

| Path | What it holds |
|---|---|
| [`docs/index.html`](docs/index.html), [`docs/map/`](docs/map/) | The site, a full-screen comparison map served by GitHub Pages from `docs/`; `docs/map/data/` holds every barangay's measures and the map tiles |
| [`docs/data-quality.md`](docs/data-quality.md) | How each source was collected, parsed and joined, the checks and their results, and where the gaps sit |
| [`notebooks/`](notebooks/) | The six analysis notebooks, run with their outputs |
| [`src/`](src/) | The pipeline code, one folder per phase script; paths and study constants in `src/shared/common.py` |
| [`results/`](results/), [`data/derived/`](data/derived/) | The committed measure, check and audit tables, the figures, and the small barangay and data-quality tables |

## What the map compares

Each pick is compared with the others and with Metro Manila as a whole.

| Measure | What it says |
|---|---|
| 15-minute score (0-100) | The share of the nine services with at least one within a 15-minute walk (1,050 m), averaged over the barangay's residents; 100 means everyone has all nine |
| Minutes to the nearest | The walk for the barangay's median resident to the nearest service of each kind, and the share of residents within 10 minutes (700 m) |
| Choice | How many of each service are within 5, 10 and 15 minutes |
| Crowding | Service per resident once the neighbours who share it are counted (E2SFCA, 15-minute catchment), against Metro Manila |
| Transit | The UN test of convenient public transport (SDG 11.2.1): within 500 m of a bus or jeepney, or 1 km of an LRT or MRT station |
| Fairness | Where the barangay sits among all Metro Manila residents, and how even access is inside it |

Jollibee stores are tracked beside these, from OpenStreetMap, but are not part of the score or the rankings.
The study measures potential access and describes differences; it does not say where people actually go or explain the causes.

## Method

- **Place every resident.** Each barangay's 2024 census count is spread over WorldPop's 100 m cells, then over the residential buildings in each cell by footprint area: 1,573,122 buildings carry all 14,001,751 people.
- **Map the services.** Overture Maps places and OpenStreetMap, merged with duplicates grouped, and DepEd's list of public schools; services up to 2 km beyond Metro Manila count.
- **Walk the streets.** Every walkable OpenStreetMap way, expressways out and footbridges in, at 4.2 km/h, close to the observed Metro Manila pace.
- **Summarise per resident.** Every figure is weighted by people, never by area; a barangay's minutes are its median resident's.
- **Show it without showing homes.** The map shows barangays and H3 hexagons (about 0.015 km²); hexagons with fewer than five buildings are left off.

The parameters live in [`src/shared/common.py`](src/shared/common.py); the analysis, with each table and chart, is in [`notebooks/`](notebooks/).

## Limitations

- **Sari-sari stores are almost unmapped.** Only 234 are named in all of Metro Manila's open data, so the walk to everyday food is too long everywhere, most of all in dense streets.
- **Mapped is not there.** New shops are missed and closed ones kept; Overture also lists some hospital clinics and wards as hospitals.
- **No health registry.** The DOH facility registry cannot be exported, so hospitals and clinics rest on open map data, and hospitals count one each rather than by beds.
- **Jeepney routes are thinly mapped** (95 in the study area), so transit shares are floors.
- **The walk itself is not scored:** heat, floods, crossings and sidewalks are not in the network.
- **The edge of Metro Manila.** People just outside it are not placed, so services near the edge look less crowded than they are.
- **The layers come from different years:** the census is from mid-2024, places and streets from late 2026.
- **Only the three example barangays** (Barangay 136, Loyola Heights and Oranbo) have been through the study's ten sensitivity checks; small gaps between other picks may not hold.

## How to reproduce

Needs Python 3.12, `curl`, [tippecanoe](https://github.com/felt/tippecanoe) (`brew install tippecanoe`) and about 1.3 GB of downloads.
Nothing is installed globally: `src/shared/setup.sh` makes a local virtual environment from `requirements.txt`.
The PSA 2024 census workbook refuses scripted downloads, so save it by hand into `data/manual/` first, as [`docs/data-quality.md`](docs/data-quality.md#getting-the-hand-downloads) describes.

```bash
git clone https://github.com/earlcyu-petcircle/ph-urban-accessibility.git
cd ph-urban-accessibility
./run_all.sh              # every phase below, in order (--refresh downloads everything again)

./01_collect_data.sh      # downloads into data/raw/
./02_build_tables.sh      # people, services and the walking network
./03_analyse.sh           # the five measures, checks and audits in results/
./04_build_map.sh         # the comparison site's data in docs/map/data/
.venv/bin/python src/04_build_map/serve_map.py   # the map at http://localhost:8000/
```

The map reads PMTiles by HTTP range requests, so the site does not open from `file://`; `serve_map.py` is a small range-aware server for `docs/`.

The checks that run on every pull request:

```bash
ruff check . && ruff format --check .
pytest
```

## Data sources

Every source is public and free to download.

| Role | Source | Licence |
|---|---|---|
| People | PSA 2024 Census of Population, by barangay | PSA publication |
| Where people live | [WorldPop](https://data.humdata.org/dataset/worldpop-population-counts-2015-2030-phl) R2025A, 100 m; [Overture Maps](https://docs.overturemaps.org/) buildings | CC BY 4.0; ODbL |
| Population check | JRC GHS-POP R2023A | CC BY 4.0 |
| Boundaries | [OCHA COD-AB Philippines](https://data.humdata.org/dataset/cod-ab-phl) | CC BY-IGO |
| Services | Overture Maps places; [OpenStreetMap](https://download.geofabrik.de/asia/philippines.html) | CDLA Permissive 2.0; ODbL |
| Public schools | DepEd school list via OpenStreetMap Philippines' [OSMaPaaralan](https://github.com/OSMPH/deped_schools_db) | DepEd data published for OpenStreetMap use |
| Streets and transit | OpenStreetMap, Geofabrik Philippines extract | ODbL |

[`docs/data-quality.md`](docs/data-quality.md) records each file's snapshot date, row counts and checks.

## Cite

Yu, E. (2026). Walking to everyday life: access to services in three Metro Manila barangays. https://earlcyu-petcircle.github.io/ph-urban-accessibility/

```bibtex
@misc{yu2026walking,
  author       = {Yu, Earl},
  title        = {Walking to everyday life: access to services in three Metro Manila barangays},
  year         = {2026},
  month        = nov,
  howpublished = {\url{https://earlcyu-petcircle.github.io/ph-urban-accessibility/}},
  note         = {Code and data: \url{https://github.com/earlcyu-petcircle/ph-urban-accessibility}}
}
```

## Licence

Code is MIT licensed (see [LICENSE](LICENSE)).
The data keep their own licences, listed above, and the committed tables, figures and map tiles are built from them.
