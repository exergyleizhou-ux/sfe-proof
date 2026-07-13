import json
import tomllib
from pathlib import Path

from app.core.config import ALGORITHM_VERSION
from app.main import app


def test_release_versions_stay_in_sync():
    root = Path(__file__).resolve().parents[2]
    backend_version = tomllib.loads((root / "backend/pyproject.toml").read_text())["project"]["version"]
    frontend_version = json.loads((root / "frontend/package.json").read_text())["version"]
    frontend_lock_version = json.loads((root / "frontend/package-lock.json").read_text())["version"]
    uv_packages = tomllib.loads((root / "backend/uv.lock").read_text())["package"]
    backend_lock_version = next(package["version"] for package in uv_packages if package["name"] == "sfe-proof-backend")

    assert backend_version == backend_lock_version == frontend_version == frontend_lock_version == app.version == "0.2.2"
    assert ALGORITHM_VERSION == f"sfe-proof-core/{app.version}"
