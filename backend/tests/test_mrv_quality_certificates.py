from datetime import datetime, timezone

import pytest

from app.services.certificates import canonical_json, certificate_id, sha256, verify
from app.services.mrv import calculate_mrv
from app.services.provenance import warning_for
from app.services.quality import scan_samples


def activity(scenario="baseline", amount=2, placeholder=False, factor_activity="electricity"):
    return {
        "scenario": scenario,
        "name": f"{scenario}电力",
        "factor_activity": factor_activity,
        "amount_low": amount * 0.8,
        "amount_base": amount,
        "amount_high": amount * 1.2,
        "unit": "kWh",
        "source": "meter",
        "data_grade": "measured",
        "placeholder": placeholder,
    }


def factors(placeholder=False):
    return {"electricity": {"value_low": 2, "value_base": 3, "value_high": 4, "source": "registry", "unit": "kgCO2e/kWh", "placeholder": placeholder}}


def run(activities, factor_registry=None, n2o=True, goal=True, unit="1_m3_treated"):
    return calculate_mrv(activities, factor_registry if factor_registry is not None else factors(), "v1", unit, n2o, goal)


def test_mrv_complete_positive():
    assert run([activity("baseline", 2), activity("project", 1)])["conclusion_status"] == "screening_positive"


def test_mrv_negative():
    assert run([activity("baseline", 1), activity("project", 2)])["conclusion_status"] == "screening_negative"


def test_mrv_n2o_gap_is_indeterminate():
    assert run([activity("baseline"), activity("project")], n2o=False)["conclusion_status"] == "indeterminate"


def test_mrv_placeholder_is_indeterminate():
    assert run([activity("baseline", placeholder=True), activity("project")])["conclusion_status"] == "indeterminate"


def test_mrv_missing_factor_is_named():
    result = run([activity("baseline", factor_activity="methanol"), activity("project")], factors())
    assert any("因子注册表缺失" in item for item in result["missing_items"])


def test_mrv_sensitivity_has_three_cases():
    result = run([activity("baseline", 2), activity("project", 1)])
    assert set(result["sensitivity"]) == {"low", "base", "high"}
    assert result["sensitivity"]["low"]["difference"] != result["sensitivity"]["high"]["difference"]


def test_mrv_contributor_keeps_grade():
    assert run([activity("baseline"), activity("project")])["contributors"][0]["data_grade"] == "measured"


def test_mrv_unconfirmed_equal_effluent_goal_is_indeterminate():
    assert run([activity("baseline"), activity("project")], goal=False)["conclusion_status"] == "indeterminate"


def test_mrv_factor_values_come_from_registry():
    result = run([activity("baseline", 2), activity("project", 1)])
    contributor = result["contributors"][0]
    assert (contributor["factor_low"], contributor["factor_base"], contributor["factor_high"]) == (2, 3, 4)


def test_mrv_rejects_activity_unit_that_does_not_match_factor():
    incompatible = activity("baseline")
    incompatible["unit"] = "kg"
    with pytest.raises(ValueError, match="单位.*不匹配"):
        run([incompatible, activity("project")])


def test_mrv_accepts_unicode_volume_unit_for_volume_factor():
    volume_factor = {"water": {"value_low": 1, "value_base": 1, "value_high": 1, "source": "registry", "unit": "kgCO₂e/m³", "placeholder": False}}
    baseline = activity("baseline", factor_activity="water")
    project = activity("project", factor_activity="water")
    baseline["unit"] = project["unit"] = "m3"
    assert run([baseline, project], volume_factor)["contributors"]


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
