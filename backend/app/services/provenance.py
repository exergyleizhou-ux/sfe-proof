PROVENANCE_WARNING = "第三方实验室送样检测，不等于第三方现场采样"


def warning_for(provenance_type: str) -> str | None:
    return PROVENANCE_WARNING if provenance_type == "submitted_to_third_party_lab" else None
