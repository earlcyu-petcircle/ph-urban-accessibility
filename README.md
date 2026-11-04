# Walking to everyday life: access to services in three Metro Manila barangays

Earl Yu, November 2026.
Open data only.

**Read the full paper: [docs/paper.md](docs/paper.md)**

Which of the three Metro Manila barangays I have lived in puts everyday life within a short walk?
This project compares walking access to nine everyday services (food shops, the palengke, pharmacies, clinics, hospitals, public schools, open space and transit) for every resident of three barangays, and sets each against the rest of Metro Manila.

| Barangay | City | For me | People (2024 census) |
|---|---|---|---:|
| Barangay 136 (Tondo) | City of Manila | Born and raised | 1,302 |
| Loyola Heights | Quezon City | Two years of college | 21,768 |
| Oranbo | City of Pasig | Home now | 3,374 |

**Status:** the research design is final, and the data are collected and built: every 2024 census resident of Metro Manila placed in a residential building, a nine-category service layer checked against the DepEd school list, and a 16,741 km walking network ([data-quality notes](docs/data-quality.md)).
Nothing has been analysed yet; the paper's results and discussion fill in as the next pull requests land.
One caveat is already known: sari-sari stores are almost absent from open maps, so food access will be understated, most of all in Barangay 136.

## Where things are

| Path | What it holds |
|---|---|
| [`docs/paper.md`](docs/paper.md) | The full paper: background, research questions, data sources, research design and web map plan, limitations, references and appendices; results and discussion to come |
| [`docs/data-quality.md`](docs/data-quality.md) | How each source was collected, parsed and joined, the checks and their results, and where the gaps sit |
| [`data/derived/`](data/derived/) | The small committed tables: barangays, service counts and registry matches, and every data-quality check |
| [`src/`](src/) | The pipeline code, one folder per phase script, plus shared paths and study constants in `src/shared/common.py` ([Appendix A](docs/paper.md#appendix-a-code-and-pipeline) of the paper) |
| [`notebooks/`](notebooks/) | The analysis notebooks, from PR 3 |
| [`results/tables/`](results/tables/), [`results/figures/`](results/figures/) | The measure, sensitivity and audit tables and the figures, from PR 3 |

## How to reproduce

Phases 1 and 2 run now; phases 3 and 4 stop with a message until PR 3 and PR 4 build them.

```bash
git clone https://github.com/earlcyu-petcircle/metro-manila-accessibility.git
cd metro-manila-accessibility
./run_all.sh              # every phase below, in order

./01_collect_data.sh      # downloads into data/raw/
./02_build_tables.sh      # people, services and the walking network
./03_analyse.sh           # the five measures, checks and audits in results/
./04_build_map.sh         # web map tiles in docs/map/data/
```

Needs Python 3.12, `curl` and [tippecanoe](https://github.com/felt/tippecanoe) for the web map (`brew install tippecanoe`).
Nothing else is installed globally: `src/shared/setup.sh` makes a local virtual environment from `requirements.txt`.
The PSA 2024 census workbook (and, optionally, the DOH facility registry) is saved by hand into `data/manual/`, which is gitignored, as the [data-quality notes](docs/data-quality.md#getting-the-hand-downloads) describe.

The checks that run on every pull request:

```bash
ruff check . && ruff format --check .
pytest
```
