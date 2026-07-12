from statistics import mean


def conservative_value(value: float, qualifier: str = "equal", detection_limit: float | None = None) -> tuple[float, str | None]:
    if qualifier == "less_than":
        if detection_limit is None:
            raise ValueError("检出限数据缺少 detection_limit")
        return detection_limit, "小于检出限值按检出限作为保守上界"
    return value, None


def concentration_reduction(influent: list[float], effluent: list[float], qualifiers: list[str] | None = None) -> dict:
    if not influent or len(influent) != len(effluent):
        raise ValueError("进出水数据必须非空且一一配对")
    if any(value < 0 for value in influent + effluent):
        raise ValueError("浓度不能为负数")
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
    if min(influent_mg_l, effluent_mg_l, flow_m3_d) < 0:
        raise ValueError("浓度和流量不能为负数")
    incoming = influent_mg_l * flow_m3_d * 1e-3
    outgoing = effluent_mg_l * flow_m3_d * 1e-3
    return {"influent_load_kg_d": incoming, "effluent_load_kg_d": outgoing, "reduction_kg_d": incoming - outgoing}


def mass_balance(inputs: dict[str, float], outputs: dict[str, float], required_terms: list[str], tolerance_pct: float = 5) -> dict:
    missing = [term for term in required_terms if term not in inputs and term not in outputs]
    if missing:
        return {"status": "incomplete", "missing_items": missing, "tolerance_pct": tolerance_pct, "calibration_note": "5%为演示阈值，需按本装置历史噪声校准"}
    total_in, total_out = sum(inputs.values()), sum(outputs.values())
    closure_error = abs(total_in - total_out) / total_in * 100 if total_in else 0
    return {
        "status": "complete",
        "within_tolerance": closure_error <= tolerance_pct,
        "closure_error_pct": round(closure_error, 3),
        "missing_items": [],
        "tolerance_pct": tolerance_pct,
        "calibration_note": "需按本装置历史噪声校准",
    }
