# Research design

Earl Yu, 4 November 2026.
Approved design, v1.0.
Nothing has been computed yet: this page is the plan the pipeline will follow, PR by PR.

## In short

- **Question.** For the residents of three Metro Manila barangays I have lived in, how long is the walk to everyday services, how much choice is within reach, and how crowded is it?
- **Places.** Barangay 136 in Tondo, Manila (born and raised), Loyola Heights in Quezon City (two years of college) and Oranbo in Pasig (now), set against all of Metro Manila.
- **Yardstick.** Every resident is an origin and services count wherever they are, so a one-block barangay is not penalised for its boundary.
- **Measures.** Walking time to the nearest service, the count within reach, a crowding-adjusted supply ratio, a 15-minute coverage share and the UN SDG 11.2.1 transit test.
- **Data.** PSA 2024 census, WorldPop, Overture Maps and OpenStreetMap, cross-checked against the DOH and DepEd registries.
- **Biggest limitation.** Sari-sari stores, the corner shops of everyday Filipino life, are almost absent from open maps, so food access is understated (section 4.1).
- **Output.** A Python pipeline in four stages and a story site with an interactive map, in five PRs.

## 1. Question and objective

The objective is a fair, reproducible comparison of everyday accessibility for the residents of the three barangays.
Accessibility here means potential access: how easily a resident could reach everyday services on foot (Geurs & van Wee 2004; Pereira & Herszenhut 2023).
It is not a record of where people actually go.

| # | Question | Measure | Lineage |
|---|---|---|---|
| RQ1 | **Proximity.** How long is the walk from home to the nearest food shop, palengke, pharmacy, clinic, hospital, public school, open space and transit? | M1 nearest walk; M4 15-minute coverage | Bruno et al. 2024; Logan et al. 2022 |
| RQ2 | **Choice.** How many of each are within 5, 10 and 15 minutes? | M2 cumulative opportunities | Geurs & van Wee 2004; Páez et al. 2012 |
| RQ3 | **Crowding.** Once neighbours competing for the same clinic or school are counted, how much service is there per resident? | M3 E2SFCA | Luo & Wang 2003; Luo & Qi 2009 |
| RQ4 | **Transit.** What share of residents is within 500 m of a bus or jeepney and 1 km of rail? | M5 SDG 11.2.1 | UNSD 2025; Hasselwander et al. 2023 |
| RQ5 | **Context and fairness.** Where does each barangay sit among all Metro Manila residents, and how unequal is access inside each? | Percentiles, P90/P10, share above a minimum | Lucas et al. 2016; Pereira et al. 2017 |

Design type:

- **Comparative case study** of three purposively chosen barangays, nested in a metro-wide cross-sectional measurement.
  They are chosen because I lived there, not to represent Metro Manila, so findings describe these three places only.
- **Descriptive, not causal.** The study shows how access differs, not why, and makes no claim about effects on health or income.
- **Present-day.** Every layer is 2024 to 2026, so it measures the barangays as they are now, not as they were when I lived in them.
- **Measurement uncertainty, not sampling error.** Every resident is an origin, so differences are reported with sensitivity ranges rather than p-values.

## 2. Study areas

All three places are compared at the same tier, the barangay.

| Barangay | City | PSGC code | People (2024) | Area | People per km² |
|---|---|---|---:|---:|---:|
| Barangay 136 (Tondo) | City of Manila | PH1303901136 | 1,302 | 0.029 km² | 45,400 |
| Loyola Heights | Quezon City | PH1307404055 | 21,768 | 2.43 km² | 9,000 |
| Oranbo | City of Pasig | PH1307403013 | 3,374 | 0.52 km² | 6,500 |

*People from the PSA 2024 Census of Population; areas from the OCHA COD-AB boundaries.*

