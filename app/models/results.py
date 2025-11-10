from pydantic import BaseModel
from typing import Optional, Dict, Any
from enum import Enum


class VerificationStatus(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    RISKY = "risky"
    UNKNOWN = "unknown"
    CATCH_ALL = "catch_all"
    DISPOSABLE = "disposable"
    ROLE_ACCOUNT = "role_account"


class VerificationResult(BaseModel):
    email: str
    status: VerificationStatus
    quality_score: int
    details: Dict[str, Any]
    is_verified: bool

    class Config:
        use_enum_values = True