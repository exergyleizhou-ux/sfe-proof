def scan_samples(samples: list[dict], measurements: list[dict] | None = None) -> list[dict]:
    findings = []
    seen = set()
    for sample in samples:
        code = sample.get("sample_code", "未知样本")
        if code in seen:
            findings.append(_finding("DUPLICATE_SAMPLE", "warn", code, "样本编号重复", "可能为复测记录", "核对并建立复测关系"))
        seen.add(code)
        if sample.get("provenance_type") == "submitted_to_third_party_lab" and (not sample.get("sampler_name") or not sample.get("sampling_location")):
            findings.append(
                _finding(
                    "PROVENANCE_GAP", "warn", code, "第三方实验室送样检测缺少采样人或采样地点，不等于第三方现场采样", "历史报告可能未记录送样前链条", "补充原始委托单或保持边界标签"
                )
            )
    for m in measurements or []:
        value, param, unit = m.get("value"), m.get("parameter_code"), m.get("unit")
        if not unit:
            findings.append(_finding("UNIT_REQUIRED", "error", param or "测量", "测量单位缺失", "原始表头可能单独记载单位", "补齐单位后重新导入"))
        if value is not None and value < 0:
            findings.append(_finding("NEGATIVE_VALUE", "error", param or "测量", "浓度出现负数", "可能是仪器基线校正结果", "核对原始报告与检出限表达"))
        if param == "pH" and value is not None and not 0 <= value <= 14:
            findings.append(_finding("PH_RANGE", "error", param, "pH超出0—14", "可能是列映射或单位错误", "核对字段映射"))
        if m.get("qualifier") == "less_than" and not m.get("detection_limit"):
            findings.append(_finding("DETECTION_LIMIT", "error", param or "测量", "小于检出限数据缺少检出限", "原报告可能仅在表头记录", "补录检出限，禁止按0处理"))
    return findings


def _finding(rule_id: str, severity: str, object_ref: str, description: str, explanation: str, action: str) -> dict:
    return {
        "rule_id": rule_id,
        "severity": severity,
        "object_ref": object_ref,
        "description": description,
        "innocent_explanation": explanation,
        "suggested_action": action,
        "status": "open",
    }
