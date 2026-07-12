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


def build_manifest(
    certificate_id_value: str,
    input_snapshot: object,
    result_snapshot: object,
    algorithm_version: str,
    git_commit_sha: str,
    factor_set_version: str,
) -> dict:
    canonical_input = canonical_json(input_snapshot)
    canonical_result = canonical_json(result_snapshot)
    return {
        "certificate_id": certificate_id_value,
        "canonical_input": canonical_input,
        "canonical_result": canonical_result,
        "input_hash": hashlib.sha256(canonical_input.encode("utf-8")).hexdigest(),
        "result_hash": hashlib.sha256(canonical_result.encode("utf-8")).hexdigest(),
        "algorithm_version": algorithm_version,
        "git_commit_sha": git_commit_sha,
        "factor_set_version": factor_set_version,
    }


def verify_submitted_manifest(manifest: dict, expected: dict, input_snapshot: object | None = None, result_snapshot: object | None = None) -> dict:
    try:
        manifest_input = json.loads(manifest["canonical_input"])
        manifest_result = json.loads(manifest["canonical_result"])
    except (KeyError, TypeError, json.JSONDecodeError):
        return _verification(False, False, False, "invalid_manifest")
    canonical_match = canonical_json(manifest_input) == manifest["canonical_input"] and canonical_json(manifest_result) == manifest["canonical_result"]
    submitted_input = input_snapshot if input_snapshot is not None else manifest_input
    submitted_result = result_snapshot if result_snapshot is not None else manifest_result
    actual_input_hash = sha256(submitted_input)
    actual_result_hash = sha256(submitted_result)
    manifest_hashes_match = sha256(manifest_input) == manifest.get("input_hash") and sha256(manifest_result) == manifest.get("result_hash")
    metadata_match = all(manifest.get(key) == expected[key] for key in ("certificate_id", "input_hash", "result_hash", "algorithm_version", "git_commit_sha", "factor_set_version"))
    input_match = actual_input_hash == expected["input_hash"]
    result_match = actual_result_hash == expected["result_hash"]
    valid = canonical_match and manifest_hashes_match and metadata_match and input_match and result_match
    return _verification(valid, input_match, result_match, "valid" if valid else "invalid")


def _verification(valid: bool, input_match: bool, result_match: bool, status: str) -> dict:
    return {
        "status": status,
        "valid": valid,
        "input_hash_match": input_match,
        "result_hash_match": result_match,
        "boundary": "仅证明计算来源和文件完整性；不证明采样真实性、算法科学结论正确，也不等于第三方核证或碳信用。",
    }


def verify(input_snapshot: object, result_snapshot: object, expected_input_hash: str, expected_result_hash: str) -> dict:
    actual_input, actual_result = sha256(input_snapshot), sha256(result_snapshot)
    valid = actual_input == expected_input_hash and actual_result == expected_result_hash
    return {
        "valid": valid,
        "input_hash_match": actual_input == expected_input_hash,
        "result_hash_match": actual_result == expected_result_hash,
        "boundary": "仅证明计算来源和文件完整性；不证明采样真实性、算法科学结论正确，也不等于第三方核证或碳信用。",
    }
