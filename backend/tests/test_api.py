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
    payload = {"samples": [{"sample_code": "A", "provenance_type": "submitted_to_third_party_lab"}]}
    assert client.post("/api/v1/quality/scan", json=payload).json()["count"] == 1
    assert len(client.get("/api/v1/quality/findings").json()) == 1


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


def test_openapi_contains_certificate_routes(client):
    assert "/api/v1/certificates/{cid}/verify" in client.get("/openapi.json").json()["paths"]
