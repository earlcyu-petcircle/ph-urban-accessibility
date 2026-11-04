# Metro Manila Urban Accessibility

Which of the three Metro Manila barangays I have lived in puts everyday life within a short walk?

This project compares walking access to everyday services (food shops, the palengke, pharmacies, clinics, hospitals, public schools, open space and transit) for the residents of three barangays, and sets each against the rest of Metro Manila.
Open data only.

| Barangay | City | For me | People (2024 census) |
|---|---|---|---:|
| Barangay 136 (Tondo) | City of Manila | Born and raised | 1,302 |
| Loyola Heights | Quezon City | Two years of college | 21,768 |
| Oranbo | City of Pasig | Home now | 3,374 |

**Status: research design approved and the pipeline skeleton in place.
No data has been collected or analysed yet.**

## The design in brief

The full plan, from the literature to the web map, is in [docs/research-design.md](docs/research-design.md).

- **Fair at very different sizes.** Barangay 136 is about one city block and Loyola Heights is 84 times its area, so every resident is an origin and services count wherever they are, not only inside the barangay.
- **Five measures, no single score.** Walking time to the nearest service, the count within 5 to 15 minutes, supply per resident once crowding is counted, the share of nine everyday services within 15 minutes, and the UN SDG 11.2.1 test for transit.
- **Tested, not just measured.** A difference between the barangays only counts as a finding if it survives ten changes of assumption, from walking speed to the data source.
- **The caveat up front.** Sari-sari stores are almost absent from open maps, so food access will be understated, most of all in Barangay 136. Every food figure says so.

## Where things are

| Path | What it holds |
|---|---|
| [`docs/research-design.md`](docs/research-design.md) | The research design: questions, study areas, literature, data, method, web map, decisions |
| [`config.toml`](config.toml) | Every study parameter: barangays, walking speed, thresholds, service basket, sensitivity grid |
| [`src/mma/`](src/mma/) | The pipeline: one package, four stages (`s1_collect`, `s2_build`, `s3_analyse`, `s4_publish`) |
| [`tests/`](tests/) | pytest checks on the config and the CLI |

## Run it

Needs [uv](https://docs.astral.sh/uv/); it installs Python 3.12 if you do not have it.

```bash
uv sync
uv run mma check     # validate config.toml and list the study barangays
uv run pytest
uv run ruff check .
```

`uv run mma collect`, `build`, `analyse` and `publish` (or `./run_all.sh` for all four) say which PR brings each stage until it is built.

## Roadmap

| PR | Scope |
|---|---|
| 1 | Research design and pipeline skeleton |
| 2 | Data collection and build: people, services, walking network |
| 3 | Analysis: walking times, the five measures, sensitivity checks, audits |
| 4 | Results: findings, the story site and the interactive map |
| 5 | Clean-up and a fresh-clone reproducibility check |
