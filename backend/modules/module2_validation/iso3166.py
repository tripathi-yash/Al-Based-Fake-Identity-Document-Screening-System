"""
iso3166.py — ISO 3166-1 alpha-3 country code reference table.

Prerequisite for Module 2 (Section 4): "ISO 3166 country code list
(free public reference table, one-time download)". Bundled here as a
static set so the module has no external dependency or network call at
runtime.

Note (say this if asked): ICAO Doc 9303 nationality/issuing-state codes
are *based on* ISO 3166-1 alpha-3 but carry a handful of ICAO-specific
exceptions (e.g. "D" historically for Germany, "UNK" for unknown/
stateless, "XXA"-"XXC" for refugees/stateless persons under UNHCR
mandate). For the prototype we validate against plain ISO 3166-1
alpha-3 and treat any ICAO-specific exception codes as a stated,
documented simplification — not a silent gap.
"""

# ISO 3166-1 alpha-3 codes (all current officially assigned codes).
ISO_3166_1_ALPHA3 = {
    "AFG", "ALB", "DZA", "ASM", "AND", "AGO", "AIA", "ATA", "ATG", "ARG",
    "ARM", "ABW", "AUS", "AUT", "AZE", "BHS", "BHR", "BGD", "BRB", "BLR",
    "BEL", "BLZ", "BEN", "BMU", "BTN", "BOL", "BES", "BIH", "BWA", "BVT",
    "BRA", "IOT", "BRN", "BGR", "BFA", "BDI", "CPV", "KHM", "CMR", "CAN",
    "CYM", "CAF", "TCD", "CHL", "CHN", "CXR", "CCK", "COL", "COM", "COD",
    "COG", "COK", "CRI", "CIV", "HRV", "CUB", "CUW", "CYP", "CZE", "DNK",
    "DJI", "DMA", "DOM", "ECU", "EGY", "SLV", "GNQ", "ERI", "EST", "SWZ",
    "ETH", "FLK", "FRO", "FJI", "FIN", "FRA", "GUF", "PYF", "ATF", "GAB",
    "GMB", "GEO", "DEU", "GHA", "GIB", "GRC", "GRL", "GRD", "GLP", "GUM",
    "GTM", "GGY", "GIN", "GNB", "GUY", "HTI", "HMD", "VAT", "HND", "HKG",
    "HUN", "ISL", "IND", "IDN", "IRN", "IRQ", "IRL", "IMN", "ISR", "ITA",
    "JAM", "JPN", "JEY", "JOR", "KAZ", "KEN", "KIR", "PRK", "KOR", "KWT",
    "KGZ", "LAO", "LVA", "LBN", "LSO", "LBR", "LBY", "LIE", "LTU", "LUX",
    "MAC", "MDG", "MWI", "MYS", "MDV", "MLI", "MLT", "MHL", "MTQ", "MRT",
    "MUS", "MYT", "MEX", "FSM", "MDA", "MCO", "MNG", "MNE", "MSR", "MAR",
    "MOZ", "MMR", "NAM", "NRU", "NPL", "NLD", "NCL", "NZL", "NIC", "NER",
    "NGA", "NIU", "NFK", "MKD", "MNP", "NOR", "OMN", "PAK", "PLW", "PSE",
    "PAN", "PNG", "PRY", "PER", "PHL", "PCN", "POL", "PRT", "PRI", "QAT",
    "ROU", "RUS", "RWA", "REU", "BLM", "SHN", "KNA", "LCA", "MAF", "SPM",
    "VCT", "WSM", "SMR", "STP", "SAU", "SEN", "SRB", "SYC", "SLE", "SGP",
    "SXM", "SVK", "SVN", "SLB", "SOM", "ZAF", "SGS", "SSD", "ESP", "LKA",
    "SDN", "SUR", "SJM", "SWE", "CHE", "SYR", "TWN", "TJK", "TZA", "THA",
    "TLS", "TGO", "TKL", "TON", "TTO", "TUN", "TUR", "TKM", "TCA", "TUV",
    "UGA", "UKR", "ARE", "GBR", "USA", "UMI", "URY", "UZB", "VUT", "VEN",
    "VNM", "VGB", "VIR", "WLF", "ESH", "YEM", "ZMB", "ZWE", "ALA",
}

# ICAO 9303 codes used on travel documents that are not plain ISO 3166-1
# alpha-3 — accept these too so a genuinely valid document is never
# flagged "invalid country" (documented exception, see module docstring).
ICAO_MRZ_EXCEPTIONS = {"UNK", "XXA", "XXB", "XXC", "XXX", "GBD", "GBN", "GBO", "GBP", "GBS"}

VALID_COUNTRY_CODES = ISO_3166_1_ALPHA3 | ICAO_MRZ_EXCEPTIONS


def is_valid_country_code(code: str) -> bool:
    """Case-insensitive check against ISO 3166-1 alpha-3 + ICAO exceptions."""
    if not code:
        return False
    return code.strip().upper() in VALID_COUNTRY_CODES
