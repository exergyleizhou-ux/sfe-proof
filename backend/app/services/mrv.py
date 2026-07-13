import hashlib
import json


def _normalized_unit(unit: str) -> str:
    return unit.strip().replace("³", "3").replace("₂", "2").replace(" ", "").lower()


def validate_activity_factor_unit(activity_unit: str, factor_unit: str) -> None:
    """Reject activity data that cannot cancel the denominator of its factor."""
    normalized_factor = _normalized_unit(factor_unit)
    if "/" not in normalized_factor:
        raise ValueError(f"排放因子单位格式无效：{factor_unit}")
    expected = normalized_factor.rsplit("/", 1)[1]
    if _normalized_unit(activity_unit) != expected:
        expected_display = factor_unit.rsplit("/", 1)[1].strip()
        raise ValueError(f"活动单位 {activity_unit} 与排放因子单位 {factor_unit} 不匹配（应为 {expected_display}）")


def canonical_hash(data: object) -> str:
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def calculate_mrv(
    activities: list[dict],
    factors: dict[str, dict],
    factor_version: str,
    functional_unit: str,
    n2o_addressed: bool,
    equal_effluent_goal_confirmed: bool,
) -> dict:
    missing: list[str] = []
    contributors: list[dict] = []
    totals = {scenario: {level: 0.0 for level in ("low", "base", "high")} for scenario in ("baseline", "project")}
    sides = {activity["scenario"] for activity in activities}
    for required_side in ("baseline", "project"):
        if required_side not in sides:
            missing.append(f"{required_side}关键活动")
    for activity in activities:
        factor = factors.get(activity["factor_activity"])
        if not factor:
            missing.append(f"{activity['name']}（因子注册表缺失）")
            continue
        validate_activity_factor_unit(activity["unit"], factor["unit"])
        placeholder = activity.get("placeholder", False) or factor["placeholder"] or activity["data_grade"] == "placeholder"
        if placeholder:
            missing.append(f"{activity['name']}（占位数据或因子）")
        emissions = {}
        for level in ("low", "base", "high"):
            value = activity[f"amount_{level}"] * factor[f"value_{level}"]
            totals[activity["scenario"]][level] += value
            emissions[level] = round(value, 6)
        contributors.append(
            {
                "scenario": activity["scenario"],
                "name": activity["name"],
                "amount_low": activity["amount_low"],
                "amount_base": activity["amount_base"],
                "amount_high": activity["amount_high"],
                "factor_low": factor["value_low"],
                "factor_base": factor["value_base"],
                "factor_high": factor["value_high"],
                "unit": activity["unit"],
                "source": activity["source"],
                "data_grade": activity["data_grade"],
                "placeholder": placeholder,
                "factor_source": factor["source"],
                "emissions": emissions,
            }
        )
    if not n2o_addressed:
        missing.append("N₂O直接排放")
    if not equal_effluent_goal_confirmed:
        missing.append("同等出水目标未确认")
    sensitivity = {
        level: {
            "baseline": round(totals["baseline"][level], 6),
            "project": round(totals["project"][level], 6),
            "difference": round(totals["baseline"][level] - totals["project"][level], 6),
        }
        for level in ("low", "base", "high")
    }
    delta = sensitivity["base"]["difference"]
    missing = sorted(set(missing))
    status = "indeterminate" if missing else "screening_positive" if delta > 0 else "screening_negative"
    return {
        "input_snapshot_hash": canonical_hash({"activities": activities, "factor_version": factor_version, "functional_unit": functional_unit, "factors": factors}),
        "factor_set_version": factor_version,
        "baseline_emissions": sensitivity["base"]["baseline"],
        "project_emissions": sensitivity["base"]["project"],
        "difference": delta,
        "contributors": contributors,
        "missing_items": missing,
        "sensitivity": sensitivity,
        "conclusion_status": status,
        "confirmed_reduction_allowed": status == "screening_positive",
    }
