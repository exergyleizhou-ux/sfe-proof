# Reuse assessment

审计日期：2026-07-13。四个仓库均通过 GitHub HTTPS 只读浅克隆成功；本项目没有整仓复制或直接复制上游源码。

| 来源仓库 | 审计提交 | 原许可 | 相关路径/能力 | 决策与改造 |
|---|---:|---|---|---|
| `exergyleizhou-ux/ai-data-marketplace` | `f0eb050` | Source-available, all rights reserved | README、可验证证据层、公开验证与追加审计思想 | 只参考“输入—算法—输出哈希绑定”与证书边界；因许可与领域差异，未复制代码；未采用市场、支付、KYC、TEE、DP、Token |
| `exergyleizhou-ux/bos-platform` | `3751c4e` | MIT | `backend/app/`、`frontend/src/`、Compose/CI 的模块化单体组织 | 参考 FastAPI + React/Vite + Docker Compose 工程做法；S-Fe schema、API、页面、测试均新写；未采用 BOS 品牌、虫体数据、Celery/Redis、数字孪生与智能体 |
| `exergyleizhou-ux/PaperGuard` | `0e24a41` | MIT | 表格导入、工业质量规则与“flags anomalies, not fraud”定位 | 参考每条发现附正常解释的表达；围绕水处理重写必填、范围、重复、来源链、检出限规则；未集成通用科研舞弊检测器 |
| `exergyleizhou-ux/ropfec` | `5f60d33` | MIT | ROP/FEC 控制研究实现 | 不采用；与当前 S-Fe 运行证据闭环无直接关系 |

采用方式均为 clean-room 风格的思想级参考。代码来源声明见根目录 `CODE_ORIGIN.md`。

