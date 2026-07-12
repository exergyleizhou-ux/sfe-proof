def create_chain(client):
    project = client.post("/api/v1/projects", json={"name": "SFe", "code": "SFE-T"}).json()
    batch = client.post("/api/v1/batches", json={"project_id": project["id"], "batch_code": "B-1"}).json()
    sample = client.post(f"/api/v1/batches/{batch['id']}/samples", json={"sample_code": "S-1", "sample_role": "influent", "provenance_type": "submitted_to_third_party_lab"}).json()
    measurement = client.post(f"/api/v1/samples/{sample['id']}/measurements", json={"parameter_code": "TN_mg_L", "value": 20, "unit": "mg/L"}).json()
    return project, batch, sample, measurement


def test_healthz(client):
    assert client.get("/healthz").json() == {"status": "ok"}


def test_readyz(client):
    assert client.get("/readyz").status_code == 200


def test_create_project_batch_sample_measurement(client):
    p, b, s, m = create_chain(client)
    assert (p["id"], b["id"], s["id"], m["id"]) == (1, 1, 1, 1)


def test_api_provenance_label(client):
    assert "不等于第三方现场采样" in create_chain(client)[2]["provenance_warning"]


def test_api_load_without_flow_422(client):
    assert client.post("/api/v1/calculations/load-reduction", json={"influent_mg_l": 20, "effluent_mg_l": 2}).status_code == 422


def test_api_claim_gate(client):
    assert client.post("/api/v1/claims/check", json={"text": "世界首创"}).json()["result"] == "block"


def test_api_mrv_gate(client):
    body = {"baseline_activities": [{"name": "电力", "amount": 2, "factor": 3}], "project_activities": [{"name": "电力", "amount": 1, "factor": 2}]}
    assert client.post("/api/v1/mrv/runs", json=body).json()["conclusion_status"] == "indeterminate"


def test_api_certificate_roundtrip(client):
    cert = client.post("/api/v1/certificates", json={"input_snapshot": {"x": 1}, "result_snapshot": {"y": 2}}).json()
    assert client.post(f"/api/v1/certificates/{cert['certificate_id']}/verify", json={}).json()["valid"] is True


def test_api_certificate_tamper(client):
    cert = client.post("/api/v1/certificates", json={"input_snapshot": {"x": 1}, "result_snapshot": {"y": 2}}).json()
    assert client.post(f"/api/v1/certificates/{cert['certificate_id']}/verify", json={"input_snapshot": {"x": 9}}).json()["valid"] is False


def test_api_quality_persists_findings(client):
    _, batch, _, _ = create_chain(client)
    result = client.post("/api/v1/quality/scan", json={"batch_id": batch["id"]}).json()
    assert result["count"] == 1
    assert result["scan_run_id"]
    persisted = client.get("/api/v1/quality/findings", params={"batch_id": batch["id"]}).json()
    assert persisted[0]["batch_id"] == batch["id"]
    assert persisted[0]["project_id"] == batch["project_id"]
    assert persisted[0]["created_at"]


def test_quality_findings_are_isolated_by_batch(client):
    project, first, _, _ = create_chain(client)
    second = client.post("/api/v1/batches", json={"project_id": project["id"], "batch_code": "B-2"}).json()
    client.post(f"/api/v1/batches/{second['id']}/samples", json={"sample_code": "S-2", "sample_role": "effluent", "provenance_type": "submitted_to_third_party_lab"})
    client.post("/api/v1/quality/scan", json={"batch_id": first["id"]})
    client.post("/api/v1/quality/scan", json={"batch_id": second["id"]})
    first_rows = client.get("/api/v1/quality/findings", params={"batch_id": first["id"]}).json()
    second_rows = client.get("/api/v1/quality/findings", params={"batch_id": second["id"]}).json()
    assert {row["batch_id"] for row in first_rows} == {first["id"]}
    assert {row["batch_id"] for row in second_rows} == {second["id"]}


def test_api_evidence_create_list(client):
    body = {"name": "查新", "artifact_type": "novelty_search", "status": "summary"}
    assert client.post("/api/v1/evidence", json=body).status_code == 201
    assert client.get("/api/v1/evidence").json()[0]["name"] == "查新"


def test_api_csv_error(client):
    assert client.post("/api/v1/batches/99/import", files={"file": ("bad.csv", b"x,y\n1,2", "text/csv")}).status_code == 404


def test_background_wide_csv_creates_samples_and_measurements(client):
    _, batch, _, _ = create_chain(client)
    content = (
        "date,NO2_N_in_mg_L,NO2_N_out_mg_L,TN_in_mg_L,TN_out_mg_L,NO3_N_in_mg_L,NO3_N_out_mg_L,provenance_type,client,laboratory,sampler,sampling_location\n"
        "2023-11-24,0.272,<0.003,12.6,0.28,9.50,0.12,submitted_to_third_party_lab,委托方,实验室,未记录,报告未记录/实验室送样\n"
    )
    response = client.post(f"/api/v1/batches/{batch['id']}/import", files={"file": ("seed.csv", content.encode(), "text/csv")})
    assert response.json()["samples_created"] == 2
    assert response.json()["measurements_created"] == 6
    imported = client.get(f"/api/v1/batches/{batch['id']}").json()["samples"]
    assert any(sample["provenance_warning"] for sample in imported)


def test_long_csv_really_writes_sample_and_measurement(client):
    _, batch, _, _ = create_chain(client)
    content = "sample_code,sample_role,parameter_code,value,unit,provenance_type\nP0-E,effluent,TN_mg_L,1.2,mg/L,team_p0_experiment\n"
    response = client.post(f"/api/v1/batches/{batch['id']}/import", files={"file": ("long.csv", content.encode(), "text/csv")})
    assert response.json()["samples_created"] == 1
    assert response.json()["measurements_created"] == 1
    detail = client.get(f"/api/v1/batches/{batch['id']}").json()
    imported = next(sample for sample in detail["samples"] if sample["sample_code"] == "P0-E")
    assert imported["measurements"][0]["value"] == 1.2


def test_csv_reports_row_level_errors_and_keeps_valid_rows(client):
    _, batch, _, _ = create_chain(client)
    content = "sample_code,sample_role,parameter_code,value,unit\nGOOD,effluent,TN_mg_L,1.2,mg/L\nBAD,effluent,TN_mg_L,nan,mg/L\n"
    result = client.post(f"/api/v1/batches/{batch['id']}/import", files={"file": ("long.csv", content.encode(), "text/csv")}).json()
    assert result["accepted"] == 1
    assert result["errors"] == [{"row": 3, "message": "value必须为有限非负数"}]


def test_openapi_contains_certificate_routes(client):
    assert "/api/v1/certificates/{cid}/verify" in client.get("/openapi.json").json()["paths"]
