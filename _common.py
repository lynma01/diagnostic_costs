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
    "emergency_dept": {
        "codes": [99281, 99282, 99283, 99284, 99285],
        "setting": "inpatient",
    },
    "critical_care": {
        "codes": [99291],
        "setting": "inpatient",
    },
    "prolonged_services": {
        "codes": [99345, 99358, 99417],
        "setting": "both",
    },
    "interprofessional_consult": {
        "codes": [99366, 99367, 99368],
        "setting": "inpatient",
    },
    "preventive_medicine": {
        "codes": [99384, 99385, 99386, 99387, 99394, 99395, 99396, 99397, 99399],
        "setting": "both",
    },
    "counseling": {
        "codes": [99406, 99407],
        "setting": "both",
    },
    "unlisted_preventive": {
        "codes": [99429],
        "setting": "both",
    },
    "care_management": {
        "codes": [99439, 99441, 99442, 99443],
        "setting": "both",
    },
    "neonatal_newborn": {
        "codes": [99461, 99463, 99464, 99465],
        "setting": "inpatient",
    },
    "complex_chronic_care": {
        "codes": [99480, 99483, 99484],
        "setting": "inpatient",
    },
    "transitional_remote_care": {
        "codes": [99490, 99491, 99492, 99493, 99494, 99495, 99496, 99498],
        "setting": "both",
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