Barangay 136 is about one city block, Loyola Heights is 84 times its area, and Barangay 136 is seven times as dense as Oranbo.
An earlier pilot ([closed PR #1](https://github.com/earlcyu-petcircle/metro-manila-accessibility/pull/1)) used the whole Tondo district (259 barangays, 637,942 people in 2024) against two single barangays; that unit is dropped.
Because the barangays differ so much in size, the comparison is kept about residents, not land:

| Lens | What it is | Why |
|---|---|---|
| Barangay (primary) | Every resident of the three barangays, placed at building level | One administrative tier for all three |
| Services anywhere | Walks may leave the barangay; services in neighbouring barangays and cities count | Stops a one-block barangay being penalised for its boundary (Hewko et al. 2002) |
| Equal walk-shed (check) | The area within a 15-minute walk along streets of each barangay's population-weighted centre | Separates the place from the size of its barangay (Oliver et al. 2007; Kwan 2012) |
| Home walk-shed (private) | A 15-minute walk from each of my three homes | A front-door check; never published, never committed |
| Neighbours | Barangay 136 against the other 258 Tondo barangays; Loyola Heights and Oranbo against their cities | Is each place typical of its area? |
| Metro | All Metro Manila residents | Percentile context |

Risks specific to these barangays:

- **Barangay 136 is about one block.** Around 1,300 people on 2.9 ha means a narrow spread of results, and a few misplaced buildings could move it, so its footprints get a by-hand check.
- **Loyola Heights is large and mixed.** The Katipunan strip, the Ateneo campus and quieter villages sit in one barangay, so its spread from P10 to P90 and its map matter more than its median.
- **Oranbo is built around Capitol Commons.** In the pilot nobody there was within ten minutes of a palengke, so the basket matters as much as the distance.

The unit of analysis is the resident.
People are placed at building level and reported on H3 resolution-10 hexagons (about 0.015 km² each), fine enough for five-minute thresholds and coarse enough that no single home is shown.
Home locations live only in a gitignored `home.local.toml`, and geocoding runs offline on the OpenStreetMap extract.

## 3. Literature

Accessibility research has settled on a small family of measures that trade simplicity against realism (Geurs & van Wee 2004; Páez et al. 2012).
Recent 15-minute-city studies apply the simplest of them, walking time along the street network to the nearest services, at city scale with open data (Logan et al. 2022; Bruno et al. 2024).
Philippine studies of Pasig and Quezon City use the same toolkit at barangay level, which gives this project local precedent.

### 3.1 Measure families

| Family | What it answers | Strength | Weakness | Used here |
|---|---|---|---|---|
| Proximity (time to nearest) | How far is the closest one? | Readable; the basis of 15-minute indices (Bruno et al. 2024; Logan et al. 2022; Nicoletti et al. 2023) | Ignores choice and crowding | M1 |
| Cumulative opportunities | How many within T minutes? | Simple and transparent (Geurs & van Wee 2004) | Hard cut-off; results depend on T (Páez et al. 2012) | M2 |
| Gravity or potential (Hansen 1959) | Opportunities weighted by distance decay | Smooth and theory-backed | Decay needs local calibration; hard to explain | Inside M3 |
| Floating catchment (2SFCA, E2SFCA) | Supply per person within reach, counting competition | Captures crowding; standard for health access (Luo & Wang 2003; Luo & Qi 2009; Leyso & Umezaki 2024) | Needs supply capacity; sensitive to catchment size | M3 |
| 15-minute or x-minute index | Share of everyday functions within T | Policy-legible, with Philippine precedent (Mañago et al. 2025a, 2025b) | Any weighting of functions is a value judgement | M4 |
| Walkability index (Frank et al. 2010; Leather et al. 2011) | How good is the walk itself? | Captures quality, not just distance | Needs sidewalk and crossing data Metro Manila lacks | Street-imagery audit |
| Person-based, space-time (Kwan 1998) | What a specific person can reach given their day | Most realistic | Needs travel diaries | Out of scope |
| Transit coverage (SDG 11.2.1) | Share within 500 m of a bus or 1 km of rail | Global standard; allows routes as access points for informal transport (UNSD 2025) | Ignores frequency where timetables are missing | M5 |

### 3.2 Choices the literature says change the answer

- **Network, not straight line.**
  Straight-line and network distances correlate above 0.95 in Montréal but diverge in suburbs and around barriers (Apparicio et al. 2008), and network buffers found land-use effects that circles missed (Oliver et al. 2007).
  Rivers, rail lines, flyovers and gated villages make Metro Manila a barrier-rich case, so every distance runs on the street network.
- **Fine origins.**
  Representing an area by one centroid misstates access most for common, very local services (Hewko et al. 2002; Apparicio et al. 2008), so origins are buildings, not barangay centroids.
- **The neighbourhood definition is itself a choice.**
  Kwan (2012) calls this the uncertain geographic context problem: the area that shapes a person's life rarely matches an administrative unit.
  The barangay result is therefore checked against equal walk-sheds and the private home walk-sheds.
- **The measure can change the equity verdict.**
  Talen & Anselin (1998) found different access measures gave different pictures of who is underserved, so several measures are reported side by side.
- **Fairness needs a stated principle.**
  Equity work contrasts equal access for everyone (egalitarian) with everyone above a minimum (sufficientarian) (Lucas et al. 2016; Pereira et al. 2017).
  This design reports both: the spread inside each barangay and the share above a local minimum.
- **Open place data is usable but uneven.**
  Overture's UK places matched a supermarket benchmark well, but records from some contributing sources were often incomplete (Ballantyne & Berragan 2024), so sources are merged and checked against registries.

### 3.3 Philippine and Southeast Asian evidence

| Study | What it did | What we borrow |
|---|---|---|
| Mañago et al. 2025a, Pasig | 15-minute City Index on a hexagon grid; OSM plus Google Maps POIs for Moreno's six social functions; age-specific walking speeds; road walkability as impedance; 90% of barangays scored 0.5 or more | Hexagon reporting, Moreno's functions, age-speed sensitivity |
| Mañago et al. 2025b, Quezon City | The same index from isochrones; 39% of barangays reached a perfect score, with a south-north divide | A citywide benchmark for Loyola Heights |
| Tolentino & Sigua 2022, Metro Manila | From the MUCEP 2015 household survey, walking is 30.7% of trips; the 75th and 85th percentile walks are 680 m and 872.5 m; observed pace 70.62 m/min | The local walking speed and the 10-minute minimum |
| Hasselwander et al. 2023, Metro Manila | SDG 11.2.1: counting jeepneys lifts the share with convenient transit from 23.9% to 65.0% | Jeepney routes count as transit access |
| Nogueira & Diaz 2023, Pasig | Public transport coverage and street-level walkability for Pasig's 30 barangays; poorer, more crowded barangays scored worse | The walkability audit protocol |
| Leyso & Umezaki 2024, Philippines | E2SFCA for outpatient and inpatient care across municipalities | E2SFCA for health |
| Lamentillo 2025, Metro Manila | The 15-minute city across informal settlements, inner-city districts and outer suburbs, with a 420-resident survey | Read results against urban type, not only rank |
| Leather et al. 2011, Asian cities | Field walkability surveys and pedestrian interviews across 13 Asian cities | Context for why walk quality matters |

I found no peer-reviewed study comparing specific Metro Manila neighbourhoods on an equal footing; the closest are the Pasig and Quezon City indices at barangay level.

## 4. Data

Every layer is open and free.
The PSA census workbooks and the DOH registry refuse scripted downloads, so they are fetched by hand.

| Role | Layer and source | Licence | Vintage |
|---|---|---|---|
| People: counts | PSA 2024 Census of Population (POPCEN), Table C, population by barangay | PSA publication | 1 July 2024 |
| People: where | [WorldPop](https://data.humdata.org/dataset/worldpop-population-counts-2015-2030-phl) constrained 100 m, via HDX | CC BY 4.0 | 2024 layer |
| People: which building | [Overture Maps](https://docs.overturemaps.org/) buildings | ODbL | Release 2026-10-21.0 |
| People: check | JRC GHS-POP R2023A | CC BY 4.0 | 2025 epoch |
| Boundaries | [OCHA COD-AB Philippines](https://data.humdata.org/dataset/cod-ab-phl) (NAMRIA, PSA) | CC BY-IGO | Files of 28 May 2026 |
| Services | Overture Maps places | CDLA Permissive 2.0 | Release 2026-10-21.0 |
| Services, markets, parks, network, transit | [OpenStreetMap](https://download.geofabrik.de/asia/philippines.html), Geofabrik Philippines extract | ODbL | Pinned snapshot |
| Health registry | DOH National Health Facility Registry | Government publication | Live |
| Health check | [Healthsites.io](https://data.humdata.org/dataset/philippines-healthsites), via HDX | ODbL | Sep 2026 |
| School registry | DepEd school locations, via HDX; HOT OSM education facilities | HDX terms; ODbL | 2008; Oct 2026 |
| Context (map only) | Meta Relative Wealth Index; UP NOAH flood hazard | CC BY-NC 4.0; to confirm | 2021; varies |
| Walk audit | Mapillary street imagery | CC BY-SA | Varies |

### 4.1 Limitation 1: the sari-sari gap

The corner sari-sari store is part of everyday Filipino life, and open maps barely record it.
OpenStreetMap names only 256 sari-sari stores in a box around all of Metro Manila, against 4,983 mapped convenience shops (Overpass count, 4 November 2026).
For scale, one retail-tech firm's partner network alone counts more than 300,000 sari-sari stores nationwide ([Interaksyon 2025](https://media.interaksyon.com/trends-spotlights/2025/08/14/300595/more-sari-sari-stores-selling-tingi-supplies-spring-up-near-schools-says-study/)); I found no recent official count.

So "food retail" in this study means supermarkets, groceries, convenience stores and the palengke.
The measured walk to everyday food will be too long, most of all in dense streets like Barangay 136's.
Carinderias are missing in the same way.

How the study handles it:

- **Stated everywhere.** Every food figure, chart and map legend says it measures formal food retail and the palengke, not the sari-sari store, and the story site's limitations open with it.
- **Measured where we can.** The street-imagery audit counts sari-sari stores along its sample routes in and around each barangay, giving a stores-per-kilometre figure reported beside the measures, not mixed into them.
- **Bounded.** The few mapped sari-sari stores stay in food retail, and food access is reported with and without convenience stores, so readers can see how much the definition matters.

### 4.2 Other gaps and risks

- **Sidewalks are tagged unevenly.**
  In rough boxes around each place, the ways carrying any sidewalk tag number 1,291 of 5,359 around Tondo, 154 of 1,794 around Loyola Heights and 172 of 868 around Oranbo, and separately drawn sidewalks are rare (16, 35 and 13).
  A sidewalk-quality impedance cannot be built from OpenStreetMap alone, which is why the walk audit exists.
- **Jeepneys stop on request.**
  Routes, not stops, are the access point, which the SDG 11.2.1 metadata allows for informal transport.
  OpenStreetMap routes may pre-date the LTFRB route rationalisation, so the jeepney rule is a sensitivity switch.
- **Population can land in the wrong place.**
  Placement errors cluster at ports, reclamations, campuses and malls, so every building in Barangay 136, the Ateneo campus and Capitol Commons get a by-hand check.
- **Access rules are uncertain.**
  Gated villages, campuses and malls may be tagged open or closed wrongly, so the edges of each barangay are checked by hand.
- **Timetables are dated.**
  The only public Metro Manila transit feed (Sakay/DOTC GTFS) was last updated in March 2015, so timetabled transit is out of scope.
- **Vintages differ.**
  The census is from mid-2024; places and the network are from late 2026.

## 5. Method

### 5.1 Steps

1. **Fix the study areas.**
   Take the three barangay polygons from COD-AB, build the check walk-sheds around each barangay's population-weighted centre, and build the private home walk-sheds from the local home file.
   Use all of Metro Manila plus a 2 km fringe as context, so services across a city border still count.
2. **Place people.**
   Spread the 2024 census barangay totals over WorldPop 2024 cells, then over residential footprints in each cell.
   Every residential building in a study barangay becomes an origin weighted by its people.
3. **Build the service layer.**
   Map Overture and OpenStreetMap records into the nine-category basket, drop closed places and Overture confidence below 0.5, and merge duplicates within 50 m that share a category or name.
   Match public facilities to the DOH and DepEd registries and record match rates per barangay.
4. **Build the walking network.**
   OpenStreetMap ways a pedestrian may use, walkable in both directions, largest connected component; expressways out, footbridges and stairs in.
5. **Compute walking times.**
   One multi-source shortest-path run per category gives every street node its time to the nearest service, and a second pass counts services within 5, 10, 15 and 20 minutes.
   Speed is 4.2 km/h (70 m/min), close to the observed Metro Manila pace of 70.62 m/min (Tolentino & Sigua 2022).
6. **Compute the five measures** per origin, then summarise per barangay over residents.
7. **Compare and test** under the rules in 5.4 and the checks in 5.5.
8. **Validate and publish** (5.6), then write the tables, figures and map tiles.

### 5.2 The five measures

| ID | Measure | Definition | Threshold | Why |
|---|---|---|---|---|
| M1 | Nearest walk | Minutes from home to the nearest service of each category; reported for the median, P10 and P90 resident | None | The core of proximity-time indices (Bruno et al. 2024) |
| M2 | Choice | Count of each category within T minutes | 5, 10, 15 min | The standard cumulative measure (Geurs & van Wee 2004) |
| M3 | Crowding-adjusted supply | E2SFCA: supply per 10,000 residents within reach, with Gaussian decay inside a 15-minute catchment; supply is 1 per facility, or beds and enrolment where registries give them | 15 min | One nearby clinic serves far more people in a dense barangay (Luo & Qi 2009) |
| M4 | 15-minute coverage | Share of the nine categories with at least one within 15 minutes, unweighted | 15 min | The x-minute-city convention (Logan et al. 2022; Mañago et al. 2025a); unweighted because weights are a value judgement (Páez et al. 2012) |
| M5 | Transit access | Resident within 500 m by street of a bus or jeepney stop or route, and within 1 km of an LRT or MRT station | 500 m; 1 km | UN SDG 11.2.1 (UNSD 2025); jeepneys via routes (Hasselwander et al. 2023) |

The headline is the profile of M1 to M5, led by M4 coverage, rather than one weighted composite score.

### 5.3 Basket and parameters

| Function | Categories |
|---|---|
| Supplying | Food retail (supermarket, grocery, convenience); palengke; pharmacy |
| Caring | Primary care (barangay health station, health centre, clinic); hospital |
| Learning | Public elementary school; public high school |
| Enjoying | Open space of at least 0.1 ha (park, plaza, playground) |
| Moving | Transit: jeepney or bus route or stop; LRT or MRT station |

*Grouped by the social functions of Moreno et al. (2021); working and civic functions are left out for want of open jobs data.*

| Parameter | Value |
|---|---|
| Walking speed | 4.2 km/h (70 m/min) |
| 5 / 10 / 15 / 20 minutes | 350 / 700 / 1,050 / 1,400 m |
| Sufficiency minimum | 10 minutes (700 m), close to the 680 m that three in four Metro Manila walking trips stay within |
| Transit (SDG 11.2.1) | 500 m to low capacity, 1 km to rail |
| Fringe beyond Metro Manila | 2 km |
| Origins / display | Buildings / H3 resolution 10 |

Every parameter lives in [`config.toml`](../config.toml).

### 5.4 Comparing the three barangays fairly

- **Same yardstick.** One data vintage, one service taxonomy, one network rule set, one speed and the same thresholds for all three.
- **One tier, residents as the unit.** All three are barangays, every resident is an origin and services count wherever they are, so barangay size alone does not decide the result; the equal walk-sheds test that.
- **People, not land.** Every statistic is weighted by residents, never by area or by hexagon.
- **Distributions, not just averages.** Median, P10 and P90 resident; the share above the 10-minute minimum; and the P90/P10 ratio inside each barangay (Lucas et al. 2016).
- **Context.** Each barangay's median resident as a percentile of all Metro Manila residents, and of residents in places of similar density, because density drives proximity (Bruno et al. 2024).
- **Robustness over significance.** A difference between barangays is called a finding only if their ordering survives the checks below.

### 5.5 Sensitivity checks

| # | Check | Values | Why |
|---|---|---|---|
| 01 | Walking speed | 3.6, 4.2, 4.8 km/h | Older adults and children walk slower (Bohannon 1997; Mañago et al. 2025a) |
| 02 | Time threshold | 5, 10, 15, 20 min | Cut-offs drive cumulative measures (Páez et al. 2012) |
| 03 | Study area | Barangay vs walk-shed of 10, 15, 20 min around its population centre | Uncertain geographic context (Kwan 2012) |
| 04 | Home lens | 15-minute walk-shed from each home, kept private | Does the front door match the barangay? |
| 05 | Distance type | Street network vs straight line | Apparicio et al. 2008; Oliver et al. 2007 |
| 06 | Origin resolution | Building vs 100 m cell vs H3 resolution 9 | Aggregation error (Hewko et al. 2002) |
| 07 | Service source | Overture only, OpenStreetMap only, merged | Source completeness differs (Ballantyne & Berragan 2024) |
| 08 | Overture confidence | 0.3, 0.5, 0.7 | Stale and duplicate listings |
| 09 | Population surface | WorldPop vs GHS-POP | Placement error near ports and campuses |
| 10 | Jeepney rule | Routes count vs mapped stops only | Informal transit (UNSD 2025) |

### 5.6 Validation

- **Service audit.** A random 30 services per barangay checked against street imagery, giving a found-and-open rate per category.
- **Registry match.** The share of DOH and DepEd public facilities found in the merged layer, per barangay.
- **Street-imagery audit.** About 20 routes in and around each barangay scored for sidewalk, crossings, shade and obstruction, after Nogueira & Diaz (2023), with a count of sari-sari stores seen per kilometre; reported beside M1 to M5, not inside them.

## 6. Interactive web map

The map is the method made visible: every colour on it is an M1 to M5 value from the pipeline, and it doubles as a quality check, since an odd patch usually means a data error.
It follows the [PH lottery story site](https://earlcyu-petcircle.github.io/ph-lottery-outlets/): a one-page story with the map embedded near the top, plus a standalone full-screen version.

- **Layers.** Access hexagons (M1 minutes, M2 count or M4 coverage for the chosen category, on fixed classes shared by every category); the three barangays in outline with their check walk-sheds; services by category and source; LRT and MRT lines and stations, and bus and jeepney routes; barangay and city boundaries; optional flood hazard and wealth context.
- **Interactions.** Go-to buttons for Barangay 136, Loyola Heights, Oranbo and Metro Manila; a category picker and a 5, 10, 15, 20-minute control; a hover card with people, minutes to each category, count within 15 minutes and metro percentile; a compare strip with each barangay's median walk; a walking-speed toggle (3.6, 4.2, 4.8 km/h).
- **What a reader learns.** Where inside and around each barangay access is good or poor, which services drive the gaps, where each sits against the rest of Metro Manila, and how far the picture moves when assumptions change.
- **Build.** The same stack as ph-lottery-outlets: MapLibre GL JS 5.6.0, PMTiles 4.3.0, the OpenFreeMap Positron basemap and tiles built with tippecanoe, served from `docs/` on GitHub Pages.
- **Privacy.** Hexagons hold many buildings, and no home location is stored in the repo or shown on the site.

## 7. Tooling and repo shape

One language, one pipeline: a Python package with numbered stages behind one command, with no SQL files.
A thin `.sh` wrapper is fine where it helps, but no logic lives in shell.

| Stage | Module | Does |
|---|---|---|
| 1 Collect | `src/mma/s1_collect/` | Download and cache the raw sources |
| 2 Build | `src/mma/s2_build/` | People, services and the walking network as GeoParquet |
| 3 Analyse | `src/mma/s3_analyse/` | Walking times, M1 to M5, sensitivity checks, audits |
| 4 Publish | `src/mma/s4_publish/` | Tables, figures, map tiles and the story site |

Planned libraries: geopandas, shapely and pyogrio for vectors; rasterio for WorldPop; the official `overturemaps` downloader; osmnx for the network (Boeing 2017); `scipy.sparse.csgraph` for multi-source shortest paths; h3 for hexagons; matplotlib for figures; tippecanoe for tiles.
Each is added in the PR that first uses it.
Each stage reads only the previous stage's outputs, and a rerun on the same raw data should be byte-identical.

| PR | Scope | Done when |
|---|---|---|
| 1 Design | This page, the package skeleton, `config.toml`, CI with ruff and pytest; no data | The design and skeleton are in `main` |
| 2 Data | Stages 1 and 2: people, services, network; a data-quality note with registry match rates | Every layer has a row count, licence and completeness figure |
| 3 Analysis | Stage 3: M1 to M5, the sensitivity grid, the service and street-imagery audits | The ordering of the three barangays is reported with its robustness |
| 4 Results | Stage 4: figures, findings, the story site and the map | The site runs locally and on GitHub Pages |
| 5 Clean-up | Fresh-clone rerun, byte-identical check, README tidy, citation | A clean clone reproduces every table |

## 8. Decisions made

1. Study area - barangay level for all three (Barangay 136 for Tondo), so the comparison sits at one administrative tier.
2. Home lens - a private check only; the repo and site publish barangays, nothing finer.
3. Travel modes - walking, plus walking to transit (SDG 11.2.1); no timetabled transit, since the only feed is from 2015.
4. Service basket - nine categories grouped by Moreno's social functions.
5. Headline - a profile of M1 to M5 led by M4 coverage, not a weighted composite.
6. Time frame - today's data only.
7. Tooling - a Python package with a CLI; thin `.sh` files where needed; no SQL files.
8. Walk quality - a street-imagery audit on sample routes, which also counts sari-sari stores.

## 9. Limitations

- **The sari-sari gap.** The most everyday shop of all is almost unmapped (section 4.1), so food results understate access and are labelled so.
- **Potential, not realised access.** There is no data on where people actually go (Kwan 1998).
- **Mapped is not there.** Informal retail aside, new and closed shops are missed or kept.
- **Quality, price and capacity** of services are invisible except where registries give capacity.
- **The walk itself.** Heat, floods, crossings, footbridges, safety and sidewalks are not in the network; the audit covers only a sample of routes.
- **Three personal cases.** No claim is made about Metro Manila in general beyond the context layer.

## References

Each entry was checked against its Crossref or publisher record on 4 November 2026.
The note in brackets says how much was read: full text, methods, abstract, or the record only.

- Apparicio, P., Abdelmajid, M., Riva, M. & Shearmur, R. (2008). Comparing alternative approaches to measuring the geographical accessibility of urban health services: distance types and aggregation-error issues. *International Journal of Health Geographics* 7, 7. <https://doi.org/10.1186/1476-072X-7-7> (abstract)
- Ballantyne, P. & Berragan, C. (2024). Overture Point of Interest data for the United Kingdom: a comprehensive, queryable open data product, validated against Geolytix supermarket data. *Environment and Planning B* 51(8), 1974-1980. <https://doi.org/10.1177/23998083241263124> (abstract)
- Boeing, G. (2017). OSMnx: new methods for acquiring, constructing, analyzing, and visualizing complex street networks. *Computers, Environment and Urban Systems* 65, 126-139. <https://doi.org/10.1016/j.compenvurbsys.2017.05.004> (abstract)
- Bohannon, R. W. (1997). Comfortable and maximum walking speed of adults aged 20-79 years: reference values and determinants. *Age and Ageing* 26(1), 15-19. <https://doi.org/10.1093/ageing/26.1.15> (abstract)
- Bruno, M., Monteiro Melo, H. P., Campanelli, B. & Loreto, V. (2024). A universal framework for inclusive 15-minute cities. *Nature Cities* 1, 633-641. <https://doi.org/10.1038/s44284-024-00119-4> (methods, from the arXiv preprint)
- Frank, L. D., Sallis, J. F., Saelens, B. E. et al. (2010). The development of a walkability index: application to the Neighborhood Quality of Life Study. *British Journal of Sports Medicine* 44(13), 924-933. <https://doi.org/10.1136/bjsm.2009.058701> (abstract)
- Geurs, K. T. & van Wee, B. (2004). Accessibility evaluation of land-use and transport strategies: review and research directions. *Journal of Transport Geography* 12(2), 127-140. <https://doi.org/10.1016/j.jtrangeo.2003.10.005> (abstract)
- Hansen, W. G. (1959). How accessibility shapes land use. *Journal of the American Institute of Planners* 25(2), 73-76. <https://doi.org/10.1080/01944365908978307> (abstract)
- Hasselwander, M., Nieland, S., Dematera-Contreras, K. & Goletz, M. (2023). MaaS for the masses: potential transit accessibility gains and required policies under Mobility-as-a-Service. *Multimodal Transportation* 2(3), 100086. <https://doi.org/10.1016/j.multra.2023.100086> (abstract)
- Hewko, J., Smoyer-Tomic, K. E. & Hodgson, M. J. (2002). Measuring neighbourhood spatial accessibility to urban amenities: does aggregation error matter? *Environment and Planning A* 34(7), 1185-1206. <https://doi.org/10.1068/a34171> (abstract)
- Interaksyon (2025). More sari-sari stores selling 'tingi' supplies spring up near schools, says study. 14 August 2025. <https://media.interaksyon.com/trends-spotlights/2025/08/14/300595/more-sari-sari-stores-selling-tingi-supplies-spring-up-near-schools-says-study/> (news, full text; used only for the size of one firm's store network)
- Kwan, M.-P. (1998). Space-time and integral measures of individual accessibility: a comparative analysis using a point-based framework. *Geographical Analysis* 30(3), 191-216. <https://doi.org/10.1111/j.1538-4632.1998.tb00396.x> (abstract)
- Kwan, M.-P. (2012). The uncertain geographic context problem. *Annals of the Association of American Geographers* 102(5), 958-968. <https://doi.org/10.1080/00045608.2012.687349> (abstract)
- Lamentillo, A. M. Y. (2025). Assessing the viability of the 15-minute city model in Metro Manila. *LSE International Development Review* 4(1), 155-189. <https://idr.lse.ac.uk/articles/110> (abstract and press coverage)
- Leather, J., Fabian, H., Gota, S. & Mejia, A. (2011). Walkability and pedestrian facilities in Asian cities: state and issues. ADB Sustainable Development Working Paper Series. Asian Development Bank. <https://www.adb.org/publications/walkability-and-pedestrian-facilities-asian-cities-state-and-issues> (publication page)
- Leyso, N. L. & Umezaki, M. (2024). Spatial inequality in the accessibility of healthcare services in the Philippines. *GeoJournal* 89, 120. <https://doi.org/10.1007/s10708-024-11098-3> (abstract)
- Logan, T. M., Hobbs, M. H., Conrow, L. C., Reid, N. L., Young, R. A. & Anderson, M. J. (2022). The x-minute city: measuring the 10, 15, 20-minute city and an evaluation of its use for sustainable urban design. *Cities* 131, 103924. <https://doi.org/10.1016/j.cities.2022.103924> (abstract)
- Lucas, K., van Wee, B. & Maat, K. (2016). A method to evaluate equitable accessibility: combining ethical theories and accessibility-based approaches. *Transportation* 43(3), 473-490. <https://doi.org/10.1007/s11116-015-9585-2> (abstract)
- Luo, W. & Qi, Y. (2009). An enhanced two-step floating catchment area (E2SFCA) method for measuring spatial accessibility to primary care physicians. *Health & Place* 15(4), 1100-1107. <https://doi.org/10.1016/j.healthplace.2009.06.002> (abstract)
- Luo, W. & Wang, F. (2003). Measures of spatial accessibility to health care in a GIS environment: synthesis and a case study in the Chicago region. *Environment and Planning B* 30(6), 865-884. <https://doi.org/10.1068/b29120> (record only)
- Mañago, C. A. R., Nasalita, M. G., Saveron, C. V., Sunga, Y. A. D. & Claridades, A. R. C. (2025a). Development of a fifteen-minute city index using walkability scores and age-classified population: the case of Pasig City, Metro Manila, Philippines. *ISPRS International Journal of Geo-Information* 14(2), 78. <https://doi.org/10.3390/ijgi14020078> (full text)
- Mañago, C. A. R., Nasalita, M. G., Saveron, C. V., Sunga, Y. A. D. & Claridades, A. R. C. (2025b). Developing a geospatial framework for calculating a 15-Minute City Index (FMCI): the case of Quezon City. *Proceedings of GISTAM 2025*, 73-84. <https://doi.org/10.5220/0013426100003935> (abstract)
- Moreno, C., Allam, Z., Chabaud, D., Gall, C. & Pratlong, F. (2021). Introducing the "15-minute city": sustainability, resilience and place identity in future post-pandemic cities. *Smart Cities* 4(1), 93-111. <https://doi.org/10.3390/smartcities4010006> (abstract)
- Nicoletti, L., Sirenko, M. & Verma, T. (2023). Disadvantaged communities have lower access to urban infrastructure. *Environment and Planning B* 50(3), 831-849. <https://doi.org/10.1177/23998083221131044> (abstract)
- Nogueira, A. C. C. S. & Diaz, C. E. D. (2023). Evaluating public transport accessibility and walkability in Pasig City (Philippines) and their correlation to socioeconomic factors at the barangay level. *Asian Transport Studies* 9, 100117. <https://doi.org/10.1016/j.eastsj.2023.100117> (abstract)
- Oliver, L. N., Schuurman, N. & Hall, A. W. (2007). Comparing circular and network buffers to examine the influence of land use on walking for leisure and errands. *International Journal of Health Geographics* 6, 41. <https://doi.org/10.1186/1476-072X-6-41> (abstract)
- Páez, A., Scott, D. M. & Morency, C. (2012). Measuring accessibility: positive and normative implementations of various accessibility indicators. *Journal of Transport Geography* 25, 141-153. <https://doi.org/10.1016/j.jtrangeo.2012.03.016> (abstract)
- Pereira, R. H. M. & Herszenhut, D. (2023). *Introduction to urban accessibility: a practical guide with R.* Ipea. <https://doi.org/10.38116/9786556350653> (abstract and contents)
- Pereira, R. H. M., Schwanen, T. & Banister, D. (2017). Distributive justice and equity in transportation. *Transport Reviews* 37(2), 170-191. <https://doi.org/10.1080/01441647.2016.1257660> (abstract)
- Talen, E. & Anselin, L. (1998). Assessing spatial equity: an evaluation of measures of accessibility to public playgrounds. *Environment and Planning A* 30(4), 595-613. <https://doi.org/10.1068/a300595> (abstract)
- Tolentino, N. J. Y. & Sigua, R. G. (2022). Characteristics of walking and cycling in Metro Manila, Philippines. *Philippine Transportation Journal* 5(1). <https://ncts.upd.edu.ph/tssp/wp-content/uploads/2022/12/TSSP2022_Vol5-No1_02-Tolentino-and-Sigua.pdf> (full text)
- UN Statistics Division and UN-Habitat (2025). SDG indicator metadata 11.2.1: proportion of population that has convenient access to public transport. Last updated 23 April 2025. <https://unstats.un.org/sdgs/metadata/files/Metadata-11-02-01.pdf> (full text)
