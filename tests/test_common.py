import polars as pl
import _common as C


def test_medstar_hospitals_has_9_entries():
    assert len(C.MEDSTAR_HOSPITALS) == 9


def test_all_hospital_urls_are_https():
    for name, url in C.MEDSTAR_HOSPITALS.items():
        assert url.startswith("https://"), f"{name} URL is not HTTPS"


def test_column_map_covers_charge_columns():
    mapped_values = set(C.COLUMN_MAP.values())
    for col in C.CHARGE_COLS:
        assert col in mapped_values, f"{col} not in COLUMN_MAP values"


def test_code_groups_all_have_codes():
    for role, group in C._CODE_GROUPS.items():
        assert len(group["codes"]) > 0, f"{role} has no codes"
        assert group["setting"] in ("inpatient", "outpatient", "both"), f"{role} bad setting"


def test_biopsy_code_present():
    all_codes = []
    for group in C._CODE_GROUPS.values():
        all_codes.extend(group["codes"])
    assert 47000 in all_codes


def test_build_episode_codes_df_schema():
    df = C.build_episode_codes_df()
    assert df.columns == ["cpt_code", "clinical_role", "setting"]
    assert df.shape[0] > 60


def test_build_episode_codes_df_no_duplicates():
    df = C.build_episode_codes_df()
    assert df.shape[0] == df.unique().shape[0]


def test_standardize_columns_renames():
    df = pl.DataFrame({"code|3": ["47000"], "standard_charge|gross": [1500.0], "other_col": ["x"]})
    result = C.standardize_columns(df)
    assert "cpt_code" in result.columns
    assert "charge_gross" in result.columns
    assert "other_col" in result.columns
    assert "code|3" not in result.columns


def test_get_connection():
    con = C.get_connection()
    result = con.sql("SELECT 1 AS n").pl()
    assert result["n"][0] == 1
    con.close()


def test_episode_frequencies_codes_exist_in_groups():
    all_codes = set()
    for group in C._CODE_GROUPS.values():
        all_codes.update(group["codes"])
    for key, freq in C.EPISODE_FREQUENCIES.items():
        assert freq["code"] in all_codes, f"Frequency code {freq['code']} for '{key}' not in code groups"
        assert freq["qty"] >= 1
