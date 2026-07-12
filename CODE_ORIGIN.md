# Code origin

本仓库的领域模型、API、计算规则、主张门控、证书机制、前端页面与测试均围绕 S-Fe 于本仓库新写，没有直接复制四个来源仓库的源代码。

工程组织与产品原则参考了公开仓库的可观察模式：`bos-platform` 的 FastAPI + React/Vite + Docker Compose 组织、`ai-data-marketplace` 的哈希绑定和诚实证书边界、`PaperGuard` 的“异常不是造假”解释方式。`ropfec` 未集成。具体审计与版本见 `docs/REUSE_ASSESSMENT.md`。

因此本仓库不包含需要保留的上游源码版权头；MIT 许可仅覆盖本仓库代码，不改变背景证据、专利、技术报告及数据原件的权利状态。

