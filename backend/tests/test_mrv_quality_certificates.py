from datetime import datetime, timezone

from app.services.certificates import canonical_json, certificate_id, sha256, verify
from app.services.mrv import calculate_mrv
from app.services.provenance import warning_for
from app.services.quality import scan_samples


def activities(placeholder=False):
    return [{"name": "电力", "amount": 2, "factor": 3, "placeholder": placeholder, "data_grade": "measured", "factor_source": "factor-v1"}]


def test_mrv_complete_positive():
    assert calculate_mrv(activities(), [{"name": "电力", "amount": 1, "factor": 2}], "v1", True)["conclusion_status"] == "screening_positive"


def test_mrv_negative():
    assert calculate_mrv([{"name": "a", "amount": 1, "factor": 1}], [{"name": "b", "amount": 2, "factor": 2}], "v1", True)["conclusion_status"] == "screening_negative"


def test_mrv_n2o_gap_is_indeterminate():
    assert calculate_mrv(activities(), activities(), "v1", False)["conclusion_status"] == "indeterminate"


def test_mrv_placeholder_is_indeterminate():
    assert calculate_mrv(activities(True), activities(), "v1", True)["conclusion_status"] == "indeterminate"


def test_mrv_missing_factor_is_named():
    assert "甲醇" in calculate_mrv([{"name": "甲醇", "amount": 1}], [], "v1", True)["missing_items"]


def test_mrv_sensitivity_has_three_cases():
    assert set(calculate_mrv(activities(), [], "v1", True)["sensitivity"]) == {"low", "medium", "high"}


def test_mrv_contributor_keeps_grade():
    assert calculate_mrv(activities(), [], "v1", True)["contributors"][0]["data_grade"] == "measured"


def test_provenance_warning_for_submitted_lab():
    assert "不等于第三方现场采样" in warning_for("submitted_to_third_party_lab")


def test_no_provenance_warning_for_team_data():
    assert warning_for("team_p0_experiment") is None


def test_quality_warns_missing_sampler():
    assert scan_samples([{"sample_code": "A", "provenance_type": "submitted_to_third_party_lab"}])[0]["rule_id"] == "PROVENANCE_GAP"


def test_quality_duplicate_sample():
    assert any(x["rule_id"] == "DUPLICATE_SAMPLE" for x in scan_samples([{"sample_code": "A"}, {"sample_code": "A"}]))


def test_quality_negative_value():
    assert scan_samples([], [{"parameter_code": "TN_mg_L", "value": -1, "unit": "mg/L"}])[0]["rule_id"] == "NEGATIVE_VALUE"


def test_quality_invalid_ph():
    assert scan_samples([], [{"parameter_code": "pH", "value": 15, "unit": "1"}])[0]["rule_id"] == "PH_RANGE"


def test_quality_missing_unit():
    assert scan_samples([], [{"parameter_code": "TN_mg_L", "value": 1}])[0]["rule_id"] == "UNIT_REQUIRED"


def test_quality_detection_limit_missing():
    assert any(x["rule_id"] == "DETECTION_LIMIT" for x in scan_samples([], [{"parameter_code": "NO2_N_mg_L", "value": 0.003, "unit": "mg/L", "qualifier": "less_than"}]))


def test_canonical_json_key_order():
    assert canonical_json({"b": 1, "a": 2}) == '{"a":2,"b":1}'


def test_hash_stable_for_key_order():
    assert sha256({"a": 1, "b": 2}) == sha256({"b": 2, "a": 1})


def test_certificate_id_format():
    assert certificate_id("abcdef123456", datetime(2026, 7, 13, tzinfo=timezone.utc)) == "SFE-20260713-ABCDEF12"


def test_certificate_verifies():
    i, r = {"x": 1}, {"y": 2}
    assert verify(i, r, sha256(i), sha256(r))["valid"] is True


def test_input_tamper_fails():
    i, r = {"x": 1}, {"y": 2}
    assert verify({"x": 9}, r, sha256(i), sha256(r))["input_hash_match"] is False


def test_result_tamper_fails():
    i, r = {"x": 1}, {"y": 2}
    assert verify(i, {"y": 9}, sha256(i), sha256(r))["result_hash_match"] is False


def test_certificate_boundary_is_honest():
    i = {}
    result = verify(i, i, sha256(i), sha256(i))
    assert "不证明采样真实性" in result["boundary"]
