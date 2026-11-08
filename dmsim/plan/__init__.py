"""計画仕様 v0 のスケルトン（承認待ち。エンジン・カードデータには依存しない）。"""
from .convert import from_loopspec, to_loopspec
from .registry import KINDS, ROLES, register_kind, register_role
from .spec import SCHEMA_VERSION, PlanSpec

__all__ = ["PlanSpec", "SCHEMA_VERSION", "KINDS", "ROLES", "register_kind", "register_role",
           "from_loopspec", "to_loopspec"]
