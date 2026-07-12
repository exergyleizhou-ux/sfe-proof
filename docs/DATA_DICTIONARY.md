# Data dictionary

核心实体包括 Project、Batch、Sample、Measurement、EvidenceArtifact、QualityFinding、MRVRun 与 EvidenceCertificate。正式数据库为 PostgreSQL 16；SQLite 仅用于隔离自动化测试。

- `system_stage`: `background_research | component_pilot | competition_prototype | field_demo`
- `sample_role`: `influent | effluent | intermediate | blank`
- `provenance_type`: `submitted_to_third_party_lab | third_party_witnessed_field | team_p0_experiment | background_literature`
- `qualifier`: `equal | less_than | greater_than`; `less_than` 必须同时保存 `detection_limit`
- `data_grade`: `measured | reported | estimated | placeholder`
- 浓度默认单位 `mg/L`；N₂O-N 必须另外记录明确单位和方法
- `evidence_level` 将背景证据与学生 P0 数据分区，禁止混用

参数代码：`TN_mg_L`、`NO3_N_mg_L`、`NO2_N_mg_L`、`NH4_N_mg_L`、`TP_mg_L`、`COD_mg_L`、`SO4_mg_L`、`Fe_dissolved_mg_L`、`pH`、`DO_mg_L`、`ORP_mV`、`temperature_C`、`N2O_N`。

