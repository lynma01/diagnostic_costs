from pathlib import Path

import duckdb
import polars as pl

PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
INTERMEDIATE_DIR = DATA_DIR / "intermediate"
CMS_DIR = DATA_DIR / "cms"

MEDSTAR_HOSPITALS: dict[str, str] = {
    "franklin_square": "https://www.medstarhealth.org/-/media/project/mho/medstar/billing-and-insurance/2025/520608007_medstarfranklinsquaremedicalcenter_standardcharges.csv",
    "georgetown_univ": "https://www.medstarhealth.org/-/media/project/mho/medstar/billing-and-insurance/2025/522218584_medstargeorgetownuniversityhospital_standardcharges.csv",
    "good_samaritan": "https://www.medstarhealth.org/-/media/project/mho/medstar/billing-and-insurance/2025/520591607_medstargoodsamaritan_standardcharges.csv",
    "harbor_hosp": "https://www.medstarhealth.org/-/media/project/mho/medstar/billing-and-insurance/2025/520491660_medstarharborhospital_standardcharges.csv",
    "montgomery_med": "https://www.medstarhealth.org/-/media/project/mho/medstar/billing-and-insurance/2025/520646893_medstarmontgomerymedicalcenter_standardcharges.csv",
    "national_rehab": "https://www.medstarhealth.org/-/media/project/mho/medstar/billing-and-insurance/2025/521369749_medstarnationalrehabilitationhospital_standardcharges.csv",
    "mary_hosp": "https://www.medstarhealth.org/-/media/project/mho/medstar/billing-and-insurance/2025/520619006_medstarstmaryshospital_standardcharges.csv",
    "union_memorial": "https://www.medstarhealth.org/-/media/project/mho/medstar/billing-and-insurance/2025/520591685_medstarunionmemorialhospital_standardcharges.csv",
    "washington_hosp_center": "https://www.medstarhealth.org/-/media/project/mho/medstar/billing-and-insurance/2025/521272129_medstarwashingtonhospitalcenter_standardcharges.csv",
}

COLUMN_MAP: dict[str, str] = {
    "code|3": "cpt_code",
    "code|3|type": "cpt_code_type",
    "code|1": "drg_code",
    "code|1|type": "drg_code_type",
    "standard_charge|gross": "charge_gross",
    "standard_charge|min": "charge_min",
    "standard_charge|max": "charge_max",
    "standard_charge|discounted_cash": "charge_discounted",
}

CHARGE_COLS: list[str] = [
    "charge_gross",
    "charge_min",
    "charge_max",
    "charge_discounted",
]

_CODE_GROUPS: dict[str, dict] = {
    "office_em": {
        "codes": [99202, 99203, 99204, 99205, 99211, 99212, 99213, 99214, 99215],
        "setting": "both",
    },
    "initial_hospital_care": {
        "codes": [99221, 99222, 99223],
        "setting": "inpatient",
    },
    "infusion": {
        "codes": [96360, 96361, 96365, 96366, 96367, 96368],
        "setting": "both",
    },
    "wound_repair": {
        "codes": [12031],
        "setting": "both",
    },
    "nerve_block": {
        "codes": [64530],
        "setting": "both",
    },
    "biopsy": {
        "codes": [47000],
        "setting": "inpatient",
    },
}

CPT_DESCRIPTIONS: dict[str, str] = {
    "12031": "Wound repair, scalp/trunk 2.5cm or less",
    "47000": "Liver biopsy, percutaneous needle",
    "64530": "Celiac plexus nerve block",
    "96360": "IV infusion, hydration initial 31 min–1 hr",
    "96361": "IV infusion, hydration each additional hr",
    "96365": "IV infusion, therapeutic initial up to 1 hr",
    "96366": "IV infusion, therapeutic each additional hr",
    "96367": "IV infusion, therapeutic additional sequential",
    "96368": "IV infusion, therapeutic concurrent",
    "99202": "Office visit, new patient, low complexity",
    "99203": "Office visit, new patient, moderate complexity",
    "99204": "Office visit, new patient, moderate-high complexity",
    "99205": "Office visit, new patient, high complexity",
    "99211": "Office visit, established patient, minimal",
    "99212": "Office visit, established patient, straightforward",
    "99213": "Office visit, established patient, low complexity",
    "99214": "Office visit, established patient, moderate complexity",
    "99215": "Office visit, established patient, high complexity",
    "99221": "Initial hospital care, low complexity",
    "99222": "Initial hospital care, moderate complexity",
    "99223": "Initial hospital care, high complexity",
}

EPISODE_FREQUENCIES: dict[str, dict] = {
    "initial_hospital_care": {"code": 99223, "qty": 1},
    "office_followup": {"code": 99214, "qty": 1},
    "biopsy": {"code": 47000, "qty": 1},
    "nerve_block": {"code": 64530, "qty": 1},
    "wound_repair": {"code": 12031, "qty": 1},
    "infusion_initial": {"code": 96365, "qty": 1},
    "infusion_additional": {"code": 96366, "qty": 1},
}


def get_connection() -> duckdb.DuckDBPyConnection:
    return duckdb.connect()


def build_episode_codes_df() -> pl.DataFrame:
    rows: list[dict] = []
    for role, group in _CODE_GROUPS.items():
        for code in group["codes"]:
            rows.append(
                {
                    "cpt_code": str(code),
                    "clinical_role": role,
                    "setting": group["setting"],
                }
            )
    return pl.DataFrame(rows, schema={"cpt_code": pl.Utf8, "clinical_role": pl.Utf8, "setting": pl.Utf8})


def standardize_columns(df: pl.DataFrame) -> pl.DataFrame:
    rename = {k: v for k, v in COLUMN_MAP.items() if k in df.columns}
    return df.rename(rename)
