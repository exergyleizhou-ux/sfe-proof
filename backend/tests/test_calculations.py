import pytest

from app.services.calculations import concentration_reduction, conservative_value, load_reduction, mass_balance

TN_IN = [39.0, 12.3, 23.7, 16.4, 18.9, 12.6]
TN_OUT = [2.12, 0.36, 1.12, 0.44, 0.39, 0.28]
NO3_IN = [23.8, 9.50, 8.24, 9.86, 13.6, 9.50]
NO3_OUT = [1.12, 0.80, 0.12, 0.24, 0.14, 0.12]


def test_tn_influent_mean():
    assert concentration_reduction(TN_IN, TN_OUT)["influent_mean"] == 20.483


def test_tn_effluent_mean():
    assert concentration_reduction(TN_IN, TN_OUT)["effluent_mean"] == 0.785


def test_tn_reduction():
    assert concentration_reduction(TN_IN, TN_OUT)["concentration_reduction_pct"] == 96.17


def test_no3_influent_mean():
    assert concentration_reduction(NO3_IN, NO3_OUT)["influent_mean"] == 12.417


def test_no3_effluent_mean():
    assert concentration_reduction(NO3_IN, NO3_OUT)["effluent_mean"] == 0.423


def test_no3_reduction():
    assert concentration_reduction(NO3_IN, NO3_OUT)["concentration_reduction_pct"] == 96.59


def test_metric_is_not_engineering_removal():
    assert concentration_reduction(TN_IN, TN_OUT)["engineering_removal_claim_allowed"] is False


def test_less_than_uses_detection_limit():
    assert conservative_value(0.001, "less_than", 0.003)[0] == 0.003


def test_less_than_has_disclosure_note():
    assert "保守上界" in conservative_value(0.001, "less_than", 0.003)[1]


def test_less_than_without_limit_rejected():
    with pytest.raises(ValueError):
        conservative_value(0.001, "less_than")


def test_load_formula():
    assert load_reduction(20, 2, 50)["reduction_kg_d"] == pytest.approx(0.9)


def test_load_without_flow_rejected():
    with pytest.raises(ValueError, match="流量"):
        load_reduction(20, 2, None)


def test_negative_concentration_rejected():
    with pytest.raises(ValueError):
        concentration_reduction([-1], [0])


def test_unpaired_samples_rejected():
    with pytest.raises(ValueError):
        concentration_reduction([1, 2], [1])


def test_complete_mass_balance():
    assert mass_balance({"n_in": {"value": 100, "unit": "kg/d"}}, {"n_out": {"value": 96, "unit": "kg/d"}}, ["n_in"], ["n_out"])["status"] == "complete"


def test_mass_balance_tolerance():
    assert mass_balance({"n_in": {"value": 100, "unit": "kg/d"}}, {"n_out": {"value": 96, "unit": "kg/d"}}, ["n_in"], ["n_out"])["within_tolerance"] is True


def test_incomplete_mass_balance():
    assert mass_balance({"n_in": {"value": 100, "unit": "kg/d"}}, {}, ["n_in"], ["n_out"])["status"] == "incomplete"


def test_mass_balance_names_missing_term():
    assert mass_balance({"n_in": {"value": 100, "unit": "kg/d"}}, {}, ["n_in"], ["n_out"])["missing_outputs"] == ["n_out"]


def test_mass_balance_zero_input_is_incomplete_not_zero_error():
    result = mass_balance({"in": {"value": 0, "unit": "kg/d"}}, {"out": {"value": 0, "unit": "kg/d"}}, ["in"], ["out"])
    assert result["status"] == "incomplete"
    assert result["error"] == "total_input_zero"
    assert "closure_error_pct" not in result


def test_mass_balance_rejects_mixed_units():
    with pytest.raises(ValueError, match="一致"):
        mass_balance({"in": {"value": 1, "unit": "kg/d"}}, {"out": {"value": 1, "unit": "g/d"}}, ["in"], ["out"])


@pytest.mark.parametrize("value", [-1, float("nan"), float("inf"), float("-inf")])
def test_mass_balance_rejects_invalid_mass(value):
    with pytest.raises(ValueError, match="有限非负"):
        mass_balance({"in": {"value": value, "unit": "kg/d"}}, {"out": {"value": 1, "unit": "kg/d"}}, ["in"], ["out"])


@pytest.mark.parametrize(("template", "expected"), [("nitrogen", "influent_TN"), ("phosphorus", "influent_TP"), ("sulfur", "sulfur_feed")])
def test_mass_balance_templates_require_domain_inputs(template, expected):
    result = mass_balance({}, {}, [], [], template=template)
    assert expected in result["missing_inputs"]
