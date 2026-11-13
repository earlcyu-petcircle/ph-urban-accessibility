# Data collection and quality

This note covers the first two phases of the study: collecting the data and building the analysis inputs.
It reports how complete each layer is and where the gaps sit, so the analysis knows what it stands on.
It holds no measures and no findings; those are on the [story site](https://earlcyu-petcircle.github.io/ph-urban-accessibility/).

Every number here is rebuilt by `./02_build_tables.sh` (or `./run_all.sh`) from the downloads in `data/raw/` and the hand download in `data/manual/`.
The machine-readable versions are in [`data/derived/`](../data/derived/): `data_quality.json`, `census_2024_check.json`, `service_quality.csv`, `barangays.csv` and `jollibee.json`.
Snapshots in this build: OpenStreetMap extract of 3 November 2026 (replication time 21:24 UTC), Overture release 2026-10-21.0, COD-AB boundaries of 28 May 2026.

## The short version

- **Population is exact at barangay level.** The PSA 2024 census workbook for Metro Manila sums to the official 14,001,751, and every one of those people lands on a COD-AB barangay; the three study barangays match by name with 1,302, 21,768 and 3,374 people.
- **People are placed in 1,573,122 residential buildings.** 99.1% of WorldPop's Metro Manila population sits in a 100 m cell that holds at least one residential footprint, so almost nobody is left to a fallback.
- **The service layer has all nine categories.** In Metro Manila it holds 7,666 food shops, 505 markets, 3,210 pharmacies, 3,582 primary care places, 563 hospitals, 483 public elementary and 231 public high schools, 666 open spaces and 4,201 transit stops and stations.
- **The DepEd registry is mostly found in the open sources.** 82% of Metro Manila's public elementary schools and 86% of its public high schools in the DepEd list have an OpenStreetMap or Overture record of the same name nearby.
- **The walking network is large and connected.** 16,741 km of walkable ways, 97.3% of nodes in one connected piece, including 47.7 km of footbridges and stairs.
- **Three gaps to carry into the analysis.** Sari-sari stores are almost unmapped (234 named in all of Metro Manila); only 95 jeepney routes are mapped in the study box against 768 bus routes; and the DOH facility registry cannot be exported (its export fails even in a browser), so hospitals and primary care rest on Overture and OpenStreetMap alone, with no registry check and no bed counts.
- **One boundary problem for the metro context.** 112 barangays (527,000 people) have a census count more than three times WorldPop's estimate, mostly where COD-AB and the 2024 census draw a barangay differently (Post Proper Southside: 68,388 people on a polygon WorldPop puts at 4,780); none of them is a study barangay.

## What was collected

| Layer | Source | Grain | Vintage | Licence | Rows used |
|---|---|---|---|---|---:|
| Population count | PSA 2024 Census of Population, "Table C - Population by Barangay", NCR workbook (hand download) | Barangay, names only | 1 July 2024 | PSA publication | 1,715 barangays |
| Population pattern | WorldPop R2025A, constrained, 100 m | Pixel | 2024 | CC BY 4.0 | 14.27M people in Metro Manila |
| Population check | JRC GHS-POP R2023A, 100 m, tile R8_C30 | Pixel | 2025 epoch | CC BY 4.0 | 13.99M people in Metro Manila |
| Residential buildings | Overture Maps buildings (OpenStreetMap, Google Open Buildings and Microsoft footprints) | Footprint | Release 2026-10-21.0 | ODbL | 1,629,555 in Metro Manila |
| Boundaries and codes | OCHA COD-AB Philippines v03 (NAMRIA and PSA), PSGC-based pcodes | Barangay | Valid from 13 Feb 2025; files 28 May 2026 | CC BY-IGO | 1,712 barangays |
| Services | Overture Maps places at confidence 0.3 or more | Point | Release 2026-10-21.0 | CDLA Permissive 2.0 and per-source terms | 320,705 in the study box |
| Services, open space, transit, network | OpenStreetMap, Geofabrik Philippines extract | Point, polygon, way, route | 3 Nov 2026 | ODbL | 141,064 tagged points and areas; 174,506 walkable ways |
| Jollibee stores (tracked, not a service) | OpenStreetMap, Geofabrik Philippines extract | Point | 28 Oct 2026 | ODbL | 349 stores in Metro Manila |
| School registry | OSMaPaaralan: DepEd's MaPaaralan public-school list, cleaned by OpenStreetMap Philippines | School, with DepEd ID, ISCED level and 2015 enrolment | 2019 | DepEd data published for OpenStreetMap use; only counts committed | 1,064 schools in the study box |
| School check | HOT OpenStreetMap education facilities (HDX export) | School | 12 Oct 2026 | ODbL | 1,862 schools in Metro Manila |
| Health registry | DOH National Health Facility Registry | Facility, with beds | Live | Government publication | Not used: the export fails |
| Health check | Healthsites.io (HDX) | Facility | Sep 2026 | ODbL | Used when HDX allows; refused in this build |

The study box is Metro Manila plus 2 km on every side (120.88-121.16 E, 14.33-14.81 N); Overture and the walking network are cut to it, and services count anywhere within 2 km of Metro Manila.
Two planned layers are not collected: the Mapillary imagery for the walk audit is viewed by hand through the links in the audit worksheets (`results/tables/`), and the map-only context layers (Relative Wealth Index, UP NOAH flood hazard) were left out of the comparison site, which keeps to the measures.

Three changes from the design's source list, all forced by the download servers:

- **DepEd school locations: the 2019 OSMaPaaralan list replaces the 2008 HDX file.** HDX answered every scripted download that day with a bot challenge (HTTP 202 and an empty body), and refused the same link in a browser session driven by the tooling.
  OSMaPaaralan is served from GitHub, is eleven years newer, and carries what the design needs from a registry: the DepEd school ID, the school level and enrolment (for the crowding measure, M3).
- **Healthsites.io is optional.** The same HDX block stopped it (and still did on 4 November 2026, when the analysis ran), so `01_collect_data.sh` warns and `02_build_tables.sh` skips the check; it runs again whenever the download gets through.
- **The DOH National Health Facility Registry is not used.** It answers scripts with HTTP 403, and its export fails even in a browser, so it is dropped for good: hospitals and primary care rest on Overture and OpenStreetMap, there is no health registry match, and hospitals have no bed counts, so the crowding measure (M3) counts each hospital as 1, the design's fallback.

## Getting the hand downloads

One source refuses scripted downloads, and HDX sometimes does too.

| File | Needed | Where to get it | Save as |
|---|---|---|---|
| PSA 2024 census, NCR | Yes | [2024 Census of Population (POPCEN) Population Counts Declared Official by the President](https://psa.gov.ph/content/2024-census-population-popcen-population-counts-declared-official-president), the National Capital Region "Table C - Population by Barangay" workbook | `data/manual/popcen2024/ncr.xlsx` |
| COD-AB boundaries (if HDX challenges the script) | Yes | [OCHA COD-AB Philippines on HDX](https://data.humdata.org/dataset/cod-ab-phl), `phl_admin_boundaries.gdb.zip` | `data/raw/phl_admin_boundaries.gdb.zip` |
| Healthsites.io (if HDX challenges the script) | No | [Philippines Healthsites on HDX](https://data.humdata.org/dataset/philippines-healthsites), the CSV | `data/raw/healthsites_philippines.csv` |

- psa.gov.ph serves scripts a Cloudflare bot check; the NCR workbook used here is the same file the [ph-lottery-outlets](https://github.com/earlcyu-petcircle/ph-lottery-outlets) study downloaded by hand on 2 November 2026.
- `download_sources.sh` keeps any file already in `data/raw/`, so a file saved by hand is used as is.
  The COD-AB file in this build is the HDX file of 28 May 2026 as downloaded by script on 29 October and 2 November 2026 (two copies, byte for byte the same, 360,586,879 bytes as HDX lists).

## The 2024 census

The population is the PSA 2024 Census of Population, as of 1 July 2024.

- The NCR workbook has one sheet per city (and one for the municipality of Pateros); the City of Manila sheet stacks its 14 districts, each with its total and then its barangays.
- Every city and district total equals the sum of its barangays, and the 1,715 barangays sum to 14,001,751, the NCR total on the workbook's "Table B".
- The Tondo district ("Tondo I/II") holds 259 barangays and 637,942 people.

The workbook carries names, not PSGC codes, so it is joined to COD-AB by name, after the ph-lottery-outlets method.

| Step | COD-AB barangays |
|---|---:|
| Same name in the same city (accents, "Sta.", roman numerals, "Poblacion" and bracketed alternatives evened out) | 1,698 |
| Same name elsewhere in Metro Manila: the ten "EMBO" barangays, in Makati on COD-AB and in Taguig in the 2024 census | 10 |
| Split since COD-AB was drawn: Caloocan's Barangay 176 holds the 2024 barangays 176-A to 176-F | 1 |
| Spelling variant in the same city ("North Bay Blvd., North" and "North Bay Boulevard North") | 1 |
| No census barangay: Manila North Cemetery and the disputed Tutuban Mall lot | 2 |

All 1,715 census barangays and all 14,001,751 people are matched.
Three COD-AB barangays have nobody: the two above and Caloocan's Barangay 76, which the census counts at zero.

## People in buildings

Each barangay's census count is spread over its WorldPop 2024 100 m cells, then over the residential buildings in each cell in proportion to footprint area (dasymetric mapping).

- **Residential buildings.** An Overture footprint of 10 m² or more that is tagged residential or not tagged at all (four in five carry no use); commercial, industrial, education, civic, religious, medical and other tagged buildings, garages and underground structures get nobody.
  Metro Manila has 1,629,555 footprints, 1,577,565 of them residential: 1,107,935 from OpenStreetMap, 363,828 from Google Open Buildings and 105,802 from Microsoft.
- **Coverage.** WorldPop puts 14,270,541 people in Metro Manila (1.9% above the census), and 99.1% of them sit in a cell holding a residential footprint.
  Every barangay with people was placed by buildings and WorldPop together; none needed the area-only or barangay-point fallbacks.
- **Result.** 1,573,122 origins carry all 14,001,751 people; the median origin holds 5.4 people.
- **The GHS-POP version** (`people_ghs`, for sensitivity check 09) places the same census counts on the GHS-POP 2025 grid; 99.1% of its people sit in cells with a residential footprint, and 138 buildings in barangays GHS-POP leaves empty are placed by area alone.

| Barangay | People | Residential buildings | Median people per building | Largest building | WorldPop 2024 | GHS-POP 2025 |
|---|---:|---:|---:|---:|---:|---:|
| Barangay 136 | 1,302 | 97 | 10.8 | 94 | 1,322 | 4,437 |
| Loyola Heights | 21,768 | 3,206 of 3,376 | 4.3 | 77 | 27,455 | 30,511 |
| Oranbo | 3,374 | 762 of 823 | 1.9 | 73 | 3,279 | 5,339 |

*WorldPop and GHS-POP columns sum the grid cells whose centres fall in each barangay, which is coarse for a 2.9 ha barangay: Barangay 136's GHS-POP sum takes in neighbouring blocks.*

Where the census and WorldPop disagree, a few buildings can carry many people.
112 barangays (526,628 people) have a census count more than three times WorldPop's, and 111 buildings carry more than 500 people each (90,175 in all).
The largest gaps are boundary problems: Post Proper Southside, one of the EMBO barangays, has 68,388 people in the 2024 census on a COD-AB polygon where WorldPop sees 4,780, so its 383 residential buildings average 179 people and one 13 m² footprint takes 3,241.
These barangays only enter the Metro Manila context percentiles.
The study barangays' census counts sit within 3% of WorldPop's for Barangay 136 and Oranbo; Loyola Heights' is 21% below it, which the campus check below should explain.
The by-hand footprint checks for Barangay 136, the Ateneo campus and Capitol Commons are part of the audits still to be scored by hand (`notebooks/06_audits.ipynb`).

## The service layer

Each source record is sorted into one of the nine categories by its tags and, where tags are unreliable, its name.
The rules live in `src/02_build_tables/build_services.py`, one named pattern each.

| Category | Overture | OpenStreetMap | Registry |
|---|---|---|---|
| Food retail | `grocery_store`, `convenience_store` and other grocery categories; kind `supermarket` by chain or name, `convenience`, `grocery`, or `sari_sari` by name | `shop` = supermarket, convenience, grocery, greengrocer, general or kiosk, or any shop named sari-sari | |
| Palengke | `farmers_market`, or a food or shopping place named palengke, public or wet market, talipapa, mercado or market (not super, mini, flea, night or online) | `amenity=marketplace`, `shop=market` | |
| Pharmacy | `pharmacy`, `drugstore` | `amenity=pharmacy`, `healthcare=pharmacy`, `shop=chemist` (Watsons sells medicine) | |
| Primary care | Clinic and health-centre categories, and `hospital` records named as clinics; dental, animal, cosmetic, laboratory and other specialist names out | `amenity` = clinic or doctors, `healthcare` = clinic, doctor or centre, with the same exclusions | |
| Hospital | `hospital` records with a hospital name, minus wards, departments, outpatient units and other parts of a hospital | `amenity` or `healthcare` = hospital unless named a clinic | |
| Public elementary, public high | `public_school`, or a school with a public-school name; level from the name | `amenity=school` that is public by `operator:type` or name; level from `isced:level` or the name | DepEd: defines the category |
| Open space | | Parks, playgrounds, gardens, commons, village greens, recreation grounds and squares of 0.1 ha or more, not private; a space inside a bigger one is dropped | |
| Transit | `bus_station` (terminals) | Bus stops and platforms; the stop positions of the LRT-1, LRT-2 and MRT-3 routes; the ways of every bus and jeepney route (`transit_routes.parquet`) | |

- **Closed and doubtful places.** Overture records marked closed are dropped; records at confidence 0.3 or more are kept so check 08 can try 0.3, 0.5 and 0.7, and the default layer uses 0.5.
- **Duplicates.** Inside a category, records within 50 m whose names agree (or where one has no name) are one service and share a `dup_group`.
  For hospitals, schools and markets the radius is 150 m when both are named, and any record inside an OpenStreetMap campus polygon with an agreeing name joins it.
  Names agree when the distinctive words of one are all in the other ("DepEd Licerio Geronimo ES" and "Licerio Geronimo Elementary School") or the two read alike.
- **The default layer.** `in_default` marks one record per group from OpenStreetMap, the registries and Overture at confidence 0.5 or more, preferring OpenStreetMap's point, then the registry's, then the most confident Overture record.
  Where a registry lists a category, it decides membership: a public school is in the default layer only if its group holds a DepEd school, because a name rule lets private and misplaced schools in (it admits 841 Overture "public elementary" records in Metro Manila against 501 DepEd schools).
  The OpenStreetMap-only and Overture-only records stay in `services.parquet` for check 07.
- **Capacity.** Every default public school carries its DepEd 2015 enrolment (`group_capacity`), for the crowding measure; hospitals have no bed counts and count 1 each.

### Counts in Metro Manila

| Category | Overture records (at 0.5) | OpenStreetMap records | DepEd | Services in the default layer | In more than one source |
|---|---:|---:|---:|---:|---:|
| Food retail | 5,820 (4,488) | 4,893 | | 7,666 | 1,233 |
| Palengke | 417 (356) | 289 | | 505 | 76 |
| Pharmacy | 2,725 (2,155) | 1,681 | | 3,210 | 625 |
| Primary care | 3,809 (3,186) | 804 | | 3,582 | 262 |
| Hospital | 582 (549) | 218 | | 563 | 147 |
| Public elementary | 841 (829) | 547 | 501 | 483 | 393 |
| Public high | 660 (623) | 391 | 242 | 231 | 197 |
| Open space | | 669 | | 666 | |
| Transit (stops and stations) | 298 (278) | 3,972 | | 4,201 | |

*Records are source records inside Metro Manila; services are duplicate groups. Food retail in the default layer is 4,878 convenience stores, 1,390 groceries, 1,164 supermarkets and 234 sari-sari stores. Transit is 3,873 bus stops, 278 bus terminals and 50 LRT and MRT stations; open space covers 589 ha (median 0.36 ha).*

- **Overture and OpenStreetMap overlap little.** Only 16% of food shops and 7% of primary care places appear in both, so the source check (07) matters most for those two.
- **Hospitals are the noisiest category.** Overture adds 355 hospitals with no OpenStreetMap counterpart; a sample shows real hospitals OpenStreetMap lacks, but also hospital clinics in malls named "Medical Center", the odd duplicate more than 150 m from its twin, and a few points misplaced from other countries ("Modern Cancer Hospital Guangzhou China").
  With no usable DOH registry, the service audit measures the error instead.
- **Sari-sari stores are almost absent**, as expected: 234 in the default layer for all of Metro Manila, and none in Barangay 136.

### Registry match

| Area | Public elementary found | Public high found |
|---|---:|---:|
| Metro Manila | 410 of 501 (82%) | 208 of 242 (86%) |
| City of Manila | 59 of 76 | 26 of 35 |
| Quezon City | 74 of 92 | 39 of 44 |
| City of Pasig | 26 of 29 | 12 of 12 |
| Loyola Heights | 1 of 1 | 1 of 1 |
| Oranbo | 1 of 1 | none listed |
| Barangay 136 | none listed | none listed |

*A DepEd school is found when its duplicate group holds an OpenStreetMap or Overture record of the default layer. There is no DOH match (the registry cannot be exported), and the Healthsites.io check is empty in this build because HDX refused the download.*

The HOT education export of 12 October 2026 holds 1,862 schools in Metro Manila against 1,851 in this build's OpenStreetMap extraction three weeks later, so the two extractions agree.

### Inside the study barangays

| Category | Barangay 136 | Loyola Heights | Oranbo |
|---|---:|---:|---:|
| Food retail | 1 | 39 | 9 |
| Palengke | 0 | 4 | 2 |
| Pharmacy | 0 | 9 | 5 |
| Primary care | 0 | 7 | 4 |
| Hospital | 0 | 1 | 1 |
| Public elementary | 0 | 1 | 1 |
| Public high | 0 | 1 | 0 |
| Open space | 0 | 9 | 2 |
| Transit stops and stations | 0 | 15 | 3 |

*Services inside the boundary only; the measures count services wherever they are, so these are not access figures.*

## Transit

- **Rail.** The LRT-1, LRT-2 and MRT-3 route relations give 50 stations in Metro Manila.
  PNR's Metro Manila service has been suspended since March 2024 and the Metro Manila Subway is not open, so neither counts.
- **Bus.** 3,873 mapped bus stops and platforms, 278 Overture bus terminals, and 768 bus routes with ways in the study box.
- **Jeepney.** 95 jeepney routes (route `share_taxi`, or a network or name marked PUJ or jeep) have ways in the study box, against 768 bus routes.
  OpenStreetMap's jeepney network is clearly incomplete, so the M5 jeepney rule (any point on a route is a stop) can only use the mapped routes; check 10 brackets it with stops only.
- `transit_routes.parquet` holds every vertex of those routes with the route's mode, network, name and reference, for the "route as stop" rule.

## The Jollibee layer

Jollibee stores are tracked beside the nine services, not as a tenth: they are shown on the map and in their own rows of the picks table (the nearest walk, and the stores within 5, 10 and 15 minutes), and they are in none of the measures, the 15-minute score or the rankings.

- **Source.** OpenStreetMap only, from the Geofabrik Philippines extract of 28 October 2026 (replication time 21:21 UTC), as recorded in `data/derived/jollibee.json`.
  The rest of this build used the extract of 3 November, which Geofabrik no longer serves; the two are six days apart, and a live Overpass count on 13 November found 321 brand-tagged and 356 name-matched features in Metro Manila, so the stores barely move between them.
  OpenStreetMap is credited under ODbL with the other layers.
- **The brand tag rule** (`is_jollibee` in `src/shared/service_rules.py`). An `amenity=fast_food` or `amenity=restaurant` node or area with `brand:wikidata=Q37614`, or, when no `brand:wikidata` is set, a name matching `jol+i+bee` as a word, which catches the "Jolibee" spelling.
  JFC's offices, the car parks it operates and other JFC brands (a Chowking carries its own brand ID) are not restaurants of this brand, so none counts.
- **One point per store.** Points within 50 m are one store, because a few are mapped as both a node and a building outline; the node is kept where there is one.
  387 records (341 with the brand ID) give 381 stores in Metro Manila and its 2 km fringe, 349 of them inside Metro Manila.
- **Completeness.** OpenStreetMap holds roughly nine in ten of Metro Manila's Jollibee stores: a source scout on 13 November put the true number at about 350 to 380, and found a few dozen stores, spread across the cities, that are not mapped.
- **Not used.** Jollibee's own store locator lists 276 stores in Metro Manila and lacks flagship branches such as SM Mall of Asia and Trinoma; its terms (section VIII) bar reuse of its content without written consent, so it is not used.
  Overture places would roughly double the count, because its Meta and Foursquare records of one store sit more than 50 m apart, and it carries no brand ID.
- Walks to the stores use the same network and the same nearest and count searches as the nine services (`src/03_analyse/jollibee_times.py`), in their own table, so the services' walk times are untouched.

## The walking network

| Measure | Value |
|---|---:|
| OpenStreetMap snapshot | 3 Nov 2026, 21:24 UTC |
| Walkable segments in the study box | 693,215 |
| Connected pieces | 1,493 |
| Nodes in the largest piece | 605,898 (97.3%) |
| Segments kept | 677,005 |
| Length kept | 16,741 km |
| Length dropped in small pieces | 326 km |
| Footbridges, footway and stair bridges | 1,692 ways, 47.7 km |

- The way filter copies OSMnx's "walk" network: any highway a person may walk on, so trunk roads such as EDSA (which have sidewalks) stay in, while expressways, cycleways, EDSA's busway, platforms, private ways, ways marked `foot=no` and anything abandoned or under construction are out.
- Every way is cut into its node-to-node segments, walkable both ways; residential streets are 53% of the length, footways and paths 9%.
- Sidewalk tags are too patchy to use, so every walkable way counts the same; the walk audit covers walk quality.

## The tables

### `data/derived/barangays.csv` (1,712 rows, one per COD-AB barangay in Metro Manila)

| Column | Meaning |
|---|---|
| `pcode`, `barangay`, `city_pcode`, `city` | COD-AB names and PSGC-based pcodes |
| `district` | City of Manila district from the census workbook (blank elsewhere) |
| `tondo_district` | In Tondo I/II: the neighbours of Barangay 136 |
| `study` | Barangay 136, Loyola Heights or Oranbo; blank for the rest |
| `people`, `census_match` | 2024 census count, and how the name join found it (`name`, `name_ncr`, `name_split`, `fuzzy`, `none`) |
| `area_km2`, `people_per_km2` | Area in UTM zone 51N, and density |
| `worldpop_2024`, `ghs_pop_2025` | Each grid's people in cells centred in the barangay, for comparison |
| `buildings`, `residential_buildings`, `origins` | Overture footprints with their centre in the barangay; those that hold people |

### `data/derived/service_quality.csv` (long format)

| Column | Meaning |
|---|---|
| `area` | Metro Manila, the three study cities, or a study barangay |
| `category` | One of the nine categories |
| `measure` | `records_overture`, `records_osm`, `records_deped`: source records inside the area; `overture_confidence_0.5`: Overture records at the default confidence; `services_default`: duplicate groups in the default layer; `services_in_more_than_one_source`; `services_default_<kind>` for food retail; `deped_registry_found` |
| `value`, `of` | The count, and for registry rows the number of registry schools |

### The large inputs in `data/work/` (gitignored)

| File | One row per | Key columns |
|---|---|---|
| `census_2024.parquet` | Barangay | `pcode`, `people`, `match`, `district` |
| `origins.parquet` | Residential building with people | `origin_id`, `pcode`, `lon`, `lat`, `people`, `people_ghs`, `area_m2`, `wp_cell`, `h3_10`, `h3_9` |
| `services.parquet` | Source record in Metro Manila and its fringe | `service_id`, `category`, `kind`, `source`, `name`, `lon`, `lat`, `pcode`, `confidence`, `group_capacity`, `dup_group`, `in_default` |
| `open_space_access.parquet` | Point every 25 m round an open space | `service_id`, `lon`, `lat` |
| `jollibee.parquet` | Jollibee store in Metro Manila and its fringe | `store_id`, `name`, `lon`, `lat`, `pcode`, `osm_ids` |
| `transit_routes.parquet` | Vertex of a bus or jeepney route | `route_id`, `mode`, `network`, `name`, `ref`, `node_id`, `lon`, `lat` |
| `walk_nodes.parquet`, `walk_edges.parquet` | Network node; segment | `node_id`, `lon`, `lat`; `u`, `v`, `length_m`, `way_id`, `highway` |

## Limitations

- There is no DOH registry, so hospitals and primary care rest on Overture and OpenStreetMap name and tag rules and hospitals carry no beds.
- The DepEd list is from 2019; schools opened since then appear only through OpenStreetMap and Overture, which the default layer leaves out of the public-school categories.
- Footprint area is the weight inside a cell; floor counts are known for under 1% of residential footprints, so high-rise condominiums are underweighted against low-rise houses in the same cell.
- Overture's geocoding errors put a few places far from home; confidence filtering and the service audit, not this build, deal with them.
- OpenStreetMap jeepney routes cover a fraction of the network, and sari-sari stores and carinderias are almost unmapped (the site's [limitations](https://earlcyu-petcircle.github.io/ph-urban-accessibility/#limits)).
