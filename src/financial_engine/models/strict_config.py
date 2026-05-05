from dataclasses import dataclass


@dataclass(frozen=True)
class StrictConfig:
    strict_mode: bool
    require_full_core_rows: bool
    disable_fallback_matching: bool
    disable_section_summation: bool
    require_identity_validation: bool


BASE_CONFIG = StrictConfig(
    strict_mode=False,
    require_full_core_rows=False,
    disable_fallback_matching=False,
    disable_section_summation=False,
    require_identity_validation=False,
)

STRICT_CONFIG = StrictConfig(
    strict_mode=True,
    require_full_core_rows=True,
    disable_fallback_matching=True,
    disable_section_summation=True,
    require_identity_validation=True,
)
