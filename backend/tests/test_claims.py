import pytest

from app.services.claims import check_claim


@pytest.mark.parametrize(
    ("claim", "result", "rewrite"),
    [
        ("本系统实现零碳", "block", "筛选级减排潜力"),
        ("项目达到负碳", "block", "给定边界"),
        ("世界首创", "block", "所检国内外文献"),
        ("国际领先", "block", "国内先进水平"),
        ("第三方现场监测证明", "block", "实验室送样检测"),
        ("集成系统已完成50 t/d中试", "block", "低温强化组件"),
        ("系统可去除微塑料", "block", "研究储备"),
        ("装置无二次污染", "block", "持续监测"),
        ("已获多项专利", "warn", "3项已授权"),
        ("证书证明数据真实", "block", "来源和完整性"),
    ],
)
def test_each_boundary_rule(claim, result, rewrite):
    checked = check_claim(claim)
    assert checked["result"] == result
    assert rewrite in checked["suggested_rewrite"]


def test_supported_claim_passes():
    assert check_claim("六批第三方实验室送样检测")["result"] == "pass"


def test_multiple_block_rules_all_reported():
    assert len(check_claim("世界首创零碳系统")["hits"]) == 2


def test_multiple_rules_produce_combined_rewrite():
    rewrite = check_claim("世界首创零碳系统")["suggested_rewrite"]
    assert "所检国内外文献" in rewrite
    assert "筛选级减排潜力" in rewrite


def test_hit_has_evidence_reference():
    assert check_claim("世界首创")["hits"][0]["evidence_refs"]
