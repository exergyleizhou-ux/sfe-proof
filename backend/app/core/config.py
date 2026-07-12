import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sfe-proof.db")
ALGORITHM_VERSION = "sfe-proof-core/0.1.0"
FACTOR_SET_VERSION = "demo-cn-screening-2026.1"
