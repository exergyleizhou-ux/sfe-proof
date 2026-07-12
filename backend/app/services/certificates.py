import hashlib
import json
from datetime import datetime, timezone


def canonical_json(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha256(data: object) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def certificate_id(input_hash: str, now: datetime | None = None) -> str:
    stamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%d")
    return f"SFE-{stamp}-{input_hash[:8].upper()}"


def verify(input_snapshot: object, result_snapshot: object, expected_input_hash: str, expected_result_hash: str) -> dict:
    actual_input, actual_result = sha256(input_snapshot), sha256(result_snapshot)
    valid = actual_input == expected_input_hash and actual_result == expected_result_hash
    return {
        "valid": valid,
        "input_hash_match": actual_input == expected_input_hash,
        "result_hash_match": actual_result == expected_result_hash,
        "boundary": "仅证明计算来源和文件完整性；不证明采样真实性、算法科学结论正确，也不等于第三方核证或碳信用。",
    }
