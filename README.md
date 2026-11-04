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
The results are in ([paper, section 6](docs/paper.md#6-results)): no barangay wins outright.
Barangay 136 has the most of the nine basics within 15 minutes but the least supply per resident once crowding is counted; Oranbo has the nearest open space but no public high school within reach; Loyola Heights trails on most basics, above all public schools.
**Compare any three barangays on foot:** [https://earlcyu-petcircle.github.io/ph-urban-accessibility/](https://earlcyu-petcircle.github.io/ph-urban-accessibility/). The three above are the featured preset, one personal point of view.
One caveat is already known: sari-sari stores are almost absent from open maps, so food access will be understated, most of all in Barangay 136.

## Where things are

| Path | What it holds |
|---|---|
| [`docs/paper.md`](docs/paper.md) | The full paper: background, research questions, data sources, research design, data, results, discussion, limitations, references and appendices |
| [`docs/index.html`](docs/index.html), [`docs/map/`](docs/map/) | The story site and the comparison map, served by GitHub Pages; `docs/map/data/` holds every barangay's measures |
| [`docs/data-quality.md`](docs/data-quality.md) | How each source was collected, parsed and joined, the checks and their results, and where the gaps sit |
| [`data/derived/`](data/derived/) | The small committed tables: barangays, service counts and registry matches, and every data-quality check |
| [`src/`](src/) | The pipeline code, one folder per phase script, plus shared paths and study constants in `src/shared/common.py` ([Appendix A](docs/paper.md#appendix-a-code-and-pipeline) of the paper) |
| [`notebooks/`](notebooks/) | The six analysis notebooks, run with their outputs: proximity and choice, crowding, coverage and transit, context and fairness, robustness, audits |
| [`results/tables/`](results/tables/), [`results/figures/`](results/figures/) | The measure, context, sensitivity and audit tables, and the figures |

## How to reproduce

All four phases run.

```bash
git clone https://github.com/earlcyu-petcircle/ph-urban-accessibility.git
cd ph-urban-accessibility
./run_all.sh              # every phase below, in order

./01_collect_data.sh      # downloads into data/raw/
./02_build_tables.sh      # people, services and the walking network
./03_analyse.sh           # the five measures, checks and audits in results/
./04_build_map.sh         # comparison site data in docs/map/data/
python3 src/04_build_map/serve_map.py   # the site at http://localhost:8000/
```

Needs Python 3.12, `curl` and [tippecanoe](https://github.com/felt/tippecanoe) for the web map (`brew install tippecanoe`).
Nothing else is installed globally: `src/shared/setup.sh` makes a local virtual environment from `requirements.txt`.
The PSA 2024 census workbook is saved by hand into `data/manual/`, which is gitignored, as the [data-quality notes](docs/data-quality.md#getting-the-hand-downloads) describe.

The checks that run on every pull request:

```bash
ruff check . && ruff format --check .
pytest
```
