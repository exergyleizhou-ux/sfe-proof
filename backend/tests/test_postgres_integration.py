import os

import httpx
import pytest

BASE_URL = os.getenv("POSTGRES_API_URL")
pytestmark = pytest.mark.skipif(not BASE_URL, reason="requires live PostgreSQL API stack")


def test_seeded_postgres_api_chain():
    dashboard = httpx.get(f"{BASE_URL}/api/v1/dashboard", timeout=10).json()
    assert dashboard == {
        "project_count": 1,
        "batch_count": 1,
        "sample_count": 12,
        "measurement_count": 36,
        "provenance_gap_count": 12,
        "latest_mrv": None,
    }
    batch = httpx.get(f"{BASE_URL}/api/v1/batches", timeout=10).json()[0]
    detail = httpx.get(f"{BASE_URL}/api/v1/batches/{batch['id']}", timeout=10).json()
    assert len(detail["samples"]) == 12
    assert sum(len(sample["measurements"]) for sample in detail["samples"]) == 36
    assert detail["calculations"]["TN_mg_L"]["concentration_reduction_pct"] == 96.17


def test_postgres_mrv_uses_registered_factor_units_and_rejects_unknown_version():
    activities = [
        {
            "scenario": scenario,
            "name": f"{scenario}电力",
            "factor_activity": "electricity",
            "amount_low": amount * 0.5,
            "amount_base": amount,
            "amount_high": amount * 1.5,
            "unit": "kWh",
            "source": "PostgreSQL integration",
            "data_grade": "reported",
        }
        for scenario, amount in (("baseline", 2), ("project", 1))
    ]
    response = httpx.post(f"{BASE_URL}/api/v1/mrv/runs", json={"activities": activities}, timeout=10)
    assert response.status_code == 201
    assert response.json()["unit_intensity"] == "kgCO2e/m3"
    assert response.json()["baseline_emissions"] == 1.1406

    unknown = httpx.post(f"{BASE_URL}/api/v1/mrv/runs", json={"activities": activities, "factor_set_version": "missing"}, timeout=10)
    assert unknown.status_code == 422
