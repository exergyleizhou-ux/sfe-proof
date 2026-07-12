import math
from statistics import mean

MASS_BALANCE_TEMPLATES = {
    "nitrogen": {"required_inputs": ["influent_TN"], "required_outputs": ["effluent_TN", "nitrogen_gas", "sludge_nitrogen"]},
    "phosphorus": {"required_inputs": ["influent_TP"], "required_outputs": ["effluent_TP", "precipitated_phosphorus", "sludge_phosphorus"]},
    "sulfur": {"required_inputs": ["sulfur_feed", "influent_sulfur"], "required_outputs": ["effluent_sulfate", "effluent_sulfide", "solid_sulfur"]},
}


def conservative_value(value: float, qualifier: str = "equal", detection_limit: float | None = None) -> tuple[float, str | None]:
    if qualifier == "less_than":
        if detection_limit is None:
            raise ValueError("检出限数据缺少 detection_limit")
        return detection_limit, "小于检出限值按检出限作为保守上界"
    return value, None


def concentration_reduction(influent: list[float], effluent: list[float], qualifiers: list[str] | None = None) -> dict:
    if not influent or len(influent) != len(effluent):
        raise ValueError("进出水数据必须非空且一一配对")
    if any(not math.isfinite(value) or value < 0 for value in influent + effluent):
        raise ValueError("浓度必须为有限非负数")
    cin, cout = mean(influent), mean(effluent)
    if cin == 0:
        raise ValueError("进水均值不能为零")
    return {
        "influent_mean": round(cin, 3),
        "effluent_mean": round(cout, 3),
        "concentration_reduction_pct": round((cin - cout) / cin * 100, 2),
        "metric_label": "浓度削减",
        "engineering_removal_claim_allowed": False,
        "qualifier_note": "含检出限定符，按保守上界处理" if qualifiers and "less_than" in qualifiers else None,
    }


def load_reduction(influent_mg_l: float, effluent_mg_l: float, flow_m3_d: float | None) -> dict:
    if flow_m3_d is None:
        raise ValueError("缺少可核验流量，禁止计算负荷削减")
    if any(not math.isfinite(value) or value < 0 for value in (influent_mg_l, effluent_mg_l, flow_m3_d)):
        raise ValueError("浓度和流量必须为有限非负数")
    incoming = influent_mg_l * flow_m3_d * 1e-3
    outgoing = effluent_mg_l * flow_m3_d * 1e-3
    return {"influent_load_kg_d": incoming, "effluent_load_kg_d": outgoing, "reduction_kg_d": incoming - outgoing}


def mass_balance(
    inputs: dict[str, dict],
    outputs: dict[str, dict],
    required_inputs: list[str],
    required_outputs: list[str],
    tolerance_pct: float = 5,
    template: str | None = None,
) -> dict:
    if template:
        if template not in MASS_BALANCE_TEMPLATES:
            raise ValueError("未知质量平衡模板")
        required_inputs = list(dict.fromkeys(required_inputs + MASS_BALANCE_TEMPLATES[template]["required_inputs"]))
        required_outputs = list(dict.fromkeys(required_outputs + MASS_BALANCE_TEMPLATES[template]["required_outputs"]))
    missing_inputs = [name for name in required_inputs if name not in inputs]
    missing_outputs = [name for name in required_outputs if name not in outputs]
    if missing_inputs or missing_outputs:
        return _incomplete(missing_inputs, missing_outputs, tolerance_pct, "required_terms_missing", template)
    terms = {**inputs, **outputs}
    units = {term.get("unit") for term in terms.values()}
    if None in units or "" in units or len(units) != 1:
        raise ValueError("质量平衡所有输入输出必须使用一致且非空的单位")
    values = [term.get("value") for term in terms.values()]
    if any(not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0 for value in values):
        raise ValueError("质量项必须为有限非负数")
    total_in = sum(term["value"] for term in inputs.values())
    total_out = sum(term["value"] for term in outputs.values())
    if total_in == 0:
        return _incomplete([], [], tolerance_pct, "total_input_zero", template)
    closure_error = abs(total_in - total_out) / total_in * 100
    return {
        "status": "complete",
        "error": None,
        "template": template,
        "unit": next(iter(units)),
        "total_input": total_in,
        "total_output": total_out,
        "within_tolerance": closure_error <= tolerance_pct,
        "closure_error_pct": round(closure_error, 3),
        "missing_inputs": [],
        "missing_outputs": [],
        "tolerance_pct": tolerance_pct,
        "calibration_note": "需按本装置历史噪声校准",
    }


def _incomplete(missing_inputs: list[str], missing_outputs: list[str], tolerance_pct: float, error: str, template: str | None) -> dict:
    return {
        "status": "incomplete",
        "error": error,
        "template": template,
        "missing_inputs": missing_inputs,
        "missing_outputs": missing_outputs,
        "tolerance_pct": tolerance_pct,
        "calibration_note": "5%为演示阈值，需按本装置历史噪声校准",
    }
