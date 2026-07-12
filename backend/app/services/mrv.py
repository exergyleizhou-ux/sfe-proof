import hashlib
import json


def canonical_hash(data: object) -> str:
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def calculate_mrv(baseline: list[dict], project: list[dict], factor_version: str, n2o_addressed: bool) -> dict:
    all_items = baseline + project
    missing = []
    contributors = []
    for item in all_items:
        if item.get("amount") is None or item.get("factor") is None:
            missing.append(item.get("name", "未命名活动"))
            continue
        if item.get("placeholder"):
            missing.append(f"{item.get('name', '未命名活动')}（占位因子）")
        contributors.append(
            {
                "name": item.get("name"),
                "emissions": item["amount"] * item["factor"],
                "data_grade": item.get("data_grade", "estimated"),
                "factor_source": item.get("factor_source", "未记录"),
            }
        )
    if not n2o_addressed:
        missing.append("N₂O直接排放")

    def total(items: list[dict]) -> float:
        return sum((i.get("amount") or 0) * (i.get("factor") or 0) for i in items)

    b, p = total(baseline), total(project)
    delta = b - p
    status = "indeterminate" if missing else "screening_positive" if delta > 0 else "screening_negative"
    return {
        "input_snapshot_hash": canonical_hash({"baseline": baseline, "project": project, "factor_version": factor_version}),
        "factor_set_version": factor_version,
        "baseline_emissions": round(b, 6),
        "project_emissions": round(p, 6),
        "difference": round(delta, 6),
        "contributors": contributors,
        "missing_items": sorted(set(missing)),
        "sensitivity": {"low": round(delta * 0.8, 6), "medium": round(delta, 6), "high": round(delta * 1.2, 6)},
        "conclusion_status": status,
        "confirmed_reduction_allowed": status == "screening_positive" and not missing,
    }
