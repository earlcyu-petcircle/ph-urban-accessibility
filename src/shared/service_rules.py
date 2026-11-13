"""
The rules that sort a place into one of the nine service categories, and tell two records of
one place apart from two places, for src/02_build_tables/build_services.py; and the rule that
picks out Jollibee stores, a service shown beside the nine but not in the score, for
build_jollibee.py.

They are plain patterns and functions with no inputs from disk, so tests/test_service_rules.py
can check them. docs/data-quality.md ("The service layer") explains each one.
"""

import difflib
import re
import unicodedata

import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

SARI_SARI = r"sari.?sari"
SUPERMARKET = (
    r"supermarket|hypermarket|puregold|savemore|save more|walter ?mart|shopwise|robinsons (?:super|easy)|landers|"
    r"s&r|metro (?:super|market)|rustan|unimart|landmark|ultra mega|cash ?(?:&|and) ?carry"
)
MARKET_NAME = r"palengke|public market|wet market|talipapa|mercado|bagsakan|\bmarket\b"
NOT_MARKET = (
    r"super ?market|mini ?market|minimart|hypermarket|flea|night market|online|stock|marketing|market ?place|"
    r"bazaar|weekend|saturday|sunday|food market|tiangge|tiange"
)
HOSPITAL_NAME = (
    r"hospital|ospital|medical cent(?:er|re)|infirmary|sanitarium|sanatorium|heart cent(?:er|re)|"
    r"lung cent(?:er|re)|kidney (?:and transplant )?institute|children'?s medical|maternity hospital"
)
# Overture lists the wards, departments and outpatient clinics of a hospital as places of their own
HOSPITAL_PART = (
    r"department|\bdept\b|\bward\b|\broom\b|\bopd\b|out ?-?patient|\bunit\b|division|office|\bwing\b|pavilion|"
    r"building|\bbldg\b|tower|section|x-?ray|laborator|diagnostic|imaging|dialysis|pharmacy|cashier|billing|"
    r"admitting|clinic|satellite|emergency room|\ber\b|cancer cent|\beye\b|dental|derma|aesthetic|wellness|rehab|"
    r"\bicu\b|picu|nicu|neurolog|cardiac|vascular|lasik|ear nose|\bent\b|oncolog|patholog|radiolog|surg|\bat\b"
)
CLINIC_NAME = (
    r"clinic|klinika|health cent(?:er|re)|health station|\bbhs\b|\brhu\b|lying.?in|birthing|medical|doctor|"
    r"\bdr\.?\s|polyclinic|family (?:health|medicine|practice)|health care|healthcare|super health"
)
NEVER_CARE = r"dental|dentist|orthodont|\bdent\b|animal|veterinar|\bvet\b|\bpets?\b"
GENERAL_CARE = r"medical clinic|health cent(?:er|re)|health station|lying.?in|birthing|family|general|polyclinic"
NOT_PRIMARY_CARE = (
    r"derma|aesthetic|cosmetic|skin|hair|slim|"
    r"spa\b|massage|optic|optical|eye (?:cent|clinic|care|institute)|ophthalm|laborator|diagnostic|imaging|x-?ray|"
    r"dialysis|rehab|therapy|psych|drug test|drug testing|wellness|beauty|laser|vision|hearing|ent clinic|"
    r"ultrasound|bite|vaccin|pharma|drugstore|pharmacy|ivf|fertility"
)
PRIVATE_SCHOOL = (
    r"academy|college|universit|montessori|christian|catholic|parochial|\bsaint\b|"
    r"\binc\b|incorporated|learning|institute|foundation|international|baptist|adventist|islamic|chinese|"
    r"colegio|ateneo|la salle|maryknoll|\bkids?\b|child|tutorial|review|seminary|cathedral|our lady|"
    r"immaculate|sacred|school of|ministr|pre-?school|preschool|nursery|kinder|day ?care|"
    r"\bcenter\b|centre|training|driving|language|music|dance|art school|technical|vocational|"
    r"special education|mission|jesus|christ|bible|gospel|church|cristo|lord|divine|blessed|living word|"
    r"integrated basic|\bschool,? inc"
)
ELEMENTARY = r"elementary|\belem\b|\bes\b|e/s|central school|primary school|elem\. school"
HIGH = r"high school|\bhs\b|\bnhs\b|\bshs\b|secondary|science high"
INTEGRATED = r"integrated school|\bis\b"
SCHOOL_PART = r"office|department|building|\bbldg\b|records|registrar|faculty|canteen|library|\bgym\b|court|gate"


