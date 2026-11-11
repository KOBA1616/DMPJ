"""計画仕様 v0 のスケルトン（承認待ち。エンジン・カードデータには依存しない）。"""
from .combo_sequence import from_hunt_record, is_verified, register_verified
from .convert import from_loopspec, to_loopspec
from .registry import KINDS, ROLES, register_kind, register_role
from .spec import MIGRATIONS, SCHEMA_VERSION, PlanSpec, dump_jsonl, load_jsonl

__all__ = ["PlanSpec", "SCHEMA_VERSION", "MIGRATIONS", "dump_jsonl", "load_jsonl", "KINDS", "ROLES", "register_kind", "register_role",
           "from_loopspec", "to_loopspec", "from_hunt_record", "is_verified", "register_verified"]
