RULES = [
    (["零碳", "负碳"], "block", "筛选级减排潜力/在给定边界下减少排放", "筛选级核算不能支持绝对碳结论"),
    (["世界首创"], "block", "在所检国内外文献中未见述及相关组合特征", "查新结论不等于世界首创"),
    (["国际领先"], "block", "成果评价为整体达到国内先进水平", "证据仅支持国内先进水平"),
    (["第三方现场监测"], "block", "六批第三方实验室送样检测", "送样检测不等于第三方现场采样"),
    (["集成系统50 t/d中试", "集成系统已完成50 t/d中试"], "block", "50 t/d为低温强化组件工程验证", "组件验证不能外推为学生集成整机"),
    (["去除微塑料"], "block", "微塑料仅为风险与机制研究储备", "当前无实测证据"),
    (["无二次污染"], "block", "持续监测SO₄²⁻、H₂S、pH及铁释放风险", "绝对安全表述超出证据边界"),
    (["已获多项专利"], "warn", "3项已授权背景专利、1项已受理、1份技术文本状态待核", "需区分授权、受理与待核状态"),
    (["证书证明数据真实", "证书即可证明数据真实", "证书证明算法正确"], "block", "证书证明输入—算法—输出的来源和完整性", "完整性证书不证明采样真实性或科学正确性"),
]


def check_claim(text: str) -> dict:
    hits = []
    for terms, result, rewrite, reason in RULES:
        matched = [term for term in terms if term in text]
        if matched:
            hits.append({"matched_terms": matched, "result": result, "reason": reason, "suggested_rewrite": rewrite, "evidence_refs": ["docs/CLAIM_BOUNDARY.md"]})
    result = "block" if any(h["result"] == "block" for h in hits) else "warn" if hits else "pass"
    return {"original_text": text, "result": result, "hits": hits, "suggested_rewrite": hits[0]["suggested_rewrite"] if hits else text}
