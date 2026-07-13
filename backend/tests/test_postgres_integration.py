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