# OpenStreetMap tags for open space, and shop tags that sell food, with the kind they get
OPEN_SPACE = {
    ("leisure", "park"),
    ("leisure", "playground"),
    ("leisure", "garden"),
    ("leisure", "common"),
    ("leisure", "village_green"),
    ("landuse", "recreation_ground"),
    ("landuse", "village_green"),
    ("place", "square"),
}
FOOD_SHOPS = {
    "supermarket": "supermarket",
    "convenience": "convenience",
    "grocery": "grocery",
    "greengrocer": "grocery",
    "general": "grocery",
    "kiosk": "grocery",
}
# Jollibee stores in OpenStreetMap: a fast-food or restaurant amenity carrying Jollibee's brand
# ID, or, when no brand ID is set, a Jollibee name (some are spelled "Jolibee")
JOLLIBEE_WIKIDATA = "Q37614"
JOLLIBEE_NAME = r"\bjol+i+bee\b"
JOLLIBEE_AMENITY = ("fast_food", "restaurant")

# Words that say what a place is rather than which one it is; names are compared without them
GENERIC = set(
    "the of and at ng sa de del la inc corp corporation co company ph phil phils philippines branch store shop "
    "mart minimart supermarket grocery convenience pharmacy drugstore drug botika market public palengke talipapa "
    "hospital medical center centre clinic health station barangay brgy bhs city general memorial "
    "school elementary es elem high hs nhs shs national integrated is senior junior main annex extension deped "
    "lrt mrt station".split()
)


def norm_name(s):
    """A name for matching: ascii, lower case, no punctuation."""
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return ""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", re.sub(r"\(.*?\)", " ", s)).strip()


def same_place(a, b):
    """Whether two normalised names can name one place: the distinctive words of one are all in
    the other's, or the two read alike. A missing name never contradicts."""
    if not a or not b:
        return True
    ta, tb = set(a.split()) - GENERIC, set(b.split()) - GENERIC
    if not ta or not tb:
        return a == b or difflib.SequenceMatcher(None, a, b).ratio() >= 0.8
    return (
        ta <= tb or tb <= ta or difflib.SequenceMatcher(None, " ".join(sorted(ta)), " ".join(sorted(tb))).ratio() >= 0.8
    )


def has(series, pattern):
    return series.fillna("").str.contains(pattern, case=False, regex=True)


def health_category(name, hospital_tag, primary_tag, trust_hospital_tag):
    """'hospital', 'primary_care' or None, from the name and the source's own health tag.

    Overture files many clinics under "hospital", so there a hospital needs a hospital name;
    an OpenStreetMap hospital tag is trusted unless the name says clinic."""
    never = has(name, NEVER_CARE)
    hosp, clinic = has(name, HOSPITAL_NAME), has(name, CLINIC_NAME)
    specialist = has(name, NOT_PRIMARY_CARE) & ~has(name, GENERAL_CARE) & ~hosp
    part = has(name, HOSPITAL_PART)
    is_hospital = (
        ~never
        & (hospital_tag | primary_tag)
        & np.where(trust_hospital_tag, hospital_tag & (hosp | ~clinic), hosp & ~part)
    )
    is_primary = ~never & ~is_hospital & ~specialist & (primary_tag | (hospital_tag & clinic))
    return np.select([is_hospital, is_primary], ["hospital", "primary_care"], None)


def school_level(name, isced=None):
    """'elementary', 'high', 'integrated' or None, from the name and an ISCED level tag."""
    level = np.select(
        [has(name, INTEGRATED), has(name, ELEMENTARY) & has(name, HIGH), has(name, ELEMENTARY), has(name, HIGH)],
        ["integrated", "integrated", "elementary", "high"],
        None,
    )
    if isced is not None:
        isced = isced.fillna("")
        from_tag = np.select(
            [isced.str.contains("1") & isced.str.contains("[23]"), isced.str.contains("1"), isced.str.contains("[23]")],
            ["integrated", "elementary", "high"],
            None,
        )
        level = np.where(pd.isna(level), from_tag, level)
    return level


def school_rows(df, level):
    """One row per public school category a school serves (an integrated school serves both)."""
    df = df.assign(level=level)
    elem = df[df.level.isin(["elementary", "integrated"])].assign(category="public_elementary")
    high = df[df.level.isin(["high", "integrated"])].assign(category="public_high")
    return pd.concat([elem, high], ignore_index=True)


def is_jollibee(amenity, brand_wikidata, name):
    """Whether OpenStreetMap features are Jollibee stores. Another brand's restaurant that JFC
    operates (a Chowking) carries its own brand ID, and JFC's offices and car parks are not
    restaurants, so neither counts."""
    brand = brand_wikidata.fillna("")
    named = brand.eq("") & has(name, JOLLIBEE_NAME)
    return amenity.fillna("").isin(JOLLIBEE_AMENITY) & (brand.eq(JOLLIBEE_WIKIDATA) | named)


def group_within(x, y, radius):
    """Group codes joining points (in metres) that lie within `radius` of each other, directly
    or through a chain of such points."""
    pairs = cKDTree(np.column_stack([x, y])).query_pairs(radius, output_type="ndarray")
    m = coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(len(x), len(x)))
    return connected_components(m, directed=False)[1]
