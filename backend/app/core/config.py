import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sfe-proof.db")
ALGORITHM_VERSION = "sfe-proof-core/0.2.1"
FACTOR_SET_VERSION = "demo-cn-screening-2026.1"
GIT_COMMIT_SHA = os.getenv("GIT_COMMIT_SHA", "local-uncommitted")
