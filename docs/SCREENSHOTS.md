# Screenshots

Playwright 核心闭环在 `docs/screenshots/` 生成：

1. `01-background-chain.png`：六批数据、复算结果与送样来源边界。
2. `02-quality-findings.png`：质量检查及可能的正常解释。
3. `03-claim-block.png`：越界表述被规则化拦截。
4. `04-certificate-valid.png`：证书输入与结果哈希验证成功。

截图由 `make e2e` 在真实 Chromium 中生成，不以手工占位图替代。

