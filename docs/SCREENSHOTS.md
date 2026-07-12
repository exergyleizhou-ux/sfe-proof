# Screenshots

Playwright 核心闭环在 `docs/screenshots/` 生成：

1. `01-background-chain.png`：六批数据、复算结果与送样来源边界。
2. `02-quality-findings.png`：质量检查及可能的正常解释。
3. `03-claim-block.png`：越界表述被规则化拦截。
4. `04-certificate-valid.png`：证书输入与结果哈希验证成功。
5. `v02-01-real-batch.png`：v0.2 从 PostgreSQL/API 读取的 12 个样本与 36 条测量。
6. `v02-02-manifest-valid.png`：v0.2 下载/提交 manifest 后由后端验证成功。

v0.2 截图由 Playwright 启动 Docker Compose、PostgreSQL、FastAPI 与真实前端后生成，不以手工占位图替代。另有后端请求被拦截的负向 E2E，断言页面只显示“无法验证”。
