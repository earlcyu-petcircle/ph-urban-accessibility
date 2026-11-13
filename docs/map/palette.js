// Written by src/04_build_map/write_web_palette.py from src/shared/map_layers.py; do not edit.
const CODES = {"food_retail": "food", "palengke": "mkt", "pharmacy": "phar", "primary_care": "care", "hospital": "hosp", "public_elementary": "elem", "public_high": "high", "open_space": "open", "transit": "trans"};
const SCORE_BREAKS = [50, 70, 80, 90, 99.95];
const SCORE = ["#DCE9FF", "#A6C4FF", "#739EFC", "#4577F0", "#1F4FE0", "#173295"];
const MINUTE_BREAKS = [5, 10, 15, 20, 30];
const MINUTES = ["#173295", "#1F4FE0", "#4577F0", "#739EFC", "#A6C4FF", "#DCE9FF"];
const SLOTS = ["#1F4FE0", "#E8407A", "#E8A317"];
const SERVICE = "#9C3F8F";
const TRANSIT = {"rail": "#111111", "bus": "#3FA7D6", "jeepney": "#9C3F8F"};
const JOLLIBEE = "#111111";
const NO_PEOPLE = "#CDD0D7";
