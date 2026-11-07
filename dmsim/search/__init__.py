"""公平探索（情報水準「公平」）。山札・盾・相手の手札を観測外とし、多重集合から決定化する。

エンジンは編集しない。公開イベント（誰が何を見たか）の記録の形は別スレッドで確定中なので、
ここでは「既知のカード」を known 引数（cid の集合）で受ける。確定後に観測の取り出しだけ差し替える。
"""
from .infoset import HIDDEN_ZONES, determinize, hidden_cids

__all__ = ["HIDDEN_ZONES", "determinize", "hidden_cids"]
