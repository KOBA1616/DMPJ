"""公平探索（情報水準「公平」）。山札・盾・相手の手札を観測外とし、多重集合から決定化する。

エンジンは編集しない。公開イベント（誰が何を見たか）の記録の形は別スレッドで確定中なので、
既知のカードは GameState.pub（Engine.note_public, PR #193）から導き、追加分を known 引数でも受ける。
"""
from .infoset import HIDDEN_ZONES, determinize, hidden_cids, known_from_pub

__all__ = ["HIDDEN_ZONES", "determinize", "hidden_cids", "known_from_pub"]
