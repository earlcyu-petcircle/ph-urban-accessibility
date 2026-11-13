# Walking to everyday life in Metro Manila

How much of everyday life is a short walk from home, for every resident of every Metro Manila barangay?

**Compare any three barangays on foot: [https://earlcyu-petcircle.github.io/ph-urban-accessibility/](https://earlcyu-petcircle.github.io/ph-urban-accessibility/)**

The site measures walking access to nine everyday services (food shops, the palengke, pharmacies, clinics, hospitals, public elementary and high schools, open space and transit) for all 14 million people of the 2024 census, placed in their buildings and walked along the street network.
Its research questions, method, limitations and citation are on the page.
Earl Yu, November 2026.
Open data only.

## Where things are

| Path | What it holds |
|---|---|
| [`docs/index.html`](docs/index.html), [`docs/map/`](docs/map/) | The story site and the comparison map, served by GitHub Pages from `docs/`; `docs/map/data/` holds every barangay's measures |
| [`docs/data-quality.md`](docs/data-quality.md) | How each source was collected, parsed and joined, the checks and their results, and where the gaps sit |
| [`notebooks/`](notebooks/) | The six analysis notebooks, run with their outputs |
| [`src/`](src/) | The pipeline code, one folder per phase script; paths and study constants in `src/shared/common.py` |
| [`results/`](results/), [`data/derived/`](data/derived/) | The committed measure, check and audit tables, the figures, and the small barangay and data-quality tables |

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
.venv/bin/python src/04_build_map/serve_map.py   # the site at http://localhost:8000/
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

## Licence

Code is MIT licensed (see [LICENSE](LICENSE)).
The data keep their own licences, listed above, and the committed tables, figures and map tiles are built from them.
