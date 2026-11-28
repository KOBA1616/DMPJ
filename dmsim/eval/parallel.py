"""互換: プロセス並列の共通の口は dmsim.base.parallel（S0）に移した。"""
from ..base.parallel import default_workers, imap_ordered, map_ordered, strided_chunks  # noqa: F401
